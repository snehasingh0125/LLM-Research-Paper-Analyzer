# 📚 LLM Research Paper Analyzer

An AI-powered web application that enables users to upload, analyze, compare, and interact with research papers using Large Language Models (LLMs). The application leverages Retrieval-Augmented Generation (RAG) and semantic search to provide context-aware answers, summaries, and document comparisons through an intuitive web interface.

---

## 🚀 Features

- 📄 Upload and analyze research papers (PDF)
- 🤖 AI-powered question answering from uploaded documents
- 📝 Automatic research paper summarization
- 🔍 Semantic search using FAISS vector indexing
- 📊 Compare multiple research papers
- 📚 Context-aware Retrieval-Augmented Generation (RAG)
- 🌐 Interactive Django web interface
- 📂 Automatic document indexing and storage

---

## 🛠️ Tech Stack

- Python
- Django
- FAISS
- Sentence Transformers
- Hugging Face Transformers
- SQLite
- HTML
- CSS
- JavaScript

---

## 📂 Project Structure

```
LLM-Research-Paper-Analyzer/
│
├── README.md
├── requirements.txt
├── .gitignore
│
└── rspaper/
    ├── manage.py
    ├── app/
    ├── media/
    ├── static/
    ├── templates/
    └── rspaper/
```

---

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/LLM-Research-Paper-Analyzer.git
```

### 2. Navigate to the project

```bash
cd LLM-Research-Paper-Analyzer/rspaper
```

### 3. Install dependencies

```bash
pip install -r ../requirements.txt
```

### 4. Apply migrations

```bash
python manage.py migrate
```

### 5. Run the application

```bash
python manage.py runserver
```

Open your browser and visit:

```
http://127.0.0.1:8000
```

---

## 📖 How It Works

1. Upload one or more research papers in PDF format.
2. The application extracts and processes the document content.
3. Research papers are converted into vector embeddings.
4. FAISS performs semantic retrieval over indexed documents.
5. Retrieved context is passed to the language model.
6. Users can:
   - Ask questions
   - Generate summaries
   - Compare research papers
   - Retrieve relevant information efficiently

---

## 📸 Screenshots

Add screenshots here after uploading them.

Example:

```
assets/
    home.png
    upload.png
    summary.png
    comparison.png
```

---

## 🔮 Future Improvements

- Support additional document formats
- Multi-user authentication
- Cloud deployment
- Citation generation
- Research recommendation system
- Chat history
- OCR support for scanned PDFs

---

## 👩‍💻 Author

**Sneha Singh**

---

## ⭐ If you found this project useful, consider giving it a star!
