"""
Persistent domain model. Mirrors the entity separation the frontend already
expects (design_handoff/NEXTJS_BUILD_PLAN.md §4): Lead, Recording,
Transcript, Check, CheckResult, Evidence, RuleVersion, Decision, AuditEvent,
HumanReview. CheckResult / GateDecision / HumanReview / AuditEvent are
treated as append-only by every service in this codebase — nothing ever
issues an UPDATE or DELETE against them (a re-evaluation writes new rows
pinned to a new rule_version, it never edits old ones).
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Retailer(Base):
    __tablename__ = "retailers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)

    checklists: Mapped[list["Checklist"]] = relationship(back_populates="retailer")


class Checklist(Base):
    __tablename__ = "checklists"

    id: Mapped[int] = mapped_column(primary_key=True)
    retailer_id: Mapped[int] = mapped_column(ForeignKey("retailers.id"))
    name: Mapped[str] = mapped_column(String(128))
    product: Mapped[str] = mapped_column(String(32))

    retailer: Mapped["Retailer"] = relationship(back_populates="checklists")
    rule_versions: Mapped[list["RuleVersion"]] = relationship(back_populates="checklist")


class RuleVersion(Base):
    """A versioned snapshot of a checklist. Historical calls must resolve to
    the version effective on the call date, never today's — see
    app/services/rule_resolution.py."""

    __tablename__ = "rule_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    checklist_id: Mapped[int] = mapped_column(ForeignKey("checklists.id"))
    version: Mapped[str] = mapped_column(String(16))
    effective_from: Mapped[dt.date] = mapped_column(Date)
    effective_to: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    live: Mapped[bool] = mapped_column(Boolean, default=False)

    checklist: Mapped["Checklist"] = relationship(back_populates="rule_versions")
    checks: Mapped[list["Check"]] = relationship(back_populates="rule_version", order_by="Check.id")

    __table_args__ = (UniqueConstraint("checklist_id", "version", name="uq_checklist_version"),)


class Check(Base):
    """A single check definition, versioned via its RuleVersion. `config` is
    the evaluator's own parameters (expected phrase, extraction pattern,
    source field, thresholds) — configuration, never hard-coded logic, per
    the brief's rule-system requirement."""

    __tablename__ = "checks"

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_version_id: Mapped[int] = mapped_column(ForeignKey("rule_versions.id"))
    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(128))
    type: Mapped[str] = mapped_column(String(16))  # enums.CheckType
    critical: Mapped[bool] = mapped_column(Boolean)
    weight: Mapped[int] = mapped_column(Integer)
    source_of_truth: Mapped[str] = mapped_column(String(128))
    config: Mapped[dict] = mapped_column(JSON, default=dict)

    rule_version: Mapped["RuleVersion"] = relationship(back_populates="checks")

    __table_args__ = (UniqueConstraint("rule_version_id", "code", name="uq_rule_version_check_code"),)


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    scenario_tag: Mapped[str | None] = mapped_column(String(16), nullable=True)
    scenario_summary: Mapped[str | None] = mapped_column(String(256), nullable=True)
    retailer_id: Mapped[int] = mapped_column(ForeignKey("retailers.id"))
    product: Mapped[str] = mapped_column(String(32))
    agent: Mapped[str] = mapped_column(String(128))
    team_lead: Mapped[str] = mapped_column(String(128))
    campaign: Mapped[str | None] = mapped_column(String(64), nullable=True)
    site: Mapped[str | None] = mapped_column(String(64), nullable=True)
    call_datetime: Mapped[dt.datetime] = mapped_column(DateTime)
    duration_sec: Mapped[int] = mapped_column(Integer)
    last_completed_step: Mapped[str | None] = mapped_column(String(64), nullable=True)
    test_contact: Mapped[str | None] = mapped_column(String(128), nullable=True)
    checklist_version_id: Mapped[int | None] = mapped_column(ForeignKey("rule_versions.id"), nullable=True)
    state: Mapped[str] = mapped_column(String(16))  # enums.LeadState
    repeat_offence: Mapped[bool] = mapped_column(Boolean, default=False)
    is_seed_scenario: Mapped[bool] = mapped_column(Boolean, default=False)
    crm_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime)

    retailer: Mapped["Retailer"] = relationship()
    checklist_version: Mapped["RuleVersion | None"] = relationship()
    recording: Mapped["Recording | None"] = relationship(back_populates="lead", uselist=False)
    transcript: Mapped["Transcript | None"] = relationship(back_populates="lead", uselist=False)
    results: Mapped[list["CheckResult"]] = relationship(back_populates="lead", order_by="CheckResult.id")
    decision: Mapped["GateDecision | None"] = relationship(back_populates="lead", uselist=False)
    reviews: Mapped[list["HumanReview"]] = relationship(back_populates="lead", order_by="HumanReview.created_at")
    audit_events: Mapped[list["AuditEvent"]] = relationship(back_populates="lead", order_by="AuditEvent.seq")
    ingest_error: Mapped["IngestError | None"] = relationship(back_populates="lead", uselist=False)


class Recording(Base):
    __tablename__ = "recordings"

    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[str] = mapped_column(ForeignKey("leads.id"), unique=True)
    source: Mapped[str] = mapped_column(String(32))
    duration_seconds: Mapped[int] = mapped_column(Integer)
    storage_reference: Mapped[str] = mapped_column(String(256))
    mime_type: Mapped[str] = mapped_column(String(64))
    processing_status: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime)

    lead: Mapped["Lead"] = relationship(back_populates="recording")


class Transcript(Base):
    __tablename__ = "transcripts"

    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[str] = mapped_column(ForeignKey("leads.id"), unique=True)
    status: Mapped[str] = mapped_column(String(32))
    source: Mapped[str] = mapped_column(String(32))
    version: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime)

    lead: Mapped["Lead"] = relationship(back_populates="transcript")
    segments: Mapped[list["TranscriptSegment"]] = relationship(
        back_populates="transcript", order_by="TranscriptSegment.start_seconds"
    )


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id: Mapped[int] = mapped_column(primary_key=True)
    transcript_id: Mapped[int] = mapped_column(ForeignKey("transcripts.id"))
    speaker: Mapped[str] = mapped_column(String(16))  # enums.Speaker
    start_seconds: Mapped[float] = mapped_column(Float)
    end_seconds: Mapped[float] = mapped_column(Float)
    text: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(16), default="pass")  # enums.TurnKind, display hint

    transcript: Mapped["Transcript"] = relationship(back_populates="segments")


class CheckResult(Base):
    __tablename__ = "check_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[str] = mapped_column(ForeignKey("leads.id"))
    check_id: Mapped[int] = mapped_column(ForeignKey("checks.id"))
    rule_version_id: Mapped[int] = mapped_column(ForeignKey("rule_versions.id"))
    status: Mapped[str] = mapped_column(String(16))  # enums.ResultStatus
    confidence: Mapped[float] = mapped_column(Float)
    timestamp_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    observed: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected: Mapped[str | None] = mapped_column(Text, nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluated_at: Mapped[dt.datetime] = mapped_column(DateTime)

    lead: Mapped["Lead"] = relationship(back_populates="results")
    check: Mapped["Check"] = relationship()
    rule_version: Mapped["RuleVersion"] = relationship()
    evidence: Mapped["Evidence | None"] = relationship(
        back_populates="check_result", uselist=False, cascade="all, delete-orphan"
    )


class Evidence(Base):
    """One canonical evidence structure, reused by finding cards, the
    evidence drawer, the timeline, and the audit trail alike — never a
    fabricated transcript quote; absence of adequate evidence lowers
    confidence rather than inventing a match."""

    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(primary_key=True)
    check_result_id: Mapped[int] = mapped_column(ForeignKey("check_results.id"), unique=True)
    source_type: Mapped[str] = mapped_column(String(32))  # "transcript" | "none"
    transcript_segment_id: Mapped[int | None] = mapped_column(ForeignKey("transcript_segments.id"), nullable=True)
    speaker: Mapped[str | None] = mapped_column(String(16), nullable=True)
    start_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    end_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    observed_value: Mapped[str | None] = mapped_column(Text, nullable=True)

    check_result: Mapped["CheckResult"] = relationship(back_populates="evidence")


class GateDecision(Base):
    """The deterministic gate's output for a lead's *current* evaluation.
    Never mutated in place by a human review — see HumanReview."""

    __tablename__ = "gate_decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[str] = mapped_column(ForeignKey("leads.id"), unique=True)
    decision: Mapped[str] = mapped_column(String(16))  # enums.Decision
    reason: Mapped[str] = mapped_column(Text)
    rule_applied: Mapped[str] = mapped_column(Text)
    critical_fails: Mapped[int] = mapped_column(Integer)
    low_confidence: Mapped[int] = mapped_column(Integer)
    checks_run: Mapped[int] = mapped_column(Integer)
    critical_checks: Mapped[int] = mapped_column(Integer)
    non_critical_fails: Mapped[int] = mapped_column(Integer)
    sampled_for_audit: Mapped[bool] = mapped_column(Boolean, default=False)
    decided_at: Mapped[dt.datetime] = mapped_column(DateTime)

    lead: Mapped["Lead"] = relationship(back_populates="decision")


class HumanReview(Base):
    """Append-only. A human decision is stored *alongside* the AI decision,
    never in place of it (CLAUDE.md #7 / brief "respect the override")."""

    __tablename__ = "human_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[str] = mapped_column(ForeignKey("leads.id"))
    reviewer_name: Mapped[str] = mapped_column(String(128))
    reviewer_role: Mapped[str] = mapped_column(String(64))
    ai_decision: Mapped[str] = mapped_column(String(16))
    human_decision: Mapped[str] = mapped_column(String(16))  # "PASS" | "HOLD"
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime)

    lead: Mapped["Lead"] = relationship(back_populates="reviews")


class AuditEvent(Base):
    """Append-only decision ledger. Never rewritten; a correction is always
    a new row."""

    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[str] = mapped_column(ForeignKey("leads.id"))
    seq: Mapped[int] = mapped_column(Integer)
    at: Mapped[dt.datetime] = mapped_column(DateTime)
    event_type: Mapped[str] = mapped_column(String(32))  # enums.AuditEventType
    actor: Mapped[str] = mapped_column(String(128))
    rule_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resulting_state: Mapped[str] = mapped_column(String(64))
    event_metadata: Mapped[dict] = mapped_column(JSON, default=dict)

    lead: Mapped["Lead"] = relationship(back_populates="audit_events")


class CalibrationSample(Base):
    """5% of clean (AUTO_SUBMIT) calls sampled to a human anyway — measuring
    the model, not just trusting it."""

    __tablename__ = "calibration_samples"

    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[str] = mapped_column(ForeignKey("leads.id"))
    sampled_at: Mapped[dt.datetime] = mapped_column(DateTime)
    sample_reason: Mapped[str] = mapped_column(String(64))
    review_status: Mapped[str] = mapped_column(String(32), default="pending")  # pending | agree | disagree


class IngestError(Base):
    __tablename__ = "ingest_errors"

    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[str] = mapped_column(ForeignKey("leads.id"), unique=True)
    code: Mapped[str] = mapped_column(String(64))
    message: Mapped[str] = mapped_column(Text)
    retry: Mapped[str] = mapped_column(String(32))
    at: Mapped[str] = mapped_column(String(32))

    lead: Mapped["Lead"] = relationship(back_populates="ingest_error")
