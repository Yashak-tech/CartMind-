"""
Audit Trail Endpoints for CartMind (TRD.md §5 & §8).
Provides chronological feeds for the Decision Ledger and Admin panel.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from backend.database import get_session
from backend.services.audit import audit_service

router = APIRouter(prefix="/audit", tags=["Audit & Admin"])


@router.get("", response_model=List[Dict[str, Any]])
def list_sessions(db: Session = Depends(get_session)) -> List[Dict[str, Any]]:
    """
    Returns all cart sessions with their audit metrics.
    Used by the Admin Audit Panel session filter dropdown.
    """
    return audit_service.list_audit_sessions(db)


@router.get("/{session_id}", response_model=Dict[str, Any])
def get_session_audit(session_id: str, db: Session = Depends(get_session)) -> Dict[str, Any]:
    """
    Returns the full chronological audit feed for a session.
    Every recommendation is paired 1:1 with its deterministic gate decision.
    Powers both the shopper-facing Decision Ledger and the /audit Admin view.
    Accepts 'latest' or literal '{SESSION_ID}' to resolve to the most recent session.
    """
    # Friendly resolution for browser users copying placeholder or asking for latest
    if session_id.lower() in ("latest", "{session_id}", "%7bsession_id%7d"):
        sessions = audit_service.list_audit_sessions(db)
        if sessions:
            session_id = sessions[0]["session_id"]
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No sessions found in database yet. Create one at POST /session or GET /session."
            )

    result = audit_service.get_session_audit_trail(session_id, db)
    if "error" in result:
        sessions = audit_service.list_audit_sessions(db)
        latest_hint = f" Available sessions: {[s['session_id'] for s in sessions[:3]]} or visit /audit/latest" if sessions else ""
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{result['error']}{latest_hint}"
        )
    return result
