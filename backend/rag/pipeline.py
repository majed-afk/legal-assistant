"""
Full RAG pipeline: from user question to relevant legal context.
Hybrid search: combines semantic (vector) search with keyword-based topic filtering.
This compensates for the multilingual model's weaker Arabic legal term understanding.
"""
from __future__ import annotations
from backend.rag.embeddings import embed_query_list
from backend.rag.vector_store import search
from backend.rag.classifier import classify_query

# Cache for RAG results (question -> context).
_rag_cache: dict[str, dict] = {}
_RAG_CACHE_MAX = 32

# Legal terms → exact ChromaDB topic names for precise filtering
LEGAL_TERM_MAP = {
    # أحوال شخصية
    "خلع": "الخلع", "مخالعة": "الخلع", "افتداء": "الخلع",
    "طلاق": "الطلاق", "تطليق": "الطلاق", "رجعي": "الطلاق", "بائن": "الطلاق", "مراجعة": "الطلاق",
    "حضانة": "الحضانة", "محضون": "الحضانة", "حاضن": "الحضانة",
    "نفقة": "النفقة", "نفقة الزوجة": "النفقة", "نفقة الأولاد": "نفقة الأقارب",
    "مهر": "المهر", "صداق": "المهر",
    "عدة": "العدة", "عدة الوفاة": "العدة", "عدة الطلاق": "العدة",
    "نسب": "النسب", "إثبات النسب": "النسب", "لعان": "النسب",
    "خطبة": "الخطبة", "خاطب": "الخطبة",
    "فسخ": "فسخ النكاح", "تفريق": "فسخ النكاح",
    "تفريق للضرر": "فسخ النكاح", "شقاق": "فسخ النكاح", "ضرر": "فسخ النكاح",
    "وصية": "الوصية", "موصي": "الوصية", "موصى": "الوصية",
    "إرث": "أحكام الإرث", "ميراث": "أحكام الإرث", "تركة": "أحكام الإرث", "ورثة": "أحكام الإرث",
    "فرض": "الإرث بالفرض", "تعصيب": "التعصيب", "حجب": "الحجب",
    "وصاية": "الوصاية", "وصي": "الوصاية", "قاصر": "الولاية على القاصر",
    "مفقود": "الغائب والمفقود", "غائب": "الغائب والمفقود",
    "زواج": "عقد الزواج", "نكاح": "عقد الزواج",
    "ولي": "الولاية في الزواج",
}


def retrieve_context(question: str, top_k: int = 5) -> dict:
    """
    Hybrid retrieval: semantic search + keyword-based topic filtering.
    Merges topic-matched results (high precision) with semantic results (recall).
    """
    cache_key = question.strip()
    if cache_key in _rag_cache:
        return _rag_cache[cache_key]

    classification = classify_query(question)
    query_embedding = embed_query_list(question)

    # === 1. Broad semantic search (for recall) ===
    semantic_results = search(query_embedding, n_results=top_k * 2)

    # === 2. Keyword-based topic search (for precision) ===
    detected_topics = _detect_topics(question)
    filtered_results = None

    if detected_topics:
        for topic in detected_topics[:2]:
            where_filter = {"topic": {"$eq": topic}}
            filtered_results = search(query_embedding, n_results=top_k, where=where_filter)
            if filtered_results["documents"] and filtered_results["documents"][0]:
                break

    # === 3. Merge: topic-matched first (precise), then semantic (broad) ===
    merged = _merge_results(semantic_results, filtered_results, top_k)

    context = build_context_string(merged, classification)

    result = {
        "classification": classification,
        "context": context,
        "sources": extract_sources(merged),
        "num_results": len(merged["documents"][0]) if merged["documents"] else 0,
    }

    if len(_rag_cache) >= _RAG_CACHE_MAX:
        oldest_key = next(iter(_rag_cache))
        del _rag_cache[oldest_key]
    _rag_cache[cache_key] = result

    return result


def _detect_topics(question: str) -> list[str]:
    """Detect specific legal topics from question keywords (longest match first)."""
    topics = []
    seen = set()
    # Sort by key length descending for longest-match-first
    sorted_terms = sorted(LEGAL_TERM_MAP.items(), key=lambda x: len(x[0]), reverse=True)
    for term, topic in sorted_terms:
        if term in question and topic not in seen:
            topics.append(topic)
            seen.add(topic)
    return topics


def _merge_results(semantic: dict, filtered: dict | None, top_k: int) -> dict:
    """Merge filtered (high precision) + semantic (broad recall), deduplicated."""
    if not filtered or not filtered["documents"] or not filtered["documents"][0]:
        return _trim(semantic, top_k)

    seen = set()
    docs, metas, dists = [], [], []

    # Filtered results first (they match the legal topic)
    for doc, meta, dist in zip(
        filtered["documents"][0], filtered["metadatas"][0], filtered["distances"][0],
    ):
        key = doc[:100]
        if key not in seen:
            seen.add(key)
            docs.append(doc)
            metas.append(meta)
            dists.append(dist)

    # Then semantic results (for additional context)
    if semantic["documents"] and semantic["documents"][0]:
        for doc, meta, dist in zip(
            semantic["documents"][0], semantic["metadatas"][0], semantic["distances"][0],
        ):
            key = doc[:100]
            if key not in seen:
                seen.add(key)
                docs.append(doc)
                metas.append(meta)
                dists.append(dist)

    return {
        "documents": [docs[:top_k]],
        "metadatas": [metas[:top_k]],
        "distances": [dists[:top_k]],
    }


def _trim(results: dict, top_k: int) -> dict:
    if not results["documents"] or not results["documents"][0]:
        return results
    return {
        "documents": [results["documents"][0][:top_k]],
        "metadatas": [results["metadatas"][0][:top_k]],
        "distances": [results["distances"][0][:top_k]],
    }


def build_context_string(results: dict, classification: dict) -> str:
    """Build a formatted context string from search results."""
    parts = []
    if not results["documents"] or not results["documents"][0]:
        parts.append("لم يتم العثور على مواد ذات صلة.")
        return "\n".join(parts)

    for i, (doc, meta, dist) in enumerate(zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0],
    )):
        law_name = meta.get("law", "نظام الأحوال الشخصية")
        section = meta.get("section", "")
        parts.append(f"[{i+1}] {law_name} | {section}" if section else f"[{i+1}] {law_name}")
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
