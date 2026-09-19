"""
Append-only audit ledger. Every write here is an INSERT; nothing in this
codebase ever UPDATEs or DELETEs an AuditEvent row (CLAUDE.md #7 / brief
§23: "Never silently mutate historical decisions").
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import AuditEvent


def _next_seq(db: Session, lead_id: str) -> int:
    current_max = db.execute(select(func.max(AuditEvent.seq)).where(AuditEvent.lead_id == lead_id)).scalar_one()
    return (current_max or 0) + 1


def append_audit_event(
    db: Session,
    *,
    lead_id: str,
    event_type: str,
    actor: str,
    resulting_state: str,
    rule_version: str | None = None,
    metadata: dict | None = None,
    at: dt.datetime | None = None,
) -> AuditEvent:
    event = AuditEvent(
        lead_id=lead_id,
        seq=_next_seq(db, lead_id),
        at=at or dt.datetime.now(dt.UTC),
        event_type=event_type,
        actor=actor,
        rule_version=rule_version,
        resulting_state=resulting_state,
        event_metadata=metadata or {},
    )
    db.add(event)
    db.flush()
    return event
