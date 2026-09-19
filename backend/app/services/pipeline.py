"""
The evaluation pipeline: ingest -> normalize -> extract -> run checks ->
collect evidence -> confidence -> deterministic gate -> persist -> route
(brief §04). This is the one place all three evaluator types get invoked
and the gate gets computed + persisted; nothing else in the codebase
produces a GateDecision.
"""

from __future__ import annotations

import datetime as dt
import random

from sqlalchemy.orm import Session

from ..config import settings
from ..enums import AuditEventType, CheckType, Decision, LeadState, ResultStatus
from ..models import CalibrationSample, Check, CheckResult, Evidence, GateDecision, Lead
from .audit import append_audit_event
from .evaluators.base import CheckOutcome, EvaluationContext, TranscriptSegmentData
from .evaluators.behaviour import evaluate_behaviour
from .evaluators.factual import evaluate_factual
from .evaluators.verbatim import evaluate_verbatim
from .gate import GateCheckInput, describe_decision, evaluate_gate, gate_rule_copy
from .repeat_offence import count_recent_critical_failures, is_repeat_offence


def record_ingest_events(db: Session, lead: Lead, *, recording_ok: bool) -> None:
    """The ingest-stage audit trail: lead created -> recording received ->
    transcript generated -> normalized -> rule set pinned. Called once,
    right after a lead's Recording/Transcript rows are created and before
    `run_evaluation`. For an ingest failure, records the failure instead of
    pretending the pipeline continued."""
    append_audit_event(db, lead_id=lead.id, event_type=AuditEventType.LEAD_CREATED, actor="CRM", resulting_state="OPEN")

    if not recording_ok:
        append_audit_event(
            db,
            lead_id=lead.id,
            event_type=AuditEventType.ERROR,
            actor="Dialler API · lead-keyed",
            resulting_state="E_EMPTY_MEDIA",
        )
        return

    append_audit_event(
        db, lead_id=lead.id, event_type=AuditEventType.RECORDING_RECEIVED, actor="Dialler API · lead-keyed", resulting_state="MEDIA_OK"
    )
    append_audit_event(
        db, lead_id=lead.id, event_type=AuditEventType.TRANSCRIPT_RECEIVED, actor="ASR · speaker-separated", resulting_state="TRANSCRIPT_OK"
    )
    append_audit_event(
        db, lead_id=lead.id, event_type=AuditEventType.NORMALIZATION_COMPLETED, actor="Pipeline", resulting_state="NORMALISED"
    )
    if lead.checklist_version is not None:
        retailer_label = lead.checklist_version.checklist.retailer.name
        append_audit_event(
            db,
            lead_id=lead.id,
            event_type=AuditEventType.RULE_VERSION_RESOLVED,
            actor="Check library",
            rule_version=f"{retailer_label} {lead.checklist_version.version}",
            resulting_state="RULES_PINNED",
        )


def _evaluate_check(check: Check, context: EvaluationContext) -> CheckOutcome:
    if check.type == CheckType.VERBATIM:
        return evaluate_verbatim(check.config, context)
    if check.type == CheckType.FACTUAL:
        return evaluate_factual(check.config, context)
    return evaluate_behaviour(check.config, context)


def run_evaluation(db: Session, lead: Lead) -> GateDecision:
    """Runs every check on `lead`'s resolved rule version against its
    transcript + crm_snapshot, persists CheckResult+Evidence rows, computes
    and persists the gate decision, and writes the corresponding audit
    events.

    Idempotent per call: re-running clears this lead's previous
    CheckResult/Evidence/GateDecision rows first and writes a fresh set —
    a re-evaluation supersedes the old result set rather than editing it in
    place, and the AuditEvent trail for the new run stays append-only (see
    docs/DECISIONS.md)."""

    if lead.checklist_version_id is None or lead.checklist_version is None:
        raise ValueError(f"lead {lead.id} has no resolved rule version")
    if lead.transcript is None:
        raise ValueError(f"lead {lead.id} has no transcript")

    checks = lead.checklist_version.checks
    segments = [
        TranscriptSegmentData(
            id=s.id, speaker=s.speaker, start_seconds=s.start_seconds, end_seconds=s.end_seconds, text=s.text
        )
        for s in lead.transcript.segments
    ]
    context = EvaluationContext(
        lead_id=lead.id, duration_sec=lead.duration_sec, segments=segments, crm_snapshot=lead.crm_snapshot or {}
    )

    # Accessing lead.results / lead.decision below both loads and CACHES
    # the relationship on the in-memory `lead` object. Simply db.add()-ing
    # replacements later (setting only the FK) would leave that cache
    # stale for the rest of this session — any code reading lead.results
    # or lead.decision afterward (including this same function, and any
    # single request that evaluates then immediately serializes the lead)
    # would see the old, deleted state. Mutate the relationship
    # collections themselves so SQLAlchemy keeps the in-memory object
    # consistent with what's actually persisted.
    for old_result in list(lead.results):
        lead.results.remove(old_result)
        db.delete(old_result)
    if lead.decision is not None:
        old_decision = lead.decision
        lead.decision = None
        db.delete(old_decision)
    db.flush()

    gate_inputs: list[GateCheckInput] = []
    persisted: list[tuple[Check, CheckResult]] = []

    retailer_label = lead.checklist_version.checklist.retailer.name
    rule_version_label = f"{retailer_label} {lead.checklist_version.version}"

    for check in checks:
        outcome = _evaluate_check(check, context)

        result = CheckResult(
            check_id=check.id,
            rule_version_id=check.rule_version_id,
            status=outcome.status,
            confidence=outcome.confidence,
            timestamp_seconds=outcome.timestamp_seconds,
            observed=outcome.observed,
            expected=outcome.expected,
            rationale=outcome.rationale,
            evaluated_at=dt.datetime.now(dt.UTC),
        )
        lead.results.append(result)  # sets result.lead_id via the relationship, keeps lead.results in sync
        db.flush()

        if outcome.evidence is not None:
            result.evidence = Evidence(
                source_type=outcome.evidence.source_type,
                transcript_segment_id=outcome.evidence.transcript_segment_id,
                speaker=outcome.evidence.speaker,
                start_seconds=outcome.evidence.start_seconds,
                end_seconds=outcome.evidence.end_seconds,
                excerpt=outcome.evidence.excerpt,
                expected_value=outcome.evidence.expected_value,
                observed_value=outcome.evidence.observed_value,
            )

        persisted.append((check, result))
        gate_inputs.append(GateCheckInput(critical=check.critical, status=outcome.status, confidence=outcome.confidence))

        append_audit_event(
            db,
            lead_id=lead.id,
            event_type=AuditEventType.CHECK_COMPLETED,
            actor="Scoring engine",
            rule_version=rule_version_label,
            resulting_state=outcome.status,
        )
        if outcome.evidence is not None and outcome.evidence.source_type == "transcript":
            append_audit_event(
                db,
                lead_id=lead.id,
                event_type=AuditEventType.EVIDENCE_CREATED,
                actor="Scoring engine",
                resulting_state="EVIDENCE_OK",
            )

    outcome = evaluate_gate(gate_inputs)

    repeat = False
    for check, result in persisted:
        if check.critical and result.status == ResultStatus.FAIL:
            count = count_recent_critical_failures(db, agent=lead.agent, check_code=check.code, as_of=lead.call_datetime)
            if is_repeat_offence(count):
                repeat = True
    lead.repeat_offence = repeat

    reason = describe_decision(outcome, repeat_offence=repeat, overridden=False)
    rule_applied = gate_rule_copy(outcome.decision)
    sampled = outcome.decision == Decision.AUTO_SUBMIT and random.random() < settings.clean_sample_rate

    decision = GateDecision(
        decision=outcome.decision,
        reason=reason,
        rule_applied=rule_applied,
        critical_fails=outcome.critical_fails,
        low_confidence=outcome.low_confidence,
        checks_run=outcome.checks_run,
        critical_checks=outcome.critical_checks,
        non_critical_fails=outcome.non_critical_fails,
        sampled_for_audit=sampled,
        decided_at=dt.datetime.now(dt.UTC),
    )
    lead.decision = decision  # sets decision.lead_id via the relationship, keeps lead.decision in sync

    if sampled:
        db.add(
            CalibrationSample(
                lead_id=lead.id, sampled_at=dt.datetime.now(dt.UTC), sample_reason="clean_call_sample", review_status="pending"
            )
        )
        append_audit_event(
            db, lead_id=lead.id, event_type=AuditEventType.SAMPLING_CREATED, actor="Sampling job", resulting_state="SAMPLED"
        )

    append_audit_event(
        db,
        lead_id=lead.id,
        event_type=AuditEventType.GATE_DECIDED,
        actor="Gate",
        rule_version="gate v1.0",
        resulting_state=outcome.decision,
    )
    terminal_event = {
        Decision.HOLD: (AuditEventType.SALE_HELD, "HOLD"),
        Decision.AUTO_SUBMIT: (AuditEventType.SALE_AUTO_SUBMITTED, "AUTO-SUBMIT"),
        Decision.QA_REVIEW: (AuditEventType.QA_REVIEW_REQUESTED, "QA REVIEW"),
    }[Decision(outcome.decision)]
    append_audit_event(db, lead_id=lead.id, event_type=terminal_event[0], actor="Gate", resulting_state=terminal_event[1])

    lead.state = LeadState.SCORED
    lead.updated_at = dt.datetime.now(dt.UTC)

    db.flush()
    return decision
