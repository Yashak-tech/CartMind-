"""
Catalog Endpoints for CartMind (TRD.md §5).
Provides public product listings and details.
CRITICAL: Exposes ProductRead which explicitly excludes margin_pct.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from backend.database import get_session
from backend.models import Product, ProductRead

router = APIRouter(prefix="/products", tags=["Catalog"])


@router.get("", response_model=List[ProductRead])
def list_products(
    category: Optional[str] = Query(None, description="Filter products by category"),
    session: Session = Depends(get_session)
) -> List[ProductRead]:
    """
    Lists catalog products with optional category filtering.
    CRITICAL: Public response uses ProductRead, strictly omitting confidential margin_pct.
    """
    statement = select(Product)
    if category:
        statement = statement.where(Product.category == category)
    products = session.exec(statement).all()
    return products


@router.get("/{product_id}", response_model=ProductRead)
def get_product(
    product_id: int,
    session: Session = Depends(get_session)
):
    """
    Retrieves details for a specific product by ID.
    CRITICAL: Excludes confidential margin_pct.
    """
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found."
        )
    return product


@router.post("/{product_id}/deplete-stock")
def deplete_stock(
    product_id: int,
    session: Session = Depends(get_session)
):
    """
    Simulates mid-conversation inventory exhaustion for Phase 6 Failure Injection.
    Zeroes out the product stock immediately.
    """
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found."
        )
    prev_stock = product.stock_qty
    product.stock_qty = 0
    session.add(product)
    session.commit()
    session.refresh(product)
    return {
        "message": f"Simulated stock race condition: '{product.name}' stock depleted from {prev_stock} to 0.",
        "product_id": product.id,
        "previous_stock": prev_stock,
        "current_stock": 0,
    }


@router.post("/{product_id}/restore-stock")
def restore_stock(
    product_id: int,
    qty: int = Query(default=10),
    session: Session = Depends(get_session)
):
    """Restores stock quantity for a product after running failure injection test."""
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found."
        )
    product.stock_qty = qty
    session.add(product)
    session.commit()
    session.refresh(product)
    return {
        "message": f"Restored stock for '{product.name}' to {qty}.",
        "product_id": product.id,
        "current_stock": product.stock_qty,
    }
