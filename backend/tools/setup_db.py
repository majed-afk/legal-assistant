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


def setup_database():
    """Load articles from JSON and store them in ChromaDB."""
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
    print(f"تم تحميل {len(articles)} مقطع")

    # Check if already populated
    existing_count = get_collection_count()
    if existing_count > 0:
        print(f"قاعدة البيانات تحتوي بالفعل على {existing_count} مقطع")
        print("حذف البيانات القديمة وإعادة البناء...")
        import chromadb
        client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        client.delete_collection("saudi_family_law")
        # Reset the module-level variables
        import backend.rag.vector_store as vs
        vs._collection = None
        vs._client = None

    # Prepare data
    ids = [a["id"] for a in articles]
    texts = [a["text"] for a in articles]
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
        for a in articles
    ]

    # Generate embeddings AND store incrementally (batch by batch)
    # This way partial progress is saved even if rate limits stop us later
    print(f"\nتوليد التضمينات وتخزينها تدريجياً لـ {len(texts)} مقطع...")

    batch_size = 25  # Smaller batches to stay within Gemini API rate limits
    stored_count = 0
    for i in range(0, len(texts), batch_size):
        end = min(i + batch_size, len(texts))
        batch_texts = texts[i:end]
        batch_ids = ids[i:end]
        batch_metas = metadatas[i:end]
        print(f"  معالجة {i+1}-{end} من {len(texts)}...")
        try:
            embeddings = embed_texts(batch_texts)
            # Store this batch immediately in ChromaDB
            add_documents(batch_ids, batch_texts, embeddings, batch_metas)
            stored_count += len(batch_texts)
            print(f"  ✓ تم تخزين {stored_count}/{len(texts)} مقطع")
        except Exception as e:
            print(f"  ⚠️ فشل في معالجة المقاطع {i+1}-{end}: {e}")
            # Continue with remaining batches — partial DB is better than nothing
            continue

    final_count = get_collection_count()
    print(f"\n✓ تم تخزين {final_count} مقطع في قاعدة البيانات")
    print(f"  المسار: {CHROMA_PERSIST_DIR}")


if __name__ == "__main__":
    setup_database()
