"""
FastAPI Backend — المساعد القانوني لنظام الأحوال الشخصية
"""
from __future__ import annotations
import json
import os
from contextlib import asynccontextmanager
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize ChromaDB at startup. Build vector DB if empty (first deploy)."""
    print("⏳ جاري تهيئة ChromaDB...")
    from backend.rag.vector_store import get_collection
    col = get_collection()
    count = col.count()

    if count == 0:
        print("📦 قاعدة البيانات فارغة — جاري بناء الفهرس عبر Gemini API...")
        from backend.tools.setup_db import setup_database
        setup_database()
        count = col.count()

    print(f"✅ ChromaDB جاهز — {count} مادة مفهرسة")
    print("✅ Embeddings عبر Gemini API (بدون نموذج محلي — ذاكرة خفيفة)")
    yield


app = FastAPI(
    title="مساعد الأحوال الشخصية",
    description="مساعد قانوني ذكي متخصص في نظام الأحوال الشخصية السعودي",
    version="1.0.0",
    lifespan=lifespan,
)

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request / Response Models ---

class QuestionRequest(BaseModel):
    question: str
    chat_history: Optional[List[Dict]] = None

class DraftRequest(BaseModel):
    draft_type: str
    case_details: Dict

class DeadlineRequest(BaseModel):
    event_type: str
    event_date: str
    details: Optional[Dict] = None

class SearchRequest(BaseModel):
    query: str
    topic: Optional[str] = None
    top_k: int = 10


# --- Endpoints ---

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    from backend.rag.vector_store import get_collection_count
    return {
        "status": "healthy",
        "service": "مساعد الأحوال الشخصية",
        "vector_db_count": get_collection_count(),
    }


@app.post("/api/ask")
async def ask_question(req: QuestionRequest):
    """Legal consultation endpoint."""
    from backend.rag.pipeline import retrieve_context
    from backend.services.legal_assistant import generate_legal_response

    if not req.question.strip():
        raise HTTPException(status_code=400, detail="السؤال مطلوب")

    rag_result = retrieve_context(req.question)

    try:
        answer = generate_legal_response(
            question=req.question,
            context=rag_result["context"],
            classification=rag_result["classification"],
            chat_history=req.chat_history,
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"خطأ في الاتصال بـ Claude API: {str(e)}")

    return {
        "answer": answer,
        "classification": rag_result["classification"],
        "sources": rag_result["sources"],
        "has_deadlines": rag_result["classification"].get("needs_deadline_check", False),
    }


@app.post("/api/search")
async def search_articles(req: SearchRequest):
    """Search law articles."""
    from backend.rag.embeddings import embed_query_list
    from backend.rag.vector_store import search

    query_embedding = embed_query_list(req.query)

    where_filter = None
    if req.topic:
        where_filter = {"topic": {"$eq": req.topic}}

    results = search(query_embedding, n_results=req.top_k, where=where_filter)

    articles = []
    if results["documents"] and results["documents"][0]:
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            articles.append({
                "text": doc,
                "chapter": meta.get("chapter", ""),
                "section": meta.get("section", ""),
                "topic": meta.get("topic", ""),
                "similarity": round(1 - dist, 3),
            })

    return {"query": req.query, "results": articles, "total": len(articles)}


@app.get("/api/articles")
async def get_all_articles():
    """Get all articles grouped by chapter."""
    from backend.config import ARTICLES_JSON_PATH

    if not os.path.exists(ARTICLES_JSON_PATH):
        raise HTTPException(status_code=404, detail="ملف المواد غير موجود")

    with open(ARTICLES_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Group by chapter
    chapters = {}
    for article in data["articles"]:
        ch = article.get("chapter", "غير محدد")
        if ch not in chapters:
            chapters[ch] = {
                "chapter": ch,
                "sections": {},
                "count": 0,
            }
        section = article.get("section", "غير محدد")
        if section not in chapters[ch]["sections"]:
            chapters[ch]["sections"][section] = []
        chapters[ch]["sections"][section].append({
            "id": article["id"],
            "text": article["text"][:300] + "..." if len(article["text"]) > 300 else article["text"],
            "topic": article.get("topic", ""),
            "topic_tags": article.get("topic_tags", []),
        })
        chapters[ch]["count"] += 1

    return {
        "law_name": data.get("law_name", ""),
        "royal_decree": data.get("royal_decree", ""),
        "total_articles": data.get("total_chunks", 0),
        "structure": data.get("structure", {}),
        "chapters": chapters,
    }


@app.get("/api/articles/topics")
async def get_topics():
    """Get available topics."""
    from backend.config import ARTICLES_JSON_PATH

    with open(ARTICLES_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    topics = {}
    for article in data["articles"]:
        t = article.get("topic", "غير محدد")
        topics[t] = topics.get(t, 0) + 1

    return {"topics": [{"name": k, "count": v} for k, v in sorted(topics.items(), key=lambda x: -x[1])]}


@app.post("/api/draft")
async def draft_document(req: DraftRequest):
    """Draft a legal document."""
    from backend.services.document_drafter import validate_draft_request, build_drafting_prompt, get_draft_types
    from backend.rag.pipeline import retrieve_context
    from backend.services.legal_assistant import generate_draft

    valid, error = validate_draft_request(req.draft_type, req.case_details)
    if not valid:
        raise HTTPException(status_code=400, detail=error)

    prompt = build_drafting_prompt(req.draft_type, req.case_details)
    rag_result = retrieve_context(prompt)

    try:
        draft = generate_draft(req.draft_type, req.case_details, rag_result["context"])
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"خطأ في صياغة المذكرة: {str(e)}")

    return {
        "draft": draft,
        "draft_type": req.draft_type,
        "sources": rag_result["sources"],
    }


@app.get("/api/draft/types")
async def get_draft_types_endpoint():
    """Get available draft types."""
    from backend.services.document_drafter import get_draft_types
    return {"types": get_draft_types()}


@app.post("/api/deadline")
async def calculate_deadline(req: DeadlineRequest):
    """Calculate legal deadlines."""
    from backend.services.deadline_calculator import calculate_deadline as calc

    result = calc(req.event_type, req.event_date, req.details)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get("/api/deadline/types")
async def get_deadline_types():
    """Get available deadline event types."""
    return {
        "types": [
            {"type": "divorce", "name": "طلاق", "description": "حساب عدة الطلاق ومهل المراجعة"},
            {"type": "death", "name": "وفاة", "description": "حساب عدة الوفاة"},
            {"type": "judgment", "name": "حكم قضائي", "description": "حساب مهل الاعتراض"},
            {"type": "custody", "name": "حضانة", "description": "مواعيد متعلقة بالحضانة"},
            {"type": "appeal", "name": "استئناف", "description": "حساب مهل الاستئناف والنقض"},
        ]
    }
