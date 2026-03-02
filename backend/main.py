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

# Sentry error tracking (optional — only active if SENTRY_DSN is set)
import sentry_sdk
_sentry_dsn = os.getenv("SENTRY_DSN", "")
if _sentry_dsn:
    sentry_sdk.init(
        dsn=_sentry_dsn,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        environment=os.getenv("ENVIRONMENT", "production"),
    )
    log.info("Sentry initialized for error tracking")

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
    description="مستشار قانوني ذكي متخصص في أنظمة الأحوال الشخصية والمعاملات المدنية والإثبات والمرافعات الشرعية والمحاكم التجارية السعودية",
    version="2.0.0",
    lifespan=lifespan,
)

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001").split(",")

# Security middleware
# Order matters: last added = outermost (processes request first)
# CORS must be outermost so it adds headers even on 401/403 responses from JWT middleware
from backend.middleware import JWTAuthMiddleware, RequestIDMiddleware
app.add_middleware(JWTAuthMiddleware)
app.add_middleware(RequestIDMiddleware)

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
        "db_complete": count >= 1300,
        "laws": ["أحوال شخصية", "معاملات مدنية", "إثبات", "مرافعات شرعية", "محاكم تجارية", "ضوابط الإثبات إلكترونياً"],
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
        from backend.services.subscription import (
            check_limit, check_model_mode, increment_usage,
            get_user_subscription, increment_trial, FREE_FEATURES,
        )
        allowed, msg = await check_limit(user_id, "questions")
        if not allowed:
            raise HTTPException(status_code=429, detail=msg)
        mode_ok, mode_msg = await check_model_mode(user_id, req.model_mode or "1.1")
        if not mode_ok:
            raise HTTPException(status_code=403, detail=mode_msg)

        # If free user is using mode 2.1, atomically consume a trial
        effective_model = req.model_mode or "1.1"
        if effective_model == "2.1":
            sub = await get_user_subscription(user_id)
            features = sub.get("features", FREE_FEATURES)
            if "2.1" not in features.get("model_modes", []):
                trial_result = await increment_trial(user_id, "model_mode_2.1")
                if not trial_result["allowed"]:
                    raise HTTPException(status_code=403, detail=(
                        "استنفدت التجارب المجانية الثلاث للوضع المفصّل (سند 2.1). "
                        "ترقَّ للباقة الأساسية أو أعلى لاستخدام غير محدود."
                    ))

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
        from backend.services.subscription import (
            check_limit, check_model_mode, increment_usage,
            get_user_subscription, increment_trial, FREE_FEATURES,
        )
        allowed, msg = await check_limit(user_id, "questions")
        if not allowed:
            raise HTTPException(status_code=429, detail=msg)
        mode_ok, mode_msg = await check_model_mode(user_id, req.model_mode or "1.1")
        if not mode_ok:
            raise HTTPException(status_code=403, detail=mode_msg)

        # If free user is using mode 2.1, atomically consume a trial
        effective_model = req.model_mode or "1.1"
        if effective_model == "2.1":
            sub = await get_user_subscription(user_id)
            features = sub.get("features", FREE_FEATURES)
            if "2.1" not in features.get("model_modes", []):
                trial_result = await increment_trial(user_id, "model_mode_2.1")
                if not trial_result["allowed"]:
                    raise HTTPException(status_code=403, detail=(
                        "استنفدت التجارب المجانية الثلاث للوضع المفصّل (سند 2.1). "
                        "ترقَّ للباقة الأساسية أو أعلى لاستخدام غير محدود."
                    ))

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


# ══════════════════════════════════════════════════════════════
# Contract Analysis Endpoint
# ══════════════════════════════════════════════════════════════

@app.post("/api/contract-analyze-stream")
async def analyze_contract_stream(request: Request):
    """
    Analyze a legal contract against Saudi law articles.
    Accepts multipart/form-data with file (PDF/DOCX) or contract_text field.
    Returns SSE stream with same protocol as /api/ask-stream.
    """
    from backend.rag.pipeline import retrieve_context
    from backend.services.contract_analyzer import (
        extract_text_from_pdf,
        extract_text_from_docx,
        detect_contract_type,
        stream_contract_analysis,
        CONTRACT_RAG_QUERIES,
    )
    from backend.services.subscription import check_limit, increment_usage, get_user_subscription

    if not _db_ready:
        raise HTTPException(
            status_code=503,
            detail="جاري تجهيز قاعدة البيانات... يرجى المحاولة بعد دقيقة",
        )

    # 1. Auth check
    user_id = _get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="يجب تسجيل الدخول لاستخدام تحليل العقود")

    # 2. Check usage limit (free users get 3/month, paid plans have their own limits)
    allowed, msg = await check_limit(user_id, "contract_analyses")
    if not allowed:
        raise HTTPException(status_code=429, detail=msg)

    # 3. Parse form data
    form = await request.form()
    contract_text = ""

    # Try file upload first
    file = form.get("file")
    if file and hasattr(file, "read"):
        file_bytes = await file.read()
        filename = getattr(file, "filename", "") or ""

        if not file_bytes:
            raise HTTPException(status_code=400, detail="الملف فارغ")

        # Max 10MB
        if len(file_bytes) > 10 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="حجم الملف يتجاوز 10 ميجابايت")

        try:
            if filename.lower().endswith(".pdf"):
                contract_text = extract_text_from_pdf(file_bytes)
            elif filename.lower().endswith(".docx"):
                contract_text = extract_text_from_docx(file_bytes)
            else:
                # Try as plain text
                contract_text = file_bytes.decode("utf-8", errors="ignore")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Fallback to text field
    if not contract_text:
        contract_text = form.get("contract_text", "")
        if isinstance(contract_text, bytes):
            contract_text = contract_text.decode("utf-8", errors="ignore")

    if not contract_text or not contract_text.strip():
        raise HTTPException(status_code=400, detail="يرجى رفع ملف العقد أو لصق نص العقد")

    # 4. Detect contract type
    contract_type = detect_contract_type(contract_text)
    log.info("Contract analysis: type=%s, text_len=%d, user=%s", contract_type, len(contract_text), user_id[:8])

    # 5. RAG — retrieve relevant articles
    rag_query = CONTRACT_RAG_QUERIES.get(contract_type, CONTRACT_RAG_QUERIES["عام"])
    rag_result = retrieve_context(rag_query, top_k=8)

    # 6. Increment usage before streaming
    await increment_usage(user_id, "contract_analyses")

    # 7. Stream analysis
    def event_stream():
        try:
            # Meta event
            meta = json.dumps({
                "type": "meta",
                "contract_type": contract_type,
                "sources": rag_result.get("sources", []),
            }, ensure_ascii=False)
            yield f"data: {meta}\n\n"

            # Token-by-token streaming
            for token in stream_contract_analysis(
                contract_text=contract_text,
                context=rag_result["context"],
                contract_type=contract_type,
            ):
                chunk = json.dumps({"type": "token", "text": token}, ensure_ascii=False)
                yield f"data: {chunk}\n\n"

            # Done
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            log.exception("Contract analysis streaming error")
            error_msg = str(e)
            if "rate_limit" in error_msg.lower() or "429" in error_msg:
                user_error = "الخادم مشغول حالياً — يرجى المحاولة بعد لحظات"
            else:
                user_error = "حدث خطأ أثناء تحليل العقد — يرجى المحاولة مرة أخرى"
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


# ══════════════════════════════════════════════════════════════
# Verdict Prediction Endpoint
# ══════════════════════════════════════════════════════════════

@app.post("/api/verdict-predict-stream")
async def predict_verdict_stream(request: Request):
    """
    Predict verdict for a legal case based on Saudi law articles.
    Accepts form data: case_type (optional) + case_details (required).
    Returns SSE stream with same protocol as /api/ask-stream.
    """
    from backend.rag.pipeline import retrieve_context
    from backend.services.verdict_predictor import (
        detect_case_type,
        stream_verdict_prediction,
        CASE_RAG_QUERIES,
    )
    from backend.services.subscription import check_limit, increment_usage

    if not _db_ready:
        raise HTTPException(
            status_code=503,
            detail="جاري تجهيز قاعدة البيانات... يرجى المحاولة بعد دقيقة",
        )

    # 1. Auth check
    user_id = _get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="يجب تسجيل الدخول لاستخدام توقع الحكم")

    # 2. Check usage limit (free users get 2/month)
    allowed, msg = await check_limit(user_id, "verdict_predictions")
    if not allowed:
        raise HTTPException(status_code=429, detail=msg)

    # 3. Parse form data
    form = await request.form()
    case_details = form.get("case_details", "")
    if isinstance(case_details, bytes):
        case_details = case_details.decode("utf-8", errors="ignore")

    case_type_input = form.get("case_type", "")
    if isinstance(case_type_input, bytes):
        case_type_input = case_type_input.decode("utf-8", errors="ignore")

    if not case_details or not case_details.strip():
        raise HTTPException(status_code=400, detail="يرجى إدخال تفاصيل القضية")

    # 4. Detect or use provided case type
    if case_type_input and case_type_input != "عام":
        case_type = case_type_input
    else:
        case_type = detect_case_type(case_details)

    log.info("Verdict prediction: type=%s, text_len=%d, user=%s", case_type, len(case_details), user_id[:8])

    # 5. RAG — retrieve relevant articles
    rag_query = CASE_RAG_QUERIES.get(case_type, CASE_RAG_QUERIES["عام"])
    rag_result = retrieve_context(rag_query, top_k=8)

    # 6. Increment usage before streaming
    await increment_usage(user_id, "verdict_predictions")

    # 7. Stream prediction
    def event_stream():
        try:
            # Meta event
            meta = json.dumps({
                "type": "meta",
                "case_type": case_type,
                "sources": rag_result.get("sources", []),
            }, ensure_ascii=False)
            yield f"data: {meta}\n\n"

            # Token-by-token streaming
            for token in stream_verdict_prediction(
                case_text=case_details,
                context=rag_result["context"],
                case_type=case_type,
            ):
                chunk = json.dumps({"type": "token", "text": token}, ensure_ascii=False)
                yield f"data: {chunk}\n\n"

            # Done
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            log.exception("Verdict prediction streaming error")
            error_msg = str(e)
            if "rate_limit" in error_msg.lower() or "429" in error_msg:
                user_error = "الخادم مشغول حالياً — يرجى المحاولة بعد لحظات"
            else:
                user_error = "حدث خطأ أثناء توقع الحكم — يرجى المحاولة مرة أخرى"
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


# --- PayPal Payment Endpoints ---

@app.post("/api/subscription/paypal/create-order")
async def paypal_create_order(req: SubscriptionCreateRequest, request: Request):
    """Create a PayPal order for subscription payment."""
    user_id = _get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="يجب تسجيل الدخول")

    from backend.services.paypal import create_order

    try:
        result = await create_order(
            user_id=user_id,
            plan_tier=req.plan_tier,
            billing_cycle=req.billing_cycle,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.exception("PayPal create order error")
        raise HTTPException(status_code=500, detail="حدث خطأ أثناء إنشاء طلب الدفع")


@app.post("/api/subscription/paypal/capture-order")
async def paypal_capture_order(request: Request):
    """Capture an approved PayPal order and activate subscription."""
    user_id = _get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="يجب تسجيل الدخول")

    from backend.services.paypal import capture_order

    try:
        body = await request.json()
        order_id = body.get("order_id")
        if not order_id:
            raise HTTPException(status_code=400, detail="معرّف الطلب مطلوب")

        result = await capture_order(order_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.exception("PayPal capture error")
        raise HTTPException(status_code=500, detail="حدث خطأ أثناء تأكيد الدفع")


@app.get("/api/usage")
async def get_usage(request: Request):
    """Get current user's usage summary."""
    user_id = _get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="يجب تسجيل الدخول")

    from backend.services.subscription import get_user_usage_summary
    summary = await get_user_usage_summary(user_id)
    return summary


# ── Admin endpoints ──────────────────────────────────────────

@app.get("/api/admin/stats")
async def admin_stats(request: Request):
    """Get admin dashboard statistics."""
    from backend.services.admin import check_admin, get_admin_stats
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(403, "يجب تسجيل الدخول")
    if not await check_admin(user_id):
        raise HTTPException(403, "ليس لديك صلاحيات الأدمن")
    return await get_admin_stats()


@app.get("/api/admin/users")
async def admin_users(request: Request, limit: int = 50, offset: int = 0):
    """Get paginated user list (admin only)."""
    from backend.services.admin import check_admin, get_admin_users
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(403, "يجب تسجيل الدخول")
    if not await check_admin(user_id):
        raise HTTPException(403, "ليس لديك صلاحيات الأدمن")
    return await get_admin_users(limit=limit, offset=offset)


@app.post("/api/admin/users/{target_user_id}/plan")
async def admin_change_plan(target_user_id: str, request: Request):
    """Change a user's subscription plan (admin only)."""
    from backend.services.admin import check_admin, update_user_subscription_admin
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(403, "يجب تسجيل الدخول")
    if not await check_admin(user_id):
        raise HTTPException(403, "ليس لديك صلاحيات الأدمن")

    body = await request.json()
    plan_tier = body.get("plan_tier")
    if not plan_tier:
        raise HTTPException(400, "يجب تحديد الباقة المطلوبة")

    result = await update_user_subscription_admin(user_id, target_user_id, plan_tier)
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "حدث خطأ"))
    return result


@app.get("/api/admin/role")
async def admin_get_my_role(request: Request):
    """Get current user's role."""
    from backend.services.admin import get_user_role
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(403, "يجب تسجيل الدخول")
    role = await get_user_role(user_id)
    return {"role": role}
