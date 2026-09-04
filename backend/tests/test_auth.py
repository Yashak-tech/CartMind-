"""
Unit & Integration Tests for CartMind Access Gate (Email OTP & JWT Middleware).
Verifies:
- 6-digit OTP code request & 3-request/10-min rate limiting
- Valid OTP verification & signed JWT issuance
- Protected endpoints require valid Bearer token (HTTP 401 when missing/invalid)
- Whitelisted endpoints (/health, /auth/*, /docs, callbacks) remain accessible
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.routes.auth import otp_rate_limiter, _otp_store, create_access_token


@pytest.fixture
def client():
    return TestClient(app)


def test_request_otp_generates_code_and_rate_limits(client):
    """Verifies that requesting an OTP generates a code and enforces the 3 req/10 min ceiling."""
    test_email = "tester_alpha@example.com"
    otp_rate_limiter.reset(test_email)
    _otp_store.pop(test_email, None)

    # 1. First 3 requests must succeed
    r1 = client.post("/auth/request-code", json={"email": test_email})
    assert r1.status_code == 200
    data1 = r1.json()
    assert data1["status"] == "code_sent"
    assert "dev_code" in data1
    assert len(data1["dev_code"]) == 6

    r2 = client.post("/auth/request-code", json={"email": test_email})
    assert r2.status_code == 200

    r3 = client.post("/auth/request-code", json={"email": test_email})
    assert r3.status_code == 200

    # 2. 4th request must be rate-limited (HTTP 429)
    r4 = client.post("/auth/request-code", json={"email": test_email})
    assert r4.status_code == 429
    assert "Too many access code requests" in r4.json()["detail"]
    assert "retry-after" in r4.headers


def test_verify_otp_valid_returns_jwt(client):
    """Verifies that submitting the correct OTP returns a signed JWT."""
    test_email = "tester_beta@example.com"
    otp_rate_limiter.reset(test_email)
    _otp_store.pop(test_email, None)

    # Request code
    req = client.post("/auth/request-code", json={"email": test_email})
    assert req.status_code == 200
    code = req.json()["dev_code"]

    # Verify code
    ver = client.post("/auth/verify-code", json={"email": test_email, "code": code})
    assert ver.status_code == 200
    res = ver.json()
    assert "token" in res
    assert res["email"] == test_email
    assert res["token_type"] == "bearer"
    assert res["expires_in_hours"] == 24


def test_verify_otp_invalid_or_expired_rejected(client):
    """Verifies invalid codes or non-existent requests return HTTP 400."""
    test_email = "tester_gamma@example.com"
    otp_rate_limiter.reset(test_email)
    _otp_store.pop(test_email, None)

    # 1. No code requested yet
    r1 = client.post("/auth/verify-code", json={"email": test_email, "code": "999999"})
    assert r1.status_code == 400
    assert "No active access code found" in r1.json()["detail"]

    # 2. Wrong code submitted
    client.post("/auth/request-code", json={"email": test_email})
    r2 = client.post("/auth/verify-code", json={"email": test_email, "code": "000000"})
    assert r2.status_code == 400
    assert "Invalid access code" in r2.json()["detail"]


def test_protected_endpoints_require_jwt(client):
    """Confirms that API routes (e.g. /products, /session) reject unauthenticated calls."""
    # 1. Without Authorization header -> 401
    r_unauth = client.get("/products")
    assert r_unauth.status_code == 401
    assert "Access gate token required" in r_unauth.json()["detail"]

    # 2. With malformed token -> 401
    r_bad = client.get("/products", headers={"Authorization": "Bearer not_a_valid_jwt_token"})
    assert r_bad.status_code == 401

    # 3. With valid signed token -> 200
    token = create_access_token("verified_judge@example.com")
    r_auth = client.get("/products", headers={"Authorization": f"Bearer {token}"})
    assert r_auth.status_code == 200
    assert isinstance(r_auth.json(), list)


def test_whitelisted_endpoints_accessible_without_jwt(client):
    """Confirms /health, /docs, and /auth/* are publicly accessible without JWT."""
    assert client.get("/health").status_code == 200
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200
