"""
Rebuild articles.json with clean أحوال شخصية text.
Keeps إثبات and مرافعات articles as-is, replaces أحوال شخصية.
"""
import json

CLEAN_AHWAL_PATH = "/Users/majedalkhudhayr/Desktop/المحامي/backend/data/ahwal_clean_articles.json"
EXISTING_PATH = "/Users/majedalkhudhayr/Desktop/المحامي/backend/data/articles.json"
OUTPUT_PATH = "/Users/majedalkhudhayr/Desktop/المحامي/backend/data/articles.json"
BACKUP_PATH = "/Users/majedalkhudhayr/Desktop/المحامي/backend/data/articles.json.backup_pre_clean"


def _generate_tags(topic, text):
    """Simple tag generation from topic and text."""
    tags = []
    if topic:
        tags.append(topic)
    keywords = ["زواج", "طلاق", "خلع", "نفقة", "حضانة", "مهر", "إرث", "وصية",
                 "ولاية", "شهادة", "فسخ", "عدة", "نسب", "خطبة"]
    for kw in keywords:
        if kw in text and kw not in tags:
            tags.append(kw)
    return tags[:5]


def main():
    # Load existing
    with open(EXISTING_PATH, "r", encoding="utf-8") as f:
        existing = json.load(f)

    existing_articles = existing["articles"]

    # Separate non-ahwal articles
    other_articles = [a for a in existing_articles if a.get("law") != "نظام الأحوال الشخصية"]
    old_ahwal = [a for a in existing_articles if a.get("law") == "نظام الأحوال الشخصية"]

    print(f"Existing: {len(old_ahwal)} أحوال + {len(other_articles)} other = {len(existing_articles)} total")

    # Load clean ahwal articles
    with open(CLEAN_AHWAL_PATH, "r", encoding="utf-8") as f:
        clean_ahwal = json.load(f)

    print(f"Clean أحوال شخصية: {len(clean_ahwal)} articles")

    # Build old article lookup for preserving metadata
    old_by_num = {a["article_number"]: a for a in old_ahwal}

    # Convert clean articles to match existing format
    new_ahwal = []
    for art in clean_ahwal:
        num = art["article_number"]
        old = old_by_num.get(num, {})

        # Format text with article prefix (matching existing format)
        text = f"المادة {num}: {art['text']}"

        new_article = {
            "law": "نظام الأحوال الشخصية",
            "article_number": num,
            "text": text,
            "id": f"ahwal_{num}",
            "chunk_index": num,
            "chapter": art["chapter"],
            "section": art["section"],
            "topic": art["topic"],
            "topic_tags": old.get("topic_tags", []),
            "has_deadline": old.get("has_deadline", False),
            "deadline_details": old.get("deadline_details", ""),
            "source_pages": "نظام الأحوال الشخصية - م/73 - 1443هـ",
        }

        # Generate topic_tags if not from old
        if not new_article["topic_tags"]:
            new_article["topic_tags"] = _generate_tags(art["topic"], art["text"])

        new_ahwal.append(new_article)

    print(f"New أحوال شخصية: {len(new_ahwal)} articles")

    # Combine all articles
    all_articles = new_ahwal + other_articles
    all_articles.sort(key=lambda a: (a.get("law", ""), a.get("article_number", 0)))

    # Backup existing
    with open(BACKUP_PATH, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    print(f"Backup saved to {BACKUP_PATH}")

    # Save new articles.json
    output = {
        "articles": all_articles,
        "total_chunks": len(all_articles),
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nNew articles.json: {len(all_articles)} total articles")
    print(f"  - أحوال شخصية: {len(new_ahwal)}")
    print(f"  - إثبات: {len([a for a in other_articles if 'إثبات' in a.get('law', '')])}")
    print(f"  - مرافعات: {len([a for a in other_articles if 'مرافعات' in a.get('law', '')])}")

    # Verify
    print("\n=== Sample clean articles ===")
    for a in new_ahwal[:3]:
        print(f"  Art {a['article_number']}: {a['text'][:80]}...")
    print(f"  Art {new_ahwal[-1]['article_number']}: {new_ahwal[-1]['text'][:80]}...")


if __name__ == "__main__":
    main()
