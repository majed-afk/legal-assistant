"""
Embedding service using FastEmbed (ONNX) for Arabic text.
No PyTorch or sentence-transformers required.
Memory-optimized for 512MB environments (~200MB total vs ~600MB with PyTorch).
"""
from __future__ import annotations
from functools import lru_cache
from backend.config import EMBEDDING_MODEL

_model = None


def get_model():
    global _model
    if _model is None:
        from fastembed import TextEmbedding
        _model = TextEmbedding(
            model_name=f"sentence-transformers/{EMBEDDING_MODEL}",
            cache_dir="/app/models_cache",
        )
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts."""
    model = get_model()
    embeddings = list(model.embed(texts, batch_size=32))
    return [e.tolist() for e in embeddings]


@lru_cache(maxsize=128)
def embed_query(query: str) -> tuple:
    """Embed a single query. Cached for repeated/similar questions."""
    model = get_model()
    embeddings = list(model.embed([query]))
    return tuple(embeddings[0].tolist())


def embed_query_list(query: str) -> list[float]:
    """Embed a single query, returning list (for ChromaDB compatibility)."""
    return list(embed_query(query))
