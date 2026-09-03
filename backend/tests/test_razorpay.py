"""
Unit and integration tests for Razorpay Service and Phase 1 endpoints.
"""

import hmac
import hashlib
from decimal import Decimal
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from backend.config import settings
from backend.razorpay_client import (
    rupees_to_paise,
    RazorpayService,
)
from backend.main import app


def test_rupees_to_paise_conversion():
    """Verify Decimal-based currency conversion avoids floating-point issues."""
    assert rupees_to_paise(0.01) == 1
    assert rupees_to_paise("0.01") == 1
    assert rupees_to_paise(100) == 10000
    assert rupees_to_paise(149.99) == 14999
    assert rupees_to_paise("149.99") == 14999
    assert rupees_to_paise(499.50) == 49950
    assert rupees_to_paise(Decimal("199.95")) == 19995
    assert rupees_to_paise(1234.567) == 123457  # Round half up


def test_order_signature_verification():
    """Verify standard Orders flow signature verification logic."""
    test_secret = "test_secret_key_12345"
    service = RazorpayService(key_id="rzp_test_12345", key_secret=test_secret)

    order_id = "order_EKwxwAgItmmXdp"
    payment_id = "pay_29Ae35XduUtik5"

    # Calculate expected signature
    msg = f"{order_id}|{payment_id}".encode("utf-8")
    valid_sig = hmac.new(test_secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

    assert service.verify_order_payment_signature(order_id, payment_id, valid_sig) is True
    assert service.verify_order_payment_signature(order_id, payment_id, "invalid_signature") is False


def test_payment_link_signature_verification():
    """Verify Payment Link redirect signature verification logic."""
    test_secret = "test_secret_key_98765"
    service = RazorpayService(key_id="rzp_test_98765", key_secret=test_secret)

    plink_id = "plink_LF78s0x8kR"
    reference_id = "cart_session_101"
    status = "paid"
    payment_id = "pay_LH98s23s"

    # Formula: payment_link_id + "|" + payment_link_reference_id + "|" + payment_link_status + "|" + razorpay_payment_id
    msg = f"{plink_id}|{reference_id}|{status}|{payment_id}".encode("utf-8")
    valid_sig = hmac.new(test_secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

    assert service.verify_payment_link_signature(
        payment_link_id=plink_id,
        payment_link_reference_id=reference_id,
        payment_link_status=status,
        razorpay_payment_id=payment_id,
        razorpay_signature=valid_sig
    ) is True

    assert service.verify_payment_link_signature(
        payment_link_id=plink_id,
        payment_link_reference_id=reference_id,
        payment_link_status=status,
        razorpay_payment_id=payment_id,
        razorpay_signature="tampered_signature"
    ) is False


def test_create_payment_link_parameters():
    """Verify that create_payment_link properly configures callback_url and callback_method."""
    test_secret = "test_secret"
    service = RazorpayService(key_id="rzp_test_mock", key_secret=test_secret, base_url="http://localhost:8000")

    # Mock the Razorpay client
    mock_client = MagicMock()
    mock_client.payment_link.create.return_value = {
        "id": "plink_test_123",
        "short_url": "https://rzp.io/i/mocktest",
        "amount": 49900,
        "currency": "INR",
        "status": "created",
        "callback_url": "http://localhost:8000/api/test-payment/callback",
        "callback_method": "get"
    }
    service.client = mock_client

    result = service.create_payment_link(
        amount=499.0,
        description="Test Checkout",
        reference_id="ref_001"
    )

    mock_client.payment_link.create.assert_called_once()
    call_args = mock_client.payment_link.create.call_args[1]["data"]

    assert call_args["amount"] == 49900
    assert call_args["currency"] == "INR"
    assert call_args["callback_url"] == "http://localhost:8000/api/test-payment/callback"
    assert call_args["callback_method"] == "get"
    assert call_args["reference_id"] == "ref_001"
    assert result["id"] == "plink_test_123"


def test_health_endpoint():
    """Test health check route."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "razorpay_configured" in data


def test_payment_link_callback_endpoint():
    """Test GET /api/test-payment/callback route with valid signature."""
    client = TestClient(app)

    # Use a service with known secret for verification
    test_secret = "test_secret_abc"
    from backend import razorpay_client
    original_secret = razorpay_client.razorpay_service.key_secret
    razorpay_client.razorpay_service.key_secret = test_secret

    try:
        plink_id = "plink_cb_test"
        ref_id = "ref_cb_test"
        status = "paid"
        payment_id = "pay_cb_123"

        msg = f"{plink_id}|{ref_id}|{status}|{payment_id}".encode("utf-8")
        valid_sig = hmac.new(test_secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

        response = client.get(
            "/api/test-payment/callback",
            params={
                "razorpay_payment_id": payment_id,
                "razorpay_payment_link_id": plink_id,
                "razorpay_payment_link_reference_id": ref_id,
                "razorpay_payment_link_status": status,
                "razorpay_signature": valid_sig,
            }
        )
        assert response.status_code == 200
        assert "PAYMENT VERIFIED" in response.text
        assert payment_id in response.text
    finally:
        razorpay_client.razorpay_service.key_secret = original_secret
