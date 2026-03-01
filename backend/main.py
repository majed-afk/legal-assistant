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
from backend.logging_config import setup_logging, get_logger

setup_logging()
log = get_logger("sanad")

# Track whether vector DB is ready (for health check)
_db_ready = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize ChromaDB at startup — DB is pre-built during Docker build."""
    global _db_ready
    log.info("Initializing ChromaDB...")
    from backend.rag.vector_store import get_collection, get_collection_count
    col = get_collection()
    count = col.count()

    if count > 0:
        _db_ready = True
        log.info("ChromaDB ready — %d articles indexed", count)
    else:
        log.warning("ChromaDB empty — attempting build from pre-computed embeddings")
        try:
            from backend.tools.setup_db import setup_database
            setup_database()
            count = get_collection_count()
            if count > 0:
                _db_ready = True
                log.info("Database built — %d articles indexed", count)
        except Exception as e:
            log.error("Failed to build database: %s", e)

    # Initialize QA cache and article lookup (zero-cost tiers)
    from backend.rag.qa_cache import initialize_qa_cache
    from backend.rag.article_lookup import initialize_article_lookup
    log.info("Initializing QA cache...")
    initialize_qa_cache()
    initialize_article_lookup()

    log.info("Server ready to accept requests")
    yield


app = FastAPI(
    title="Sanad AI — سند",
    description="مستشار قانوني ذكي متخصص في أنظمة الأحوال الشخصية والمعاملات المدنية والإثبات والمرافعات الشرعية السعودية",
    version="2.0.0",
    lifespan=lifespan,
)

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001").split(",")

# Security middleware
# Order matters: last added = outermost (processes request first)
# CORS must be outermost so it adds headers even on 401/403 responses from JWT middleware
from backend.middleware import JWTAuthMiddleware
app.add_middleware(JWTAuthMiddleware)

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
    model_mode: Optional[str] = "1.1"  # "1.1" (quick) or "2.1" (detailed)

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
        mode_ok, mode_msg = await check_model_mode(user_id, req.model_mode or "1.1")
        if not mode_ok:
            raise HTTPException(status_code=403, detail=mode_msg)

    # === Tier 1 & 2: Zero-cost layers (skip for follow-up questions) ===
    if not req.chat_history:
        from backend.rag.qa_cache import match_qa_cache
        from backend.rag.article_lookup import lookup_article

        # Tier 1: QA cache match
        qa_match = match_qa_cache(req.question)
        if qa_match:
            log.info("QA cache hit (similarity=%.3f, id=%s)", qa_match["similarity"], qa_match["qa_id"])
            if user_id:
                await increment_usage(user_id, "questions")
            return {
                "answer": qa_match["corrected_answer"],
                "classification": {
                    "category": qa_match["category"],
                    "intent": "استشارة",
                    "urgency": "عادي",
                    "needs_deadline_check": False,
                    "all_categories": [qa_match["category"]],
                    "source": "qa_cache",
                },
                "sources": qa_match["sources"],
                "has_deadlines": False,
            }

        # Tier 2: Direct article lookup
        article_match = lookup_article(req.question)
        if article_match:
            log.info("Article lookup hit (article %s — %s)", article_match["article_number"], article_match["law"])
            if user_id:
                await increment_usage(user_id, "questions")
            return {
                "answer": article_match["response"],
                "classification": {
                    "category": article_match["category"],
                    "intent": "معلومة",
                    "urgency": "عادي",
                    "needs_deadline_check": False,
                    "all_categories": [article_match["category"]],
                    "source": "article_lookup",
                },
                "sources": article_match["sources"],
                "has_deadlines": False,
            }

    # === Tier 2.5: Response cache (cached Claude responses) ===
    if not req.chat_history:
        from backend.rag.qa_cache import get_cached_response
        cached = get_cached_response(req.question, req.model_mode or "1.1")
        if cached:
            log.info("Response cache hit")
            if user_id:
                await increment_usage(user_id, "questions")
            return {
                "answer": cached["answer"],
                "classification": cached["classification"],
                "sources": cached["sources"],
                "has_deadlines": cached["classification"].get("needs_deadline_check", False),
            }

    # === Tier 3: Claude API (full RAG + LLM) ===
    # Pre-classify for smart routing and context optimization
    from backend.rag.classifier import classify_query
    pre_class = classify_query(req.question)

    # Smart model routing: simple factual → mode 1.1 (saves ~62% tokens)
    effective_mode = req.model_mode or "1.1"
    if (effective_mode == "2.1"
        and not req.chat_history
        and pre_class["intent"] == "معلومة"
        and len(pre_class.get("all_categories", [])) <= 1):
        effective_mode = "1.1"
        log.info("Smart routing: 2.1→1.1 (intent=معلومة)")

    # Reduce RAG context for simple questions
    top_k = 3 if pre_class["intent"] == "معلومة" else 5
    rag_result = retrieve_context(req.question, top_k=top_k, chat_history=req.chat_history)

    try:
        answer = generate_legal_response(
            question=req.question,
            context=rag_result["context"],
            classification=rag_result["classification"],
            chat_history=req.chat_history,
            model_mode=effective_mode,
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        log.exception("Claude API error")
        raise HTTPException(status_code=500, detail=f"خطأ في الاتصال بـ Claude API: {str(e)}")

    # Cache response for future reuse (only first questions, not follow-ups)
    if not req.chat_history:
        from backend.rag.qa_cache import cache_response
        cache_response(
            req.question, effective_mode, answer,
            rag_result["classification"], rag_result["sources"],
        )
        log.info("Response cached: %s...", req.question[:50])

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
        mode_ok, mode_msg = await check_model_mode(user_id, req.model_mode or "1.1")
        if not mode_ok:
            raise HTTPException(status_code=403, detail=mode_msg)
        # Increment usage before streaming (can't do it after for StreamingResponse)
        await increment_usage(user_id, "questions")

    # === Tier 1 & 2: Zero-cost layers (skip for follow-up questions) ===
    if not req.chat_history:
        from backend.rag.qa_cache import match_qa_cache
        from backend.rag.article_lookup import lookup_article

        # Tier 1: QA cache match
        qa_match = match_qa_cache(req.question)
        if qa_match:
            log.info("QA cache hit [stream] (similarity=%.3f, id=%s)", qa_match["similarity"], qa_match["qa_id"])

            def cached_event_stream():
                import time
                classification = {
                    "category": qa_match["category"],
                    "intent": "استشارة",
                    "urgency": "عادي",
                    "needs_deadline_check": False,
                    "all_categories": [qa_match["category"]],
                    "source": "qa_cache",
                }
                meta = json.dumps({
                    "type": "meta",
                    "classification": classification,
                    "sources": qa_match["sources"],
                    "has_deadlines": False,
                }, ensure_ascii=False)
                yield f"data: {meta}\n\n"

                # Split answer into paragraphs for natural streaming feel
                answer = qa_match["corrected_answer"]
                paragraphs = answer.split("\n\n")
                for i, para in enumerate(paragraphs):
                    text = para if i == 0 else f"\n\n{para}"
                    chunk = json.dumps({"type": "token", "text": text}, ensure_ascii=False)
                    yield f"data: {chunk}\n\n"
                    time.sleep(0.02)

                yield f"data: {json.dumps({'type': 'done'})}\n\n"

            return StreamingResponse(
                cached_event_stream(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
            )

        # Tier 2: Direct article lookup
        article_match = lookup_article(req.question)
        if article_match:
            log.info("Article lookup hit [stream] (article %s — %s)", article_match["article_number"], article_match["law"])

            def article_event_stream():
                import time
                classification = {
                    "category": article_match["category"],
                    "intent": "معلومة",
                    "urgency": "عادي",
                    "needs_deadline_check": False,
                    "all_categories": [article_match["category"]],
                    "source": "article_lookup",
                }
                meta = json.dumps({
                    "type": "meta",
                    "classification": classification,
                    "sources": article_match["sources"],
                    "has_deadlines": False,
                }, ensure_ascii=False)
                yield f"data: {meta}\n\n"

                answer = article_match["response"]
                paragraphs = answer.split("\n\n")
                for i, para in enumerate(paragraphs):
                    text = para if i == 0 else f"\n\n{para}"
                    chunk = json.dumps({"type": "token", "text": text}, ensure_ascii=False)
                    yield f"data: {chunk}\n\n"
                    time.sleep(0.02)

                yield f"data: {json.dumps({'type': 'done'})}\n\n"

            return StreamingResponse(
                article_event_stream(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
            )

    # === Tier 2.5: Response cache (cached Claude responses) ===
    if not req.chat_history:
        from backend.rag.qa_cache import get_cached_response
        cached = get_cached_response(req.question, req.model_mode or "1.1")
        if cached:
            log.info("Response cache hit [stream]")

            def response_cache_stream():
                import time
                meta = json.dumps({
                    "type": "meta",
                    "classification": cached["classification"],
                    "sources": cached["sources"],
                    "has_deadlines": cached["classification"].get("needs_deadline_check", False),
                }, ensure_ascii=False)
                yield f"data: {meta}\n\n"

                answer = cached["answer"]
                paragraphs = answer.split("\n\n")
                for i, para in enumerate(paragraphs):
                    text = para if i == 0 else f"\n\n{para}"
                    chunk = json.dumps({"type": "token", "text": text}, ensure_ascii=False)
                    yield f"data: {chunk}\n\n"
                    time.sleep(0.02)

                yield f"data: {json.dumps({'type': 'done'})}\n\n"

            return StreamingResponse(
                response_cache_stream(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
            )

    # === Tier 3: Claude API (full RAG + LLM) ===
    # Pre-classify for smart routing and context optimization
    from backend.rag.classifier import classify_query
    pre_class = classify_query(req.question)

    # Smart model routing: simple factual → mode 1.1 (saves ~62% tokens)
    effective_mode = req.model_mode or "1.1"
    if (effective_mode == "2.1"
        and not req.chat_history
        and pre_class["intent"] == "معلومة"
        and len(pre_class.get("all_categories", [])) <= 1):
        effective_mode = "1.1"
        log.info("Smart routing [stream]: 2.1→1.1 (intent=معلومة)")

    # Reduce RAG context for simple questions
    top_k = 3 if pre_class["intent"] == "معلومة" else 5
    rag_result = retrieve_context(req.question, top_k=top_k, chat_history=req.chat_history)

    # Capture request params for use in generator closure
    _question = req.question
    _chat_history = req.chat_history
    _model_mode = effective_mode

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
        accumulated_tokens = []
        try:
            for token in stream_legal_response(
                question=_question,
                context=rag_result["context"],
                classification=rag_result["classification"],
                chat_history=_chat_history,
                model_mode=_model_mode,
            ):
                accumulated_tokens.append(token)
                chunk = json.dumps({"type": "token", "text": token}, ensure_ascii=False)
                yield f"data: {chunk}\n\n"

            # Signal completion
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

            # Cache response for future reuse (only first questions)
            if not _chat_history and accumulated_tokens:
                from backend.rag.qa_cache import cache_response
                full_response = "".join(accumulated_tokens)
                cache_response(
                    _question, _model_mode, full_response,
                    rag_result["classification"], rag_result["sources"],
                )
                log.info("Response cached [stream]: %s...", _question[:50])

        except Exception as e:
            log.exception("Streaming error")
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
        log.exception("Draft generation error")
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
        log.error("Feedback error: %s", e)
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
        log.warning("Analytics event error: %s", e)
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
        log.exception("Payment creation error")
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
        log.exception("Payment verification error")
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
        log.error("Webhook error: %s", e)
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
