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

Low confidence is scoped to ANY check, critical or not — this is the
CIMET spec's literal rule ("low confidence on any check — routed to QA
rather than auto-passed") and is treated as authoritative over an earlier,
narrower reading of this codebase that scoped it to critical checks only
(see docs/DECISIONS.md's "Phase 4" section for why that reading was
corrected back). The practical consequence: every check — including the
non-critical Behaviour heuristics — must report a confidence that's
genuinely >= the floor whenever it has nothing concerning to report,
because a low-confidence PASS still routes here exactly like a
low-confidence FAIL or a not-evaluable REVIEW. This does NOT make
Behaviour checks "critical" — a low-confidence non-critical check still
can't produce a HOLD, only a QA_REVIEW (a human look, not a block) — see
`describe_decision` and `critical_fails` below, which are unaffected.
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
    """criticalFails > 0 -> HOLD; any check's confidence < floor ->
    QA_REVIEW; else AUTO_SUBMIT. A low-confidence non-critical check still
    cannot produce a HOLD — only QA_REVIEW, and only when no critical
    check has already failed (HOLD takes precedence either way)."""
    critical_fails = sum(1 for c in checks if c.critical and c.status == ResultStatus.FAIL)
    low_confidence = sum(1 for c in checks if c.confidence < settings.confidence_floor)
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
    Decision.QA_REVIEW: "Gate rule: low confidence on any check → route to QA, never auto-pass.",
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
            return "Insufficient confidence on a check. Never auto-passed."
        return f"Insufficient confidence on {outcome.low_confidence} checks. Never auto-passed."

    base = (
        f"All {outcome.critical_checks} critical checks passed."
        if outcome.critical_checks > 0
        else "All critical checks passed."
    )
    if outcome.non_critical_fails > 0:
        plural = "s" if outcome.non_critical_fails != 1 else ""
        return f"{base} {outcome.non_critical_fails} non-critical behaviour note{plural} raised for coaching."
    return f"{base} No human touch required."
