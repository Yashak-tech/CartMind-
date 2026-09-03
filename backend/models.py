"""
SQLModel Data Models for CartMind.
Implements the exact schema specified in TRD.md §4:
- Product
- CartSession
- CartItem
- AgentRecommendation
- GateDecision
- Order
- AuditLog

Also defines customer-facing Pydantic schemas (ProductRead, CartResponse)
that strictly shield internal merchant metadata (such as margin_pct).
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, JSON
from pydantic import BaseModel


def utc_now() -> datetime:
    """Returns current UTC timestamp."""
    return datetime.now(timezone.utc)


# ==============================================================================
# 1. Product Model (TRD.md §4: products)
# ==============================================================================
class ProductBase(SQLModel):
    name: str = Field(index=True)
    price: float = Field(ge=0, description="Price in INR")
    stock_qty: int = Field(default=0, ge=0, description="Available inventory quantity")
    category: str = Field(index=True)
    description: str
    image_url: Optional[str] = Field(default=None)


class Product(ProductBase, table=True):
    """
    Internal database model for products.
    Includes margin_pct which is confidential merchant data.
    """
    __tablename__ = "products"

    id: Optional[int] = Field(default=None, primary_key=True)
    margin_pct: float = Field(ge=0, le=100, description="Confidential merchant margin percentage (0-100)")

    # Relationships
    cart_items: List["CartItem"] = Relationship(back_populates="product")


class ProductRead(ProductBase):
    """
    Customer-facing product representation.
    CRITICAL: Strictly excludes margin_pct so internal margins never leak in public APIs.
    """
    id: int


# ==============================================================================
# 2. Cart Session Model (TRD.md §4: cart_sessions)
# ==============================================================================
class CartSession(SQLModel, table=True):
    """
    Represents an active or historical shopping cart session.
    Status can be 'active', 'checked_out', or 'abandoned'.
    """
    __tablename__ = "cart_sessions"

    id: str = Field(primary_key=True, description="UUID session identifier")
    created_at: datetime = Field(default_factory=utc_now)
    status: str = Field(default="active", index=True, description="active | checked_out | abandoned")

    # Relationships
    items: List["CartItem"] = Relationship(back_populates="session", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    orders: List["Order"] = Relationship(back_populates="session")
    recommendations: List["AgentRecommendation"] = Relationship(back_populates="session")
    audit_logs: List["AuditLog"] = Relationship(back_populates="session")


# ==============================================================================
# 3. Cart Item Model (TRD.md §4: cart_items)
# ==============================================================================
class CartItem(SQLModel, table=True):
    """Individual line item in a shopping cart."""
    __tablename__ = "cart_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="cart_sessions.id", index=True)
    product_id: int = Field(foreign_key="products.id", index=True)
    qty: int = Field(default=1, ge=1)
    added_at: datetime = Field(default_factory=utc_now)

    # Relationships
    session: Optional[CartSession] = Relationship(back_populates="items")
    product: Optional[Product] = Relationship(back_populates="cart_items")


# ==============================================================================
# 4. Agent Recommendations (TRD.md §4: agent_recommendations)
# ==============================================================================
class AgentRecommendation(SQLModel, table=True):
    """
    Records an action proposed by the LLM reasoning layer.
    The LLM proposes; it never executes directly.
    """
    __tablename__ = "agent_recommendations"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="cart_sessions.id", index=True)
    # Strictly typed as a JSON dict (e.g. {"tool": "recommend_product", "product_id": 10, "reason": "..."})
    proposed_action: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    reasoning_text: str = Field(description="LLM's stated rationale for proposing this action")
    created_at: datetime = Field(default_factory=utc_now)

    # Relationships
    session: Optional[CartSession] = Relationship(back_populates="recommendations")
    decisions: List["GateDecision"] = Relationship(back_populates="recommendation")


# ==============================================================================
# 5. Gate Decisions (TRD.md §4: gate_decisions)
# ==============================================================================
class GateDecision(SQLModel, table=True):
    """
    Records the outcome of the pure-Python deterministic Gating Engine.
    Decision: 'approved', 'blocked', or 'modified'.
    """
    __tablename__ = "gate_decisions"

    id: Optional[int] = Field(default=None, primary_key=True)
    recommendation_id: int = Field(foreign_key="agent_recommendations.id", index=True)
    decision: str = Field(index=True, description="approved | blocked | modified")
    reason_text: str = Field(description="Deterministic explanation of why the gate approved, blocked, or modified")
    rule_triggered: str = Field(description="The specific policy rule that evaluated this action")
    decided_at: datetime = Field(default_factory=utc_now)

    # Relationships
    recommendation: Optional[AgentRecommendation] = Relationship(back_populates="decisions")


# ==============================================================================
# 6. Orders (TRD.md §4: orders)
# ==============================================================================
class Order(SQLModel, table=True):
    """Represents a checkout order created via Razorpay."""
    __tablename__ = "orders"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="cart_sessions.id", index=True)
    razorpay_order_id: str = Field(index=True)
    amount: float = Field(ge=0, description="Order amount in INR")
    status: str = Field(default="created", index=True, description="created | paid | failed")
    created_at: datetime = Field(default_factory=utc_now)

    # Relationships
    session: Optional[CartSession] = Relationship(back_populates="orders")


# ==============================================================================
# 7. Audit Log (TRD.md §4: audit_log)
# ==============================================================================
class AuditLog(SQLModel, table=True):
    """
    Complete persistent audit trail of every meaningful session event
    (checkout_initiated, recommendation_evaluated, gate_decision, payment_confirmed, etc.).
    """
    __tablename__ = "audit_log"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="cart_sessions.id", index=True)
    event_type: str = Field(index=True, description="Type of audit event")
    # Strictly typed as a JSON dict
    payload: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utc_now)

    # Relationships
    session: Optional[CartSession] = Relationship(back_populates="audit_logs")


# ==============================================================================
# API Request / Response DTOs
# ==============================================================================
class AddCartItemRequest(BaseModel):
    product_id: int
    qty: int = Field(default=1, ge=1)


class CartItemRead(BaseModel):
    id: int
    product_id: int
    name: str
    price: float
    qty: int
    line_total: float
    category: str
    image_url: Optional[str] = None


class CartResponse(BaseModel):
    session_id: str
    status: str
    items: List[CartItemRead]
    subtotal: float
    total_items: int


class CheckoutResponse(BaseModel):
    session_id: str
    order_id: int
    razorpay_order_id: str
    amount: float
    payment_link_id: Optional[str] = None
    payment_link_url: Optional[str] = None
    status: str
