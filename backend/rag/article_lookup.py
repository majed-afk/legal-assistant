"""
Article Lookup — استخراج نص مادة نظامية مباشرة بدون AI.
يكتشف أنماط مثل "ما نص المادة 15 من نظام الأحوال الشخصية؟" عبر regex،
ويرجع النص من articles.json مباشرة.
"""
from __future__ import annotations
import json
import logging
import os
import re

log = logging.getLogger("sanad.article_lookup")

_articles_data: list[dict] = []

# Arabic-Western digit mapping
_ARABIC_DIGITS = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')

# Law name aliases → canonical law name
_LAW_ALIASES = {
    "الأحوال الشخصية": "نظام الأحوال الشخصية",
    "أحوال شخصية": "نظام الأحوال الشخصية",
    "احوال شخصية": "نظام الأحوال الشخصية",
    "الاحوال": "نظام الأحوال الشخصية",
    "الأحوال": "نظام الأحوال الشخصية",
    "الإثبات": "نظام الإثبات",
    "إثبات": "نظام الإثبات",
    "اثبات": "نظام الإثبات",
    "المرافعات الشرعية": "نظام المرافعات الشرعية",
    "المرافعات": "نظام المرافعات الشرعية",
    "مرافعات": "نظام المرافعات الشرعية",
    "المعاملات المدنية": "نظام المعاملات المدنية",
    "معاملات مدنية": "نظام المعاملات المدنية",
    "المعاملات": "نظام المعاملات المدنية",
    "معاملات": "نظام المعاملات المدنية",
    "مدني": "نظام المعاملات المدنية",
    "المدني": "نظام المعاملات المدنية",
}

# Regex patterns for article reference extraction
# Matches: "المادة 15", "مادة ٤٥", "نص المادة 100/2", etc.
_ARTICLE_PATTERNS = [
    # "ما نص المادة X من نظام Y"
    re.compile(
        r'(?:ما\s+)?(?:نص\s+)?(?:ال)?مادة\s+(\d+|[٠-٩]+)'
        r'(?:\s*[/\\]\s*(\d+|[٠-٩]+))?'
        r'(?:\s+من\s+(?:نظام\s+)?(.+?))?'
        r'\s*[؟?]?\s*$',
        re.UNICODE
    ),
    # "عطني/اعطني المادة X من Y"
    re.compile(
        r'(?:عطني|اعطني|أعطني|اذكر|اذكر لي)\s+(?:نص\s+)?(?:ال)?مادة\s+(\d+|[٠-٩]+)'
        r'(?:\s*[/\\]\s*(\d+|[٠-٩]+))?'
        r'(?:\s+(?:من|في)\s+(?:نظام\s+)?(.+?))?'
        r'\s*[؟?]?\s*$',
        re.UNICODE
    ),
]


def initialize_article_lookup():
    """Load articles data at startup."""
    global _articles_data
    from backend.config import ARTICLES_JSON_PATH
    if os.path.exists(ARTICLES_JSON_PATH):
        with open(ARTICLES_JSON_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        _articles_data = data.get('articles', [])
        log.info("Article lookup ready — %d articles loaded", len(_articles_data))


def _to_western_digits(s: str) -> str:
    """Convert Arabic digits to Western digits."""
    return s.translate(_ARABIC_DIGITS)


def _resolve_law_name(raw: str | None) -> str | None:
    """Resolve law name alias to canonical name."""
    if not raw:
        return None
    raw = raw.strip().rstrip('؟?. ')
    # Direct match
    if raw in _LAW_ALIASES:
        return _LAW_ALIASES[raw]
    # Try without "نظام" prefix
    without_nizam = raw.replace("نظام ", "").strip()
    if without_nizam in _LAW_ALIASES:
        return _LAW_ALIASES[without_nizam]
    # Try fuzzy match
    for alias, canonical in _LAW_ALIASES.items():
        if alias in raw:
            return canonical
    return None


def lookup_article(question: str) -> dict | None:
    """Try to extract an article reference from the question and look it up.

    Returns dict with article data and formatted response, or None if not matched.
    """
    if not _articles_data:
        return None

    q = question.strip()

    for pattern in _ARTICLE_PATTERNS:
        m = pattern.search(q)
        if not m:
            continue

        art_num_str = _to_western_digits(m.group(1))
        art_num = int(art_num_str)
        sub_article = m.group(2)
        if sub_article:
            sub_article = _to_western_digits(sub_article)
        law_name_raw = m.group(3) if m.lastindex >= 3 else None
        law_name = _resolve_law_name(law_name_raw)

        # Find matching articles
        matches = []
        for art in _articles_data:
            if art['article_number'] != art_num:
                continue
            if law_name and art['law'] != law_name:
                continue
            matches.append(art)

        if not matches:
            return None

        # Format response
        response_parts = []
        sources = []
        for art in matches:
            response_parts.append(
                f"📖 {art['law']} — {art.get('section', '')}\n\n"
                f"{art['text']}\n\n"
                f"📌 التصنيف: {art.get('topic', '')}"
            )
            if art.get('has_deadline') and art.get('deadline_details'):
                response_parts.append(f"⏰ مهلة: {art['deadline_details']}")
            sources.append({
                "chapter": art.get("chapter", ""),
                "section": art.get("section", ""),
                "topic": art.get("topic", ""),
                "pages": art.get("source_pages", ""),
            })

        full_response = "\n\n---\n\n".join(response_parts)
        full_response += "\n\n⚖️ هذه استشارة أولية لا تُغني عن مراجعة محامي مرخص."

        category = matches[0].get('topic', 'عام')

        return {
            "response": full_response,
            "category": category,
            "sources": sources,
            "article_number": art_num,
            "law": matches[0].get('law', ''),
        }

    return None
