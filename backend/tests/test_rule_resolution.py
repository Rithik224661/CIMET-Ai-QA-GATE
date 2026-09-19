"""Historical rule resolution: a call must always resolve to the checklist
version effective on ITS call date, never today's (CLAUDE.md #8)."""

from __future__ import annotations

import datetime as dt

from app.models import Checklist, Retailer, RuleVersion
from app.services.rule_resolution import resolve_rule_version


def _make_retailer_with_versions(db_session, name: str, versions: list[tuple[str, dt.date]]) -> Retailer:
    retailer = Retailer(name=name)
    db_session.add(retailer)
    db_session.flush()
    checklist = Checklist(retailer_id=retailer.id, name="Energy QA checklist", product="Energy")
    db_session.add(checklist)
    db_session.flush()
    for version, effective_from in versions:
        db_session.add(RuleVersion(checklist_id=checklist.id, version=version, effective_from=effective_from, live=False))
    db_session.flush()
    return retailer


def test_resolves_the_latest_version_effective_on_or_before_the_call_date(db_session):
    retailer = _make_retailer_with_versions(
        db_session,
        "Retailer X",
        [("v1.0", dt.date(2026, 1, 1)), ("v1.1", dt.date(2026, 6, 1)), ("v1.2", dt.date(2026, 9, 1))],
    )

    resolved = resolve_rule_version(db_session, retailer.id, dt.date(2026, 7, 15))
    assert resolved is not None
    assert resolved.version == "v1.1", "a July call must resolve to v1.1, not the September version that didn't exist yet"


def test_a_call_after_the_newest_version_gets_the_newest_version(db_session):
    retailer = _make_retailer_with_versions(
        db_session, "Retailer Y", [("v1.0", dt.date(2026, 1, 1)), ("v2.0", dt.date(2026, 6, 1))]
    )
    resolved = resolve_rule_version(db_session, retailer.id, dt.date(2027, 1, 1))
    assert resolved.version == "v2.0"


def test_a_call_exactly_on_the_effective_date_gets_that_version(db_session):
    retailer = _make_retailer_with_versions(
        db_session, "Retailer Z", [("v1.0", dt.date(2026, 1, 1)), ("v2.0", dt.date(2026, 6, 1))]
    )
    resolved = resolve_rule_version(db_session, retailer.id, dt.date(2026, 6, 1))
    assert resolved.version == "v2.0"


def test_a_call_before_any_version_existed_resolves_to_nothing(db_session):
    retailer = _make_retailer_with_versions(db_session, "Retailer W", [("v1.0", dt.date(2026, 6, 1))])
    resolved = resolve_rule_version(db_session, retailer.id, dt.date(2026, 1, 1))
    assert resolved is None


def test_never_leaks_across_retailers(db_session):
    r1 = _make_retailer_with_versions(db_session, "Retailer A1", [("v1.0", dt.date(2026, 1, 1))])
    r2 = _make_retailer_with_versions(db_session, "Retailer A2", [("v9.0", dt.date(2026, 1, 1))])
    resolved = resolve_rule_version(db_session, r1.id, dt.date(2026, 6, 1))
    assert resolved.version == "v1.0"
    assert resolved.checklist_id != r2  # sanity: didn't accidentally cross-match
