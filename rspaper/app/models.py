from django.db import models
from django.contrib.auth.models import AbstractUser
class User(AbstractUser):
    """
    Custom user model extending Django's AbstractUser.
    Provides flexibility for research-specific fields.
    """
    institution = models.CharField(max_length=255, blank=True, null=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.username


class OTPVerification(models.Model):
    """
    Stores OTPs for signup/login verification.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otps")
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"OTP for {self.user.username} - {self.otp_code}"
class ResearchPaper(models.Model):
    """
    Represents an uploaded research paper (PDF).
    Stores metadata, extracted text, and links to the user.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="papers")
    title = models.CharField(max_length=500)
    authors = models.TextField(blank=True, null=True)
    abstract = models.TextField(blank=True, null=True)
    pdf_file = models.FileField(upload_to="papers/")
    extracted_text = models.TextField(blank=True, null=True)
    metadata_json = models.JSONField(blank=True, null=True)  # raw parsed metadata
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
class PaperSummary(models.Model):
    """
    Stores LLM-generated outputs for a research paper.
    """
    paper = models.OneToOneField(
        ResearchPaper, on_delete=models.CASCADE, related_name="summary"
    )
    summary_text = models.TextField()
    key_findings = models.TextField(blank=True, null=True)
    methodology = models.TextField(blank=True, null=True)
    gap_analysis = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Summary of {self.paper.title}"


class PaperEmbedding(models.Model):
    """
    Stores embeddings for semantic search (FAISS index is local).
    Keeping metadata about model used and vector bytes.
    """
    paper = models.ForeignKey(
        ResearchPaper, on_delete=models.CASCADE, related_name="embeddings"
    )
    vector = models.BinaryField()  # serialized embedding vector
    model_used = models.CharField(max_length=100, default="gemini-2.5-pro")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Embedding for {self.paper.title}"


class SearchQuery(models.Model):
    """
    Logs user search queries and results for dashboard history.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="searches")
    query_text = models.TextField()
    results = models.JSONField()  # store paper IDs + similarity scores
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Search by {self.user.username} - {self.query_text[:50]}"


class PaperComparison(models.Model):
    """
    Stores LLM-powered comparison between multiple research papers.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comparisons")
    papers = models.ManyToManyField(ResearchPaper, related_name="comparisons")
    comparison_result = models.TextField()  # LLM output (commonalities, differences, gaps)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comparison by {self.user.username} at {self.created_at}"



class VoiceCommandLog(models.Model):
    """
    Stores voice assistant commands given from the dashboard.
    For conversational Jarvis-style interaction.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="voice_logs")
    command_text = models.TextField()
    response_text = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Voice Command by {self.user.username} at {self.created_at}"


class SlideDeck(models.Model):
    """
    Stores auto-generated slides (from LLM summaries).
    Could export to PowerPoint or PDF later.
    """
    paper = models.ForeignKey(
        ResearchPaper, on_delete=models.CASCADE, related_name="slides"
    )
    slides_json = models.JSONField()  # structured data for slides (titles, bullet points)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Slides for {self.paper.title}"
