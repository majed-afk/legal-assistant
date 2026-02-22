"""
Initialize the vector database with law articles.
Run this script after extracting articles to build the search index.
"""
import json
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(project_root))

from backend.config import ARTICLES_JSON_PATH, CHROMA_PERSIST_DIR
from backend.rag.embeddings import embed_texts
from backend.rag.vector_store import add_documents, get_collection_count


def setup_database(force_rebuild: bool = False):
    """Load articles from JSON and store them in ChromaDB.

    Supports resuming: if the DB already has some articles,
    only the missing ones are embedded and added.
    """
    print("=" * 60)
    print("إعداد قاعدة البيانات المتجهة (Vector Database)")
    print("=" * 60)

    # Load articles
    if not os.path.exists(ARTICLES_JSON_PATH):
        print(f"خطأ: ملف المواد غير موجود: {ARTICLES_JSON_PATH}")
        print("قم بتشغيل extract_articles.py أولاً")
        return

    with open(ARTICLES_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    articles = data["articles"]
    total = len(articles)
    print(f"تم تحميل {total} مقطع")

    # Check existing state
    existing_count = get_collection_count()

    if force_rebuild and existing_count > 0:
        print(f"إعادة بناء كاملة — حذف {existing_count} مقطع موجود...")
        import chromadb
        client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        client.delete_collection("saudi_family_law")
        import backend.rag.vector_store as vs
        vs._collection = None
        vs._client = None
        existing_count = 0

    if existing_count >= total:
        print(f"✅ قاعدة البيانات مكتملة — {existing_count}/{total} مقطع")
        return

    # Find which article IDs are already stored so we can skip them
    existing_ids = set()
    if existing_count > 0:
        from backend.rag.vector_store import get_collection
        col = get_collection()
        # Get all stored IDs
        stored = col.get(include=[])
        existing_ids = set(stored["ids"])
        print(f"تم العثور على {len(existing_ids)}/{total} مقطع محفوظ — استكمال الباقي...")

    # Filter to only missing articles
    missing = [(a, i) for i, a in enumerate(articles) if a["id"] not in existing_ids]
    print(f"المقاطع المتبقية: {len(missing)}")

    if not missing:
        print("✅ جميع المقاطع محفوظة بالفعل")
        return

    # Prepare data for missing articles only
    ids = [a["id"] for a, _ in missing]
    texts = [a["text"] for a, _ in missing]
    metadatas = [
        {
            "chapter": a.get("chapter", ""),
            "section": a.get("section", ""),
            "topic": a.get("topic", ""),
            "topic_tags": ",".join(a.get("topic_tags", [])),
            "has_deadline": str(a.get("has_deadline", False)),
            "deadline_details": a.get("deadline_details", ""),
            "source_pages": a.get("source_pages", ""),
        }
        for a, _ in missing
    ]

    # Generate embeddings AND store incrementally (batch by batch)
    print(f"\nتوليد التضمينات وتخزينها تدريجياً لـ {len(texts)} مقطع...")

    batch_size = 25  # Smaller batches to stay within Gemini API rate limits
    stored_count = 0
    for i in range(0, len(texts), batch_size):
        end = min(i + batch_size, len(texts))
        batch_texts = texts[i:end]
        batch_ids = ids[i:end]
        batch_metas = metadatas[i:end]
        print(f"  معالجة {i+1}-{end} من {len(texts)} (متبقي)...")
        try:
            embeddings = embed_texts(batch_texts)
            add_documents(batch_ids, batch_texts, embeddings, batch_metas)
            stored_count += len(batch_texts)
            print(f"  ✓ تم تخزين {existing_count + stored_count}/{total} مقطع إجمالاً")
        except Exception as e:
            print(f"  ⚠️ فشل في معالجة المقاطع {i+1}-{end}: {e}")
            continue

    final_count = get_collection_count()
    print(f"\n✓ إجمالي المقاطع في قاعدة البيانات: {final_count}/{total}")
    print(f"  المسار: {CHROMA_PERSIST_DIR}")
    if final_count < total:
        print(f"  ⚠️ {total - final_count} مقطع لم يتم تخزينها — سيتم استكمالها عند إعادة التشغيل")


if __name__ == "__main__":
    setup_database()
