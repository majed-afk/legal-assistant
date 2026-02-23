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

# Legal terms → exact ChromaDB topic names for precise filtering.
# Longest-match-first: put compound terms before single words.
# Covers all 62 topics across 3 laws.
LEGAL_TERM_MAP = {
    # ══════════════════════════════════════════════════════════
    # نظام الأحوال الشخصية (27 topic)
    # ══════════════════════════════════════════════════════════
    # الخطبة
    "خطبة": "الخطبة", "خاطب": "الخطبة", "مخطوبة": "الخطبة", "عدول عن الخطبة": "الخطبة",
    # عقد الزواج (أحكام عامة)
    "عقد الزواج": "عقد الزواج", "عقد النكاح": "عقد الزواج", "توثيق الزواج": "عقد الزواج",
    # أركان الزواج
    "أركان الزواج": "أركان الزواج", "أركان عقد الزواج": "أركان الزواج", "أركان النكاح": "أركان الزواج",
    "أركان": "أركان الزواج", "إيجاب وقبول": "أركان الزواج", "ركن": "أركان الزواج",
    # شروط الزواج — compound terms BEFORE generic "شروط"
    "شروط عقد الزواج": "شروط الزواج", "شروط الزواج": "شروط الزواج", "شروط النكاح": "شروط الزواج",
    "شروط في العقد": "شروط الزواج",
    # الولاية في الزواج
    "ولاية الزواج": "الولاية في الزواج", "ولي في الزواج": "الولاية في الزواج",
    "ولي": "الولاية في الزواج", "عضل": "الولاية في الزواج",
    # المحرمات
    "محرمات": "المحرمات", "محرم": "المحرمات", "محرمات النكاح": "المحرمات",
    "رضاع": "المحرمات", "مصاهرة": "المحرمات", "جمع بين": "المحرمات",
    # أنواع الزواج
    "أنواع الزواج": "أنواع الزواج", "زواج المسيار": "أنواع الزواج", "تعدد الزوجات": "أنواع الزواج",
    "تعدد": "أنواع الزواج",
    # الزواج الباطل والفاسد
    "الزواج الباطل": "الزواج الباطل والفاسد", "الزواج الفاسد": "الزواج الباطل والفاسد",
    "زواج باطل": "الزواج الباطل والفاسد", "زواج فاسد": "الزواج الباطل والفاسد",
    "بطلان الزواج": "الزواج الباطل والفاسد", "فساد الزواج": "الزواج الباطل والفاسد",
    "باطل": "الزواج الباطل والفاسد",
    # حقوق الزوجين
    "حقوق الزوجين": "حقوق الزوجين", "حقوق الزوج": "حقوق الزوجين", "حقوق الزوجة": "حقوق الزوجين",
    # المهر
    "مهر": "المهر", "صداق": "المهر", "مهر المثل": "المهر", "مقدم المهر": "المهر", "مؤخر المهر": "المهر",
    # زواج (عام — fallback بعد المركبات)
    "زواج": "عقد الزواج", "نكاح": "عقد الزواج",
    # أسباب الفرقة
    "فرقة": "أسباب الفرقة", "أسباب الفرقة": "أسباب الفرقة",
    # الطلاق
    "طلاق": "الطلاق", "تطليق": "الطلاق", "رجعي": "الطلاق", "بائن": "الطلاق",
    "مراجعة": "الطلاق", "طلقة": "الطلاق", "يمين الطلاق": "الطلاق",
    # الخلع
    "خلع": "الخلع", "مخالعة": "الخلع", "افتداء": "الخلع", "عوض الخلع": "الخلع",
    # فسخ النكاح
    "فسخ النكاح": "فسخ النكاح", "فسخ": "فسخ النكاح", "تفريق للضرر": "فسخ النكاح",
    "تفريق": "فسخ النكاح", "شقاق": "فسخ النكاح", "ضرر": "فسخ النكاح", "إيلاء": "فسخ النكاح",
    # العدة
    "عدة": "العدة", "عدة الوفاة": "العدة", "عدة الطلاق": "العدة", "عدة الحامل": "العدة",
    # الحضانة
    "حضانة": "الحضانة", "محضون": "الحضانة", "حاضن": "الحضانة", "سن الحضانة": "الحضانة",
    # النفقة
    "نفقة": "النفقة", "نفقة الزوجة": "النفقة", "إنفاق": "النفقة",
    "نفقة الأقارب": "نفقة الأقارب", "نفقة الأولاد": "نفقة الأقارب", "نفقة الوالدين": "نفقة الأقارب",
    # النسب
    "نسب": "النسب", "إثبات النسب": "النسب", "نفي النسب": "النسب", "لعان": "النسب",
    # الوصية
    "وصية": "الوصية", "موصي": "الوصية", "موصى": "الوصية", "ثلث التركة": "الوصية",
    # أحكام الإرث
    "إرث": "أحكام الإرث", "ميراث": "أحكام الإرث", "تركة": "أحكام الإرث", "ورثة": "أحكام الإرث",
    # الإرث بالفرض / التعصيب / الحجب
    "فرض": "الإرث بالفرض", "إرث بالفرض": "الإرث بالفرض",
    "تعصيب": "التعصيب", "عاصب": "التعصيب",
    "حجب": "الحجب", "محجوب": "الحجب",
    # الوصاية والولاية
    "وصاية": "الوصاية", "وصي": "الوصاية",
    "ولاية على القاصر": "الولاية على القاصر", "قاصر": "الولاية على القاصر",
    "ناقص أهلية": "الولاية على القاصر",
    # الغائب والمفقود
    "مفقود": "الغائب والمفقود", "غائب": "الغائب والمفقود",

    # ══════════════════════════════════════════════════════════
    # نظام الإثبات (22 topic)
    # ══════════════════════════════════════════════════════════
    # إقرار
    "إقرار": "إقرار", "اعتراف": "إقرار", "مقر": "إقرار", "أقر": "إقرار",
    # استجواب
    "استجواب": "استجواب", "استجوب": "استجواب",
    # شهادة (compound first)
    "شهادة الشهود": "شهادة", "أداء الشهادة": "شهادة", "نصاب الشهادة": "شهادة",
    "شهادة": "شهادة", "شاهد": "شهادة", "شهود": "شهادة",
    # شروط الشهادة
    "شروط الشهادة": "شروط الشهادة", "أهلية الشاهد": "شروط الشهادة",
    # إجراءات الشهادة
    "إجراءات الشهادة": "إجراءات الشهادة",
    # دعوى مستعجلة للشهادة
    "دعوى مستعجلة للشهادة": "دعوى مستعجلة للشهادة",
    # يمين (compound first)
    "يمين حاسمة": "يمين حاسمة", "يمين متممة": "يمين متممة",
    "يمين": "يمين", "حلف": "يمين", "نكول": "يمين", "استحلاف": "يمين",
    # محررات
    "محررات رسمية": "محررات رسمية", "محرر رسمي": "محررات رسمية", "سند رسمي": "محررات رسمية",
    "محررات عادية": "محررات عادية", "محرر عادي": "محررات عادية", "سند عادي": "محررات عادية",
    "محرر": "إثبات بالكتابة", "محررات": "إثبات بالكتابة", "مستند": "إثبات بالكتابة",
    "كتابة": "إثبات بالكتابة", "سند": "إثبات بالكتابة",
    # إلزام بتقديم محررات
    "إلزام بتقديم": "إلزام بتقديم محررات", "تقديم محررات": "إلزام بتقديم محررات",
    # تزوير
    "تزوير": "تزوير وتحقيق خطوط", "مزور": "تزوير وتحقيق خطوط",
    "تحقيق خطوط": "تزوير وتحقيق خطوط", "ادعاء بالتزوير": "تزوير وتحقيق خطوط",
    # دليل رقمي
    "دليل رقمي": "دليل رقمي", "إلكتروني": "دليل رقمي", "رقمي": "دليل رقمي",
    "توقيع إلكتروني": "دليل رقمي", "بريد إلكتروني": "دليل رقمي",
    # قرائن
    "قرينة": "قرائن", "قرائن": "قرائن",
    # عرف
    "عرف": "عرف", "عادة": "عرف",
    # معاينة
    "معاينة": "معاينة", "إثبات حالة": "معاينة", "انتقال": "معاينة",
    # خبرة
    "خبرة": "خبرة", "خبير": "خبرة", "تقرير خبير": "خبرة", "ندب خبير": "خبرة",
    # إثبات أحكام عامة/ختامية
    "بينة": "إثبات - أحكام عامة", "أدلة": "إثبات - أحكام عامة", "طرق الإثبات": "إثبات - أحكام عامة",

    # ══════════════════════════════════════════════════════════
    # نظام المرافعات الشرعية (13 topic)
    # ══════════════════════════════════════════════════════════
    # رفع الدعوى
    "رفع دعوى": "رفع الدعوى", "صحيفة دعوى": "رفع الدعوى", "لائحة دعوى": "رفع الدعوى",
    "قيد الدعوى": "رفع الدعوى", "دعوى": "رفع الدعوى",
    # اختصاص المحاكم
    "اختصاص نوعي": "اختصاص المحاكم", "اختصاص": "اختصاص المحاكم", "محكمة مختصة": "اختصاص المحاكم",
    # اختصاص مكاني
    "اختصاص مكاني": "اختصاص مكاني",
    # إجراءات الجلسات
    "جلسة": "إجراءات الجلسات", "جلسات": "إجراءات الجلسات", "تأجيل": "إجراءات الجلسات",
    # حضور الخصوم
    "حضور": "حضور الخصوم", "غياب": "حضور الخصوم", "حكم غيابي": "حضور الخصوم",
    # دفوع وتدخل
    "دفع": "دفوع وتدخل", "دفوع": "دفوع وتدخل", "تدخل": "دفوع وتدخل",
    "إدخال": "دفوع وتدخل", "عدم قبول": "دفوع وتدخل",
    # وقف الخصومة
    "وقف الخصومة": "وقف الخصومة", "ترك الخصومة": "وقف الخصومة",
    # قضاء مستعجل
    "مستعجل": "قضاء مستعجل", "قضاء مستعجل": "قضاء مستعجل", "أمر مؤقت": "قضاء مستعجل",
    "حماية مؤقتة": "قضاء مستعجل",
    # إنهاءات
    "إنهاء": "إنهاءات", "إنهاءات": "إنهاءات", "إثبات وفاة": "إنهاءات", "حصر ورثة": "إنهاءات",
    # تنحي وردّ القضاة
    "رد القاضي": "تنحي وردّ القضاة", "تنحي": "تنحي وردّ القضاة", "رد": "تنحي وردّ القضاة",
    # إثبات في المرافعات
    "إثبات في المرافعات": "إثبات في المرافعات",
    # مرافعات أحكام عامة
    "مرافعات": "مرافعات - أحكام عامة", "إجراءات قضائية": "مرافعات - أحكام عامة",
    "تبليغ": "مرافعات - أحكام عامة",
    # اعتراض واستئناف (mapped to أحكام ختامية since it covers appeals)
    "اعتراض على حكم": "مرافعات - أحكام ختامية", "اعتراض": "مرافعات - أحكام ختامية",
    "استئناف": "مرافعات - أحكام ختامية", "نقض": "مرافعات - أحكام ختامية",
    "طعن": "مرافعات - أحكام ختامية", "التماس إعادة النظر": "مرافعات - أحكام ختامية",
    "تمييز": "مرافعات - أحكام ختامية",
    # تنفيذ
    "تنفيذ حكم": "مرافعات - أحكام ختامية", "تنفيذ": "مرافعات - أحكام ختامية",
}


def _enrich_followup(question: str, chat_history: list | None) -> str:
    """Enrich a follow-up question with context from chat history.

    When a user asks a short follow-up like "من هي المحكمة ذات الاختصاص؟"
    after discussing custody/divorce, we combine the original topic with the
    new question so the RAG pipeline finds the right articles.
    """
    if not chat_history:
        return question

    q = question.strip()

    # Heuristic: short questions (< 40 chars) with no legal keywords
    # are likely follow-ups that need context enrichment
    detected = _detect_topics(q)
    if detected and len(detected) >= 2:
        return question  # Already has enough context

    # Extract topic keywords from recent user messages in chat history
    topic_keywords = []
    for msg in reversed(chat_history[-4:]):
        if msg.get("role") == "user":
            prev_topics = _detect_topics(msg.get("content", ""))
            for t in prev_topics:
                if t not in topic_keywords:
                    topic_keywords.append(t)
            if topic_keywords:
                break  # Use the most recent user message's topics

    if not topic_keywords:
        return question

    # Build enriched query: original question + topic context
    topic_str = " ".join(topic_keywords[:2])
    enriched = f"{question} ({topic_str})"
    print(f"🔗 Enriched follow-up: '{question}' → '{enriched}'")
    return enriched


def retrieve_context(question: str, top_k: int = 5, chat_history: list | None = None) -> dict:
    """
    Hybrid retrieval: semantic search + keyword-based topic filtering.
    Merges topic-matched results (high precision) with semantic results (recall).
    """
    # Enrich follow-up questions with context from chat history
    enriched_question = _enrich_followup(question, chat_history)

    cache_key = enriched_question.strip()
    if cache_key in _rag_cache:
        return _rag_cache[cache_key]

    classification = classify_query(question)  # Classify original question
    query_embedding = embed_query_list(enriched_question)  # Search with enriched

    # === 1. Broad semantic search (for recall) ===
    semantic_results = search(query_embedding, n_results=top_k * 2)

    # === 2. Keyword-based topic search (for precision) ===
    detected_topics = _detect_topics(enriched_question)
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


def _normalize_arabic(text: str) -> str:
    """Light Arabic normalization for better matching."""
    # Remove common prefixes/suffixes that block substring matching
    # Also strip ال التعريف from question for flexible matching
    import re
    text = re.sub(r'[إأآا]', 'ا', text)  # Normalize alef variants
    return text


# Verb/derived forms → topic mapping (handles Arabic morphology)
LEGAL_VERB_MAP = {
    "أعترض": "مرافعات - أحكام ختامية", "يعترض": "مرافعات - أحكام ختامية",
    "أستأنف": "مرافعات - أحكام ختامية", "يستأنف": "مرافعات - أحكام ختامية",
    "أطعن": "مرافعات - أحكام ختامية", "يطعن": "مرافعات - أحكام ختامية",
    "أرفع": "رفع الدعوى", "يرفع": "رفع الدعوى",
    "أوثق": "عقد الزواج", "يوثق": "عقد الزواج",
    "أثبت": "إثبات - أحكام عامة", "يثبت": "إثبات - أحكام عامة",
    "أنفق": "النفقة", "ينفق": "النفقة",
    "طلقني": "الطلاق", "طلقها": "الطلاق", "يطلق": "الطلاق",
    "خالعت": "الخلع", "خالعني": "الخلع",
}

# Short words that are too ambiguous — only match as whole words
_SHORT_AMBIGUOUS = {"عرف", "رد", "سند", "دفع", "ركن", "أقر"}


def _detect_topics(question: str) -> list[str]:
    """Detect specific legal topics from question keywords (longest match first).
    Uses both LEGAL_TERM_MAP (noun phrases) and LEGAL_VERB_MAP (verb forms).
    """
    topics = []
    seen = set()
    q = question.strip()

    # 1. Check verb forms first
    for verb, topic in LEGAL_VERB_MAP.items():
        if verb in q and topic not in seen:
            topics.append(topic)
            seen.add(topic)

    # 2. Sort LEGAL_TERM_MAP by key length descending for longest-match-first
    sorted_terms = sorted(LEGAL_TERM_MAP.items(), key=lambda x: len(x[0]), reverse=True)

    for term, topic in sorted_terms:
        if topic in seen:
            continue

        # Short ambiguous words: require word-boundary match (space or start/end)
        if term in _SHORT_AMBIGUOUS:
            import re
            if re.search(r'(?:^|\s)' + re.escape(term) + r'(?:\s|$)', q):
                topics.append(topic)
                seen.add(topic)
            continue

        # For regular terms: also try with/without ال prefix for flexibility
        if term in q:
            topics.append(topic)
            seen.add(topic)
        elif len(term) > 3:
            # Try adding/removing ال for flexible matching
            if term.startswith("ال") and term[2:] in q:
                topics.append(topic)
                seen.add(topic)
            elif not term.startswith("ال") and ("ال" + term) in q:
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
