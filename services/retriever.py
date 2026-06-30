"""
retriever.py
------------
Search the FAISS index for assessments that are semantically related to a
query, then re-rank them with lightweight metadata matching from the catalog.
"""

import re
from typing import Any, Dict, List

try:
    import faiss
except ImportError:  # pragma: no cover - defensive fallback
    faiss = None

from services.catalog_loader import load_and_parse_catalog
from services.embeddings import embed_texts, load_index

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "need",
    "of",
    "or",
    "the",
    "to",
    "what",
    "with",
    "you",
    "your",
}


class Retriever:
    """Thin wrapper around a FAISS index and its metadata."""

    def __init__(self) -> None:
        self.index = None
        self.entries: List[Dict[str, Any]] = []
        try:
            self.index, self.entries = load_index()
        except Exception:
            self.index = None
            self.entries = load_and_parse_catalog("catalog.json")

    def _tokenize_query(self, query: str) -> List[str]:
        return [
            token
            for token in re.findall(r"[A-Za-z0-9+.-]+", query.lower())
            if len(token) > 2 and token not in STOPWORDS
        ]

    def _metadata_boost(self, query_terms: List[str], entry: Dict[str, Any]) -> float:
        boost = 0.0
        name = (entry.get("name") or "").lower()
        description = (entry.get("description") or "").lower()
        test_type = (entry.get("test_type") or "").lower()
        job_levels = (entry.get("job_levels") or "").lower()
        keys = (entry.get("keys") or "").lower()

        for term in query_terms:
            if term in name:
                boost += 0.18
            if term in description:
                boost += 0.07
            if term in test_type:
                boost += 0.10
            if term in job_levels:
                boost += 0.05
            if term in keys:
                boost += 0.05

        return boost

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Return top_k results re-ranked by semantic similarity plus metadata overlap."""
        if top_k <= 0 or not query or not str(query).strip():
            return []

        query_terms = self._tokenize_query(query)
        if not self.entries:
            return []

        if self.index is not None and faiss is not None:
            query_vector = embed_texts([query])
            candidate_limit = max(top_k * 3, top_k)
            scores, ids = self.index.search(query_vector, candidate_limit)

            results: List[Dict[str, Any]] = []
            seen_names = set()
            for score, idx in zip(scores[0], ids[0]):
                if idx == -1:
                    continue
                entry = dict(self.entries[idx])
                entry_name = entry.get("name")
                if entry_name in seen_names:
                    continue
                seen_names.add(entry_name)
                entry["score"] = float(score) + self._metadata_boost(query_terms, entry)
                results.append(entry)

            results.sort(key=lambda item: item.get("score", 0.0), reverse=True)
            return results[:top_k]

        results = []
        for entry in self.entries:
            entry_copy = dict(entry)
            entry_copy["score"] = self._metadata_boost(query_terms, entry_copy)
            results.append(entry_copy)

        results.sort(key=lambda item: item.get("score", 0.0), reverse=True)
        return results[:top_k]
