"""
Security middleware: JWT authentication with API key fallback.

JWT Auth (primary):
  - Validates Supabase JWT from Authorization: Bearer <token>
  - Sets request.state.user_id and request.state.auth_method = "jwt"

API Key Auth (legacy fallback):
  - If X-API-Key matches API_KEY env, allows request with user_id=None
  - This is a temporary backward-compatibility measure

Usage limits are checked inside endpoint handlers (not here)
because middleware cannot easily read request bodies with StreamingResponse.
"""
from __future__ import annotations

import jwt
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from backend.config import API_KEY, SUPABASE_JWT_SECRET


# Paths that require no authentication at all
PUBLIC_PATHS = {
    "/api/health",
    "/api/plans",
    "/api/subscription/webhook",
    "/docs",
    "/openapi.json",
    "/redoc",
}


def verify_jwt_token(token: str) -> dict:
    """
    Verify a Supabase JWT and return the decoded payload.
    Raises jwt.InvalidTokenError on failure.
    """
    if not SUPABASE_JWT_SECRET:
        raise jwt.InvalidTokenError("JWT secret not configured")

    payload = jwt.decode(
        token,
        SUPABASE_JWT_SECRET,
        algorithms=["HS256"],
        audience="authenticated",
    )

    if not payload.get("sub"):
        raise jwt.InvalidTokenError("Missing sub claim")

    return payload


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """
    JWT-based authentication middleware.
    Replaces the old AuthMiddleware + RateLimitMiddleware.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip auth for public paths and non-API routes
        if path in PUBLIC_PATHS or not path.startswith("/api/"):
            request.state.user_id = None
            request.state.auth_method = "public"
            return await call_next(request)

        # Try JWT from Authorization header (primary method)
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                payload = verify_jwt_token(token)
                request.state.user_id = payload["sub"]
                request.state.email = payload.get("email", "")
                request.state.auth_method = "jwt"
                return await call_next(request)
            except jwt.ExpiredSignatureError:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "انتهت صلاحية الجلسة — سجّل الدخول مرة أخرى"},
                )
            except jwt.InvalidTokenError as e:
                return JSONResponse(
                    status_code=401,
                    content={"detail": f"رمز مصادقة غير صالح: {str(e)}"},
                )

        # Fallback: API key authentication (legacy — will be removed later)
        api_key = request.headers.get("x-api-key") or request.query_params.get("api_key")
        if api_key and API_KEY and api_key == API_KEY:
            request.state.user_id = None
            request.state.email = None
            request.state.auth_method = "api_key"
            return await call_next(request)

        # No valid auth provided
        return JSONResponse(
            status_code=401,
            content={"detail": "يجب تسجيل الدخول — أضف Authorization: Bearer <token> في الهيدر"},
        )
