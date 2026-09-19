"""
Historical rule resolution. A call is always scored against the checklist
version that was LIVE ON THE CALL DATE, never today's version — CLAUDE.md
non-negotiable #8, brief §07 "Scored against the rules that were live".
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Checklist, RuleVersion


def resolve_rule_version(db: Session, retailer_id: int, call_date: dt.date) -> RuleVersion | None:
    """The rule version for `retailer_id` with the latest `effective_from`
    that is still <= call_date. Returns None if no version was live yet on
    that date (e.g. a call predating the checklist's introduction)."""
    stmt = (
        select(RuleVersion)
        .join(Checklist, RuleVersion.checklist_id == Checklist.id)
        .where(Checklist.retailer_id == retailer_id, RuleVersion.effective_from <= call_date)
        .order_by(RuleVersion.effective_from.desc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()
