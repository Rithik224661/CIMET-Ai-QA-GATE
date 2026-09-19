"""
Repeat-offence detection: the same critical check failing 3+ times for the
same agent within a rolling 7-day window flags the TL (brief §06). The
threshold/window are configuration (settings), never hard-coded — a policy
change should not require touching this module.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..enums import ResultStatus
from ..models import Check, CheckResult, Lead


def count_recent_critical_failures(db: Session, *, agent: str, check_code: str, as_of: dt.datetime) -> int:
    window_start = as_of - dt.timedelta(days=settings.repeat_offence_window_days)
    stmt = (
        select(func.count(CheckResult.id))
        .join(Lead, CheckResult.lead_id == Lead.id)
        .join(Check, CheckResult.check_id == Check.id)
        .where(
            Lead.agent == agent,
            Check.code == check_code,
            Check.critical.is_(True),
            CheckResult.status == ResultStatus.FAIL,
            Lead.call_datetime >= window_start,
            Lead.call_datetime <= as_of,
        )
    )
    return db.execute(stmt).scalar_one()


def is_repeat_offence(failure_count: int) -> bool:
    return failure_count >= settings.repeat_offence_threshold
