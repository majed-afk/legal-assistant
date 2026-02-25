"""
Sanad AI — FastAPI Backend (أحوال شخصية + معاملات مدنية + إثبات + مرافعات)
"""
from __future__ import annotations
import json
import os
from contextlib import asynccontextmanager
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Track whether vector DB is ready (for health check)
_db_ready = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize ChromaDB at startup — DB is pre-built during Docker build."""
    global _db_ready
    print("⏳ جاري تهيئة ChromaDB...")
    from backend.rag.vector_store import get_collection, get_collection_count
    col = get_collection()
    count = col.count()

    if count > 0:
        _db_ready = True
        print(f"✅ ChromaDB جاهز — {count} مادة مفهرسة")
    else:
        # DB not built (shouldn't happen with pre-computed embeddings in Docker)
        # Try building from pre-computed embeddings as fallback
        print("⚠️ قاعدة البيانات فارغة — محاولة البناء من التضمينات المحسوبة مسبقاً...")
        try:
            from backend.tools.setup_db import setup_database
            setup_database()
            count = get_collection_count()
            if count > 0:
                _db_ready = True
                print(f"✅ تم بناء قاعدة البيانات — {count} مادة مفهرسة")
        except Exception as e:
            print(f"⚠️ فشل بناء قاعدة البيانات: {e}")

    print("🚀 السيرفر جاهز لاستقبال الطلبات")
    yield


app = FastAPI(
    title="Sanad AI — سند",
    description="مستشار قانوني ذكي متخصص في أنظمة الأحوال الشخصية والمعاملات المدنية والإثبات والمرافعات الشرعية السعودية",
    version="2.0.0",
    lifespan=lifespan,
)

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001").split(",")

# Security middleware (order matters: CORS first, then auth, then rate limit)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from backend.middleware import AuthMiddleware, RateLimitMiddleware
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthMiddleware)


# --- Request / Response Models ---

class QuestionRequest(BaseModel):
    question: str
    chat_history: Optional[List[Dict]] = None
    model_mode: Optional[str] = "2.1"  # "1.1" (quick) or "2.1" (detailed)

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
    count = get_collection_count()
    return {
        "status": "healthy",
        "service": "Sanad AI",
        "vector_db_count": count,
        "db_ready": _db_ready,
        "db_complete": count >= 1200,
        "laws": ["أحوال شخصية", "معاملات مدنية", "إثبات", "مرافعات شرعية"],
    }


@app.post("/api/ask")
async def ask_question(req: QuestionRequest):
    """Legal consultation endpoint."""
    from backend.rag.pipeline import retrieve_context
    from backend.services.legal_assistant import generate_legal_response

    if not req.question.strip():
        raise HTTPException(status_code=400, detail="السؤال مطلوب")

    if not _db_ready:
        raise HTTPException(
            status_code=503,
            detail="جاري تجهيز قاعدة البيانات... يرجى المحاولة بعد دقيقة"
        )

    rag_result = retrieve_context(req.question, chat_history=req.chat_history)

    try:
        answer = generate_legal_response(
            question=req.question,
            context=rag_result["context"],
            classification=rag_result["classification"],
            chat_history=req.chat_history,
            model_mode=req.model_mode or "2.1",
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


@app.post("/api/ask-stream")
async def ask_question_stream(req: QuestionRequest):
    """Legal consultation endpoint with SSE streaming."""
    from backend.rag.pipeline import retrieve_context
    from backend.services.legal_assistant import stream_legal_response

    if not req.question.strip():
        raise HTTPException(status_code=400, detail="السؤال مطلوب")

    if not _db_ready:
        raise HTTPException(
            status_code=503,
            detail="جاري تجهيز قاعدة البيانات... يرجى المحاولة بعد دقيقة"
        )

    rag_result = retrieve_context(req.question, chat_history=req.chat_history)

    def event_stream():
        # Send metadata first (classification + sources)
        meta = json.dumps({
            "type": "meta",
            "classification": rag_result["classification"],
            "sources": rag_result["sources"],
            "has_deadlines": rag_result["classification"].get("needs_deadline_check", False),
        }, ensure_ascii=False)
        yield f"data: {meta}\n\n"

        # Stream Claude response token by token
        try:
            for token in stream_legal_response(
                question=req.question,
                context=rag_result["context"],
                classification=rag_result["classification"],
                chat_history=req.chat_history,
                model_mode=req.model_mode or "2.1",
            ):
                chunk = json.dumps({"type": "token", "text": token}, ensure_ascii=False)
                yield f"data: {chunk}\n\n"

            # Signal completion
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            import traceback
            traceback.print_exc()
            # Show user-friendly Arabic error instead of raw API errors
            error_msg = str(e)
            if "rate_limit" in error_msg.lower() or "429" in error_msg:
                user_error = "الخادم مشغول حالياً — يرجى الانتظار بضع ثوانٍ ثم إعادة المحاولة"
            elif "overloaded" in error_msg.lower() or "529" in error_msg:
                user_error = "الخادم مشغول — يرجى المحاولة مرة أخرى بعد لحظات"
            elif "api_key" in error_msg.lower() or "auth" in error_msg.lower():
                user_error = "خطأ في إعدادات النظام — يرجى التواصل مع الإدارة"
            else:
                user_error = "حدث خطأ أثناء معالجة طلبك — يرجى المحاولة مرة أخرى"
            error = json.dumps({"type": "error", "message": user_error}, ensure_ascii=False)
            yield f"data: {error}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/search")
async def search_articles(req: SearchRequest):
    """Search law articles."""
    if not _db_ready:
        raise HTTPException(
            status_code=503,
            detail="جاري تجهيز قاعدة البيانات... يرجى المحاولة بعد دقيقة"
        )

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
