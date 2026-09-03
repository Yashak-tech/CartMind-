"""
Razorpay Service Client for CartMind.
Handles test-mode order creation, payment link generation, and signature verification.

IMPORTANT ARCHITECTURAL RULE (AGENTS.md):
The LLM reasoning layer must NEVER call this service directly.
Only the deterministic Action Executor (after Gate approval) may execute these methods.
"""

import hmac
import hashlib
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Union, Dict, Any
import razorpay

from backend.config import settings


def rupees_to_paise(amount: Union[float, int, str, Decimal]) -> int:
    """
    Converts currency amount in INR to paise (subunits) using Decimal rounding.
    Prevents floating-point precision issues.

    Example:
        rupees_to_paise(149.99) -> 14999
        rupees_to_paise("499.50") -> 49950
    """
    dec_amt = Decimal(str(amount))
    paise = (dec_amt * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(paise)


class RazorpayService:
    """Service wrapping the Razorpay Python SDK in test mode."""

    def __init__(
        self,
        key_id: Optional[str] = None,
        key_secret: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.key_id = key_id or settings.RAZORPAY_KEY_ID
        self.key_secret = key_secret or settings.RAZORPAY_KEY_SECRET
        self.base_url = base_url or settings.BASE_URL

        if self.key_id and self.key_secret:
            # Enforce test-mode check
            if not self.key_id.startswith("rzp_test_"):
                raise ValueError("SECURITY VIOLATION: Only Razorpay test keys (starting with 'rzp_test_') are permitted.")
            self.client = razorpay.Client(auth=(self.key_id, self.key_secret))
        else:
            self.client = None

    def _ensure_client(self) -> razorpay.Client:
        """Ensures Razorpay client is initialized with credentials."""
        if not self.client:
            raise ValueError(
                "Razorpay test credentials not configured. Please set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in backend/.env."
            )
        return self.client

    def create_order(
        self,
        amount: Union[float, int, str, Decimal],
        receipt: str,
        notes: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Creates a Razorpay test order.
        Amount is converted to paise using Decimal rounding.
        """
        client = self._ensure_client()
        amount_in_paise = rupees_to_paise(amount)
        data = {
            "amount": amount_in_paise,
            "currency": "INR",
            "receipt": receipt,
            "notes": notes or {},
        }
        return client.order.create(data=data)

    def create_payment_link(
        self,
        amount: Union[float, int, str, Decimal],
        description: str,
        reference_id: Optional[str] = None,
        customer: Optional[Dict[str, str]] = None,
        notes: Optional[Dict[str, Any]] = None,
        callback_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Creates a Razorpay Payment Link (short_url) with explicit callback parameters.
        When payment completes, Razorpay redirects to callback_url with GET parameters.
        """
        client = self._ensure_client()
        amount_in_paise = rupees_to_paise(amount)
        resolved_callback = callback_url or f"{self.base_url.rstrip('/')}/api/test-payment/callback"

        payload: Dict[str, Any] = {
            "amount": amount_in_paise,
            "currency": "INR",
            "accept_partial": False,
            "description": description,
            "callback_url": resolved_callback,
            "callback_method": "get",
            "notes": notes or {},
        }
        if reference_id:
            payload["reference_id"] = reference_id
        if customer:
            payload["customer"] = customer

        return client.payment_link.create(data=payload)

    def verify_order_payment_signature(
        self,
        order_id: str,
        payment_id: str,
        signature: str,
    ) -> bool:
        """
        Verifies signature for standard Orders checkout flow:
        HMAC-SHA256(order_id + "|" + payment_id, key_secret)
        """
        if not self.key_secret:
            raise ValueError("RAZORPAY_KEY_SECRET is required to verify signature.")

        msg = f"{order_id}|{payment_id}".encode("utf-8")
        generated_signature = hmac.new(
            self.key_secret.encode("utf-8"),
            msg,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(generated_signature, signature)

    def verify_payment_link_signature(
        self,
        payment_link_id: str,
        payment_link_reference_id: str,
        payment_link_status: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
    ) -> bool:
        """
        Verifies signature for Payment Link redirect callback:
        HMAC-SHA256(payment_link_id + "|" + payment_link_reference_id + "|" + payment_link_status + "|" + razorpay_payment_id, key_secret)
        """
        if not self.key_secret:
            raise ValueError("RAZORPAY_KEY_SECRET is required to verify signature.")

        msg = f"{payment_link_id}|{payment_link_reference_id}|{payment_link_status}|{razorpay_payment_id}".encode("utf-8")
        generated_signature = hmac.new(
            self.key_secret.encode("utf-8"),
            msg,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(generated_signature, signature_str if (signature_str := razorpay_signature) else "")

    def verify_webhook_signature(
        self,
        body_bytes: bytes,
        signature: str,
        secret: Optional[str] = None,
    ) -> bool:
        """
        Verifies Razorpay Webhook signature:
        HMAC-SHA256(raw_request_body, webhook_secret or key_secret)
        """
        webhook_secret = secret or getattr(settings, "RAZORPAY_WEBHOOK_SECRET", None) or self.key_secret
        if not webhook_secret:
            raise ValueError("Razorpay secret required for webhook signature verification.")

        generated_sig = hmac.new(
            webhook_secret.encode("utf-8"),
            body_bytes,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(generated_sig, signature)

    def fetch_order(self, order_id: str) -> Dict[str, Any]:
        """Fetches order details from Razorpay."""
        client = self._ensure_client()
        return client.order.fetch(order_id)

    def fetch_payment(self, payment_id: str) -> Dict[str, Any]:
        """Fetches payment details from Razorpay."""
        client = self._ensure_client()
        return client.payment.fetch(payment_id)

    def fetch_payment_link(self, payment_link_id: str) -> Dict[str, Any]:
        """Fetches payment link status and details from Razorpay."""
        client = self._ensure_client()
        return client.payment_link.fetch(payment_link_id)


# Default singleton instance
razorpay_service = RazorpayService()
