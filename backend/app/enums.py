from __future__ import annotations

from enum import StrEnum


class Decision(StrEnum):
    AUTO_SUBMIT = "AUTO_SUBMIT"
    HOLD = "HOLD"
    QA_REVIEW = "QA_REVIEW"


class CheckType(StrEnum):
    VERBATIM = "Verbatim"
    FACTUAL = "Factual"
    BEHAVIOUR = "Behaviour"


class ResultStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW = "REVIEW"


class LeadState(StrEnum):
    SCORED = "scored"
    PROCESSING = "processing"
    ERROR = "error"


class Speaker(StrEnum):
    AGENT = "AGENT"
    CUSTOMER = "CUSTOMER"
    SYSTEM = "SYSTEM"


class TurnKind(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    REVIEW = "review"
    NOTE = "note"


class AuditEventType(StrEnum):
    LEAD_CREATED = "LEAD_CREATED"
    RECORDING_RECEIVED = "RECORDING_RECEIVED"
    TRANSCRIPT_RECEIVED = "TRANSCRIPT_RECEIVED"
    NORMALIZATION_COMPLETED = "NORMALIZATION_COMPLETED"
    RULE_VERSION_RESOLVED = "RULE_VERSION_RESOLVED"
    CHECK_STARTED = "CHECK_STARTED"
    CHECK_COMPLETED = "CHECK_COMPLETED"
    EVIDENCE_CREATED = "EVIDENCE_CREATED"
    GATE_DECIDED = "GATE_DECIDED"
    SALE_HELD = "SALE_HELD"
    SALE_AUTO_SUBMITTED = "SALE_AUTO_SUBMITTED"
    QA_REVIEW_REQUESTED = "QA_REVIEW_REQUESTED"
    HUMAN_OVERRIDE = "HUMAN_OVERRIDE"
    SAMPLING_CREATED = "SAMPLING_CREATED"
    ERROR = "ERROR"
