"""
Security middleware: API key authentication + rate limiting.

API Key Auth:
  - If API_KEY env var is set, all /api/* endpoints (except /api/health)
    require `X-API-Key` header or `api_key` query param.
  - If API_KEY is empty, auth is disabled (open access).

Rate Limiting:
  - Per-IP sliding window: RATE_LIMIT_PER_MINUTE requests/minute.
  - Per-IP daily cap: RATE_LIMIT_PER_DAY requests/day.
  - Only counts requests to expensive endpoints (/api/ask, /api/ask-stream, /api/draft).
"""
from __future__ import annotations

import time
from collections import defaultdict
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from backend.config import API_KEY, RATE_LIMIT_PER_MINUTE, RATE_LIMIT_PER_DAY

# ---- Rate Limit Storage (in-memory, resets on restart) ----
_minute_requests: dict[str, list[float]] = defaultdict(list)
_day_requests: dict[str, list[float]] = defaultdict(list)

# Expensive endpoints that count toward rate limits
RATE_LIMITED_PATHS = {"/api/ask", "/api/ask-stream", "/api/draft"}

# Endpoints that skip auth
PUBLIC_PATHS = {"/api/health", "/docs", "/openapi.json", "/redoc"}


def _get_client_ip(request: Request) -> str:
    """Get client IP, respecting X-Forwarded-For from reverse proxies."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _clean_old_entries(entries: list[float], window_seconds: float) -> list[float]:
    """Remove entries older than the window."""
    cutoff = time.time() - window_seconds
    return [t for t in entries if t > cutoff]


class AuthMiddleware(BaseHTTPMiddleware):
    """API key authentication middleware."""

    async def dispatch(self, request: Request, call_next):
        # Skip auth if no API_KEY configured
        if not API_KEY:
            return await call_next(request)

        path = request.url.path

        # Skip auth for public paths
        if path in PUBLIC_PATHS or not path.startswith("/api/"):
            return await call_next(request)

        # Check API key from header or query param
        key = request.headers.get("x-api-key") or request.query_params.get("api_key")
        if key != API_KEY:
            return JSONResponse(
                status_code=401,
                content={"detail": "مفتاح API غير صالح. أضف X-API-Key في الهيدر."},
            )

        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-IP rate limiting middleware."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Only rate-limit expensive endpoints
        if path not in RATE_LIMITED_PATHS:
            return await call_next(request)

        client_ip = _get_client_ip(request)
        now = time.time()

        # Per-minute check
        _minute_requests[client_ip] = _clean_old_entries(
            _minute_requests[client_ip], 60
        )
        if len(_minute_requests[client_ip]) >= RATE_LIMIT_PER_MINUTE:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": f"تجاوزت الحد المسموح ({RATE_LIMIT_PER_MINUTE} طلبات/دقيقة). انتظر قليلاً.",
                },
            )

        # Per-day check
        _day_requests[client_ip] = _clean_old_entries(
            _day_requests[client_ip], 86400
        )
        if len(_day_requests[client_ip]) >= RATE_LIMIT_PER_DAY:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": f"تجاوزت الحد اليومي ({RATE_LIMIT_PER_DAY} طلبات/يوم). حاول غداً.",
                },
            )

        # Record this request
        _minute_requests[client_ip].append(now)
        _day_requests[client_ip].append(now)

        response = await call_next(request)

        # Add rate limit headers
        remaining_minute = max(0, RATE_LIMIT_PER_MINUTE - len(_minute_requests[client_ip]))
        remaining_day = max(0, RATE_LIMIT_PER_DAY - len(_day_requests[client_ip]))
        response.headers["X-RateLimit-Limit-Minute"] = str(RATE_LIMIT_PER_MINUTE)
        response.headers["X-RateLimit-Remaining-Minute"] = str(remaining_minute)
        response.headers["X-RateLimit-Limit-Day"] = str(RATE_LIMIT_PER_DAY)
        response.headers["X-RateLimit-Remaining-Day"] = str(remaining_day)

        return response
