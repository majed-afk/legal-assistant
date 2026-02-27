"""
Sanad AI — FastAPI Backend (أحوال شخصية + معاملات مدنية + إثبات + مرافعات)
"""
from __future__ import annotations
import json
import os
from contextlib import asynccontextmanager
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request
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

from backend.middleware import JWTAuthMiddleware
app.add_middleware(JWTAuthMiddleware)


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

class FeedbackRequest(BaseModel):
    message_id: str
    conversation_id: str
    rating: str  # 'positive' or 'negative'
    feedback_type: Optional[str] = None
    correction_text: Optional[str] = None

class AnalyticsEventRequest(BaseModel):
    event_type: str
    event_data: Optional[Dict] = None

class SubscriptionCreateRequest(BaseModel):
    plan_tier: str
    billing_cycle: str = "monthly"


# --- Helper: get user_id from request ---

def _get_user_id(request) -> Optional[str]:
    """Extract user_id from request state (set by JWTAuthMiddleware)."""
    return getattr(request.state, "user_id", None)


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
async def ask_question(req: QuestionRequest, request: Request):
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

    # Check subscription limits
    user_id = _get_user_id(request)
    if user_id:
        from backend.services.subscription import check_limit, check_model_mode, increment_usage
        allowed, msg = await check_limit(user_id, "questions")
        if not allowed:
            raise HTTPException(status_code=429, detail=msg)
        mode_ok, mode_msg = await check_model_mode(user_id, req.model_mode or "2.1")
        if not mode_ok:
            raise HTTPException(status_code=403, detail=mode_msg)

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

    # Increment usage after success
    if user_id:
        await increment_usage(user_id, "questions")

    return {
        "answer": answer,
        "classification": rag_result["classification"],
        "sources": rag_result["sources"],
        "has_deadlines": rag_result["classification"].get("needs_deadline_check", False),
    }


@app.post("/api/ask-stream")
async def ask_question_stream(req: QuestionRequest, request: Request):
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

    # Check subscription limits before streaming
    user_id = _get_user_id(request)
    if user_id:
        from backend.services.subscription import check_limit, check_model_mode, increment_usage
        allowed, msg = await check_limit(user_id, "questions")
        if not allowed:
            raise HTTPException(status_code=429, detail=msg)
        mode_ok, mode_msg = await check_model_mode(user_id, req.model_mode or "2.1")
        if not mode_ok:
            raise HTTPException(status_code=403, detail=mode_msg)
        # Increment usage before streaming (can't do it after for StreamingResponse)
        await increment_usage(user_id, "questions")

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
async def draft_document(req: DraftRequest, request: Request):
    """Draft a legal document."""
    from backend.services.document_drafter import validate_draft_request, build_drafting_prompt, get_draft_types
    from backend.rag.pipeline import retrieve_context
    from backend.services.legal_assistant import generate_draft

    # Check subscription limits
    user_id = _get_user_id(request)
    if user_id:
        from backend.services.subscription import check_limit, increment_usage
        allowed, msg = await check_limit(user_id, "drafts")
        if not allowed:
            raise HTTPException(status_code=429, detail=msg)

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

    # Increment usage after success
    if user_id:
        await increment_usage(user_id, "drafts")

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
async def calculate_deadline(req: DeadlineRequest, request: Request):
    """Calculate legal deadlines."""
    from backend.services.deadline_calculator import calculate_deadline as calc

    # Check subscription limits
    user_id = _get_user_id(request)
    if user_id:
        from backend.services.subscription import check_limit, increment_usage
        allowed, msg = await check_limit(user_id, "deadlines")
        if not allowed:
            raise HTTPException(status_code=429, detail=msg)

    result = calc(req.event_type, req.event_date, req.details)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    # Increment usage after success
    if user_id:
        await increment_usage(user_id, "deadlines")

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


# --- Feedback & Analytics Endpoints ---

@app.post("/api/feedback")
async def submit_feedback(req: FeedbackRequest):
    """Submit feedback (thumbs up/down) on an AI response."""
    from backend.db import get_supabase

    if req.rating not in ("positive", "negative"):
        raise HTTPException(status_code=400, detail="التقييم يجب أن يكون positive أو negative")

    valid_types = {
        "accurate", "helpful", "clear",
        "inaccurate", "unhelpful", "incomplete",
        "wrong_article", "missing_info", "other",
    }
    if req.feedback_type and req.feedback_type not in valid_types:
        raise HTTPException(status_code=400, detail="نوع التقييم غير صالح")

    sb = get_supabase()
    if not sb:
        raise HTTPException(status_code=503, detail="خدمة التقييم غير متوفرة حالياً")

    try:
        result = sb.table("message_feedback").upsert({
            "message_id": req.message_id,
            "conversation_id": req.conversation_id,
            "rating": req.rating,
            "feedback_type": req.feedback_type,
            "correction_text": req.correction_text,
        }, on_conflict="message_id").execute()

        return {"status": "ok", "message": "تم تسجيل التقييم بنجاح"}
    except Exception as e:
        print(f"Feedback error: {e}")
        raise HTTPException(status_code=500, detail="حدث خطأ أثناء تسجيل التقييم")


@app.post("/api/analytics/event")
async def log_analytics_event(req: AnalyticsEventRequest):
    """Log an analytics event (fire-and-forget)."""
    from backend.db import get_supabase

    sb = get_supabase()
    if not sb:
        return {"status": "skipped"}  # Silently skip if Supabase not configured

    try:
        sb.table("analytics_events").insert({
            "event_type": req.event_type,
            "event_data": req.event_data or {},
        }).execute()
        return {"status": "ok"}
    except Exception as e:
        print(f"Analytics event error: {e}")
        return {"status": "error"}  # Don't fail the request for analytics


# --- Subscription & Payment Endpoints ---

@app.get("/api/plans")
async def get_plans():
    """Get all available subscription plans (public endpoint)."""
    from backend.services.subscription import get_all_plans
    plans = await get_all_plans()
    return {"plans": plans}


@app.get("/api/subscription")
async def get_subscription(request: Request):
    """Get current user's subscription details."""
    user_id = _get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="يجب تسجيل الدخول")

    from backend.services.subscription import get_user_subscription
    sub = await get_user_subscription(user_id)
    return sub


@app.post("/api/subscription/create")
async def create_subscription(req: SubscriptionCreateRequest, request: Request):
    """Create a subscription payment via Moyasar."""
    user_id = _get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="يجب تسجيل الدخول")

    from backend.services.payment import create_payment_form_data

    try:
        result = await create_payment_form_data(
            user_id=user_id,
            plan_tier=req.plan_tier,
            billing_cycle=req.billing_cycle,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="حدث خطأ أثناء إنشاء عملية الدفع")


@app.get("/api/subscription/verify")
async def verify_subscription_payment(payment_id: str, tx_id: Optional[str] = None):
    """Verify a payment after 3DS redirect."""
    from backend.services.payment import verify_payment

    try:
        result = await verify_payment(payment_id, tx_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="حدث خطأ أثناء التحقق من الدفع")


@app.post("/api/subscription/cancel")
async def cancel_sub(request: Request):
    """Cancel user's active subscription at end of period."""
    user_id = _get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="يجب تسجيل الدخول")

    from backend.services.payment import cancel_subscription

    try:
        result = await cancel_subscription(user_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/subscription/webhook")
async def subscription_webhook(request: Request):
    """Moyasar webhook callback (public — no auth required)."""
    from backend.services.payment import handle_webhook

    try:
        payload = await request.json()
        result = await handle_webhook(payload)
        return result
    except Exception as e:
        print(f"Webhook error: {e}")
        return {"status": "error"}


@app.get("/api/usage")
async def get_usage(request: Request):
    """Get current user's usage summary."""
    user_id = _get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="يجب تسجيل الدخول")

    from backend.services.subscription import get_user_usage_summary
    summary = await get_user_usage_summary(user_id)
    return summary
