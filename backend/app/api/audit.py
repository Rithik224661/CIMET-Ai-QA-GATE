from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import AuditEvent, Lead
from ..schemas import AuditEventOut, AuditOut

router = APIRouter(tags=["audit"])


@router.get("/api/audit/{lead_id}", response_model=AuditOut)
def get_audit_ledger(lead_id: str, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="lead not found")

    events = db.execute(select(AuditEvent).where(AuditEvent.lead_id == lead_id).order_by(AuditEvent.seq)).scalars().all()
    return AuditOut(
        events=[
            AuditEventOut(
                time=e.at.strftime("%H:%M:%S"),
                event=_label(e.event_type),
                actor=e.actor,
                version=e.rule_version,
                resulting_state=e.resulting_state,
            )
            for e in events
        ]
    )


def _label(event_type: str) -> str:
    return event_type.replace("_", " ").title().replace("Qa ", "QA ")
