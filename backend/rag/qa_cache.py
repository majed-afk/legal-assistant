"""
QA Cache — مطابقة الأسئلة المتكررة من قاعدة الإجابات الموثقة.
يستخدم embeddings محلية لحساب التشابه الدلالي مع 208 سؤال/جواب مصحح.
إذا تشابه السؤال ≥ threshold → يرجع الإجابة مباشرة بدون استدعاء Claude API.
"""
from __future__ import annotations
import json
import os
import re

import numpy as np

from backend.rag.embeddings import embed_texts, embed_query

QA_MATCH_THRESHOLD = float(os.getenv("QA_MATCH_THRESHOLD", "0.91"))
RESPONSE_CACHE_MAX = int(os.getenv("RESPONSE_CACHE_MAX", "256"))

_qa_entries: list[dict] = []
_qa_embeddings: np.ndarray | None = None
_qa_index: list[int] = []  # maps embedding row → qa_entry index
_articles_by_number: dict[str, list[dict]] = {}  # "15_نظام الأحوال الشخصية" → article

# === Response Cache: stores Claude responses for repeated questions ===
from collections import OrderedDict
_response_cache: OrderedDict[str, dict] = OrderedDict()


def _cache_key(question: str, model_mode: str) -> str:
    """Normalize question for cache key."""
    q = re.sub(r'[إأآا]', 'ا', question.strip())
    q = re.sub(r'\s+', ' ', q)
    return f"{model_mode}:{q}"


def get_cached_response(question: str, model_mode: str) -> dict | None:
    """Check if a Claude response is cached for this question."""
    key = _cache_key(question, model_mode)
    if key in _response_cache:
        # Move to end (most recently used)
        _response_cache.move_to_end(key)
        print(f"⚡ Response cache hit: {key[:60]}...")
        return _response_cache[key]
    return None


def cache_response(question: str, model_mode: str, response: str,
                   classification: dict, sources: list) -> None:
    """Cache a Claude response for future reuse."""
    key = _cache_key(question, model_mode)
    _response_cache[key] = {
        "answer": response,
        "classification": {**classification, "source": "response_cache"},
        "sources": sources,
    }
    # Evict oldest if over limit
    while len(_response_cache) > RESPONSE_CACHE_MAX:
        _response_cache.popitem(last=False)


def _normalize_arabic(text: str) -> str:
    """Light Arabic normalization for better matching."""
    text = re.sub(r'[إأآا]', 'ا', text)
    return text.strip()


def initialize_qa_cache():
    """Load QA data and pre-compute embeddings. Called once at startup."""
    global _qa_entries, _qa_embeddings, _qa_index, _articles_by_number

    qa_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'corrected_qa.json')
    if not os.path.exists(qa_path):
        print("⚠️ corrected_qa.json غير موجود — تخطي QA cache")
        return

    with open(qa_path, 'r', encoding='utf-8') as f:
        _qa_entries = json.load(f)

    # Build articles lookup for source metadata extraction
    from backend.config import ARTICLES_JSON_PATH
    if os.path.exists(ARTICLES_JSON_PATH):
        with open(ARTICLES_JSON_PATH, 'r', encoding='utf-8') as f:
            articles_data = json.load(f)
        for art in articles_data.get('articles', []):
            key = f"{art['article_number']}_{art['law']}"
            _articles_by_number[key] = art

    # Collect all questions (formal + colloquial)
    questions = []
    _qa_index.clear()
    for i, entry in enumerate(_qa_entries):
        questions.append(entry.get('question_formal', ''))
        _qa_index.append(i)
        questions.append(entry.get('question_colloquial', ''))
        _qa_index.append(i)

    # Embed all questions at once (batch, local, free)
    raw_embeddings = embed_texts(questions)
    _qa_embeddings = np.array(raw_embeddings, dtype=np.float32)

    # Normalize for cosine similarity via dot product
    norms = np.linalg.norm(_qa_embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1  # avoid division by zero
    _qa_embeddings = _qa_embeddings / norms

    print(f"✅ ذاكرة QA جاهزة — {len(_qa_entries)} إجابة موثقة ({len(questions)} سؤال مفهرس)")


def _extract_sources(corrected_articles: list[str], category: str) -> list[dict]:
    """Build sources list from corrected_articles, matching the existing format."""
    sources = []
    for art_ref in corrected_articles:
        # Extract article number from strings like "المادة 15" or "المادة 5/2"
        m = re.search(r'(\d+)', art_ref)
        if not m:
            continue
        art_num = int(m.group(1))

        # Try to find the article in our lookup
        matched = None
        for key, art in _articles_by_number.items():
            if art['article_number'] == art_num:
                matched = art
                break

        if matched:
            sources.append({
                "chapter": matched.get("chapter", ""),
                "section": matched.get("section", ""),
                "topic": matched.get("topic", ""),
                "pages": matched.get("source_pages", ""),
            })
        else:
            sources.append({
                "chapter": "",
                "section": "",
                "topic": category,
                "pages": art_ref,
            })
    return sources


def match_qa_cache(question: str, threshold: float | None = None) -> dict | None:
    """Match a question against the QA cache using semantic similarity.

    Returns dict with answer details if similarity >= threshold, else None.
    """
    if _qa_embeddings is None or len(_qa_entries) == 0:
        return None

    if threshold is None:
        threshold = QA_MATCH_THRESHOLD

    # Embed the incoming question (cached via lru_cache)
    query_emb = np.array(embed_query(question), dtype=np.float32)
    query_norm = np.linalg.norm(query_emb)
    if query_norm == 0:
        return None
    query_emb = query_emb / query_norm

    # Cosine similarity = dot product (both normalized)
    similarities = np.dot(_qa_embeddings, query_emb)
    # Handle edge cases from floating-point precision
    similarities = np.nan_to_num(similarities, nan=0.0, posinf=0.0, neginf=0.0)
    best_idx = int(np.argmax(similarities))
    best_score = float(similarities[best_idx])

    if best_score < threshold:
        return None

    # Get the matched QA entry
    qa_idx = _qa_index[best_idx]
    entry = _qa_entries[qa_idx]

    category = entry.get("category", "عام")
    corrected_articles = entry.get("corrected_articles", [])

    return {
        "corrected_answer": entry["corrected_answer"],
        "category": category,
        "corrected_articles": corrected_articles,
        "sources": _extract_sources(corrected_articles, category),
        "similarity": round(best_score, 4),
        "qa_id": entry.get("id", qa_idx),
        "matched_question": entry.get("question_formal", ""),
    }
