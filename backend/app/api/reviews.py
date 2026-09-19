from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..enums import AuditEventType
from ..models import HumanReview, Lead
from ..schemas import ReviewIn, ReviewOut
from ..serializers import serialize_override
from ..services.audit import append_audit_event

router = APIRouter(tags=["reviews"])

_DEFAULT_REVIEWER_NAME = "S. Bhandari"
_DEFAULT_REVIEWER_ROLE = "QA Analyst"


def _submit_review(lead_id: str, body: ReviewIn, db: Session) -> ReviewOut:
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="lead not found")
    if lead.decision is None:
        raise HTTPException(status_code=400, detail="lead has not been scored yet — nothing to review")
    if body.human_decision not in ("PASS", "HOLD"):
        raise HTTPException(status_code=422, detail="humanDecision must be PASS or HOLD")
    if not body.reason or len(body.reason.strip()) <= 3:
        raise HTTPException(status_code=422, detail="reason is required and must be more than 3 characters")

    review = HumanReview(
        lead_id=lead.id,
        reviewer_name=body.reviewer_name or _DEFAULT_REVIEWER_NAME,
        reviewer_role=body.reviewer_role or _DEFAULT_REVIEWER_ROLE,
        ai_decision=lead.decision.decision,
        human_decision=body.human_decision,
        reason=body.reason.strip(),
        created_at=dt.datetime.now(dt.UTC),
    )
    db.add(review)
    db.flush()

    append_audit_event(
        db,
        lead_id=lead.id,
        event_type=AuditEventType.HUMAN_OVERRIDE,
        actor=f"{review.reviewer_role} · {review.reviewer_name}",
        resulting_state=review.human_decision,
    )

    db.commit()
    db.refresh(lead)
    return ReviewOut(ok=True, review=serialize_override(review))


@router.post("/api/reviews", response_model=ReviewOut)
def submit_review(body: ReviewIn, db: Session = Depends(get_db)):
    return _submit_review(body.lead_id, body, db)


@router.post("/api/leads/{lead_id}/override", response_model=ReviewOut)
def submit_override(lead_id: str, body: ReviewIn, db: Session = Depends(get_db)):
    """Alias of POST /api/reviews scoped by URL path, per brief §29."""
    return _submit_review(lead_id, body, db)
