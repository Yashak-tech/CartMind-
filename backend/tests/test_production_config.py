"""
Unit tests for production configuration, CORS hardening, and callback URL resolution.
"""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from backend.config import Settings
from backend.main import app
from backend.razorpay_client import RazorpayService


def test_cors_origins_never_wildcard():
    """Verify that cors_origins never contains wildcard '*' and explicitly contains configured frontend."""
    custom_settings = Settings(
        FRONTEND_URL="https://cartmind-demo.vercel.app",
        ALLOWED_ORIGINS="https://cartmind-demo.vercel.app,http://localhost:5173",
    )
    origins = custom_settings.cors_origins
    assert "*" not in origins
    assert "https://cartmind-demo.vercel.app" in origins
    assert "http://localhost:5173" in origins


def test_backend_url_resolution_and_callback_route():
    """Verify that BACKEND_URL sets BASE_URL and Razorpay callback_url reflects it."""
    custom_backend = "https://cartmind-api.onrender.com"
    service = RazorpayService(
        key_id="rzp_test_prod_mock",
        key_secret="test_secret_123",
        base_url=custom_backend
    )

    mock_client = MagicMock()
    mock_client.payment_link.create.return_value = {
        "id": "plink_live_123",
        "short_url": "https://rzp.io/i/live_mock",
        "callback_url": f"{custom_backend}/api/test-payment/callback",
        "callback_method": "get"
    }
    service.client = mock_client

    result = service.create_payment_link(
        amount=999.0,
        description="Production Test Checkout",
        reference_id="prod_ref_001"
    )

    call_args = mock_client.payment_link.create.call_args[1]["data"]
    assert call_args["callback_url"] == f"{custom_backend}/api/test-payment/callback"
    assert call_args["callback_method"] == "get"
    assert result["id"] == "plink_live_123"


def test_cors_headers_with_allowed_origin():
    """Verify FastAPI CORS middleware returns Access-Control-Allow-Origin for permitted origins."""
    client = TestClient(app)
    # Make a preflight OPTIONS request
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        }
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
