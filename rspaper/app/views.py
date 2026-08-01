import os
import io
import uuid
import json
import base64
import numpy as np
import requests
from google import genai
from google.genai import types
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.utils.crypto import get_random_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.db import transaction

import fitz  # PyMuPDF
from PIL import Image

from .models import (
    ResearchPaper,
    PaperSummary,
    OTPVerification,
    PaperComparison,
    VoiceCommandLog,
    SlideDeck,
    SearchQuery,
    PaperEmbedding,
)

User = get_user_model()
# Add this to your views.py or a new helpers.py file

import faiss # Make sure to import faiss at the top

def find_similar_papers(query_text, top_k=5, user=None):

    faiss_path = os.path.join(settings.MEDIA_ROOT, "faiss.index")
    meta_path = os.path.join(settings.MEDIA_ROOT, "faiss_meta.json")
    if not os.path.exists(faiss_path) or not os.path.exists(meta_path):
        print("FAISS index not found. Please upload a paper first.")
        return []

    try:
        index = faiss.read_index(faiss_path)
        with open(meta_path, "r") as f:
            meta = json.load(f)
        
        db_paper_ids = meta.get("ids", [])
        query_vector = create_embedding(query_text)
        query_vector_reshaped = query_vector.reshape(1, -1).astype('float32')
        distances, indices = index.search(query_vector_reshaped, top_k)
        found_paper_ids = [db_paper_ids[i] for i in indices[0]]
        from django.db.models import Case, When
        
        preserved_order = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(found_paper_ids)])
        
        similar_papers = ResearchPaper.objects.filter(id__in=found_paper_ids, user=user).order_by(preserved_order)
        return list(similar_papers)

    except Exception as e:
        print(f"An error occurred during FAISS search: {e}")
        return []
# -------------------------
# Helper utilities
# -------------------------
def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def extract_pdf_text_and_images(pdf_path, paper):
    text_pages = []
    images_info = []
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        return {"text": "", "images": [], "error": f"Could not open PDF: {e}"}

    media_dir = os.path.join(settings.MEDIA_ROOT, "papers", str(paper.id), "images")
    ensure_dir(media_dir)

    for page_number in range(len(doc)):
        page = doc.load_page(page_number)
        page_text = page.get_text("text") or ""
        text_pages.append(page_text)

        image_list = page.get_images(full=True)
        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image.get("image")
            image_ext = base_image.get("ext", "png")
            if image_bytes:
                image_filename = f"{uuid.uuid4().hex}_p{page_number +1}_{img_index}.{image_ext}"
                image_path = os.path.join(media_dir, image_filename)
                with open(image_path, "wb") as f:
                    f.write(image_bytes)
                images_info.append({
                    "page": page_number + 1,
                    "path": os.path.join("papers", str(paper.id), "images", image_filename)
                })
    full_text = "\n\n".join([p.strip() for p in text_pages if p.strip()])
    return {"text": full_text, "images": images_info, "error": None}
def call_gemini_for_metadata(text):
    """
    A dedicated, lightweight call to Gemini to extract structured metadata.
    """
    api_key = getattr(settings, "GOOGLE_API_KEY", None) or os.getenv("GOOGLE_API_KEY")
    model_name = "gemini-2.5-flash"
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY not configured")

    client = genai.Client(api_key=api_key)

    # We only need the first ~4000 characters to find the metadata
    prompt_text = text[:4000]

    prompt = f"""
    From the following text from the first page of a research paper, extract the title, authors, and abstract.
    Provide ONLY a single, valid JSON object with the keys "title", "authors", and "abstract".
    The authors should be a single string (e.g., "John Doe, Jane Smith").

    Text:
    ---
    {prompt_text}
    ---
    """
    response = client.models.generate_content(
        model=model_name,
        contents=[prompt],
    )

    response_text = response.text.strip()
    # The cleanup logic for backticks is still a good fallback
    if response_text.startswith("```"):
        # Remove the first line which is often ```json
        response_text = response_text.split("\n", 1)[1]
        if response_text.endswith("```"):
            # Remove the last line which is often ```
            response_text = response_text.rsplit("\n", 1)[0]

    try:
        data = json.loads(response_text)
        return {
            "title": data.get("title", "Untitled"),
            "authors": data.get("authors", ""),
            "abstract": data.get("abstract", "")
        }
    except (json.JSONDecodeError, AttributeError):
        return {"title": "Untitled", "authors": "", "abstract": ""}
def call_gemini_summary(text, title=None, max_tokens=15000): # Increased tokens for better results
    api_key = getattr(settings, "GOOGLE_API_KEY", None) or os.getenv("GOOGLE_API_KEY")
    model_name = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash") # Updated to a modern model name
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY not configured in settings or env")

    client = genai.Client(api_key=api_key)

    # Improved prompt for more reliable JSON output
    prompt = f"""
    Title: {title}

    Document Text: {text}

    Please analyze the provided document text and return ONLY a single, valid JSON object.
    Do not include any explanatory text before or after the JSON.
    The JSON object must be enclosed in ```json ... ``` and have the following keys:
    - "summary": (string) A concise summary of the paper.
    - "findings": (list of strings) The key findings or results as a list of bullet points.
    - "methodology": (string) A brief description of the methodology used.
    - "gaps": (list of strings) Any identified research gaps or areas for future work as a list of bullet points.
    """

    contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]

    # --- MODIFICATION: Replaced streaming with a single, non-streaming call ---
    response = client.models.generate_content(
        model=model_name,
        contents=contents
    )

    # --- User Request: Print the raw text received from the API ---
    response_text = response.text.strip()
    # The cleanup logic for backticks is still a good fallback
    if response_text.startswith("```"):
        # Remove the first line which is often ```json
        response_text = response_text.split("\n", 1)[1]
        if response_text.endswith("```"):
            # Remove the last line which is often ```
            response_text = response_text.rsplit("\n", 1)[0]

    try:
        # --- User Request: Convert the cleaned text to JSON ---
        parsed = json.loads(response_text)
        
        return {
            "summary": parsed.get("summary", "Summary not found in response."),
            "findings": parsed.get("findings", []),
            "methodology": parsed.get("methodology", "Methodology not found in response."),
            "gaps": parsed.get("gaps", []),
        }
    except json.JSONDecodeError as e:
        print(f"Error: Failed to decode JSON. Error: {e}")
        # Fallback to returning the raw text if JSON parsing fails
        return {"summary": response_text, "findings": [], "methodology": "", "gaps": []}
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return {"summary": "An error occurred during processing.", "findings": [], "methodology": "", "gaps": []}


def create_embedding(text):
    api_key = getattr(settings, "GOOGLE_API_KEY", None) or os.getenv("GOOGLE_API_KEY")
    emb_model = getattr(settings, "GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")  
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY not configured in settings or env")

    client = genai.Client(api_key=api_key)

    # Gemini embedding model accepts a list of texts
    resp = client.models.embed_content(
        model=emb_model,
        contents=[text],  # truncate to safe size
    )

    if not hasattr(resp, "embeddings") or not resp.embeddings:
        raise RuntimeError("No embeddings returned from Gemini")

    # Take the first embedding
    vec = resp.embeddings[0].values
    return np.array(vec, dtype=np.float32)



def save_embedding_to_model(paper, vector, model_used="gemini-2.5-pro"):
    b = vector.tobytes()
    PaperEmbedding.objects.create(paper=paper, vector=b, model_used=model_used)
def update_faiss_index():
    try:
        import faiss
    except ImportError:
        return  # faiss not available; skip

    embeddings = PaperEmbedding.objects.all()
    if embeddings.count() == 0:
        return

    vecs = []
    ids = []

    for e in embeddings:
        try:
            arr = np.frombuffer(e.vector, dtype=np.float32)
            if arr.size == 0:
                continue
            vecs.append(arr)
            ids.append(e.paper.id)
        except Exception as ex:
            print(f"Skipping embedding {e.id}: {ex}")

    if not vecs:
        return

    dim = vecs[0].shape[0]
    xb = np.vstack(vecs).astype("float32")

    # Build FAISS index
    index = faiss.IndexFlatL2(dim)
    index.add(xb)

    # Store mapping (position → paper.id)
    meta = {"ids": ids}

    faiss_path = os.path.join(settings.MEDIA_ROOT, "faiss.index")
    meta_path = os.path.join(settings.MEDIA_ROOT, "faiss_meta.json")

    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

    faiss.write_index(index, faiss_path)
    with open(meta_path, "w") as f:
        json.dump(meta, f)

    print(f"FAISS index updated with {len(ids)} embeddings.")



# -------------------------
# Views (existing flows remain)
# -------------------------
def index(req):
    return render(req, "index.html")


def signup_view(request):
    if request.user.is_authenticated:
        return redirect('/dashboard')
    if request.method == "POST":
        email = request.POST.get("email")
        username = request.POST.get("username")
        password = request.POST.get("password")
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return redirect("signup")
        user = User.objects.create_user(username=username, email=email, password=password, is_active=False)
        otp_code = get_random_string(6, "0123456789")
        OTPVerification.objects.create(user=user, otp_code=otp_code)
        send_mail("Your OTP Code", f"OTP: {otp_code}", settings.DEFAULT_FROM_EMAIL, [email])
        messages.success(request, "Check your email for OTP.")
        return redirect("verify_otp")
    return render(request, "signup.html")


def verify_otp_view(request):
    if request.user.is_authenticated:
        return redirect('/dashboard')
    if request.method == "POST":
        email = request.POST.get("email")
        otp = request.POST.get("otp")
        try:
            user = User.objects.get(email=email)
            otp_obj = OTPVerification.objects.filter(user=user, otp_code=otp, is_verified=False).last()
            if otp_obj:
                otp_obj.is_verified = True
                otp_obj.save()
                user.is_active = True
                user.is_verified = True
                user.save()
                messages.success(request, "Account verified. You can log in now.")
                return redirect("login")
            else:
                messages.error(request, "Invalid OTP.")
        except User.DoesNotExist:
            messages.error(request, "Invalid email.")
    return render(request, "verify_otp.html")


def login_view(request):
    if request.user.is_authenticated:
        return redirect('/dashboard')
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            next_url = request.GET.get("next") or "dashboard"
            return redirect(next_url)
        else:
            messages.error(request, "Invalid credentials.")
    return render(request, "login.html")


def logout_view(request):
    logout(request)
    return redirect("login")


def password_reset_request_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        try:
            user = User.objects.get(email=email)
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            reset_link = request.build_absolute_uri(f"/password-reset/{uid}/{token}/")
            send_mail("Password Reset", f"Reset your password: {reset_link}", settings.DEFAULT_FROM_EMAIL, [email])
            messages.success(request, "Password reset link sent.")
        except User.DoesNotExist:
            messages.error(request, "No account with that email.")
    return render(request, "password_reset_request.html")


def password_reset_confirm_view(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (User.DoesNotExist, ValueError, TypeError):
        user = None
    if user and default_token_generator.check_token(user, token):
        if request.method == "POST":
            password = request.POST.get("password")
            user.set_password(password)
            user.save()
            messages.success(request, "Password reset successful.")
            return redirect("login")
        return render(request, "password_reset_confirm.html")
    else:
        messages.error(request, "Invalid link.")
        return redirect("password_reset_request")


@login_required
def dashboard_view(request):
    papers = ResearchPaper.objects.filter(user=request.user)
    return render(request, "dashboard.html", {"papers": papers})
@login_required
def upload_paper_view(request):
    if request.method == "POST":
        pdf_file = request.FILES.get("pdf_file")
        if not pdf_file:
            messages.error(request, "No PDF file was selected.")
            return redirect("upload_paper")
            
        with transaction.atomic():
            # Create a temporary paper object to associate the file with
            # We will update it with AI-extracted metadata shortly
            temp_title = getattr(pdf_file, "name", "Processing...")
            paper = ResearchPaper.objects.create(user=request.user, title=temp_title, pdf_file=pdf_file)
            
            paper_path = os.path.join(settings.MEDIA_ROOT, paper.pdf_file.name)
            extraction = extract_pdf_text_and_images(paper_path, paper)
            
            if extraction.get("error"):
                messages.error(request, f"Extraction error: {extraction['error']}")
                return redirect("upload_paper") # Transaction will roll back

            paper.extracted_text = extraction["text"]
            paper.metadata_json = {"images": extraction["images"]}

            # --- FIX: Step 1 - Call AI for Metadata ---
            if paper.extracted_text:
                metadata = call_gemini_for_metadata(paper.extracted_text)
                paper.title = metadata.get("title", temp_title)
                paper.authors = metadata.get("authors", "Authors not found")
                paper.abstract = metadata.get("abstract", "Abstract not found")
            
            paper.save() # Save the extracted metadata

            # --- Step 2 - Call AI for Full Summary (as before) ---
            try:
                llm_out = call_gemini_summary(paper.extracted_text, title=paper.title)
            except Exception as e:
                messages.warning(request, f"LLM summary failed during upload: {e}")
                llm_out = {"summary": "LLM summary could not be generated.", "findings": [], "methodology": "", "gaps": []}

            findings_str = "\n".join(f"• {item}" for item in llm_out.get("findings", []))
            gaps_str = "\n".join(f"• {item}" for item in llm_out.get("gaps", []))

            PaperSummary.objects.update_or_create(
                paper=paper,
                defaults={
                    "summary_text": llm_out.get("summary", ""),
                    "key_findings": findings_str,
                    "methodology": llm_out.get("methodology", ""),
                    "gap_analysis": gaps_str,
                },
            )

            # Embeddings and FAISS update
            try:
                emb_vec = create_embedding(paper.extracted_text[:8192])
                save_embedding_to_model(paper, emb_vec)
                update_faiss_index()
            except Exception as e:
                messages.info(request, f"Embedding or FAISS update skipped: {e}")

            messages.success(request, f"Paper '{paper.title}' uploaded and analyzed.")
            return redirect("dashboard")
            
    return render(request, "upload_paper.html")


@login_required
def paper_detail_view(request, paper_id):
    paper = get_object_or_404(ResearchPaper, id=paper_id, user=request.user)
    summary = getattr(paper, "summary", None)
    return render(request, "paper_detail.html", {"paper": paper, "summary": summary})

@login_required
def summarize_paper_view(request, paper_id):
    paper = get_object_or_404(ResearchPaper, id=paper_id, user=request.user)
    summary = PaperSummary.objects.filter(paper=paper).first()
    
    if summary and summary.summary_text and "could not be generated" not in summary.summary_text:
        messages.info(request, "Displaying existing summary.")
        return render(request, "paper_summary.html", {"paper": paper, "summary": summary})

    messages.info(request, "Generating new summary...")
    try:
        llm_out = call_gemini_summary(paper.extracted_text or "", title=paper.title)
        
        # Convert list outputs to strings for saving in TextField
        findings_str = "\n".join(f"• {item}" for item in llm_out.get("findings", []))
        gaps_str = "\n".join(f"• {item}" for item in llm_out.get("gaps", []))

        # Update or create the summary object in the database
        summary, _ = PaperSummary.objects.update_or_create(
            paper=paper,
            defaults={
                "summary_text": llm_out.get("summary", ""),
                "key_findings": findings_str,
                "methodology": llm_out.get("methodology", ""),
                "gap_analysis": gaps_str,
            },
        )
        messages.success(request, "Summary generated successfully.")
        
    except Exception as e:
        messages.error(request, f"LLM summarize error: {e}")
        # Create a placeholder summary to show the error
        summary, _ = PaperSummary.objects.update_or_create(
            paper=paper,
            defaults={"summary_text": f"Failed to generate summary: {e}"}
        )
    
    return render(request, "paper_summary.html", {"paper": paper, "summary": summary})

def call_gemini_for_comparison(paper_data_chunks):
    """
    Takes pre-formatted chunks of paper summaries and asks the LLM
    to generate a final comparative analysis in Markdown.
    """
    api_key = getattr(settings, "GOOGLE_API_KEY", None) or os.getenv("GOOGLE_API_KEY")
    model_name = "gemini-2.5-flash"
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY not configured")

    client = genai.Client(api_key=api_key)
    
    # Combine all the individual paper data into one large context string
    full_context = "\n\n".join(paper_data_chunks)

    prompt = f"""
    You are a highly skilled research analyst. Your task is to analyze and compare the following research papers based on their provided summaries, findings, and identified gaps.

    Here is the structured data for the papers:
    {full_context}

    ---
    **INSTRUCTIONS:**

    Generate a comprehensive comparative analysis in **Markdown format**. Your analysis must include:
    1.  **Comparative Table:** Create a Markdown table that contrasts the key aspects of each paper side-by-side. Columns should include 'Paper Title', 'Methodology', and 'Key Findings'.
    2.  **Synthesis Summary:** After the table, write a paragraph summarizing the core similarities and differences in their approaches and conclusions.
    3.  **Combined Gaps & Future Work:** Conclude with a bulleted list analyzing the combined research gaps. Suggest potential future research directions that could build upon the work of all presented papers.

    Return ONLY the Markdown content. Do not include any other text or introductions.
    """
    
    response = client.models.generate_content(model=model_name, contents=[prompt])
    return response.text
@login_required
def compare_papers_view(request, paper_id):
    main_paper = get_object_or_404(ResearchPaper, id=paper_id, user=request.user)
    other_ids = request.GET.getlist("other")
    
    papers_to_compare = {main_paper.id: main_paper}
    other_papers = ResearchPaper.objects.filter(id__in=other_ids, user=request.user)
    for p in other_papers:
        papers_to_compare[p.id] = p
    
    # --- NEW LOGIC: Gather existing summaries first ---
    paper_data_chunks = []
    for paper in papers_to_compare.values():
        # Check if a summary already exists for the paper
        summary = PaperSummary.objects.filter(paper=paper).first()
        
        chunk = f"### Paper Title: {paper.title}\n\n"
        
        if summary:
            # If summary exists, use the structured data
            chunk += f"**Summary:** {summary.summary_text}\n\n"
            chunk += f"**Key Findings:**\n{summary.key_findings}\n\n"
            chunk += f"**Methodology:** {summary.methodology}\n\n"
            chunk += f"**Identified Gaps:**\n{summary.gap_analysis}\n"
        elif paper.abstract:
            # Fallback to using the abstract if no summary is available
            chunk += f"**Abstract:** {paper.abstract}\n\n"
            chunk += "*Note: A detailed summary was not available for this paper. Analysis is based on the abstract.*"
        else:
            # Fallback if there's no data at all
            chunk += "*Note: No summary or abstract was available for analysis.*"
        
        paper_data_chunks.append(chunk)

    try:
        # Pass the compiled, high-quality data to our new function
        comparison_result_md = call_gemini_for_comparison(paper_data_chunks)
    except Exception as e:
        comparison_result_md = f"### Comparison Failed\n\nAn error occurred while generating the analysis: {e}"

    comparison = PaperComparison.objects.create(
        user=request.user, 
        comparison_result=comparison_result_md
    )
    comparison.papers.add(*papers_to_compare.keys())
    
    return render(request, "paper_compare.html", {"comparison": comparison})

@login_required
def search_papers_view(request):
    query = request.GET.get("q", "").strip()
    results = []

    if query:
        # Perform semantic search using our new function
        results = find_similar_papers(query, top_k=10, user=request.user)
        print(results)
        # Log the search query
        SearchQuery.objects.create(
            user=request.user, 
            query_text=query, 
            results={"count": len(results), "ids": [p.id for p in results]}
        )
        
    return render(request, "search_results.html", {"results": results, "query": query})

@login_required
def select_comparison_papers_view(request, paper_id):
    """
    Renders a page allowing the user to select which papers to compare against the main one.
    """
    main_paper = get_object_or_404(ResearchPaper, id=paper_id, user=request.user)
    other_papers = ResearchPaper.objects.filter(user=request.user).exclude(id=paper_id)
    
    context = {
        'main_paper': main_paper,
        'other_papers': other_papers,
    }
    return render(request, 'select_comparison.html', context)
@login_required
def voice_command_view(request):
    if request.method == "POST":
        command = request.POST.get("command")
        # For advanced voice processing you can forward 'command' to Gemini for an action
        try:
            llm_out = call_gemini_summary(command, title="Voice Command", max_tokens=400)
            response = llm_out.get("summary", "Processed")
        except Exception as e:
            response = f"Error: {e}"
        VoiceCommandLog.objects.create(user=request.user, command_text=command, response_text=response)
        return JsonResponse({"response": response})
    return render(request, "voice_command.html")

@login_required
def generate_slides_view(request, paper_id):
    paper = get_object_or_404(ResearchPaper, id=paper_id, user=request.user)
    
    # Check if slides have already been generated to avoid costly re-generation
    slide_deck = SlideDeck.objects.filter(paper=paper).first()
    if slide_deck and "beamer_code" in slide_deck.slides_json:
        messages.info(request, "Displaying previously generated slides.")
        return render(request, "slides.html", {"paper": paper, "slide_deck": slide_deck})

    messages.info(request, "Generating new presentation slides with AI, please wait...")
    try:
        # Call our new function with the paper's full text
        latex_code = call_gemini_for_beamer_slides(
            title=paper.title,
            authors=paper.authors or "Authors not specified",
            full_text=paper.extracted_text
        )
    except Exception as e:
        messages.error(request, f"Failed to generate slides: {e}")
        latex_code = f"% ---\n% Error generating LaTeX code:\n% {e}\n% ---"

    # Save the generated code into our model
    # We store it in a JSON field for consistency, but it's just a string
    slide_deck, created = SlideDeck.objects.update_or_create(
        paper=paper,
        defaults={"slides_json": {"beamer_code": latex_code}}
    )

    return render(request, "slides.html", {"paper": paper, "slide_deck": slide_deck})




def call_gemini_for_beamer_slides(title, authors, full_text):
    """
    Takes the full text of a paper and asks a powerful LLM to generate a
    complete LaTeX Beamer presentation.
    """
    api_key = getattr(settings, "GOOGLE_API_KEY", None) or os.getenv("GOOGLE_API_KEY")
    # A powerful model is required for this complex task
    model_name = "gemini-2.5-pro" 
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY not configured")

    client = genai.Client(api_key=api_key)

    prompt = f"""
    You are an expert academic assistant specializing in LaTeX and Beamer presentations.
    Your task is to generate a complete, compilable LaTeX Beamer presentation code from the full text of a research paper.

    Paper Title: {title}
    Paper Authors: {authors}
    Full Text of the Paper:
    ---
    {full_text}
    ---

    INSTRUCTIONS:
    1.  Create a concise but informative presentation of about 6-8 slides.
    2.  The structure MUST be: Title Page, Introduction/Abstract, Methodology, Key Results (this can be 1-3 slides), Conclusion/Future Work, and a final "Thank You & Questions" slide.
    3.  For each content slide, extract the most critical information from the full text and present it as 3-5 concise bullet points using the 'itemize' environment.
    4.  The output MUST be ONLY raw, valid LaTeX code. Do not include ```latex, explanations, or any text other than the compilable code itself.
    5.  Ensure the document is a complete and valid Beamer document, starting with `\\documentclass{{beamer}}` and ending with `\\end{{document}}`.
    """
    
    response = client.models.generate_content(model=model_name, contents=[prompt])
    
    # Clean the response to remove potential markdown code blocks
    raw_code = response.text.strip()
    if raw_code.startswith("```"):
        raw_code = raw_code.split("\n", 1)[1]
        if raw_code.endswith("```"):
            raw_code = raw_code.rsplit("\n", 1)[0]
    
    return raw_code