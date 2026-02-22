"""
ChromaDB vector store for law articles.
"""
from __future__ import annotations
import chromadb
from backend.config import CHROMA_PERSIST_DIR

_client = None
_collection = None
COLLECTION_NAME = "saudi_family_law"


def get_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def add_documents(ids: list[str], texts: list[str], embeddings: list[list[float]], metadatas: list[dict]):
    """Add documents to the vector store."""
    collection = get_collection()
    batch_size = 100
    for i in range(0, len(ids), batch_size):
        end = min(i + batch_size, len(ids))
        collection.add(
            ids=ids[i:end],
            documents=texts[i:end],
            embeddings=embeddings[i:end],
            metadatas=metadatas[i:end],
        )


def search(query_embedding: list[float], n_results: int = 5, where: dict = None) -> dict:
    """Search for similar documents."""
    collection = get_collection()
    kwargs = {
        "query_embeddings": [query_embedding],
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        kwargs["where"] = where
    return collection.query(**kwargs)


def get_collection_count() -> int:
    """Get the number of documents in the collection."""
    return get_collection().count()
