"""
Embedding service using Google Gemini API for Arabic text.
No local model needed — uses Gemini's gemini-embedding-001 (free tier).
Memory footprint: ~0MB (API-based, no local model).
"""
from __future__ import annotations
import os
import time
from functools import lru_cache

_client = None


def _get_client():
    """Get or create the Google GenAI client."""
    global _client
    if _client is None:
        from google import genai
        api_key = os.getenv("GOOGLE_API_KEY", "")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required for embeddings")
        _client = genai.Client(api_key=api_key)
    return _client


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts using Gemini API. Used at build time for documents."""
    client = _get_client()
    all_embeddings = []
    # Gemini supports batch embedding — process in chunks of 100
    batch_size = 100
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        # Add retry logic for rate limits
        for attempt in range(3):
            try:
                result = client.models.embed_content(
                    model="gemini-embedding-001",
                    contents=batch,
                    config={
                        "output_dimensionality": 768,
                    },
                )
                for embedding in result.embeddings:
                    all_embeddings.append(embedding.values)
                break
            except Exception as e:
                if "429" in str(e) or "RATE" in str(e).upper():
                    wait_time = 2 ** attempt * 5
                    print(f"  ⏳ Rate limit hit, waiting {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise
        # Small delay between batches to avoid rate limits
        if i + batch_size < len(texts):
            time.sleep(0.5)
    return all_embeddings


@lru_cache(maxsize=128)
def embed_query(query: str) -> tuple:
    """Embed a single query. Cached for repeated/similar questions."""
    client = _get_client()
    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents=query,
        config={
            "output_dimensionality": 768,
        },
    )
    return tuple(result.embeddings[0].values)


def embed_query_list(query: str) -> list[float]:
    """Embed a single query, returning list (for ChromaDB compatibility)."""
    return list(embed_query(query))
