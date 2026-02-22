"""
Embedding service using sentence-transformers for Arabic text.
Includes LRU cache for repeated queries.
"""
from __future__ import annotations
from functools import lru_cache
from sentence_transformers import SentenceTransformer
from backend.config import EMBEDDING_MODEL

_model = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts."""
    model = get_model()
    embeddings = model.encode(texts, show_progress_bar=False)
    return embeddings.tolist()


@lru_cache(maxsize=256)
def embed_query(query: str) -> tuple:
    """Embed a single query. Cached for repeated/similar questions."""
    model = get_model()
    embedding = model.encode([query], show_progress_bar=False)
    return tuple(embedding[0].tolist())


def embed_query_list(query: str) -> list[float]:
    """Embed a single query, returning list (for ChromaDB compatibility)."""
    return list(embed_query(query))
