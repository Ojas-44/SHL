# SHL Assessment Recommender

A conversational recommendation system that suggests relevant SHL assessments based on hiring requirements provided by recruiters.

## Project Overview

This project uses semantic search and AI-powered reasoning to recommend suitable SHL assessments for different job roles, experience levels, and hiring needs.

For example:

- Java Developer (4 years experience)
- Data Scientist
- Sales Executive
- Graduate Hiring
- Leadership Roles

The system retrieves relevant assessments from the SHL catalog and generates recommendations through a conversational interface.

---

## Features

- Conversational hiring assistant
- SHL assessment recommendations
- Semantic search using FAISS
- Sentence Transformer embeddings
- Gemini-powered response generation
- FastAPI backend
- Swagger API documentation

---

## Tech Stack

- Python
- FastAPI
- FAISS
- Sentence Transformers
- Google Gemini API
- Uvicorn

---

## Project Structure

```text
SHL/
│
├── services/
├── app.py
├── main.py
├── catalog.json
├── catalog_raw.txt
├── clean_catalog.json
├── test_retrieval.py
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## How It Works

1. User provides hiring requirements.
2. Query is converted into embeddings.
3. FAISS retrieves the most relevant assessments.
4. Gemini analyzes retrieved results.
5. Final recommendations are returned with explanations.

---

## API Endpoints

### Health Check

```http
GET /health
```

### Chat Endpoint

```http
POST /chat
```

Example Request:

```json
{
  "messages": [
    {
      "role": "user",
      "content": "I am hiring a Java developer with 4 years experience"
    }
  ]
}
```

---

## Live Deployment

### API Base URL

https://shl-production-4363.up.railway.app

### Swagger Documentation

https://shl-production-4363.up.railway.app/docs

---

## Running Locally

Install dependencies:

```bash
pip install -r requirements.txt
```

Build the FAISS index:

```bash
python app.py --build
```

Run the application:

```bash
uvicorn app:app --reload
```

---

## Future Improvements

- Better assessment reranking
- Multi-turn recruiter conversations
- Improved recommendation accuracy
- Frontend dashboard
- Assessment comparison support

---

## Author

Ojas

B.Tech CSE (AI & ML)
