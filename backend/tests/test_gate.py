"""Exhaustive unit tests for the deterministic gate — mirrors the frontend's
src/lib/gate.test.ts so both implementations are independently proven
against the same rule."""

from __future__ import annotations

from app.config import settings
from app.services.gate import GateCheckInput, describe_decision, evaluate_gate, gate_rule_copy


def check(critical=True, status="PASS", confidence=0.99) -> GateCheckInput:
    return GateCheckInput(critical=critical, status=status, confidence=confidence)


def test_auto_submits_with_no_checks_at_all():
    outcome = evaluate_gate([])
    assert outcome.decision == "AUTO_SUBMIT"
    assert outcome.checks_run == 0
    assert outcome.critical_fails == 0
    assert outcome.low_confidence == 0


def test_auto_submits_when_everything_passes_above_floor():
    outcome = evaluate_gate([check(critical=True, status="PASS", confidence=0.99), check(critical=False, status="PASS", confidence=0.86)])
    assert outcome.decision == "AUTO_SUBMIT"


def test_holds_on_a_single_critical_fail():
    outcome = evaluate_gate([check(critical=True, status="FAIL", confidence=0.98)])
    assert outcome.decision == "HOLD"
    assert outcome.critical_fails == 1


def test_counts_every_critical_fail_not_just_whether_one_exists():
    outcome = evaluate_gate([check(status="FAIL"), check(status="FAIL"), check(status="PASS")])
    assert outcome.critical_fails == 2
    assert outcome.decision == "HOLD"


def test_does_not_hold_on_a_non_critical_fail():
    outcome = evaluate_gate([check(critical=False, status="FAIL", confidence=0.95)])
    assert outcome.decision == "AUTO_SUBMIT"
    assert outcome.critical_fails == 0
    assert outcome.non_critical_fails == 1


def test_routes_to_qa_review_on_low_confidence_even_if_status_is_review_not_fail():
    outcome = evaluate_gate([check(status="REVIEW", confidence=0.61), check(status="PASS", confidence=0.99)])
    assert outcome.decision == "QA_REVIEW"
    assert outcome.low_confidence == 1


def test_low_confidence_non_critical_check_does_not_route_to_qa_review():
    """Non-critical confidence never gates the decision — it's coaching
    signal (brief §15 "never critical, never blocking"), not a reason to
    escalate a call to a human who didn't need to see it."""
    outcome = evaluate_gate([check(critical=False, status="PASS", confidence=0.5)])
    assert outcome.decision == "AUTO_SUBMIT"
    assert outcome.low_confidence == 0


def test_confidence_exactly_at_floor_is_not_low_boundary_is_exclusive():
    outcome = evaluate_gate([check(confidence=settings.confidence_floor)])
    assert outcome.low_confidence == 0
    assert outcome.decision == "AUTO_SUBMIT"


def test_confidence_just_below_floor_is_low():
    outcome = evaluate_gate([check(confidence=settings.confidence_floor - 0.01)])
    assert outcome.low_confidence == 1
    assert outcome.decision == "QA_REVIEW"


def test_hold_takes_precedence_over_qa_review():
    outcome = evaluate_gate([check(status="FAIL", confidence=0.98), check(status="PASS", confidence=0.5)])
    assert outcome.decision == "HOLD"


def test_critical_checks_counted_independent_of_status():
    outcome = evaluate_gate([check(critical=True, status="PASS"), check(critical=True, status="FAIL"), check(critical=False, status="PASS")])
    assert outcome.critical_checks == 2
    assert outcome.checks_run == 3


def test_describes_a_plain_hold():
    outcome = evaluate_gate([check(status="FAIL")])
    assert describe_decision(outcome) == "1 critical check failed. Sale held and routed to the TL queue."


def test_pluralises_multiple_critical_fails():
    outcome = evaluate_gate([check(status="FAIL"), check(status="FAIL")])
    assert "2 critical checks failed." in describe_decision(outcome)


def test_flags_a_repeat_offence():
    outcome = evaluate_gate([check(status="FAIL")])
    assert "Third failure of this check in a rolling 7 days" in describe_decision(outcome, repeat_offence=True)


def test_notes_an_overridden_hold():
    outcome = evaluate_gate([check(status="FAIL")])
    assert "Overturned by a human reviewer." in describe_decision(outcome, overridden=True)


def test_describes_qa_review_singular():
    outcome = evaluate_gate([check(confidence=0.5)])
    assert describe_decision(outcome) == "Insufficient confidence on a critical check. Never auto-passed."


def test_describes_qa_review_plural():
    outcome = evaluate_gate([check(confidence=0.5), check(confidence=0.5, critical=True)])
    assert describe_decision(outcome) == "Insufficient confidence on 2 critical checks. Never auto-passed."


def test_describes_a_clean_auto_submit():
    outcome = evaluate_gate([check(), check()])
    assert describe_decision(outcome) == "All 2 critical checks passed. No human touch required."


def test_describes_auto_submit_with_a_non_critical_coaching_note():
    outcome = evaluate_gate([check(), check(critical=False, status="FAIL", confidence=0.92)])
    assert describe_decision(outcome) == "All 1 critical checks passed. 1 non-critical behaviour note raised for coaching."


def test_gate_rule_copy_has_text_for_every_decision():
    assert "submit without human touch" in gate_rule_copy("AUTO_SUBMIT")
    assert "hold, route to the TL queue" in gate_rule_copy("HOLD")
    assert "route to QA, never auto-pass" in gate_rule_copy("QA_REVIEW")
