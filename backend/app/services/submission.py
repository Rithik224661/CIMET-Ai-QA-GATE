"""
The submission boundary (brief §11): GateDecision -> Submission Service ->
SUBMITTED or HELD. Only AUTO_SUBMIT ever produces a Submission row — HOLD
and QA_REVIEW never submit, by construction (there is no code path that
creates a Submission for them).

This is a **DEMO / MOCK SANDBOX** — clearly labeled as such everywhere it
surfaces (the `sandbox` field on every payload, this docstring, the
backend README). No real CIMET CRM submission endpoint exists yet; wiring
one in only requires changing `MockSubmissionAdapter.submit()`, not
anything upstream of it — the same anti-corruption-layer pattern as
app/services/sandbox_adapter.py.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Protocol

from ..enums import Decision
from ..models import GateDecision, Lead, Submission


@dataclass(frozen=True)
class SubmissionResult:
    status: str
    payload: dict


class SubmissionAdapter(Protocol):
    def submit(self, lead: Lead, decision: GateDecision) -> SubmissionResult: ...


class MockSubmissionAdapter:
    """The only adapter wired up in this build. Builds the payload CIMET's
    CRM would presumably need (lead id, retailer, agent, decision, checks
    run) and marks it submitted — no network call, no real system of
    record involved."""

    def submit(self, lead: Lead, decision: GateDecision) -> SubmissionResult:
        payload = {
            "sandbox": "DEMO_MOCK",
            "leadId": lead.id,
            "retailer": lead.retailer.name,
            "product": lead.product,
            "agent": lead.agent,
            "decision": decision.decision,
            "checksRun": decision.checks_run,
            "criticalChecks": decision.critical_checks,
            "ruleVersion": lead.checklist_version.version if lead.checklist_version else None,
        }
        return SubmissionResult(status="SUBMITTED", payload=payload)


def submit_if_auto_submitted(db, lead: Lead, decision: GateDecision, adapter: SubmissionAdapter | None = None) -> Submission | None:
    """Only ever called for AUTO_SUBMIT — HOLD and QA_REVIEW must never
    reach here (the pipeline only calls this after checking the decision).
    Idempotent: replaces any prior Submission for this lead rather than
    accumulating duplicates, matching the pipeline's own re-evaluation
    behavior."""
    if decision.decision != Decision.AUTO_SUBMIT:
        raise ValueError(f"refusing to submit a {decision.decision} decision — only AUTO_SUBMIT may submit")

    adapter = adapter or MockSubmissionAdapter()
    result = adapter.submit(lead, decision)

    if lead.submission_record is not None:
        db.delete(lead.submission_record)
        lead.submission_record = None
        db.flush()

    submission = Submission(
        lead_id=lead.id,
        decision_id=decision.id,
        status=result.status,
        payload=result.payload,
        submitted_at=dt.datetime.now(dt.UTC),
    )
    db.add(submission)
    db.flush()
    return submission
