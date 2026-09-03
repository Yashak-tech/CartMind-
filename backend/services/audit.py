"""
Audit Service for CartMind (TRD.md §8).
Provides chronological, explainable audit feeds for the Decision Ledger
and Admin view with 1:1 proposal-to-gate decision pairing.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlmodel import Session, select

from backend.models import (
    CartSession,
    AuditLog,
    AgentRecommendation,
    GateDecision,
    Order,
    CartItem,
    Product,
)


def _format_time_str(dt: Optional[datetime]) -> str:
    """Formats datetime to HH:MM:SS for the monospace Decision Ledger."""
    if not dt:
        return "00:00:00"
    return dt.strftime("%H:%M:%S")


class AuditService:
    """Service generating formatted audit feeds and session summaries."""

    def get_session_audit_trail(self, session_id: str, db: Session) -> Dict[str, Any]:
        """
        Retrieves the complete, chronological audit trail for a session.
        Combines audit_log, paired agent_recommendations, and gate_decisions.
        """
        cart_session = db.get(CartSession, session_id)
        if not cart_session:
            return {"error": f"Session '{session_id}' not found.", "timeline": [], "summary": {}}

        # 1. Fetch paired recommendations and decisions
        recs = db.exec(
            select(AgentRecommendation)
            .where(AgentRecommendation.session_id == session_id)
            .order_by(AgentRecommendation.created_at.asc())
        ).all()

        rec_decision_map: Dict[int, GateDecision] = {}
        for r in recs:
            decision = db.exec(
                select(GateDecision).where(GateDecision.recommendation_id == r.id)
            ).first()
            if decision:
                rec_decision_map[r.id] = decision

        # 2. Fetch all raw AuditLog entries
        audit_entries = db.exec(
            select(AuditLog)
            .where(AuditLog.session_id == session_id)
            .order_by(AuditLog.created_at.asc())
        ).all()

        timeline: List[Dict[str, Any]] = []
        approved_cnt = 0
        blocked_cnt = 0
        modified_cnt = 0

        # Build timeline entries from paired recommendations
        for r in recs:
            dec = rec_decision_map.get(r.id)
            decision_verdict = dec.decision if dec else "pending"
            rule_name = dec.rule_triggered if dec else "none"
            reason = dec.reason_text if dec else r.reasoning_text
            decided_at = dec.decided_at if dec else r.created_at

            tool_name = r.proposed_action.get("tool", "action")
            args = r.proposed_action.get("arguments", {})

            # Format action type and summary string
            if tool_name == "recommend_product":
                action_type = "RECOMMEND"
                prod_id = args.get("product_id")
                prod = db.get(Product, int(prod_id)) if prod_id else None
                summary_text = prod.name if prod else f"Product #{prod_id}"
            elif tool_name == "apply_discount":
                action_type = "DISCOUNT"
                prop_pct = args.get("percent", 0.0)
                if decision_verdict == "modified" and dec and "capped to" in dec.reason_text:
                    # e.g. "DISCOUNT 35%->20%"
                    summary_text = f"DISCOUNT {prop_pct:.0f}%->20%"
                else:
                    summary_text = f"DISCOUNT {prop_pct:.0f}%"
            elif tool_name == "initiate_checkout":
                action_type = "CHECKOUT"
                summary_text = "CHECKOUT (User Confirmed)" if args.get("confirmed_by_user") else "CHECKOUT (Unconfirmed)"
            else:
                action_type = tool_name.upper()
                summary_text = tool_name

            if decision_verdict == "approved":
                approved_cnt += 1
            elif decision_verdict == "blocked":
                blocked_cnt += 1
            elif decision_verdict == "modified":
                modified_cnt += 1

            timeline.append({
                "id": f"rec_{r.id}",
                "timestamp": decided_at.isoformat(),
                "time_str": _format_time_str(decided_at),
                "event_type": "gate_decision",
                "action": action_type,
                "decision": decision_verdict,
                "summary": summary_text,
                "reason_text": reason,
                "rule_triggered": rule_name,
                "payload": {
                    "recommendation_id": r.id,
                    "decision_id": dec.id if dec else None,
                    "proposed_action": r.proposed_action,
                }
            })

        # Add any system events (checkout_initiated, payment_confirmed) from audit_log
        for a in audit_entries:
            if a.event_type.startswith("gate_decision_"):
                # Already captured above via paired recommendations
                continue

            event_time = a.created_at
            if a.event_type == "checkout_initiated":
                amt = a.payload.get("amount", 0.0)
                timeline.append({
                    "id": f"audit_{a.id}",
                    "timestamp": event_time.isoformat(),
                    "time_str": _format_time_str(event_time),
                    "event_type": a.event_type,
                    "action": "CHECKOUT",
                    "decision": "approved",
                    "summary": f"Order Initiated (₹{amt:,.2f})",
                    "reason_text": "Customer proceeded to checkout; payment link created.",
                    "rule_triggered": "checkout_execution",
                    "payload": a.payload,
                })
            elif a.event_type == "payment_confirmed":
                pay_id = a.payload.get("payment_id", "verified")
                timeline.append({
                    "id": f"audit_{a.id}",
                    "timestamp": event_time.isoformat(),
                    "time_str": _format_time_str(event_time),
                    "event_type": a.event_type,
                    "action": "PAYMENT",
                    "decision": "approved",
                    "summary": f"Payment Verified ({pay_id})",
                    "reason_text": "Authoritative payment signature validated.",
                    "rule_triggered": "razorpay_verification",
                    "payload": a.payload,
                })
            else:
                timeline.append({
                    "id": f"audit_{a.id}",
                    "timestamp": event_time.isoformat(),
                    "time_str": _format_time_str(event_time),
                    "event_type": a.event_type,
                    "action": "SYSTEM",
                    "decision": "info",
                    "summary": a.event_type,
                    "reason_text": str(a.payload),
                    "rule_triggered": "audit_log",
                    "payload": a.payload,
                })

        # Sort combined timeline chronologically
        timeline.sort(key=lambda x: x["timestamp"])

        summary = {
            "session_id": session_id,
            "status": cart_session.status,
            "created_at": cart_session.created_at.isoformat(),
            "total_events": len(timeline),
            "total_proposals": len(recs),
            "approved_count": approved_cnt,
            "blocked_count": blocked_cnt,
            "modified_count": modified_cnt,
        }

        return {
            "session_id": session_id,
            "status": cart_session.status,
            "summary": summary,
            "timeline": timeline,
        }

    def list_audit_sessions(self, db: Session) -> List[Dict[str, Any]]:
        """
        Lists all sessions with their audit metrics for the Admin view dropdown filter.
        """
        sessions = db.exec(
            select(CartSession).order_by(CartSession.created_at.desc())
        ).all()

        results = []
        for s in sessions:
            # Count gate decisions for this session
            recs = db.exec(select(AgentRecommendation).where(AgentRecommendation.session_id == s.id)).all()
            approved = 0
            blocked = 0
            modified = 0

            for r in recs:
                dec = db.exec(select(GateDecision).where(GateDecision.recommendation_id == r.id)).first()
                if dec:
                    if dec.decision == "approved":
                        approved += 1
                    elif dec.decision == "blocked":
                        blocked += 1
                    elif dec.decision == "modified":
                        modified += 1

            orders_cnt = len(db.exec(select(Order).where(Order.session_id == s.id)).all())

            results.append({
                "session_id": s.id,
                "status": s.status,
                "created_at": s.created_at.isoformat(),
                "time_str": _format_time_str(s.created_at),
                "total_proposals": len(recs),
                "approved_count": approved,
                "blocked_count": blocked,
                "modified_count": modified,
                "has_order": orders_cnt > 0,
            })

        return results


audit_service = AuditService()
