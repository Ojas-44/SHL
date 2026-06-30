"""
embeddings.py
-------------
Turns catalog text into vectors (embeddings) and stores them in a FAISS
index so we can later search "what's semantically similar to this query".

Why all-MiniLM-L6-v2?
It's small (~80MB), fast on CPU, and good enough quality for short
text like job/assessment descriptions. No GPU required - important for a
take-home assignment that needs to run on a reviewer's laptop.

Why FAISS instead of a real vector database?
The catalog is small (dozens to a few hundred items). FAISS's
IndexFlatIP (exact, brute-force search) is plenty fast at this scale and
needs zero extra infrastructure - no server, no database, just two files
on disk. That matches the assignment's "don't over-engineer" requirement.
"""

import os
import pickle
import re
from typing import Any, Dict, List, Tuple

try:
    import faiss
except ImportError:  # pragma: no cover - defensive fallback
    faiss = None

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except ImportError:  # pragma: no cover - defensive fallback
    SentenceTransformer = None

from services.catalog_loader import build_search_text

# Paths where we persist the index + the metadata that goes with it.
# We keep them as module-level constants so every function agrees on
# where things live, instead of passing strings around everywhere.
VECTORSTORE_DIR = "vectorstore"
INDEX_PATH = os.path.join(VECTORSTORE_DIR, "catalog.index")
METADATA_PATH = os.path.join(VECTORSTORE_DIR, "catalog_metadata.pkl")

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Loading the model is somewhat slow (a few seconds) so we only want to do
# it once per process, not once per request. This module-level variable
# acts as a simple cache.
_model = None


class SimpleEmbeddingFallback:
    """A lightweight fallback embedding implementation when sentence-transformers is unavailable."""

    def encode(self, texts: List[str], convert_to_numpy: bool = True, show_progress_bar: bool = False, normalize_embeddings: bool = True) -> np.ndarray:
        vectors = []
        for text in texts:
            tokens = re.findall(r"[A-Za-z0-9]+", text.lower())
            vector = np.zeros(256, dtype="float32")
            for token in tokens:
                idx = abs(hash(token)) % 256
                vector[idx] += 1.0
            if normalize_embeddings:
                norm = np.linalg.norm(vector)
                if norm > 0:
                    vector = vector / norm
            vectors.append(vector)
        return np.array(vectors, dtype="float32")


def get_model() -> Any:
    """Lazily loads (and caches) the sentence-transformer model when available."""
    global _model
    if _model is None:
        if SentenceTransformer is None:
            _model = SimpleEmbeddingFallback()
        else:
            _model = SentenceTransformer(MODEL_NAME)
    return _model


def embed_texts(texts: List[str]) -> np.ndarray:
    """
    Converts a list of strings into a 2D numpy array of embeddings.

    We L2-normalize each vector. That matters because we use FAISS's
    IndexFlatIP (inner product) as our similarity search. Inner product on
    normalized vectors is mathematically equivalent to cosine similarity,
    which is the standard, well-behaved way to compare sentence embeddings.
    """
    model = get_model()
    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        show_progress_bar=False,
        normalize_embeddings=True,  # does the L2 normalization for us
    )
    # FAISS expects float32, sentence-transformers sometimes returns float64.
    return embeddings.astype("float32")


def build_index(entries: List[Dict[str, Any]]) -> Tuple[Any, List[Dict[str, Any]]]:
    """
    Builds a FAISS index from a list of parsed catalog entries.

    Steps:
    1. Turn each entry into a single search-friendly text string.
    2. Embed all those strings in one batch (faster than one-by-one).
    3. Add the vectors to a flat (exact search) FAISS index.

    Returns both the index and the original entries list, because FAISS
    only stores vectors + integer ids - it knows nothing about the actual
    assessment data. We keep that mapping ourselves.
    """
    search_texts = [build_search_text(e) for e in entries]
    vectors = embed_texts(search_texts)

    if faiss is None:
        raise ImportError("faiss is not installed")

    dimension = vectors.shape[1]  # 384 for all-MiniLM-L6-v2
    index = faiss.IndexFlatIP(dimension)
    index.add(vectors)

    return index, entries


def save_index(index: Any, entries: List[Dict[str, Any]]) -> None:
    """Persists the FAISS index and the matching metadata list to disk."""
    if faiss is None:
        raise ImportError("faiss is not installed")

    os.makedirs(VECTORSTORE_DIR, exist_ok=True)
    faiss.write_index(index, INDEX_PATH)
    with open(METADATA_PATH, "wb") as f:
        pickle.dump(entries, f)


def load_index() -> Tuple[Any, List[Dict[str, Any]]]:
    """Loads a previously saved FAISS index and its metadata from disk."""
    if faiss is None:
        raise ImportError("faiss is not installed")
    if not (os.path.exists(INDEX_PATH) and os.path.exists(METADATA_PATH)):
        raise FileNotFoundError(
            "No saved index found in 'vectorstore/'. Run `python app.py --build` "
            "(or call build_and_save_index()) first."
        )
    index = faiss.read_index(INDEX_PATH)
    with open(METADATA_PATH, "rb") as f:
        entries = pickle.load(f)
    return index, entries


def build_and_save_index(catalog_entries: List[Dict[str, Any]]) -> None:
    """One-shot convenience function: build the index, then persist it."""
    index, entries = build_index(catalog_entries)
    save_index(index, entries)
    print(f"Built and saved FAISS index with {index.ntotal} vectors -> {VECTORSTORE_DIR}/")
