"""
Embedding service using sentence-transformers for Arabic text.
Includes LRU cache for repeated queries.
Memory-optimized for 512MB environments.
"""
from __future__ import annotations
import gc
from functools import lru_cache
from backend.config import EMBEDDING_MODEL

_model = None


def get_model():
    global _model
    if _model is None:
        import torch
        torch.set_num_threads(1)  # Reduce memory overhead from threads
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(EMBEDDING_MODEL)
        gc.collect()  # Free any unused memory after loading
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts."""
    model = get_model()
    embeddings = model.encode(texts, show_progress_bar=False, batch_size=32)
    return embeddings.tolist()


@lru_cache(maxsize=128)
def embed_query(query: str) -> tuple:
    """Embed a single query. Cached for repeated/similar questions."""
    model = get_model()
    embedding = model.encode([query], show_progress_bar=False)
    return tuple(embedding[0].tolist())


def embed_query_list(query: str) -> list[float]:
    """Embed a single query, returning list (for ChromaDB compatibility)."""
    return list(embed_query(query))
