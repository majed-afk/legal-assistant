"""
Embedding service using sentence-transformers for Arabic text.
Uses paraphrase-multilingual-MiniLM-L12-v2 locally — no API needed.
Dimension: 384. Model loaded once, cached in memory (~120 MB).
"""
from __future__ import annotations
from functools import lru_cache

_model = None
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


def _get_model():
    """Get or create the sentence-transformers model (lazy loaded)."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts locally. Used at build time for documents."""
    model = _get_model()
    embeddings = model.encode(texts, show_progress_bar=len(texts) > 50, batch_size=64)
    return [emb.tolist() for emb in embeddings]


@lru_cache(maxsize=128)
def embed_query(query: str) -> tuple:
    """Embed a single query. Cached for repeated/similar questions."""
    model = _get_model()
    emb = model.encode(query)
    return tuple(emb.tolist())


def embed_query_list(query: str) -> list[float]:
    """Embed a single query, returning list (for ChromaDB compatibility)."""
    return list(embed_query(query))
