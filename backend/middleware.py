"""
Security middleware: JWT authentication with API key fallback.

JWT Auth (primary):
  - Validates Supabase JWT from Authorization: Bearer <token>
  - Supports both ES256 (new JWKS-based) and HS256 (legacy secret-based)
  - Sets request.state.user_id and request.state.auth_method = "jwt"

API Key Auth (legacy fallback):
  - If X-API-Key matches API_KEY env, allows request with user_id=None
  - This is a temporary backward-compatibility measure

Usage limits are checked inside endpoint handlers (not here)
because middleware cannot easily read request bodies with StreamingResponse.
"""
from __future__ import annotations

import jwt
from jwt import PyJWKClient
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from backend.config import API_KEY, SUPABASE_JWT_SECRET, SUPABASE_URL


# Paths that require no authentication at all
PUBLIC_PATHS = {
    "/api/health",
    "/api/plans",
    "/api/subscription/webhook",
    "/docs",
    "/openapi.json",
    "/redoc",
}

# JWKS client for ES256 verification (caches keys automatically)
_jwks_client = None


def _get_jwks_client() -> PyJWKClient | None:
    """Lazy-initialize JWKS client from Supabase URL."""
    global _jwks_client
    if _jwks_client is not None:
        return _jwks_client
    if SUPABASE_URL:
        jwks_url = f"{SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
        _jwks_client = PyJWKClient(jwks_url, cache_keys=True, lifespan=3600)
        return _jwks_client
    return None


def verify_jwt_token(token: str) -> dict:
    """
    Verify a Supabase JWT and return the decoded payload.
    Tries ES256 (JWKS) first, then falls back to HS256 (legacy secret).
    Raises jwt.InvalidTokenError on failure.
    """
    errors = []

    # --- Method 1: ES256 via JWKS (current Supabase default) ---
    jwks = _get_jwks_client()
    if jwks:
        try:
            signing_key = jwks.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256"],
                audience="authenticated",
            )
            if not payload.get("sub"):
                raise jwt.InvalidTokenError("Missing sub claim")
            return payload
        except (jwt.InvalidTokenError, Exception) as e:
            errors.append(f"ES256/JWKS: {e}")

    # --- Method 2: HS256 with shared secret (legacy) ---
    if SUPABASE_JWT_SECRET:
        try:
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
            )
            if not payload.get("sub"):
                raise jwt.InvalidTokenError("Missing sub claim")
            return payload
        except (jwt.InvalidTokenError, Exception) as e:
            errors.append(f"HS256: {e}")

    # Both methods failed
    if not errors:
        raise jwt.InvalidTokenError("JWT verification not configured (no JWKS URL or secret)")
    raise jwt.InvalidTokenError(" | ".join(errors))


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
