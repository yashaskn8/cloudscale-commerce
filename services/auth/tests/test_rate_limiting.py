"""Tests for Rate Limiting on Auth Endpoints.

Validates that /register, /login, and /refresh endpoints enforce
rate limiting via RateLimiter when Redis is available, and that
they operate normally (bypass rate limiting) when Redis is absent.
"""

from unittest.mock import AsyncMock, patch

import pytest
from app.main import app
from app.router import get_auth_service
from app.service import AuthService
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def test_app(db_session: AsyncSession):
    """Fixture that overrides database injection to use the test session."""

    def get_test_auth_service():
        return AuthService(db_session)

    app.dependency_overrides[get_auth_service] = get_test_auth_service
    yield app
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_register_rate_limit_bypass_without_redis(test_app: FastAPI):
    """Without Redis, rate limiter is a no-op and registration works normally."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "email": "ratelimit_test@cloudscale.com",
            "password": "SecurePass123!",
            "first_name": "Rate",
            "last_name": "Limit",
        }
        res = await client.post("/api/v1/auth/register", json=payload)
        assert res.status_code == 201
        assert res.json()["email"] == "ratelimit_test@cloudscale.com"


@pytest.mark.asyncio
async def test_login_rate_limit_bypass_without_redis(test_app: FastAPI):
    """Without Redis, login still works (rate limiter returns early)."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register first
        register_payload = {
            "email": "ratelimit_login@cloudscale.com",
            "password": "SecurePass123!",
            "first_name": "Rate",
            "last_name": "Login",
        }
        await client.post("/api/v1/auth/register", json=register_payload)

        # Login
        login_payload = {"email": "ratelimit_login@cloudscale.com", "password": "SecurePass123!"}
        res = await client.post("/api/v1/auth/login", json=login_payload)
        assert res.status_code == 200
        assert "access_token" in res.json()


@pytest.mark.asyncio
async def test_register_rate_limit_enforced_with_redis(test_app: FastAPI):
    """With Redis mock, rate limiter should return 429 after exceeding max_requests."""
    # Create a mock Redis client that tracks incr calls
    mock_redis = AsyncMock()
    call_count = 0

    async def mock_incr(key):
        nonlocal call_count
        call_count += 1
        return call_count

    mock_redis.incr = mock_incr
    mock_redis.expire = AsyncMock()

    # Attach mock Redis to app state
    test_app.state.redis_client = mock_redis

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First 10 requests should succeed or fail on validation but NOT 429
        for i in range(10):
            payload = {
                "email": f"ratelimit_{i}@cloudscale.com",
                "password": "SecurePass123!",
                "first_name": "Rate",
                "last_name": "Test",
            }
            res = await client.post("/api/v1/auth/register", json=payload)
            assert res.status_code != 429, f"Request {i + 1} should not be rate limited"

        # The 11th request should be rate limited (429)
        payload = {
            "email": "ratelimit_11@cloudscale.com",
            "password": "SecurePass123!",
            "first_name": "Rate",
            "last_name": "Blocked",
        }
        res = await client.post("/api/v1/auth/register", json=payload)
        assert res.status_code == 429

    # Clean up
    del test_app.state.redis_client


@pytest.mark.asyncio
async def test_refresh_rate_limit_bypass_without_redis(test_app: FastAPI):
    """Without Redis, refresh endpoint still works normally."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register + Login to get tokens
        register_payload = {
            "email": "ratelimit_refresh@cloudscale.com",
            "password": "SecurePass123!",
            "first_name": "Rate",
            "last_name": "Refresh",
        }
        await client.post("/api/v1/auth/register", json=register_payload)

        login_payload = {"email": "ratelimit_refresh@cloudscale.com", "password": "SecurePass123!"}
        login_res = await client.post("/api/v1/auth/login", json=login_payload)
        assert login_res.status_code == 200

        refresh_token = login_res.json()["refresh_token"]

        # Refresh tokens
        res = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert res.status_code == 200
        assert "access_token" in res.json()
