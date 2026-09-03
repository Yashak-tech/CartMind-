"""
Action Executor and State Boundary for CartMind.
THE ONLY COMPONENT AUTHORIZED TO MUTATE STATE AFTER GATE APPROVAL.

Per AGENTS.md:
Zero code paths allow an LLM response to flow directly into a database write
or Razorpay call without passing through the Gating Engine and this Executor.
"""

from typing import List, Dict, Any
from sqlmodel import Session

from backend.models import AgentRecommendation, GateDecision, AuditLog
from backend.gate.engine import GateResult


class ActionExecutor:
    """
    Executes gate-validated decisions and records audit trails.
    """

    def record_and_apply(
        self,
        session_id: str,
        gate_results: List[GateResult],
        llm_reasoning: str,
        db: Session
    ) -> List[Dict[str, Any]]:
        """
        Persists each proposed action to agent_recommendations, its gate verdict
        to gate_decisions, logs an AuditLog row, and returns enriched decision dicts.
        """
        executed_decisions: List[Dict[str, Any]] = []

        for result in gate_results:
            # 1. Record proposal
            recommendation = AgentRecommendation(
                session_id=session_id,
                proposed_action={
                    "tool": result.tool_name,
                    "arguments": result.proposed_arguments,
                },
                reasoning_text=result.proposed_arguments.get("reason") or llm_reasoning or "Agent proposed action",
            )
            db.add(recommendation)
            db.flush()  # Populates recommendation.id

            # 2. Record gate decision
            decision = GateDecision(
                recommendation_id=recommendation.id,
                decision=result.decision,
                reason_text=result.reason_text,
                rule_triggered=result.rule_triggered,
            )
            db.add(decision)
            db.flush()  # Populates decision.id

            # 3. Record AuditLog entry
            audit_entry = AuditLog(
                session_id=session_id,
                event_type=f"gate_decision_{result.decision}",
                payload={
                    "recommendation_id": recommendation.id,
                    "decision_id": decision.id,
                    "tool": result.tool_name,
                    "decision": result.decision,
                    "rule_triggered": result.rule_triggered,
                    "reason_text": result.reason_text,
                    "action_data": result.action_data or {},
                }
            )
            db.add(audit_entry)

            # Build enriched decision payload for frontend rendering
            decision_summary = {
                "recommendation_id": recommendation.id,
                "decision_id": decision.id,
                "tool_name": result.tool_name,
                "decision": result.decision,
                "rule_triggered": result.rule_triggered,
                "reason_text": result.reason_text,
                "action_data": result.action_data or {},
                "decided_at": decision.decided_at.isoformat(),
            }
            executed_decisions.append(decision_summary)

        db.commit()
        return executed_decisions


action_executor = ActionExecutor()
