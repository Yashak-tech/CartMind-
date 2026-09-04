"""
Unit and Integration Tests for CartMind Gating Engine & Reasoning Layer.
Proves that EVERY rule in TRD.md §6 deterministically blocks or modifies violating actions.
Uses unique UUIDs for complete test idempotency.
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from backend.main import app
from backend.database import engine, init_db, seed_catalog
from backend.models import Product, CartSession, CartItem, AgentRecommendation, GateDecision
from backend.gate.engine import gating_engine, GateResult
from backend.agent.reasoner import ToolCallProposal


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Initializes schema and seeds catalog before running tests."""
    init_db()
    seed_catalog()


from backend.routes.auth import create_access_token


@pytest.fixture
def client():
    """FastAPI TestClient with lifespan events and auth enabled."""
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {create_access_token('test_gate@cartmind.ai')}"})
    with c as test_client:
        yield test_client


def test_rule_1_stock_check():
    """
    RULE 1: Recommended product must be in stock (stock_qty > 0).
    Violating action MUST be blocked with rule_triggered='stock_check'.
    """
    with Session(engine) as db:
        session = CartSession(id=f"sess_{uuid.uuid4().hex[:10]}", status="active")
        # Create an out-of-stock product
        oos_product = Product(
            name="Ghost Item",
            price=999.0,
            stock_qty=0,  # OUT OF STOCK
            margin_pct=40.0,
            category="Test",
            description="Out of stock test item",
        )
        db.add(session)
        db.add(oos_product)
        db.commit()
        db.refresh(oos_product)

        # Propose recommending the out-of-stock item
        tool_calls = [
            ToolCallProposal(
                name="recommend_product",
                arguments={"product_id": oos_product.id, "reason": "You might like this."}
            )
        ]

        results = gating_engine.evaluate_turn(
            session_id=session.id,
            tool_calls=tool_calls,
            db=db
        )

        assert len(results) == 1
        res = results[0]
        assert res.decision == "blocked", "Out-of-stock product was NOT blocked!"
        assert res.rule_triggered == "stock_check"
        assert "out of stock" in res.reason_text.lower()


def test_rule_2_turn_recommendation_cap():
    """
    RULE 2: Max 1 recommendation per conversational turn.
    A second proposal in the same turn MUST be blocked with rule_triggered='turn_recommendation_cap'.
    """
    with Session(engine) as db:
        session = CartSession(id=f"sess_{uuid.uuid4().hex[:10]}", status="active")
        db.add(session)
        db.commit()

        # Propose TWO recommendations within the same turn
        tool_calls = [
            ToolCallProposal(
                name="recommend_product",
                arguments={"product_id": 1, "reason": "First recommendation"}
            ),
            ToolCallProposal(
                name="recommend_product",
                arguments={"product_id": 2, "reason": "Second recommendation in same turn"}
            )
        ]

        results = gating_engine.evaluate_turn(
            session_id=session.id,
            tool_calls=tool_calls,
            db=db
        )

        assert len(results) == 2

        # First proposal should be approved (product 1 is in stock)
        assert results[0].decision == "approved"
        assert results[0].rule_triggered == "stock_check"

        # Second proposal MUST be blocked by the turn cap
        assert results[1].decision == "blocked"
        assert results[1].rule_triggered == "turn_recommendation_cap"
        assert "Maximum 1 product recommendation" in results[1].reason_text


def test_rule_3_and_4_unified_discount_ceiling():
    """
    RULE 4: Discount Ceiling (20% absolute max).
    When proposed discount > 20% on a high-margin cart, it MUST be MODIFIED
    and capped down to 20.0% with rule_triggered='discount_ceiling'.
    """
    with Session(engine) as db:
        session = CartSession(id=f"sess_{uuid.uuid4().hex[:10]}", status="active")
        # Product 6: TitanFold Wallet (margin 65%, price ₹1499)
        db.add(session)
        db.commit()
        db.add(CartItem(session_id=session.id, product_id=6, qty=1))
        db.commit()

        # Proposed discount: 35.0%
        tool_calls = [
            ToolCallProposal(
                name="apply_discount",
                arguments={"percent": 35.0, "reason": "VIP customer promotion"}
            )
        ]

        results = gating_engine.evaluate_turn(
            session_id=session.id,
            tool_calls=tool_calls,
            db=db
        )

        assert len(results) == 1
        res = results[0]
        assert res.decision == "modified", "Over-limit discount was not modified!"
        assert res.rule_triggered == "discount_ceiling"
        assert res.action_data["applied_percent"] == 20.0
        assert res.action_data["proposed_percent"] == 35.0
        assert "store ceiling of 20.0%" in res.reason_text


def test_rule_3_and_4_unified_margin_floor():
    """
    RULE 3: Margin Floor (10% minimum profit).
    When proposed discount drops cart margin below 10%, it MUST be capped or blocked
    with rule_triggered='margin_floor'.
    """
    with Session(engine) as db:
        session = CartSession(id=f"sess_{uuid.uuid4().hex[:10]}", status="active")
        # Create a product with a tight 16% margin (floor allowance = 16% - 10% = 6%)
        tight_product = Product(
            name="Low Margin Gadget",
            price=1000.0,
            stock_qty=10,
            margin_pct=16.0,  # 16% margin -> max allowed discount is 6%
            category="Test",
            description="Low margin test item",
        )
        db.add(session)
        db.add(tight_product)
        db.commit()
        db.refresh(tight_product)
        db.add(CartItem(session_id=session.id, product_id=tight_product.id, qty=1))
        db.commit()

        # Case A: Request 15% discount (exceeds 6% allowance) -> MODIFIED to 6.0% with rule_triggered='margin_floor'
        tool_calls = [
            ToolCallProposal(
                name="apply_discount",
                arguments={"percent": 15.0, "reason": "Requested 15%"}
            )
        ]

        results = gating_engine.evaluate_turn(session_id=session.id, tool_calls=tool_calls, db=db)
        assert len(results) == 1
        res = results[0]
        assert res.decision == "modified"
        assert res.rule_triggered == "margin_floor"
        assert res.action_data["applied_percent"] == 6.0
        assert "protect the 10.0% margin floor" in res.reason_text

        # Case B: Cart with margin <= 10% -> BLOCKED
        no_margin_product = Product(
            name="Zero Margin Item",
            price=500.0,
            stock_qty=10,
            margin_pct=8.0,  # 8% margin is already below 10% floor
            category="Test",
            description="Below floor item",
        )
        session_no_margin = CartSession(id=f"sess_{uuid.uuid4().hex[:10]}", status="active")
        db.add(no_margin_product)
        db.add(session_no_margin)
        db.commit()
        db.refresh(no_margin_product)
        db.add(CartItem(session_id=session_no_margin.id, product_id=no_margin_product.id, qty=1))
        db.commit()

        results_blocked = gating_engine.evaluate_turn(
            session_id=session_no_margin.id,
            tool_calls=[ToolCallProposal(name="apply_discount", arguments={"percent": 5.0, "reason": "Any deal?"})],
            db=db
        )
        assert len(results_blocked) == 1
        assert results_blocked[0].decision == "blocked"
        assert results_blocked[0].rule_triggered == "margin_floor"
        assert "at or below the 10.0% margin floor" in results_blocked[0].reason_text


def test_rule_5_checkout_confirmation():
    """
    RULE 5: Checkout requires explicit user confirmation flag (confirmed_by_user=True).
    If False or unconfirmed, MUST be blocked with rule_triggered='checkout_confirmation'.
    """
    with Session(engine) as db:
        session = CartSession(id=f"sess_{uuid.uuid4().hex[:10]}", status="active")
        db.add(session)
        db.commit()
        db.add(CartItem(session_id=session.id, product_id=1, qty=1))
        db.commit()

        # 1. Unconfirmed checkout proposal -> BLOCKED
        unconfirmed_call = [
            ToolCallProposal(
                name="initiate_checkout",
                arguments={"confirmed_by_user": False}
            )
        ]
        res_unconfirmed = gating_engine.evaluate_turn(session_id=session.id, tool_calls=unconfirmed_call, db=db)
        assert len(res_unconfirmed) == 1
        assert res_unconfirmed[0].decision == "blocked"
        assert res_unconfirmed[0].rule_triggered == "checkout_confirmation"
        assert "explicit customer confirmation is required" in res_unconfirmed[0].reason_text

        # 2. Confirmed checkout proposal -> APPROVED
        confirmed_call = [
            ToolCallProposal(
                name="initiate_checkout",
                arguments={"confirmed_by_user": True}
            )
        ]
        res_confirmed = gating_engine.evaluate_turn(session_id=session.id, tool_calls=confirmed_call, db=db)
        assert len(res_confirmed) == 1
        assert res_confirmed[0].decision == "approved"
        assert res_confirmed[0].rule_triggered == "checkout_confirmation"


def test_chat_endpoint_end_to_end(client):
    """
    Test POST /session/{id}/message end-to-end:
    - User asks for a discount
    - Reasoner proposes tool call
    - Gating engine evaluates and caps/approves
    - Action executor persists AgentRecommendation and GateDecision
    - Returns multi-decision list with enriched action payloads
    """
    # 1. Create session and add high-margin item (TitanFold Wallet, ₹1499, margin 65%)
    sess_res = client.post("/session")
    session_id = sess_res.json()["session_id"]
    client.post(f"/session/{session_id}/cart/items", json={"product_id": 6, "qty": 1})

    # 2. Send message asking for 35% discount (exceeds 20% ceiling)
    msg_res = client.post(
        f"/session/{session_id}/message",
        json={"message": "Can I get a 35% discount on this order please?"}
    )
    assert msg_res.status_code == 200
    data = msg_res.json()

    assert "reply" in data
    assert "decisions" in data
    assert isinstance(data["decisions"], list)
    assert len(data["decisions"]) >= 1

    discount_dec = next(d for d in data["decisions"] if d["tool_name"] == "apply_discount")
    assert discount_dec["decision"] == "modified"
    assert discount_dec["rule_triggered"] == "discount_ceiling"
    assert discount_dec["action_data"]["applied_percent"] == 20.0
    assert discount_dec["action_data"]["proposed_percent"] == 35.0

    # 3. Verify database persistence
    with Session(engine) as db:
        rec = db.exec(
            select(AgentRecommendation).where(AgentRecommendation.session_id == session_id)
        ).first()
        assert rec is not None
        assert rec.proposed_action["tool"] == "apply_discount"

        dec = db.exec(
            select(GateDecision).where(GateDecision.recommendation_id == rec.id)
        ).first()
        assert dec is not None
        assert dec.decision == "modified"
        assert dec.rule_triggered == "discount_ceiling"
