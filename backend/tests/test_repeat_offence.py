from __future__ import annotations

import datetime as dt

from app.config import settings
from app.services.repeat_offence import count_recent_critical_failures, is_repeat_offence


def test_threshold_is_configurable_not_hard_coded():
    assert is_repeat_offence(settings.repeat_offence_threshold) is True
    assert is_repeat_offence(settings.repeat_offence_threshold - 1) is False


def test_repeat_offence_flag_true_at_exactly_the_configured_threshold(seeded_db):
    # Lead 3613778 (Lead G) fails "Recording disclaimer" as its 3rd
    # occurrence within the rolling window (2 seeded history calls + this
    # one) — the pipeline must have flagged it genuinely, not by a
    # hand-set boolean.
    from app.models import Lead

    lead = seeded_db.get(Lead, "3613778")
    assert lead.repeat_offence is True


def test_a_single_isolated_failure_is_not_a_repeat_offence(seeded_db):
    from app.models import Lead

    # Lead 3613790 (Lead B) fails Rates and Email but neither check has
    # any prior history for Agent A within the window.
    lead = seeded_db.get(Lead, "3613790")
    assert lead.repeat_offence is False


def test_count_only_looks_within_the_rolling_window(seeded_db):
    from app.models import Lead

    lead = seeded_db.get(Lead, "3613778")
    as_of = lead.call_datetime
    count = count_recent_critical_failures(seeded_db, agent=lead.agent, check_code="RET1-VB-001", as_of=as_of)
    assert count == 3

    before_any_history = as_of - dt.timedelta(days=settings.repeat_offence_window_days + 30)
    count_before = count_recent_critical_failures(seeded_db, agent=lead.agent, check_code="RET1-VB-001", as_of=before_any_history)
    assert count_before == 0, "a point in time before any of the failures happened must count zero of them"
