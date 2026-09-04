"""
Unit and integration tests for CartMind Phase 2:
- Catalog listing & confidential margin shielding (margin_pct never exposed)
- Quantity-precise stock validation (existing_qty + requested_qty <= stock_qty)
- Cart subtotal and item manipulation
- Audited checkout (Order and AuditLog row created on Day One)
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from backend.main import app
from backend.database import engine, init_db, seed_catalog
from backend.models import Product, CartSession, CartItem, Order, AuditLog


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
    c.headers.update({"Authorization": f"Bearer {create_access_token('test_catalog@cartmind.ai')}"})
    with c as test_client:
        yield test_client


def test_products_hide_margin_pct(client):
    """
    CRITICAL TEST: Ensure margin_pct is NEVER exposed in customer-facing APIs.
    margin_pct is confidential merchant metadata for the Gating Engine only.
    """
    # 1. Test /products catalog list
    response = client.get("/products")
    assert response.status_code == 200
    products = response.json()
    assert len(products) >= 15

    for p in products:
        assert "margin_pct" not in p, f"Security Violation: margin_pct leaked in product '{p.get('name')}'"
        assert "price" in p
        assert "stock_qty" in p
        assert "name" in p
        assert "category" in p
        assert "description" in p

    # 2. Test /products/{id} detail endpoint
    single_res = client.get(f"/products/{products[0]['id']}")
    assert single_res.status_code == 200
    p_detail = single_res.json()
    assert "margin_pct" not in p_detail, "Security Violation: margin_pct leaked in single product detail"


def test_quantity_precise_stock_check(client):
    """
    Verify quantity-precise stock validation:
    existing_cart_qty + requested_qty <= product.stock_qty.
    Product 10 (UltraSpeed USB-C 100W Hub) has exactly 2 units in stock.
    """
    # Create new session
    session_res = client.post("/session")
    assert session_res.status_code == 201
    session_id = session_res.json()["session_id"]

    # Product 10 has stock_qty = 2
    # 1. Add 1 unit (allowed: 0 + 1 <= 2)
    add1 = client.post(
        f"/session/{session_id}/cart/items",
        json={"product_id": 10, "qty": 1}
    )
    assert add1.status_code == 200
    assert add1.json()["total_items"] == 1
    assert add1.json()["items"][0]["qty"] == 1

    # 2. Add 1 more unit (allowed: 1 + 1 <= 2)
    add2 = client.post(
        f"/session/{session_id}/cart/items",
        json={"product_id": 10, "qty": 1}
    )
    assert add2.status_code == 200
    assert add2.json()["total_items"] == 2
    assert add2.json()["items"][0]["qty"] == 2

    # 3. Add 1 more unit (rejected: 2 + 1 > 2)
    add3 = client.post(
        f"/session/{session_id}/cart/items",
        json={"product_id": 10, "qty": 1}
    )
    assert add3.status_code == 400
    err_detail = add3.json()["detail"]
    assert "Insufficient stock" in err_detail
    assert "only 2 unit(s) are available" in err_detail


def test_cart_subtotal_calculation_and_removal(client):
    """Verify cart subtotal computation and item removal."""
    # Create session
    session_res = client.post("/session")
    session_id = session_res.json()["session_id"]

    # Add Product 6 (TitanFold Wallet, ₹1499.0) x 2 = ₹2998.0
    client.post(
        f"/session/{session_id}/cart/items",
        json={"product_id": 6, "qty": 2}
    )

    # Add Product 7 (HydroChamber Bottle, ₹999.0) x 1 = ₹999.0
    cart_res = client.post(
        f"/session/{session_id}/cart/items",
        json={"product_id": 7, "qty": 1}
    )
    cart_data = cart_res.json()
    assert cart_data["subtotal"] == 3997.0
    assert cart_data["total_items"] == 3

    # Fetch cart via GET
    get_cart_res = client.get(f"/session/{session_id}/cart")
    assert get_cart_res.status_code == 200
    assert get_cart_res.json()["subtotal"] == 3997.0

    # Remove item 7
    item_to_remove = next(i for i in cart_data["items"] if i["product_id"] == 7)
    del_res = client.delete(f"/session/{session_id}/cart/items/{item_to_remove['id']}")
    assert del_res.status_code == 200
    del_data = del_res.json()
    assert del_data["subtotal"] == 2998.0
    assert del_data["total_items"] == 2


def test_checkout_writes_audit_log_and_creates_order(client):
    """
    CRITICAL TEST: Ensure checkout creates an Order AND writes an AuditLog
    entry ('checkout_initiated') from Day One.
    """
    # 1. Create session and add item
    session_res = client.post("/session")
    session_id = session_res.json()["session_id"]

    # Add Product 9 (ProShield Cable, ₹799) x 1
    client.post(
        f"/session/{session_id}/cart/items",
        json={"product_id": 9, "qty": 1}
    )

    # 2. Checkout
    checkout_res = client.post(f"/session/{session_id}/checkout")
    assert checkout_res.status_code == 200
    checkout_data = checkout_res.json()

    assert checkout_data["session_id"] == session_id
    assert checkout_data["amount"] == 799.0
    assert checkout_data["status"] == "created"
    assert "razorpay_order_id" in checkout_data

    # 3. Verify Order row directly in database
    with Session(engine) as db:
        order = db.exec(
            select(Order).where(Order.session_id == session_id)
        ).first()
        assert order is not None
        assert order.amount == 799.0
        assert order.status == "created"

        # 4. CRITICAL: Verify AuditLog row was written
        audit_log = db.exec(
            select(AuditLog)
            .where(AuditLog.session_id == session_id)
            .where(AuditLog.event_type == "checkout_initiated")
        ).first()
        assert audit_log is not None, "AuditLog entry for checkout_initiated was not written!"
        assert audit_log.payload["amount"] == 799.0
        assert audit_log.payload["total_items"] == 1
        assert audit_log.payload["items"][0]["product_id"] == 9


def test_checkout_empty_cart_fails(client):
    """Verify cannot checkout an empty cart."""
    session_res = client.post("/session")
    session_id = session_res.json()["session_id"]

    checkout_res = client.post(f"/session/{session_id}/checkout")
    assert checkout_res.status_code == 400
    assert "Cannot checkout an empty cart" in checkout_res.json()["detail"]
