"""Tests for backend.middleware — JWT authentication middleware."""
import pytest
from unittest.mock import patch, MagicMock
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from httpx import AsyncClient, ASGITransport

from backend.middleware import JWTAuthMiddleware, PUBLIC_PATHS, verify_jwt_token


# ---------------------------------------------------------------------------
# Minimal FastAPI app for testing middleware in isolation
# ---------------------------------------------------------------------------

def _create_test_app() -> FastAPI:
    """Create a minimal FastAPI app with JWTAuthMiddleware for testing."""
    app = FastAPI()
    app.add_middleware(JWTAuthMiddleware)

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    @app.get("/api/plans")
    async def plans():
        return {"plans": []}

    @app.get("/api/protected")
    async def protected(request: Request):
        return {
            "user_id": request.state.user_id,
            "auth_method": request.state.auth_method,
        }

    @app.get("/non-api-route")
    async def non_api():
        return {"message": "public"}

    return app


# ===================================================================
# Public path tests
# ===================================================================

class TestPublicPaths:
    """Tests that public paths bypass authentication."""

    @pytest.mark.asyncio
    async def test_health_endpoint_no_auth_required(self):
        """GET /api/health should return 200 without any auth headers."""
        app = _create_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/health")
            assert resp.status_code == 200
            assert resp.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_plans_endpoint_no_auth_required(self):
        """GET /api/plans should return 200 without any auth headers."""
        app = _create_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/plans")
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_non_api_route_no_auth_required(self):
        """Non-/api/ routes should bypass auth entirely."""
        app = _create_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/non-api-route")
            assert resp.status_code == 200

    def test_public_paths_set_is_correct(self):
        """PUBLIC_PATHS should contain the expected endpoints."""
        assert "/api/health" in PUBLIC_PATHS
        assert "/api/plans" in PUBLIC_PATHS
        assert "/api/subscription/webhook" in PUBLIC_PATHS
        assert "/docs" in PUBLIC_PATHS
        assert "/openapi.json" in PUBLIC_PATHS


# ===================================================================
# Missing / Invalid auth header tests
# ===================================================================

class TestMissingAuth:
    """Tests for requests without proper authentication."""

    @pytest.mark.asyncio
    async def test_missing_auth_header_returns_401(self):
        """Protected endpoint without Authorization header should return 401."""
        app = _create_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/protected")
            assert resp.status_code == 401
            body = resp.json()
            assert "detail" in body

    @pytest.mark.asyncio
    async def test_empty_bearer_token_returns_401(self):
        """Empty Bearer token should return 401."""
        app = _create_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/protected",
                headers={"Authorization": "Bearer "}
            )
            assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token_returns_401(self):
        """Invalid JWT token should return 401."""
        app = _create_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/protected",
                headers={"Authorization": "Bearer invalid.jwt.token"}
            )
            assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_wrong_auth_scheme_returns_401(self):
        """Non-Bearer auth scheme without API key should return 401."""
        app = _create_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/protected",
                headers={"Authorization": "Basic dXNlcjpwYXNz"}
            )
            assert resp.status_code == 401


# ===================================================================
# Valid JWT authentication
# ===================================================================

class TestValidJWT:
    """Tests for valid JWT authentication."""

    @pytest.mark.asyncio
    async def test_valid_jwt_authenticates(self):
        """A valid JWT token should authenticate the user and set user_id."""
        app = _create_test_app()
        transport = ASGITransport(app=app)

        with patch("backend.middleware.verify_jwt_token") as mock_verify:
            mock_verify.return_value = {
                "sub": "user-abc-123",
                "email": "test@example.com",
                "aud": "authenticated",
            }

            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    "/api/protected",
                    headers={"Authorization": "Bearer valid.jwt.token"}
                )
                assert resp.status_code == 200
                body = resp.json()
                assert body["user_id"] == "user-abc-123"
                assert body["auth_method"] == "jwt"

    @pytest.mark.asyncio
    async def test_expired_jwt_returns_401(self):
        """An expired JWT token should return 401 with expiry message."""
        import jwt as pyjwt

        app = _create_test_app()
        transport = ASGITransport(app=app)

        with patch("backend.middleware.verify_jwt_token") as mock_verify:
            mock_verify.side_effect = pyjwt.ExpiredSignatureError("Token expired")

            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    "/api/protected",
                    headers={"Authorization": "Bearer expired.jwt.token"}
                )
                assert resp.status_code == 401
                assert "صلاحية" in resp.json()["detail"]


# ===================================================================
# API key fallback authentication
# ===================================================================

class TestAPIKeyAuth:
    """Tests for API key fallback authentication."""

    @pytest.mark.asyncio
    async def test_valid_api_key_authenticates(self):
        """Valid API key in X-API-Key header should authenticate."""
        app = _create_test_app()
        transport = ASGITransport(app=app)

        with patch("backend.middleware.API_KEY", "test-secret-key"):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    "/api/protected",
                    headers={"X-API-Key": "test-secret-key"}
                )
                assert resp.status_code == 200
                body = resp.json()
                assert body["auth_method"] == "api_key"

    @pytest.mark.asyncio
    async def test_invalid_api_key_returns_401(self):
        """Invalid API key should return 401."""
        app = _create_test_app()
        transport = ASGITransport(app=app)

        with patch("backend.middleware.API_KEY", "test-secret-key"):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    "/api/protected",
                    headers={"X-API-Key": "wrong-key"}
                )
                assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_api_key_in_query_param_authenticates(self):
        """Valid API key as query parameter should also authenticate."""
        app = _create_test_app()
        transport = ASGITransport(app=app)

        with patch("backend.middleware.API_KEY", "test-secret-key"):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    "/api/protected",
                    params={"api_key": "test-secret-key"}
                )
                assert resp.status_code == 200
                body = resp.json()
                assert body["auth_method"] == "api_key"

    @pytest.mark.asyncio
    async def test_empty_api_key_config_rejects(self):
        """When API_KEY is empty, API key auth should not work."""
        app = _create_test_app()
        transport = ASGITransport(app=app)

        with patch("backend.middleware.API_KEY", ""):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    "/api/protected",
                    headers={"X-API-Key": "some-key"}
                )
                assert resp.status_code == 401
