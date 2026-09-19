"""
API response shapes. Every model below is deliberately shaped to match the
frontend's existing TypeScript types (src/lib/types.ts) field-for-field —
CamelModel auto-generates the camelCase JSON alias from a snake_case Python
field, so `check_code` serializes as `checkCode`. This is the
anti-corruption boundary: internal SQLAlchemy models stay Pythonic;
external JSON stays exactly what the approved frontend already expects.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# ---- shared pieces ----


class CheckResultOut(CamelModel):
    check_code: str
    name: str
    type: str
    critical: bool
    status: str
    confidence: float
    timestamp: str | None
    rule_version: str
    source_of_truth: str
    observed: str | None
    expected: str | None
    evidence_quote: str | None
    rationale: str | None


class TranscriptTurnOut(CamelModel):
    timestamp: str
    speaker: str
    text: str
    kind: str


class HumanOverrideOut(CamelModel):
    ai_decision: str
    human_decision: str
    reason: str
    reviewer_role: str
    reviewer_name: str
    at: str


class IngestErrorOut(CamelModel):
    code: str
    message: str
    retry: str
    at: str


class GateOutcomeOut(CamelModel):
    decision: str
    critical_fails: int
    low_confidence: int
    checks_run: int
    critical_checks: int
    non_critical_fails: int
    reason: str
    rule_applied: str


class SubmissionOut(CamelModel):
    id: int
    status: str
    sandbox: str
    submitted_at: str
    payload: dict


class LeadOut(CamelModel):
    id: str
    scenario_tag: str
    scenario_summary: str
    retailer: str
    product: str
    agent: str
    team_lead: str
    call_date: str
    duration_sec: int
    checklist_version: str
    state: str
    repeat_offence: bool
    results: list[CheckResultOut]
    transcript: list[TranscriptTurnOut]
    override: HumanOverrideOut | None
    ingest_error: IngestErrorOut | None
    decision: GateOutcomeOut | None
    submission: SubmissionOut | None = None


class LeadsListOut(CamelModel):
    leads: list[LeadOut]


# ---- rules / checks ----


class RuleSetVersionOut(CamelModel):
    retailer: str
    checklist: str
    version: str
    effective_from: str
    live: bool


class RuleSetsOut(CamelModel):
    rule_sets: list[RuleSetVersionOut]


class CheckDefinitionOut(CamelModel):
    code: str
    name: str
    type: str
    critical: bool
    weight: int
    source_of_truth: str


class ChecksOut(CamelModel):
    checks: list[CheckDefinitionOut]


# ---- calibration ----


class CalibrationKpiOut(CamelModel):
    label: str
    value: str
    unit: str
    sub: str
    tone: str


class ConfidenceBucketOut(CamelModel):
    label: str
    count: int
    below_floor: bool


class DisagreementCategoryOut(CamelModel):
    name: str
    count: int


class CalibrationOut(CamelModel):
    kpis: list[CalibrationKpiOut]
    confidence_buckets: list[ConfidenceBucketOut]
    confidence_bucket_max: int
    disagreements: list[DisagreementCategoryOut]
    disagreement_max: int
    sampled_calls_total: int
    sampled_disagreements_total: int


# ---- dashboard ----


class DashboardKpiOut(CamelModel):
    label: str
    value: str
    unit: str
    sub: str
    tone: str


class DistributionRowOut(CamelModel):
    label: str
    count: str
    pct: str
    pct_value: float
    tone: str


class FailingCheckRowOut(CamelModel):
    name: str
    type: str
    count: int


class RecentFailureRowOut(CamelModel):
    lead_id: str
    check: str
    meta: str
    age: str


class RecentOverrideRowOut(CamelModel):
    lead_id: str
    ai: str
    human: str
    reason: str
    who: str
    time: str


class DashboardOut(CamelModel):
    kpis: list[DashboardKpiOut]
    distribution: list[DistributionRowOut]
    failing_checks: list[FailingCheckRowOut]
    recent_failures: list[RecentFailureRowOut]
    recent_overrides: list[RecentOverrideRowOut]


# ---- audit ----


class AuditEventOut(CamelModel):
    time: str
    event: str
    actor: str
    version: str | None
    resulting_state: str


class AuditOut(CamelModel):
    events: list[AuditEventOut]


# ---- reviews (write path) ----


class ReviewIn(CamelModel):
    lead_id: str
    human_decision: str  # "PASS" | "HOLD"
    reason: str
    reviewer_name: str | None = None
    reviewer_role: str | None = None


class ReviewOut(CamelModel):
    ok: bool
    review: HumanOverrideOut


# ---- evaluations ----


class EvaluationRequestIn(CamelModel):
    lead_id: str


class EvaluationOut(CamelModel):
    lead_id: str
    decision: GateOutcomeOut
    checks_run: int


# ---- health ----


class HealthOut(CamelModel):
    status: str
    database: str
    data_mode: str
    ai_provider: str
    seeded: bool
