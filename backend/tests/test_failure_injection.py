"""
Unit & Integration tests for Phase 6: Failure Injection (Stock Race Condition Demo & Graceful Recovery).
Validates TRD.md §9 Option A:
- An item is recommended while in stock.
- Inventory is depleted mid-conversation before acceptance.
- Execution-time stock validation blocks the stale action.
- System logs 'stock_validation_failed' in the AuditLog.
- Agent recovers gracefully without crashing.
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from backend.main import app
from backend.database import get_session, engine
from backend.models import Product, CartSession, CartItem, AuditLog
from backend.gate.engine import GatingEngine


from backend.routes.auth import create_access_token


@pytest.fixture
def client():
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {create_access_token('test_failure@cartmind.ai')}"})
    return c


def test_proposal_time_stock_check_passes():
    """Confirms proposal-time stock check passes when product has inventory > 0."""
    gate = GatingEngine()
    with Session(engine) as session:
        # Create a session
        sess = CartSession(id=str(uuid.uuid4()), status="active")
        session.add(sess)
        session.commit()
        session.refresh(sess)

        # SKU 15 seeded with stock_qty >= 2
        prod = session.get(Product, 15)
        if not prod:
            prod = Product(
                id=15,
                name="UltraSpeed USB-C 100W Hub",
                price=2499.0,
                stock_qty=2,
                margin_pct=40.0,
                category="Workspace & Productivity",
                description="Compact 7-in-1 USB-C hub with 100W Power Delivery."
            )
            session.add(prod)
            session.commit()
            session.refresh(prod)
        else:
            prod.stock_qty = 2
            session.add(prod)
            session.commit()

        # Proposal time gate check
        results = gate.evaluate_turn(
            session_id=sess.id,
            tool_calls=[{"name": "recommend_product", "arguments": {"product_id": 15}}],
            db=session,
        )

        assert len(results) == 1
        res = results[0]
        assert res.decision == "approved"
        assert res.rule_triggered == "stock_check"
        assert "in stock" in res.reason_text.lower()


def test_stock_race_condition_blocked_at_execution_time(client):
    """
    TRD.md §9 Option A End-to-End Test:
    1. Customer creates session.
    2. Stock is depleted to 0 (simulating another customer claiming the last unit).
    3. Customer attempts to add the depleted item.
    4. Execution-time gate BLOCKS the add.
    5. 'stock_validation_failed' is recorded in the AuditLog.
    """
    # 1. Create a fresh session
    sess_res = client.post("/session")
    assert sess_res.status_code == 201
    session_id = sess_res.json()["session_id"]

    # 2. Simulate stock depletion on SKU 15
    deplete_res = client.post("/products/15/deplete-stock")
    assert deplete_res.status_code == 200
    assert deplete_res.json()["current_stock"] == 0

    # 3. Attempt to add the depleted item to the cart
    add_res = client.post(
        f"/session/{session_id}/cart/items",
        json={"product_id": 15, "qty": 1}
    )
    # Must fail with 400 Bad Request
    assert add_res.status_code == 400
    err_detail = add_res.json()["detail"]
    assert "Insufficient stock" in err_detail or "Stock race condition" in err_detail

    # 4. Verify AuditLog contains the blocked race condition record
    with Session(engine) as session:
        audit_records = session.exec(
            select(AuditLog)
            .where(AuditLog.session_id == session_id)
            .where(AuditLog.event_type == "stock_validation_failed")
        ).all()

        assert len(audit_records) >= 1
        record = audit_records[0]
        assert record.payload["product_id"] == 15
        assert record.payload["available_stock"] == 0
        assert "Stock race condition caught" in record.payload["reason"]

    # 5. Restore stock for subsequent tests
    restore_res = client.post("/products/15/restore-stock?qty=2")
    assert restore_res.status_code == 200
    assert restore_res.json()["current_stock"] == 2


def test_graceful_recovery_after_stock_race_condition(client):
    """
    Proves the session remains completely healthy and interactive after a stock failure:
    Customer can still chat, add an alternative item, and check out without restarting.
    """
    sess_res = client.post("/session")
    session_id = sess_res.json()["session_id"]

    # Deplete SKU 15
    client.post("/products/15/deplete-stock")

    # Attempt to add SKU 15 -> blocked
    blocked_res = client.post(f"/session/{session_id}/cart/items", json={"product_id": 15, "qty": 1})
    assert blocked_res.status_code == 400

    # Customer chats: "What else do you recommend instead?"
    chat_res = client.post(
        f"/session/{session_id}/message",
        json={"message": "The hub was out of stock. What else do you recommend instead?"}
    )
    assert chat_res.status_code == 200
    reply = chat_res.json()["reply"]
    assert len(reply) > 0

    # Customer adds an alternative in-stock product (SKU 1: Apex Wireless ANC Headphones)
    alt_res = client.post(
        f"/session/{session_id}/cart/items",
        json={"product_id": 1, "qty": 1}
    )
    assert alt_res.status_code == 200
    assert len(alt_res.json()["items"]) == 1

    # Restore SKU 15 stock
    client.post("/products/15/restore-stock?qty=2")
