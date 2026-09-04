"""
Unit and Integration Tests for Phase 4: Audit Trail & Webhooks.
Verifies chronological audit ordering, 1:1 proposal-to-decision pairing,
and authoritative Razorpay webhook processing.
"""

import json
import uuid
import hmac
import hashlib
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from backend.main import app
from backend.config import settings
from backend.database import engine, init_db, seed_catalog
from backend.models import Order, AuditLog, CartSession, CartItem


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Initializes schema and seeds catalog before running tests."""
    init_db()
    seed_catalog()


from backend.routes.auth import create_access_token


@pytest.fixture
def client():
    """FastAPI TestClient with lifespan events enabled."""
    c = TestClient(app)
    token = create_access_token("test_audit@cartmind.ai")
    c.headers.update({"Authorization": f"Bearer {token}"})
    with c as test_client:
        yield test_client


def test_audit_trail_chronological_ordering(client):
    """
    Verify GET /audit/{session_id} returns an immutable, chronological feed
    with paired recommendations and gate decisions.
    """
    # 1. Create a session and add an item
    sess_res = client.post("/session")
    session_id = sess_res.json()["session_id"]
    client.post(f"/session/{session_id}/cart/items", json={"product_id": 6, "qty": 1})

    # 2. Chat action 1: Ask for recommendation
    client.post(
        f"/session/{session_id}/message",
        json={"message": "Can you recommend a complementary item?"}
    )

    # 3. Chat action 2: Ask for 35% discount (modified to 20%)
    client.post(
        f"/session/{session_id}/message",
        json={"message": "Give me a 35% discount on this order"}
    )

    # 4. Checkout
    client.post(f"/session/{session_id}/checkout")

    # 5. Query the audit trail
    audit_res = client.get(f"/audit/{session_id}")
    assert audit_res.status_code == 200
    data = audit_res.json()

    assert data["session_id"] == session_id
    timeline = data["timeline"]
    summary = data["summary"]

    # Verify minimum expected events
    assert len(timeline) >= 3
    assert summary["total_proposals"] >= 2
    assert summary["approved_count"] >= 1  # Recommendation approved
    assert summary["modified_count"] >= 1  # Discount capped to 20%

    # Verify chronological ordering (each timestamp >= preceding)
    for i in range(len(timeline) - 1):
        assert timeline[i]["timestamp"] <= timeline[i + 1]["timestamp"], "Audit timeline is not in chronological order!"

    # Verify structure of ledger entries
    for entry in timeline:
        assert "action" in entry
        assert "decision" in entry
        assert "reason_text" in entry
        assert "rule_triggered" in entry
        assert "summary" in entry
        assert "time_str" in entry

    # Verify discount entry has modified status and binding rule
    discount_entry = next(e for e in timeline if e["action"] == "DISCOUNT")
    assert discount_entry["decision"] == "modified"
    assert discount_entry["rule_triggered"] == "discount_ceiling"

    # Verify checkout entry exists in timeline
    checkout_entry = next(e for e in timeline if e["action"] == "CHECKOUT")
    assert checkout_entry["decision"] == "approved"


def test_list_audit_sessions(client):
    """Verify GET /audit returns all sessions with decision counts for admin filter."""
    res = client.get("/audit")
    assert res.status_code == 200
    sessions = res.json()
    assert isinstance(sessions, list)
    assert len(sessions) >= 1

    first = sessions[0]
    assert "session_id" in first
    assert "status" in first
    assert "approved_count" in first
    assert "total_proposals" in first


def test_authoritative_webhook_processing(client):
    """
    Verify POST /api/webhooks/razorpay validates HMAC signature,
    transitions Order to 'paid', and appends an authoritative audit entry.
    """
    # 1. Create session, add item, and checkout
    sess_res = client.post("/session")
    session_id = sess_res.json()["session_id"]
    client.post(f"/session/{session_id}/cart/items", json={"product_id": 9, "qty": 1})
    co_res = client.post(f"/session/{session_id}/checkout")
    order_data = co_res.json()

    # 2. Construct simulated webhook payload
    webhook_secret = settings.RAZORPAY_KEY_SECRET or "cartmind_test_webhook_secret_123"
    from backend import razorpay_client
    orig_secret = razorpay_client.razorpay_service.key_secret
    razorpay_client.razorpay_service.key_secret = webhook_secret

    try:
        payment_id = f"pay_wh_{uuid.uuid4().hex[:8]}"
        payload_dict = {
            "entity": "event",
            "account_id": "acc_test",
            "event": "payment_link.paid",
            "contains": ["payment_link", "payment"],
            "payload": {
                "payment_link": {
                    "entity": {
                        "id": order_data.get("payment_link_id") or "plink_test",
                        "reference_id": session_id,
                        "amount_paid": 79900,
                        "status": "paid"
                    }
                },
                "payment": {
                    "entity": {
                        "id": payment_id,
                        "amount": 79900,
                        "status": "captured"
                    }
                }
            }
        }
        body_bytes = json.dumps(payload_dict).encode("utf-8")

        # Generate HMAC-SHA256 signature
        valid_signature = hmac.new(
            webhook_secret.encode("utf-8"),
            body_bytes,
            hashlib.sha256
        ).hexdigest()

        # Send webhook request
        wh_res = client.post(
            "/api/webhooks/razorpay",
            content=body_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Razorpay-Signature": valid_signature,
            }
        )
        assert wh_res.status_code == 200
        assert wh_res.json()["status"] == "processed"

        # 3. Check Order status in DB is now 'paid'
        with Session(engine) as db:
            order = db.exec(select(Order).where(Order.session_id == session_id)).first()
            assert order is not None
            assert order.status == "paid"

            # Check authoritative AuditLog entry
            audit_entry = db.exec(
                select(AuditLog)
                .where(AuditLog.session_id == session_id)
                .where(AuditLog.event_type == "payment_confirmed")
            ).first()
            assert audit_entry is not None
            assert audit_entry.payload["authoritative"] is True
            assert audit_entry.payload["payment_id"] == payment_id

        # 4. Check that GET /audit/{session_id} now contains the PAYMENT confirmation
        audit_after = client.get(f"/audit/{session_id}").json()
        payment_timeline_event = next(
            (e for e in audit_after["timeline"] if e["action"] == "PAYMENT"),
            None
        )
        assert payment_timeline_event is not None
        assert payment_timeline_event["decision"] == "approved"
        assert payment_id in payment_timeline_event["summary"]
    finally:
        razorpay_client.razorpay_service.key_secret = orig_secret
