"""
Full RAG pipeline: from user question to relevant legal context.
Includes caching for repeated queries.
"""
from __future__ import annotations
from functools import lru_cache
from backend.rag.embeddings import embed_query_list
from backend.rag.vector_store import search
from backend.rag.classifier import classify_query

# Cache for RAG results (question -> context). Stores last 128 unique questions.
_rag_cache: dict[str, dict] = {}
_RAG_CACHE_MAX = 32


def retrieve_context(question: str, top_k: int = 5) -> dict:
    """
    Retrieve relevant legal articles for a question.
    Returns classified query + relevant context string.
    Uses cache for repeated questions.
    """
    # Check cache first
    cache_key = question.strip()
    if cache_key in _rag_cache:
        return _rag_cache[cache_key]

    classification = classify_query(question)
    query_embedding = embed_query_list(question)

    # Search with topic filter if we have a clear category
    where_filter = None
    category = classification["category"]
    if category != "عام":
        # Try both with and without "ال" prefix since topics may vary
        category_with_al = "ال" + category if not category.startswith("ال") else category
        category_without_al = category[2:] if category.startswith("ال") else category
        where_filter = {
            "$or": [
                {"topic": {"$eq": category}},
                {"topic": {"$eq": category_with_al}},
                {"topic": {"$eq": category_without_al}},
            ]
        }

    results = search(query_embedding, n_results=top_k, where=where_filter)

    # If filtered search returns too few results, do unfiltered search
    if not results["documents"] or not results["documents"][0] or len(results["documents"][0]) < 3:
        results = search(query_embedding, n_results=top_k)

    context = build_context_string(results, classification)

    result = {
        "classification": classification,
        "context": context,
        "sources": extract_sources(results),
        "num_results": len(results["documents"][0]) if results["documents"] else 0,
    }

    # Cache the result
    if len(_rag_cache) >= _RAG_CACHE_MAX:
        # Remove oldest entry
        oldest_key = next(iter(_rag_cache))
        del _rag_cache[oldest_key]
    _rag_cache[cache_key] = result

    return result


def build_context_string(results: dict, classification: dict) -> str:
    """Build a formatted context string from search results."""
    parts = []

    if not results["documents"] or not results["documents"][0]:
        parts.append("لم يتم العثور على مواد ذات صلة.")
        return "\n".join(parts)

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances)):
        chapter = meta.get("chapter", "")
        if "الإثبات" in chapter:
            law_name = "نظام الإثبات"
        elif "المرافعات" in chapter:
            law_name = "نظام المرافعات الشرعية"
        else:
            law_name = "نظام الأحوال الشخصية"
        parts.append(f"[{i+1}] {law_name} | {meta.get('section', '')}")
        parts.append(doc)
        if meta.get("has_deadline") == "True":
            parts.append(f"⏰ مهلة: {meta.get('deadline_details', '')}")
        parts.append("")

    return "\n".join(parts)


def extract_sources(results: dict) -> list[dict]:
    """Extract source references from results."""
    sources = []
    if not results["metadatas"] or not results["metadatas"][0]:
        return sources

    for meta in results["metadatas"][0]:
        sources.append({
            "chapter": meta.get("chapter", ""),
            "section": meta.get("section", ""),
            "topic": meta.get("topic", ""),
            "pages": meta.get("source_pages", ""),
        })
    return sources
