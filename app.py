
import sys
from typing import List, Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from services.catalog_loader import load_and_parse_catalog
from services.embeddings import build_and_save_index
from services.retriever import Retriever
from services.chat_agent import ChatAgent

app = FastAPI(
    title="SHL Assessment Recommender",
    description="Conversational SHL Assessment Recommendation Service",
    version="1.0.0",
)

retriever = None
agent = None


@app.on_event("startup")
def startup_event():
    global retriever, agent

    try:
        retriever = Retriever()
        agent = ChatAgent(retriever)

        print(
            f"Loaded existing FAISS index with "
            f"{len(retriever.entries)} assessments."
        )

    except FileNotFoundError:
        print("No index found. Build index first using --build.")


class ChatRequest(BaseModel):
    messages: List[Dict[str, Any]]


@app.get("/health")
def health_check():
    return {
        "status": "ok"
    }


@app.post("/chat")
def chat(request: ChatRequest):

    if agent is None:
        raise HTTPException(
            status_code=400,
            detail="Index not built yet."
        )

    return agent.chat(request.messages)


if __name__ == "__main__":

    if "--build" in sys.argv:

        entries = load_and_parse_catalog("catalog.json")

        build_and_save_index(entries)

        print(
            f"Successfully indexed "
            f"{len(entries)} assessments."
        )

    else:

        print(
            "Usage:\n"
            "uv run python app.py --build\n\n"
            "Run API:\n"
            "uv run uvicorn app:app --reload"
        )


