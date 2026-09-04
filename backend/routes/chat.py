"""
Chat and Conversational Commerce Route for CartMind (TRD.md §5).
Coordinates the Reasoner (LLM proposes), Gating Engine (validates),
and Action Executor (mutates state and logs audit trail).
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from backend.database import get_session
from backend.models import CartSession, CartItem, Product, CartResponse
from backend.routes.cart import _calculate_cart_response
from backend.agent.reasoner import reasoner
from backend.gate.engine import gating_engine
from backend.gate.executor import action_executor

router = APIRouter(prefix="/session", tags=["Chat & Agent"])


class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Shopper's conversational message")


class ChatResponse(BaseModel):
    reply: str
    decisions: List[Dict[str, Any]] = []
    cart: CartResponse


@router.post("/{session_id}/message", response_model=ChatResponse)
def send_message(
    session_id: str,
    payload: ChatMessageRequest,
    db: Session = Depends(get_session)
) -> ChatResponse:
    """
    Handles a customer chat turn:
    1. Gathers cart state and catalog items (excluding confidential margin_pct).
    2. Calls the LLM Reasoner to interpret intent and propose tool calls.
    3. Gating Engine evaluates proposals with zero LLM calls.
    4. Action Executor persists proposals, decisions, and audit records.
    5. Returns agent reply, enriched decisions list, and updated cart state.
    """
    cart_session = db.get(CartSession, session_id)
    if not cart_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cart session '{session_id}' not found."
        )

    if cart_session.status != "active":
        # Gracefully reactivate session so the shopper can keep chatting or start another order
        cart_session.status = "active"
        db.add(cart_session)
        db.commit()
        db.refresh(cart_session)

    # 1. Gather cart context (clean public data only)
    cart_items = db.exec(select(CartItem).where(CartItem.session_id == session_id)).all()
    cart_context = []
    for item in cart_items:
        p = db.get(Product, item.product_id)
        if p:
            cart_context.append({
                "product_id": p.id,
                "name": p.name,
                "price": p.price,
                "qty": item.qty,
                "line_total": round(p.price * item.qty, 2)
            })

    # Gather catalog context (clean public data only - NO margin_pct)
    catalog_products = [
        {
            "id": p.id,
            "name": p.name,
            "price": p.price,
            "stock_qty": p.stock_qty,
            "category": p.category,
            "description": p.description,
        }
        for p in db.exec(select(Product)).all()
    ]

    # 2. LLM proposes actions (Zero execution authority)
    turn_proposal = reasoner.propose_turn(
        user_message=payload.message,
        cart_items=cart_context,
        catalog_products=catalog_products,
    )

    # 3. Deterministic Gating Engine evaluates proposals (Pure Python, zero LLM calls)
    gate_results = gating_engine.evaluate_turn(
        session_id=session_id,
        tool_calls=turn_proposal.tool_calls,
        db=db,
    )

    # 4. Action Executor executes approved/modified actions and persists audit records
    decisions = action_executor.record_and_apply(
        session_id=session_id,
        gate_results=gate_results,
        llm_reasoning=turn_proposal.content,
        db=db,
    )

    # 5. Format conversational reply
    reply_text = turn_proposal.content
    for d in decisions:
        if d["decision"] == "modified":
            applied = d["action_data"].get("applied_percent")
            reply_text += f"\n\n(Note: Store policy adjusted the discount to {applied:.1f}% to protect margin thresholds.)"
        elif d["decision"] == "blocked":
            reply_text += f"\n\n(Action blocked by store policy: {d['reason_text']})"

    current_cart = _calculate_cart_response(cart_session, db)

    return ChatResponse(
        reply=reply_text.strip(),
        decisions=decisions,
        cart=current_cart,
    )
