# ResearchXplain: AI-Powered Research Paper Analysis Platform

**Live Application Link: [https://research.xplainnn.com/](https://research.xplainnn.com/)**

[](https://www.python.org/)
[](https://www.djangoproject.com/)
[](https://opensource.org/licenses/MIT)

ResearchXplain is a sophisticated web platform designed to accelerate the academic research process. By leveraging the power of large language models (Google's Gemini) and high-performance vector search (FAISS), it transforms static PDF research papers into a dynamic, searchable, and interconnected knowledge base. This tool empowers researchers, students, and professionals to rapidly understand complex topics, identify research gaps, and discover relevant literature with unparalleled efficiency.

-----

## Project Demo
The project is available at [https://research.xplainnn.com/](https://research.xplainnn.com/)


-----

## Core Features

This platform provides a suite of powerful tools to streamline the research workflow from discovery to analysis.

### 📄 **1. Paper Upload & Intelligent Content Extraction**

  * **Seamless PDF Uploads:** A user-friendly web interface allows for easy uploading of research papers.
  * **Automated Text Parsing:** The system utilizes PyMuPDF to robustly extract clean, readable text from complex, multi-column academic PDFs.
  * **AI-Powered Metadata Extraction:** A dedicated call to the Gemini-Flash model intelligently analyzes the first page of each document to automatically identify and populate key metadata, including the **Title**, **Authors**, and **Abstract**.

### 🧠 **2. LLM-Powered Summarization & Analysis**

  * **Concise Summaries:** The full text of each paper is processed by the Gemini-Pro model to generate a comprehensive yet concise summary, capturing the core essence of the research.
  * **Structured Data Extraction:** The platform goes beyond simple summarization by extracting structured insights, including:
      * **Key Findings:** A bulleted list of the main contributions and results.
      * **Methodology:** A clear description of the research methods employed.

### 🗺️ **3. Advanced Research Gap Analysis**

  * **AI-Driven Insights:** The LLM is prompted to critically analyze the paper's text to identify stated limitations and potential unexplored areas.
  * **Future Work Suggestions:** The system automatically generates a list of potential future work directions, providing a valuable starting point for new research initiatives.

### 🔍 **4. High-Performance Semantic Search**

  * **Beyond Keywords:** Traditional keyword search is replaced by a state-of-the-art semantic search engine. The system understands the *meaning* and *context* of your query, not just the words.
  * **Vector-Based Discovery:** Powered by Google's embedding models and a FAISS index, the search functionality finds the most conceptually similar papers, even if they don't share the exact keywords.

-----

## Extra Features

### **Multi-Paper Comparative Analysis**

  * Select two or more papers from your library for a head-to-head comparison.
  * The system gathers the pre-generated summaries and findings for the selected papers.
  * A final, synthesizing prompt is sent to the Gemini-Pro model, which generates a rich, **Markdown-formatted report** comparing the papers' methodologies, findings, and identifying overlapping or unique research gaps.

### **Automatic Slide Deck Generation**

  * Instantly generate a presentation from any research paper with a single click.
  * The system leverages the Gemini-Pro model to read the paper's full text and generate a complete, compilable **LaTeX Beamer presentation**.
  * The generated `.tex` code is displayed in the UI with a "Copy to Clipboard" feature, ready to be used in any LaTeX editor.

-----

## How It Works: The Technical Architecture

The platform's intelligence is built on a multi-step data processing pipeline.

1.  **Ingestion & Parsing:** When a user uploads a PDF, Django saves the file. The **PyMuPDF** library is used to extract the raw text content page by page.

2.  **Metadata & Summarization (Two-Step AI Call):**

      * **Step 1 (Metadata):** The text from the first page is sent to the fast and efficient **Gemini-Flash** model with a specific prompt to extract the Title, Authors, and Abstract in a structured JSON format. This data populates the primary model fields.
      * **Step 2 (Analysis):** The full extracted text is sent to the more powerful **Gemini-Pro** model. This call generates the detailed summary, key findings, methodology, and research gaps.

3.  **Embedding & Indexing:**

      * The full extracted text is passed to **Google's `embedding-001` model**, which converts the entire document into a high-dimensional vector (an embedding) that represents its semantic meaning.
      * This vector is stored in the database and, crucially, is added to a local **FAISS (Facebook AI Similarity Search) index**. FAISS is a library optimized for extremely fast similarity searches among millions of vectors.

4.  **Semantic Search Execution:**

      * When a user enters a search query (e.g., "novel techniques for battery degradation"), that query is also converted into a vector using the same embedding model.
      * This query vector is then used to search the FAISS index. FAISS returns the IDs of the most similar paper vectors from the database, ranked by relevance.
      * The application then fetches the corresponding paper objects from the database and displays them to the user.

-----

## Tech Stack

| Category      | Technology                                                                                                  |
|---------------|-------------------------------------------------------------------------------------------------------------|
| **Backend** | Python, Django                                                                                              |
| **AI & ML** | Google Generative AI (Gemini 1.5 Pro & Flash), FAISS, PyMuPDF, NumPy                                          |
| **Frontend** | HTML, Tailwind CSS, JavaScript, Marked.js (for client-side Markdown rendering)                              |
| **Database** | SQLite (for development), PostgreSQL (recommended for production)                                           |

-----

## Setup and Local Installation

To run this project locally, follow these steps:

1.  **Clone the Repository**


2.  **Create a Virtual Environment**

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install Dependencies**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables**

      * Create a `.env` file in the project's root directory.
      * Add your Google Generative AI API key to this file:
        ```env
        GOOGLE_API_KEY="YOUR_API_KEY_HERE"
        ```

5.  **Run Database Migrations**

    ```bash
    python manage.py migrate
    ```

6.  **Create a Superuser**

    ```bash
    python manage.py createsuperuser
    ```

7.  **Run the Development Server**

    ```bash
    python manage.py runserver
    ```

    The application will be available at `http://127.0.0.1:8000`.

-----

## Author

  * **Ojas Gupta**
  * **Email:** [gupta.ojas.27@gmail.com](mailto:gupta.ojas.27@gmail.com)

-----

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.