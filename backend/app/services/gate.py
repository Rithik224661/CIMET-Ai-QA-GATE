"""
The deterministic gate. Pure functions only — no database session, no I/O,
no model call. This is the one place the sale/hold/review decision is made,
and it is never delegated to an LLM (CLAUDE.md #6, brief §05 "Gate logic").
This backend module is the SOLE AUTHORITATIVE gate — the frontend never
independently decides a final business outcome; it only displays the
`GateOutcome` this function returns (see docs/DECISIONS.md, "single source
of truth for the gate").

Mirrors frontend src/lib/gate.ts's shape and precedence (kept as a pure,
unit-tested reference implementation — not on the live decision path, see
src/lib/data/leads.ts's gateForLead()).

Low confidence is scoped to CRITICAL checks only: a non-critical
behavioural heuristic (rapport, interruptions, objection handling) being
honestly uncertain is coaching signal, never a reason to escalate a call a
human didn't need to see — brief §15 "never critical, never blocking" and
§20's gate pseudocode ("any APPLICABLE CRITICAL check = LOW_CONFIDENCE").
A critical check that could not be evaluated at all is represented as
REVIEW status + confidence below the floor (see evaluators/base.py's
`not_evaluable_outcome`), which routes here identically to a low-confidence
PASS/FAIL — "not evaluable" and "low confidence" collapse into the same
mechanism deliberately, per brief §10's "required checks incomplete/not
evaluable -> QA_REVIEW".
"""

from __future__ import annotations

from dataclasses import dataclass

from ..config import settings
from ..enums import Decision, ResultStatus


@dataclass(frozen=True)
class GateCheckInput:
    critical: bool
    status: str  # ResultStatus
    confidence: float


@dataclass(frozen=True)
class GateOutcome:
    decision: str
    critical_fails: int
    low_confidence: int
    checks_run: int
    critical_checks: int
    non_critical_fails: int


def evaluate_gate(checks: list[GateCheckInput]) -> GateOutcome:
    """criticalFails > 0 -> HOLD; any CRITICAL check's confidence < floor ->
    QA_REVIEW; else AUTO_SUBMIT. Non-critical confidence never gates the
    decision — see module docstring."""
    critical_fails = sum(1 for c in checks if c.critical and c.status == ResultStatus.FAIL)
    low_confidence = sum(1 for c in checks if c.critical and c.confidence < settings.confidence_floor)
    non_critical_fails = sum(1 for c in checks if not c.critical and c.status == ResultStatus.FAIL)
    critical_checks = sum(1 for c in checks if c.critical)

    if critical_fails > 0:
        decision = Decision.HOLD
    elif low_confidence > 0:
        decision = Decision.QA_REVIEW
    else:
        decision = Decision.AUTO_SUBMIT

    return GateOutcome(
        decision=decision,
        critical_fails=critical_fails,
        low_confidence=low_confidence,
        checks_run=len(checks),
        critical_checks=critical_checks,
        non_critical_fails=non_critical_fails,
    )


_GATE_RULES = {
    Decision.AUTO_SUBMIT: "Gate rule: all criticals pass → submit without human touch.",
    Decision.QA_REVIEW: "Gate rule: low confidence on any critical check → route to QA, never auto-pass.",
    Decision.HOLD: "Gate rule: any critical fail → hold, route to the TL queue.",
}


def gate_rule_copy(decision: str) -> str:
    return _GATE_RULES[Decision(decision)]


def describe_decision(outcome: GateOutcome, *, repeat_offence: bool = False, overridden: bool = False) -> str:
    """Human-readable sentence generated FROM the outcome — never
    hand-authored per lead, so copy can't drift from what the gate actually
    computed. Mirrors frontend src/lib/gate.ts describeDecision()."""
    if outcome.decision == Decision.HOLD:
        base = f"{outcome.critical_fails} critical check{'s' if outcome.critical_fails != 1 else ''} failed."
        if overridden:
            return f"{base} Overturned by a human reviewer."
        if repeat_offence:
            return f"{base} Third failure of this check in a rolling 7 days — TL flagged."
        return f"{base} Sale held and routed to the TL queue."

    if outcome.decision == Decision.QA_REVIEW:
        if outcome.low_confidence == 1:
            return "Insufficient confidence on a critical check. Never auto-passed."
        return f"Insufficient confidence on {outcome.low_confidence} critical checks. Never auto-passed."

    base = (
        f"All {outcome.critical_checks} critical checks passed."
        if outcome.critical_checks > 0
        else "All critical checks passed."
    )
    if outcome.non_critical_fails > 0:
        plural = "s" if outcome.non_critical_fails != 1 else ""
        return f"{base} {outcome.non_critical_fails} non-critical behaviour note{plural} raised for coaching."
    return f"{base} No human touch required."
