"""
Authoritative Razorpay Webhook Endpoint for CartMind (TRD.md §8 & Phase 4).
Processes server-to-server payment confirmations even if the customer closes
their browser tab before the client-side redirect completes.
"""

import json
from typing import Dict, Any
from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlmodel import Session, select

from backend.database import get_session
from backend.models import Order, CartSession, AuditLog
from backend.razorpay_client import razorpay_service

router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])


@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    db: Session = Depends(get_session)
) -> Dict[str, Any]:
    """
    Authoritative server-to-server Razorpay webhook listener:
    1. Validates HMAC-SHA256 signature against request body.
    2. Updates Order status to 'paid'.
    3. Persists an authoritative 'payment_confirmed' entry in AuditLog.
    """
    body_bytes = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")

    if not signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-Razorpay-Signature header."
        )

    try:
        is_valid = razorpay_service.verify_webhook_signature(
            body_bytes=body_bytes,
            signature=signature
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Webhook verification failure: {str(e)}"
        )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Razorpay webhook signature."
        )

    try:
        payload = json.loads(body_bytes.decode("utf-8"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload."
        )

    event = payload.get("event")
    event_data = payload.get("payload", {})

    # Extract payment / order details based on event structure
    session_id = None
    payment_id = None
    amount = 0.0

    if event == "payment_link.paid":
        payment_link_entity = event_data.get("payment_link", {}).get("entity", {})
        payment_entity = event_data.get("payment", {}).get("entity", {})
        session_id = payment_link_entity.get("reference_id") or payment_link_entity.get("notes", {}).get("session_id")
        payment_id = payment_entity.get("id")
        amount = payment_link_entity.get("amount_paid", 0) / 100.0

    elif event in ("order.paid", "payment.captured"):
        payment_entity = event_data.get("payment", {}).get("entity", {})
        order_entity = event_data.get("order", {}).get("entity", {})
        session_id = order_entity.get("notes", {}).get("session_id")
        payment_id = payment_entity.get("id")
        amount = payment_entity.get("amount", 0) / 100.0

    # If session is identified, record authoritative payment confirmation
    if session_id:
        cart_session = db.get(CartSession, session_id)
        if cart_session:
            # Update order if present
            order = db.exec(select(Order).where(Order.session_id == session_id)).first()
            if order:
                order.status = "paid"
                db.add(order)

            # Record authoritative AuditLog row
            audit_entry = AuditLog(
                session_id=session_id,
                event_type="payment_confirmed",
                payload={
                    "event": event,
                    "payment_id": payment_id,
                    "amount": amount,
                    "source": "razorpay_webhook",
                    "authoritative": True,
                }
            )
            db.add(audit_entry)
            db.commit()

    return {"status": "processed", "event": event, "session_id": session_id}
