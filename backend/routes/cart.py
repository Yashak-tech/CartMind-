"""
Cart and Session Endpoints for CartMind (TRD.md §5).
Manages cart sessions, line items with quantity-precise stock checks,
and audited checkout with Razorpay test-mode integration.
"""

import uuid
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from backend.config import settings
from backend.database import get_session
from backend.models import (
    CartSession,
    CartItem,
    Product,
    Order,
    AuditLog,
    AddCartItemRequest,
    CartItemRead,
    CartResponse,
    CheckoutResponse,
)
from backend.razorpay_client import razorpay_service

router = APIRouter(prefix="/session", tags=["Cart & Session"])


def _calculate_cart_response(cart_session: CartSession, db: Session) -> CartResponse:
    """Helper to compute itemized cart and subtotal without leaking margin_pct."""
    items_statement = select(CartItem).where(CartItem.session_id == cart_session.id)
    cart_items = db.exec(items_statement).all()

    items_read: List[CartItemRead] = []
    subtotal = 0.0
    total_items = 0

    for item in cart_items:
        product = db.get(Product, item.product_id)
        if not product:
            continue
        line_total = round(product.price * item.qty, 2)
        subtotal += line_total
        total_items += item.qty
        items_read.append(
            CartItemRead(
                id=item.id,
                product_id=product.id,
                name=product.name,
                price=product.price,
                qty=item.qty,
                line_total=line_total,
                category=product.category,
                image_url=product.image_url,
            )
        )

    return CartResponse(
        session_id=cart_session.id,
        status=cart_session.status,
        items=items_read,
        subtotal=round(subtotal, 2),
        total_items=total_items,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_session(db: Session = Depends(get_session)) -> Dict[str, Any]:
    """Starts a new shopping cart session."""
    session_id = str(uuid.uuid4())
    cart_session = CartSession(id=session_id, status="active")
    db.add(cart_session)
    db.commit()
    db.refresh(cart_session)
    return {
        "session_id": cart_session.id,
        "status": cart_session.status,
        "created_at": cart_session.created_at,
    }


@router.get("", status_code=status.HTTP_200_OK)
def get_or_create_session_browser(db: Session = Depends(get_session)) -> Dict[str, Any]:
    """Browser-friendly session creator so typing /session never throws 405 Method Not Allowed."""
    session_id = str(uuid.uuid4())
    cart_session = CartSession(id=session_id, status="active")
    db.add(cart_session)
    db.commit()
    db.refresh(cart_session)
    return {
        "message": "New shopping cart session created successfully!",
        "session_id": cart_session.id,
        "status": cart_session.status,
        "created_at": cart_session.created_at,
        "cart_url": f"http://127.0.0.1:8000/session/{cart_session.id}/cart",
        "audit_url": f"http://127.0.0.1:8000/audit/{cart_session.id}",
        "interactive_docs": "http://127.0.0.1:8000/docs",
    }


@router.get("/{session_id}/cart", response_model=CartResponse)
def get_cart(session_id: str, db: Session = Depends(get_session)) -> CartResponse:
    """Returns the current state of a shopping cart session."""
    cart_session = db.get(CartSession, session_id)
    if not cart_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cart session '{session_id}' not found."
        )
    return _calculate_cart_response(cart_session, db)


@router.post("/{session_id}/cart/items", response_model=CartResponse)
def add_cart_item(
    session_id: str,
    payload: AddCartItemRequest,
    db: Session = Depends(get_session)
) -> CartResponse:
    """
    Adds a product to the cart with quantity-precise stock validation:
    existing_cart_qty + requested_qty <= product.stock_qty.
    """
    cart_session = db.get(CartSession, session_id)
    if not cart_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cart session '{session_id}' not found."
        )

    if cart_session.status != "active":
        # Auto-reactivate session for the shopper so they can start a fresh cart smoothly
        cart_session.status = "active"
        prev_items = db.exec(select(CartItem).where(CartItem.session_id == session_id)).all()
        for itm in prev_items:
            db.delete(itm)
        db.add(cart_session)
        db.commit()
        db.refresh(cart_session)

    product = db.get(Product, payload.product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {payload.product_id} not found."
        )

    # Check for existing item in cart
    existing_item = db.exec(
        select(CartItem)
        .where(CartItem.session_id == session_id)
        .where(CartItem.product_id == payload.product_id)
    ).first()

    existing_qty = existing_item.qty if existing_item else 0
    requested_qty = payload.qty
    total_requested_qty = existing_qty + requested_qty

    # CRITICAL: Quantity-precise stock validation
    if total_requested_qty > product.stock_qty:
        # Failure Injection Audit: Log blocked execution-time stock check
        audit_entry = AuditLog(
            session_id=session_id,
            event_type="stock_validation_failed",
            payload={
                "product_id": product.id,
                "product_name": product.name,
                "requested_qty": requested_qty,
                "existing_cart_qty": existing_qty,
                "available_stock": product.stock_qty,
                "reason": (
                    f"Stock race condition caught: '{product.name}' only has {product.stock_qty} unit(s) remaining, "
                    f"attempted to claim {total_requested_qty}."
                ),
            }
        )
        db.add(audit_entry)
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Insufficient stock for '{product.name}'. "
                f"Cart already has {existing_qty} unit(s), you requested {requested_qty} more, "
                f"but only {product.stock_qty} unit(s) are available."
            )
        )

    if existing_item:
        existing_item.qty = total_requested_qty
        db.add(existing_item)
    else:
        new_item = CartItem(
            session_id=session_id,
            product_id=product.id,
            qty=requested_qty
        )
        db.add(new_item)

    db.commit()
    return _calculate_cart_response(cart_session, db)


@router.delete("/{session_id}/cart/items/{item_id}", response_model=CartResponse)
def remove_cart_item(
    session_id: str,
    item_id: int,
    db: Session = Depends(get_session)
) -> CartResponse:
    """Removes a specific line item from the cart."""
    cart_session = db.get(CartSession, session_id)
    if not cart_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cart session '{session_id}' not found."
        )

    if cart_session.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot modify cart with status '{cart_session.status}'."
        )

    item = db.get(CartItem, item_id)
    if not item or item.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cart item with ID {item_id} not found in this session."
        )

    db.delete(item)
    db.commit()
    return _calculate_cart_response(cart_session, db)


@router.post("/{session_id}/checkout", response_model=CheckoutResponse)
def checkout_cart(
    session_id: str,
    db: Session = Depends(get_session)
) -> CheckoutResponse:
    """
    Triggers checkout for the cart session:
    1. Validates active session and non-empty cart.
    2. Re-validates stock for all cart items.
    3. Creates Razorpay payment link with explicit callback_url and callback_method.
    4. Records an Order row.
    5. CRITICAL: Writes an AuditLog row ('checkout_initiated') from Day One.
    6. Updates CartSession status to 'checked_out'.
    """
    cart_session = db.get(CartSession, session_id)
    if not cart_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cart session '{session_id}' not found."
        )

    if cart_session.status != "active":
        cart_items = db.exec(
            select(CartItem).where(CartItem.session_id == session_id)
        ).all()
        if cart_items:
            cart_session.status = "active"
            db.add(cart_session)
            db.commit()
            db.refresh(cart_session)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot checkout an empty or already completed cart."
            )

    cart_items = db.exec(
        select(CartItem).where(CartItem.session_id == session_id)
    ).all()

    if not cart_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot checkout an empty cart."
        )

    # Re-validate stock for every item at checkout time
    subtotal = 0.0
    items_summary = []
    for item in cart_items:
        product = db.get(Product, item.product_id)
        if not product or item.qty > product.stock_qty:
            item_name = product.name if product else f"ID {item.product_id}"
            available = product.stock_qty if product else 0
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stock error: '{item_name}' only has {available} available, but cart contains {item.qty}."
            )
        line_cost = round(product.price * item.qty, 2)
        subtotal += line_cost
        items_summary.append({
            "product_id": product.id,
            "name": product.name,
            "qty": item.qty,
            "unit_price": product.price,
            "line_total": line_cost,
        })

    subtotal = round(subtotal, 2)
    callback_url = f"{settings.BASE_URL.rstrip('/')}/api/test-payment/callback"

    # Razorpay Payment Link creation
    rzp_order_id = f"order_sim_{uuid.uuid4().hex[:12]}"
    payment_link_id = None
    payment_link_url = None

    if settings.has_razorpay_credentials:
        try:
            link = razorpay_service.create_payment_link(
                amount=subtotal,
                description=f"CartMind Checkout - Session {session_id[:8]}",
                reference_id=session_id,
                callback_url=callback_url,
                notes={"session_id": session_id, "item_count": len(cart_items)}
            )
            payment_link_id = link["id"]
            payment_link_url = link["short_url"]
            rzp_order_id = link.get("order_id") or payment_link_id
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Razorpay checkout initiation failed: {str(e)}"
            )
    else:
        # Fallback simulation for offline / testing without live keys
        payment_link_url = f"{callback_url}?simulated=true&session_id={session_id}&amount={subtotal}"

    # 4. Create Order row
    order = Order(
        session_id=session_id,
        razorpay_order_id=rzp_order_id,
        amount=subtotal,
        status="created",
    )
    db.add(order)
    db.flush()  # Assigns order.id

    # 5. CRITICAL: Write AuditLog entry from Day One
    audit_entry = AuditLog(
        session_id=session_id,
        event_type="checkout_initiated",
        payload={
            "order_id": order.id,
            "razorpay_order_id": rzp_order_id,
            "amount": subtotal,
            "payment_link_id": payment_link_id,
            "payment_link_url": payment_link_url,
            "items": items_summary,
            "total_items": sum(i["qty"] for i in items_summary),
        }
    )
    db.add(audit_entry)

    # 6. Update session status
    cart_session.status = "checked_out"
    db.add(cart_session)

    db.commit()
    db.refresh(order)

    return CheckoutResponse(
        session_id=session_id,
        order_id=order.id,
        razorpay_order_id=rzp_order_id,
        amount=subtotal,
        payment_link_id=payment_link_id,
        payment_link_url=payment_link_url,
        status=order.status,
    )
