"""
استخراج المواد القانونية من كتاب شرح نظام الأحوال الشخصية
وتحويلها إلى JSON منظم لاستخدامه في RAG Pipeline
"""
import json
import re
import os
import sys
import PyPDF2

# Law structure based on table of contents analysis
LAW_STRUCTURE = {
    "الباب الأول": {
        "title": "الزواج",
        "chapters": {
            "الفصل الأول": "الخطبة",
            "الفصل الثاني": "أركان عقد الزواج وشروطه",
            "الفصل الثالث": "المهر",
            "الفصل الرابع": "حقوق الزوجين",
        },
        "article_range": (1, 42),
    },
    "الباب الثاني": {
        "title": "آثار عقد الزواج",
        "chapters": {
            "الفصل الأول": "النفقة",
            "الفصل الثاني": "النسب",
        },
        "article_range": (43, 76),
    },
    "الباب الثالث": {
        "title": "الفرقة بين الزوجين",
        "chapters": {
            "الفصل الأول": "الطلاق",
            "الفصل الثاني": "الخلع",
            "الفصل الثالث": "فسخ عقد الزواج",
            "الفصل الرابع": "التحكيم في حال الشقاق",
        },
        "article_range": (77, 117),
    },
    "الباب الرابع": {
        "title": "آثار الفرقة بين الزوجين",
        "chapters": {
            "الفصل الأول": "العدة",
            "الفصل الثاني": "الحضانة",
        },
        "article_range": (118, 144),
    },
    "الباب الخامس": {
        "title": "الوصاية والولاية",
        "chapters": {
            "الفصل الأول": "أحكام عامة للوصاية والولاية",
            "الفصل الثاني": "الوصي",
            "الفصل الثالث": "الولي المعين من المحكمة",
            "الفصل الرابع": "تصرفات الوصي والولي",
            "الفصل الخامس": "الغائبون والمفقودون",
        },
        "article_range": (145, 183),
    },
    "الباب السادس": {
        "title": "الوصية",
        "chapters": {
            "الفصل الأول": "أحكام عامة للوصية",
            "الفصل الثاني": "أركان الوصية وشروطها",
            "الفصل الثالث": "مبطلات الوصية",
        },
        "article_range": (184, 207),
    },
    "الباب السابع": {
        "title": "التركة والإرث",
        "chapters": {
            "الفصل الأول": "أحكام عامة للتركة والإرث",
            "الفصل الثاني": "الإرث بالفرض",
            "الفصل الثالث": "الإرث بالتعصيب",
            "الفصل الرابع": "الحجب والعول والرد",
            "الفصل الخامس": "ميراث المفقود والحمل ومنفي النسب",
            "الفصل السادس": "التخارج في التركة",
        },
        "article_range": (208, 232),
    },
}

# Topic tags mapping for common legal topics
TOPIC_TAGS = {
    "خطبة": ["خطبة", "مهر", "هدية", "عدول"],
    "زواج": ["زواج", "عقد", "إيجاب", "قبول", "ولي", "شهود"],
    "مهر": ["مهر", "صداق", "مهر المثل", "مسمى"],
    "طلاق": ["طلاق", "رجعي", "بائن", "يمين", "عدة"],
    "خلع": ["خلع", "عوض", "فدية", "كراهة"],
    "فسخ": ["فسخ", "عيب", "ضرر", "غياب", "إيلاء"],
    "نفقة": ["نفقة", "إنفاق", "سكن", "كسوة", "طعام"],
    "حضانة": ["حضانة", "محضون", "حاضن", "زيارة"],
    "نسب": ["نسب", "إثبات", "إقرار", "ولادة"],
    "وصاية": ["وصاية", "وصي", "قاصر", "ولاية"],
    "وصية": ["وصية", "موصي", "موصى له", "ثلث"],
    "إرث": ["إرث", "ميراث", "تركة", "فرض", "تعصيب", "حجب"],
    "عدة": ["عدة", "طلاق", "وفاة", "حمل"],
    "ولاية": ["ولاية", "ولي", "عضل", "إذن"],
}

# Common deadlines in the law
DEADLINE_ARTICLES = {
    95: "عدة الطلاق - ثلاث حيضات أو ثلاثة أشهر",
    96: "عدة الوفاة - أربعة أشهر وعشرة أيام",
    97: "عدة الحامل - وضع الحمل",
    118: "مدة العدة",
    119: "عدة المتوفى عنها زوجها",
}


def extract_text_from_pdf(pdf_path: str) -> list[dict]:
    """Extract text from all pages of a PDF."""
    pages = []
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                pages.append({"page_number": i + 1, "text": text.strip()})
    return pages


def get_chapter_for_article(article_num: int) -> dict:
    """Determine the chapter and section for a given article number."""
    for bab_key, bab_info in LAW_STRUCTURE.items():
        start, end = bab_info["article_range"]
        if start <= article_num <= end:
            return {
                "chapter": bab_key,
                "chapter_title": bab_info["title"],
                "sections": bab_info["chapters"],
            }
    return {"chapter": "غير محدد", "chapter_title": "غير محدد", "sections": {}}


def get_topic_tags(text: str) -> list[str]:
    """Extract topic tags from article text."""
    tags = set()
    for topic, keywords in TOPIC_TAGS.items():
        for kw in keywords:
            if kw in text:
                tags.add(topic)
                break
    return list(tags)


def get_related_articles(article_num: int, text: str) -> list[int]:
    """Find related article numbers mentioned in the text."""
    related = set()
    # Match Arabic article number references
    patterns = [
        r'المادة\s*\(?\s*(\d+)\s*\)?',
        r'المادة\s+(\d+)',
        r'للمادة\s*\(?\s*(\d+)\s*\)?',
        r'بالمادة\s*\(?\s*(\d+)\s*\)?',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for m in matches:
            num = int(m)
            if num != article_num and 1 <= num <= 232:
                related.add(num)
    return sorted(list(related))


def check_deadline(text: str) -> tuple[bool, str]:
    """Check if article contains deadline information."""
    deadline_keywords = [
        "مهلة", "مدة", "خلال", "أيام", "أشهر", "شهر",
        "سنة", "سنتين", "حيضات", "ثلاثين يوماً",
        "عدة", "أربعة أشهر", "ثلاثة أشهر",
    ]
    for kw in deadline_keywords:
        if kw in text:
            return True, kw
    return False, ""


def build_articles_from_pages(pages: list[dict]) -> list[dict]:
    """
    Build structured articles from extracted PDF pages.
    Since Arabic PDF extraction can be messy, we build a comprehensive
    knowledge base from the full text.
    """
    articles = []

    # Combine all text
    full_text = "\n".join(p["text"] for p in pages)

    # Try to split by article patterns
    # Arabic numbers for articles: المادة الأولى, المادة الثانية, etc.
    arabic_ordinals = {
        "الأولى": 1, "الثانية": 2, "الثالثة": 3, "الرابعة": 4,
        "الخامسة": 5, "السادسة": 6, "السابعة": 7, "الثامنة": 8,
        "التاسعة": 9, "العاشرة": 10,
        "الحادية عشرة": 11, "الثانية عشرة": 12, "الثالثة عشرة": 13,
        "الرابعة عشرة": 14, "الخامسة عشرة": 15, "السادسة عشرة": 16,
        "السابعة عشرة": 17, "الثامنة عشرة": 18, "التاسعة عشرة": 19,
        "العشرون": 20,
        "الحادية والعشرون": 21, "الثانية والعشرون": 22,
        "الثالثة والعشرون": 23, "الرابعة والعشرون": 24,
        "الخامسة والعشرون": 25,
        "الثلاثون": 30, "الأربعون": 40, "الخمسون": 50,
        "الستون": 60, "السبعون": 70, "الثمانون": 80,
        "التسعون": 90, "المائة": 100,
        "العشرون بعد المائة": 120,
        "الثلاثون بعد المائة": 130,
        "الأربعون بعد المائة": 140,
        "الخمسون بعد المائة": 150,
        "المائتان": 200,
        "العاشرة بعد المائتين": 210,
        "العشرون بعد المائتين": 220,
        "الثلاثون بعد المائتين": 230,
    }

    # Since PDF extraction is imperfect for Arabic,
    # build knowledge chunks from page ranges based on TOC
    page_ranges = {
        # Chapter: (start_page, end_page, title)
        "الخطبة": (12, 25, "الباب الأول", "الفصل الأول - الخطبة"),
        "أركان العقد": (25, 55, "الباب الأول", "الفصل الثاني - أركان عقد الزواج"),
        "المهر": (55, 90, "الباب الأول", "الفصل الثالث - المهر"),
        "حقوق الزوجين": (90, 97, "الباب الأول", "الفصل الرابع - حقوق الزوجين"),
        "النفقة": (97, 140, "الباب الثاني", "الفصل الأول - النفقة"),
        "النسب": (140, 160, "الباب الثاني", "الفصل الثاني - النسب"),
        "الطلاق": (160, 195, "الباب الثالث", "الفصل الأول - الطلاق"),
        "الخلع": (195, 215, "الباب الثالث", "الفصل الثاني - الخلع"),
        "فسخ الزواج": (215, 235, "الباب الثالث", "الفصل الثالث - فسخ عقد الزواج"),
        "العدة": (233, 250, "الباب الرابع", "الفصل الأول - العدة"),
        "الحضانة": (250, 272, "الباب الرابع", "الفصل الثاني - الحضانة"),
        "الوصاية والولاية": (272, 337, "الباب الخامس", "الوصاية والولاية"),
        "الوصية": (337, 389, "الباب السادس", "الوصية"),
        "التركة والإرث": (389, 495, "الباب السابع", "التركة والإرث"),
    }

    article_id = 0
    for topic, (start, end, bab, section) in page_ranges.items():
        # Extract text for this section
        section_pages = [p for p in pages if start <= p["page_number"] <= end]
        section_text = "\n".join(p["text"] for p in section_pages)

        if not section_text.strip():
            continue

        # Split section into chunks of ~1500 chars for better RAG
        chunks = split_text_into_chunks(section_text, max_chars=1500)

        for i, chunk in enumerate(chunks):
            article_id += 1
            has_deadline, deadline_detail = check_deadline(chunk)
            tags = get_topic_tags(chunk)
            if not tags:
                tags = [topic]

            articles.append({
                "id": f"chunk_{article_id}",
                "chunk_index": i,
                "text": chunk,
                "chapter": bab,
                "section": section,
                "topic": topic,
                "topic_tags": tags,
                "has_deadline": has_deadline,
                "deadline_details": deadline_detail if has_deadline else "",
                "source_pages": f"{start}-{end}",
            })

    return articles


def split_text_into_chunks(text: str, max_chars: int = 1500) -> list[str]:
    """Split text into chunks, trying to break at sentence boundaries."""
    if len(text) <= max_chars:
        return [text] if text.strip() else []

    chunks = []
    current = ""

    # Split by common sentence boundaries
    sentences = re.split(r'(?<=[.،؛:!؟\n])\s+', text)

    for sentence in sentences:
        if not sentence.strip():
            continue
        if len(current) + len(sentence) <= max_chars:
            current += " " + sentence if current else sentence
        else:
            if current:
                chunks.append(current.strip())
            current = sentence

    if current.strip():
        chunks.append(current.strip())

    return chunks


def extract_regulations(pdf_path: str) -> list[dict]:
    """Extract articles from the executive regulations PDF."""
    pages = extract_text_from_pdf(pdf_path)
    regulations = []

    full_text = "\n".join(p["text"] for p in pages)

    # The regulations text is reversed (RTL extraction issue)
    # Split into articles based on pattern
    chunks = split_text_into_chunks(full_text, max_chars=1000)

    for i, chunk in enumerate(chunks):
        if chunk.strip():
            tags = get_topic_tags(chunk)
            has_deadline, detail = check_deadline(chunk)
            regulations.append({
                "id": f"reg_{i+1}",
                "text": chunk,
                "chapter": "اللائحة التنفيذية",
                "section": "لائحة نظام الأحوال الشخصية",
                "topic": "لائحة تنفيذية",
                "topic_tags": tags or ["لائحة"],
                "has_deadline": has_deadline,
                "deadline_details": detail if has_deadline else "",
                "source_pages": "لائحة",
            })

    return regulations


def main():
    """Main extraction pipeline."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(os.path.dirname(script_dir))

    explanation_pdf = os.path.join(project_dir, "شرح نظام الأحوال الشخصية.pdf")
    regulations_pdf = os.path.join(project_dir, "pdf.pdf")

    print("=" * 60)
    print("استخراج المواد القانونية من نظام الأحوال الشخصية")
    print("=" * 60)

    all_articles = []

    # 1. Extract from explanation book (508 pages)
    if os.path.exists(explanation_pdf):
        print(f"\nاستخراج من كتاب الشرح: {explanation_pdf}")
        pages = extract_text_from_pdf(explanation_pdf)
        print(f"  تم استخراج {len(pages)} صفحة")
        articles = build_articles_from_pages(pages)
        print(f"  تم إنشاء {len(articles)} مقطع معرفي")
        all_articles.extend(articles)
    else:
        print(f"تنبيه: ملف الشرح غير موجود: {explanation_pdf}")

    # 2. Extract from regulations (5 pages)
    if os.path.exists(regulations_pdf):
        print(f"\nاستخراج من اللائحة: {regulations_pdf}")
        regulations = extract_regulations(regulations_pdf)
        print(f"  تم إنشاء {len(regulations)} مقطع من اللائحة")
        all_articles.extend(regulations)
    else:
        print(f"تنبيه: ملف اللائحة غير موجود: {regulations_pdf}")

    # 3. Save to JSON
    output_path = os.path.join(script_dir, "articles.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "total_chunks": len(all_articles),
            "law_name": "نظام الأحوال الشخصية",
            "royal_decree": "م/73",
            "decree_date": "1443/6/8هـ",
            "structure": {k: v["title"] for k, v in LAW_STRUCTURE.items()},
            "articles": all_articles,
        }, f, ensure_ascii=False, indent=2)

    print(f"\n✓ تم حفظ {len(all_articles)} مقطع في: {output_path}")

    # Print summary
    topics = {}
    for a in all_articles:
        t = a.get("topic", "غير محدد")
        topics[t] = topics.get(t, 0) + 1

    print("\nتوزيع المقاطع حسب الموضوع:")
    for topic, count in sorted(topics.items(), key=lambda x: -x[1]):
        print(f"  {topic}: {count}")

    return all_articles


if __name__ == "__main__":
    main()
