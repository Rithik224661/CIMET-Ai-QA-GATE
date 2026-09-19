"""
ORM -> API response shape. Kept separate from the ORM models themselves so
the persisted, normalized schema can differ from the flatter, embedded
shape the frontend expects (CLAUDE.md's "adapter, don't leak internal
schema" principle applied to the outbound direction too).
"""

from __future__ import annotations

from . import models
from .schemas import (
    CheckResultOut,
    GateOutcomeOut,
    HumanOverrideOut,
    IngestErrorOut,
    LeadOut,
    SubmissionOut,
    TranscriptTurnOut,
)
from .services.audio_storage import has_recording


def _format_timestamp(seconds: float | None) -> str | None:
    if seconds is None:
        return None
    mm = int(seconds // 60)
    ss = int(seconds % 60)
    return f"{mm:02d}:{ss:02d}"


def serialize_check_result(result: models.CheckResult) -> CheckResultOut:
    check = result.check
    return CheckResultOut(
        check_code=check.code,
        name=check.name,
        type=check.type,
        critical=check.critical,
        status=result.status,
        confidence=result.confidence,
        timestamp=_format_timestamp(result.timestamp_seconds),
        rule_version=f"{check.code} · {result.rule_version.version}",
        source_of_truth=check.source_of_truth,
        observed=result.observed,
        expected=result.expected,
        evidence_quote=result.evidence.excerpt if result.evidence else None,
        rationale=result.rationale,
    )


def serialize_transcript_turn(segment: models.TranscriptSegment) -> TranscriptTurnOut:
    return TranscriptTurnOut(
        timestamp=_format_timestamp(segment.start_seconds) or "00:00",
        speaker=segment.speaker,
        text=segment.text,
        kind=segment.kind,
    )


def serialize_gate_decision(decision: models.GateDecision) -> GateOutcomeOut:
    return GateOutcomeOut(
        evaluation_id=decision.id,
        decision=decision.decision,
        critical_fails=decision.critical_fails,
        low_confidence=decision.low_confidence,
        checks_run=decision.checks_run,
        critical_checks=decision.critical_checks,
        non_critical_fails=decision.non_critical_fails,
        reason=decision.reason,
        rule_applied=decision.rule_applied,
    )


def _latest_review(lead: models.Lead) -> models.HumanReview | None:
    return lead.reviews[-1] if lead.reviews else None


def serialize_submission(submission: models.Submission) -> SubmissionOut:
    return SubmissionOut(
        id=submission.id,
        status=submission.status,
        sandbox=submission.payload.get("sandbox", "DEMO_MOCK"),
        submitted_at=submission.submitted_at.strftime("%Y-%m-%d %H:%M:%S"),
        payload=submission.payload,
    )


def serialize_override(review: models.HumanReview) -> HumanOverrideOut:
    return HumanOverrideOut(
        ai_decision=review.ai_decision,
        human_decision=review.human_decision,
        reason=review.reason,
        reviewer_role=review.reviewer_role,
        reviewer_name=review.reviewer_name,
        at=review.created_at.strftime("%Y-%m-%d %H:%M"),
    )


def serialize_lead(lead: models.Lead) -> LeadOut:
    review = _latest_review(lead)
    ingest_error = lead.ingest_error

    return LeadOut(
        id=lead.id,
        scenario_tag=lead.scenario_tag or "",
        scenario_summary=lead.scenario_summary or "",
        retailer=lead.retailer.name,
        product=lead.product,
        agent=lead.agent,
        team_lead=lead.team_lead,
        call_date=lead.call_datetime.strftime("%Y-%m-%d %H:%M"),
        duration_sec=lead.duration_sec,
        checklist_version=lead.checklist_version.version if lead.checklist_version else "",
        state=lead.state,
        repeat_offence=lead.repeat_offence,
        results=[serialize_check_result(r) for r in lead.results],
        transcript=[serialize_transcript_turn(s) for s in (lead.transcript.segments if lead.transcript else [])],
        override=serialize_override(review) if review else None,
        ingest_error=(
            IngestErrorOut(code=ingest_error.code, message=ingest_error.message, retry=ingest_error.retry, at=ingest_error.at)
            if ingest_error
            else None
        ),
        decision=serialize_gate_decision(lead.decision) if lead.decision else None,
        submission=serialize_submission(lead.submission_record) if lead.submission_record else None,
        has_audio=has_recording(lead.id),
    )
