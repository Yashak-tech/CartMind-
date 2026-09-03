"""
Pure-Python Deterministic Gating Engine for CartMind.
Enforces the 5 rules from TRD.md §6 with ZERO LLM involvement.

RULES TABLE:
1. Stock check: Recommended product must be in stock (stock_qty > 0) -> BLOCKED if 0.
2. Recommendation turn cap: Max 1 recommendation per turn -> BLOCKED if >= 2.
3. Margin floor: Cart revenue-weighted margin must not drop below 10% -> BLOCKED or MODIFIED.
4. Discount ceiling: Absolute maximum discount is 20% -> MODIFIED (capped to 20%).
5. Checkout confirmation: Requires confirmed_by_user=True -> BLOCKED if False.

NON-NEGOTIABLE (AGENTS.md):
Zero LLM calls are made inside this module. All validation is pure Python code.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from sqlmodel import Session, select

from backend.models import Product, CartItem, CartSession


class GateResult(BaseModel):
    """Encapsulates the deterministic decision for a single proposed action."""
    tool_name: str
    proposed_arguments: Dict[str, Any]
    decision: str  # "approved" | "blocked" | "modified"
    reason_text: str
    rule_triggered: str
    modified_arguments: Optional[Dict[str, Any]] = None
    action_data: Optional[Dict[str, Any]] = None


class GatingEngine:
    """
    Deterministic rule engine validating proposed tool calls against hard business policies.
    """

    DISCOUNT_CEILING_PCT = 20.0  # Rule 4: Absolute maximum discount cap
    MARGIN_FLOOR_PCT = 10.0      # Rule 3: Minimum allowable profit margin

    def evaluate_turn(
        self,
        session_id: str,
        tool_calls: List[Any],
        db: Session
    ) -> List[GateResult]:
        """
        Evaluates all tool calls emitted within a single conversational turn.
        Enforces turn-level limits (e.g. max 1 recommendation) across the full set.
        """
        results: List[GateResult] = []
        recommendation_count_in_turn = 0

        for tc in tool_calls:
            name = getattr(tc, "name", tc.get("name") if isinstance(tc, dict) else "")
            args = getattr(tc, "arguments", tc.get("arguments") if isinstance(tc, dict) else {})

            if name == "recommend_product":
                res = self._evaluate_recommend_product(
                    session_id=session_id,
                    arguments=args,
                    recommendation_count_in_turn=recommendation_count_in_turn,
                    db=db
                )
                recommendation_count_in_turn += 1
                results.append(res)

            elif name == "apply_discount":
                res = self._evaluate_apply_discount(
                    session_id=session_id,
                    arguments=args,
                    db=db
                )
                results.append(res)

            elif name == "initiate_checkout":
                res = self._evaluate_initiate_checkout(
                    session_id=session_id,
                    arguments=args,
                    db=db
                )
                results.append(res)

            else:
                # Fail closed: Any unknown or malformed tool call is blocked by default
                results.append(
                    GateResult(
                        tool_name=name or "unknown",
                        proposed_arguments=args,
                        decision="blocked",
                        reason_text=f"Unknown or unauthorized tool '{name}' rejected by security policy.",
                        rule_triggered="unknown_tool_rejection"
                    )
                )

        return results

    def _evaluate_recommend_product(
        self,
        session_id: str,
        arguments: Dict[str, Any],
        recommendation_count_in_turn: int,
        db: Session
    ) -> GateResult:
        """
        Enforces Rule 1 (stock check) and Rule 2 (max 1 recommendation per turn).
        """
        # Rule 2: Turn Recommendation Cap
        if recommendation_count_in_turn >= 1:
            return GateResult(
                tool_name="recommend_product",
                proposed_arguments=arguments,
                decision="blocked",
                reason_text="Maximum 1 product recommendation allowed per conversational turn.",
                rule_triggered="turn_recommendation_cap"
            )

        # Validate product_id exists
        product_id = arguments.get("product_id")
        if product_id is None:
            return GateResult(
                tool_name="recommend_product",
                proposed_arguments=arguments,
                decision="blocked",
                reason_text="Missing product_id parameter.",
                rule_triggered="malformed_parameter"
            )

        try:
            p_id_int = int(product_id)
        except (ValueError, TypeError):
            return GateResult(
                tool_name="recommend_product",
                proposed_arguments=arguments,
                decision="blocked",
                reason_text=f"Invalid product_id '{product_id}'. Must be an integer.",
                rule_triggered="malformed_parameter"
            )

        product = db.get(Product, p_id_int)
        if not product:
            return GateResult(
                tool_name="recommend_product",
                proposed_arguments=arguments,
                decision="blocked",
                reason_text=f"Product ID {p_id_int} does not exist in store catalog.",
                rule_triggered="stock_check"
            )

        # Rule 1: Stock Check (Proposal time check)
        if product.stock_qty <= 0:
            return GateResult(
                tool_name="recommend_product",
                proposed_arguments=arguments,
                decision="blocked",
                reason_text=f"Product '{product.name}' is out of stock (0 available).",
                rule_triggered="stock_check"
            )

        # Approved: product is in stock and turn limit respected
        return GateResult(
            tool_name="recommend_product",
            proposed_arguments=arguments,
            decision="approved",
            reason_text=f"Product '{product.name}' is in stock ({product.stock_qty} available).",
            rule_triggered="stock_check",
            action_data={
                "product_id": product.id,
                "name": product.name,
                "price": product.price,
                "category": product.category,
                "image_url": product.image_url,
                "reason": arguments.get("reason", "Complementary addition to your cart.")
            }
        )

    def _evaluate_apply_discount(
        self,
        session_id: str,
        arguments: Dict[str, Any],
        db: Session
    ) -> GateResult:
        """
        Enforces Unified Rule 3 & 4:
        Computes revenue-weighted average cart margin and bounds proposed discount
        against both the 10.0% margin floor and 20.0% discount ceiling.
        """
        try:
            proposed_percent = float(arguments.get("percent", 0.0))
        except (ValueError, TypeError):
            return GateResult(
                tool_name="apply_discount",
                proposed_arguments=arguments,
                decision="blocked",
                reason_text="Invalid discount percent. Must be a numeric percentage.",
                rule_triggered="malformed_parameter"
            )

        if proposed_percent <= 0.0:
            return GateResult(
                tool_name="apply_discount",
                proposed_arguments=arguments,
                decision="blocked",
                reason_text="Proposed discount must be greater than 0%.",
                rule_triggered="malformed_parameter"
            )

        # Fetch cart line items
        cart_items = db.exec(
            select(CartItem).where(CartItem.session_id == session_id)
        ).all()

        if not cart_items:
            return GateResult(
                tool_name="apply_discount",
                proposed_arguments=arguments,
                decision="blocked",
                reason_text="Cannot apply discount to an empty cart.",
                rule_triggered="margin_floor"
            )

        # 1. Compute cart subtotal and revenue-weighted average margin
        subtotal = 0.0
        weighted_margin_numerator = 0.0

        for item in cart_items:
            product = db.get(Product, item.product_id)
            if not product:
                continue
            line_rev = product.price * item.qty
            subtotal += line_rev
            weighted_margin_numerator += line_rev * product.margin_pct

        if subtotal <= 0.0:
            return GateResult(
                tool_name="apply_discount",
                proposed_arguments=arguments,
                decision="blocked",
                reason_text="Cart total is zero; discount cannot be applied.",
                rule_triggered="margin_floor"
            )

        weighted_avg_margin_pct = weighted_margin_numerator / subtotal

        # 2. Compute max allowed discount:
        # max_allowed_discount = max(0.0, min(discount_ceiling_pct, weighted_avg_margin_pct - margin_floor_pct))
        margin_allowance = weighted_avg_margin_pct - self.MARGIN_FLOOR_PCT
        max_allowed_discount = max(0.0, min(self.DISCOUNT_CEILING_PCT, margin_allowance))

        # Case A: Cart margin is already at or below floor
        if max_allowed_discount <= 0.0:
            return GateResult(
                tool_name="apply_discount",
                proposed_arguments=arguments,
                decision="blocked",
                reason_text=(
                    f"Cart weighted margin ({weighted_avg_margin_pct:.1f}%) is at or below the "
                    f"{self.MARGIN_FLOOR_PCT:.1f}% margin floor; no discount permitted."
                ),
                rule_triggered="margin_floor",
                action_data={
                    "proposed_percent": proposed_percent,
                    "applied_percent": 0.0,
                    "weighted_cart_margin": round(weighted_avg_margin_pct, 1),
                }
            )

        # Case B: Proposed discount is fully within limits -> APPROVED
        if proposed_percent <= max_allowed_discount:
            discount_amt = round(subtotal * (proposed_percent / 100.0), 2)
            new_subtotal = round(subtotal - discount_amt, 2)
            return GateResult(
                tool_name="apply_discount",
                proposed_arguments=arguments,
                decision="approved",
                reason_text=(
                    f"Proposed {proposed_percent:.1f}% discount is within margin floor "
                    f"({self.MARGIN_FLOOR_PCT:.1f}%) and ceiling ({self.DISCOUNT_CEILING_PCT:.1f}%)."
                ),
                rule_triggered="discount_approved",
                action_data={
                    "proposed_percent": proposed_percent,
                    "applied_percent": proposed_percent,
                    "discount_amount": discount_amt,
                    "original_subtotal": round(subtotal, 2),
                    "new_subtotal": new_subtotal,
                    "weighted_cart_margin": round(weighted_avg_margin_pct, 1),
                }
            )

        # Case C: Proposed discount exceeds max allowed -> MODIFIED (capped)
        applied_percent = round(max_allowed_discount, 1)
        discount_amt = round(subtotal * (applied_percent / 100.0), 2)
        new_subtotal = round(subtotal - discount_amt, 2)

        # Determine which constraint was binding
        if self.DISCOUNT_CEILING_PCT <= margin_allowance:
            binding_rule = "discount_ceiling"
            reason_str = (
                f"Discount capped to store ceiling of {self.DISCOUNT_CEILING_PCT:.1f}% "
                f"(proposed: {proposed_percent:.1f}%)."
            )
        else:
            binding_rule = "margin_floor"
            reason_str = (
                f"Discount capped to {applied_percent:.1f}% to protect the "
                f"{self.MARGIN_FLOOR_PCT:.1f}% margin floor (cart margin: {weighted_avg_margin_pct:.1f}%, proposed: {proposed_percent:.1f}%)."
            )

        return GateResult(
            tool_name="apply_discount",
            proposed_arguments=arguments,
            decision="modified",
            reason_text=reason_str,
            rule_triggered=binding_rule,
            modified_arguments={
                "percent": applied_percent,
                "reason": arguments.get("reason", "")
            },
            action_data={
                "proposed_percent": proposed_percent,
                "applied_percent": applied_percent,
                "discount_amount": discount_amt,
                "original_subtotal": round(subtotal, 2),
                "new_subtotal": new_subtotal,
                "weighted_cart_margin": round(weighted_avg_margin_pct, 1),
            }
        )

    def _evaluate_initiate_checkout(
        self,
        session_id: str,
        arguments: Dict[str, Any],
        db: Session
    ) -> GateResult:
        """
        Enforces Rule 5: Checkout requires explicit user confirmation flag.
        """
        confirmed = bool(arguments.get("confirmed_by_user", False))

        if not confirmed:
            return GateResult(
                tool_name="initiate_checkout",
                proposed_arguments=arguments,
                decision="blocked",
                reason_text="Checkout blocked: explicit customer confirmation is required.",
                rule_triggered="checkout_confirmation"
            )

        # Validate cart has active items
        cart_items = db.exec(
            select(CartItem).where(CartItem.session_id == session_id)
        ).all()

        if not cart_items:
            return GateResult(
                tool_name="initiate_checkout",
                proposed_arguments=arguments,
                decision="blocked",
                reason_text="Checkout blocked: cart is currently empty.",
                rule_triggered="checkout_confirmation"
            )

        return GateResult(
            tool_name="initiate_checkout",
            proposed_arguments=arguments,
            decision="approved",
            reason_text="Checkout approved: explicit customer confirmation verified.",
            rule_triggered="checkout_confirmation",
            action_data={
                "confirmed_by_user": True,
                "ready_for_checkout": True,
                "item_count": sum(i.qty for i in cart_items),
            }
        )


gating_engine = GatingEngine()
