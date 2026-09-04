"""
Unit tests for the Chat Rate Limiter (TRD.md §11).
Verifies that rapid conversational turns are capped to 15/minute and return HTTP 429.
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException
from backend.rate_limiter import InMemoryRateLimiter, chat_rate_limiter
from backend.main import app


from backend.routes.auth import create_access_token


@pytest.fixture
def client():
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {create_access_token('test_limiter@cartmind.ai')}"})
    return c


def test_in_memory_rate_limiter_blocks_after_threshold():
    """Confirms that the rate limiter permits N requests and blocks N+1."""
    limiter = InMemoryRateLimiter(requests_per_minute=3, window_seconds=10)
    test_key = "test_sess_limiter"

    # First 3 requests must pass
    limiter.check(test_key)
    limiter.check(test_key)
    limiter.check(test_key)

    # 4th request must raise HTTP 429
    with pytest.raises(HTTPException) as exc_info:
        limiter.check(test_key)

    assert exc_info.value.status_code == 429
    assert "Rate limit exceeded" in exc_info.value.detail
    assert "Retry-After" in exc_info.value.headers


def test_rate_limiter_per_session_isolation():
    """Confirms limits are isolated per session."""
    limiter = InMemoryRateLimiter(requests_per_minute=2, window_seconds=10)
    sess_a = "sess_user_alpha"
    sess_b = "sess_user_beta"

    limiter.check(sess_a)
    limiter.check(sess_a)

    # sess_a is blocked
    with pytest.raises(HTTPException):
        limiter.check(sess_a)

    # sess_b is unaffected
    limiter.check(sess_b)
    limiter.check(sess_b)


def test_chat_route_rate_limiting(client):
    """End-to-end test on POST /session/{id}/message when rate limit is exceeded."""
    # Create session
    resp = client.post("/session")
    assert resp.status_code == 201
    sid = resp.json()["session_id"]

    # Temporarily set limit to 2 for fast verification
    original_limit = chat_rate_limiter.requests_per_minute
    chat_rate_limiter.requests_per_minute = 2
    chat_rate_limiter.reset(sid)

    try:
        # Request 1
        r1 = client.post(f"/session/{sid}/message", json={"message": "Hello 1"})
        assert r1.status_code == 200

        # Request 2
        r2 = client.post(f"/session/{sid}/message", json={"message": "Hello 2"})
        assert r2.status_code == 200

        # Request 3 -> Exceeded limit!
        r3 = client.post(f"/session/{sid}/message", json={"message": "Hello 3"})
        assert r3.status_code == 429
        assert "Rate limit exceeded" in r3.json()["detail"]
        assert "retry-after" in r3.headers
    finally:
        chat_rate_limiter.requests_per_minute = original_limit
        chat_rate_limiter.reset(sid)
