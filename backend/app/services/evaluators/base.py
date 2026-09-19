"""
The common check-evaluator interface. Every evaluator implements
`evaluate(check, context) -> CheckOutcome` and returns a STRUCTURED result
— never only natural language (brief §11: "No evaluator may return only
natural language"). This is what "not just an LLM asked PASS/FAIL" means in
code: the interface forces every evaluator to justify itself with observed
value, expected value, an evidence span, and a confidence number.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ...enums import ResultStatus


@dataclass(frozen=True)
class TranscriptSegmentData:
    id: int
    speaker: str
    start_seconds: float
    end_seconds: float
    text: str


@dataclass(frozen=True)
class EvaluationContext:
    lead_id: str
    duration_sec: int
    segments: list[TranscriptSegmentData]
    crm_snapshot: dict[str, object]

    def segments_by(self, speaker: str) -> list[TranscriptSegmentData]:
        return [s for s in self.segments if s.speaker == speaker]

    def segments_in_window(self, start: float | None, end: float | None) -> list[TranscriptSegmentData]:
        lo = start if start is not None else 0.0
        hi = end if end is not None else float(self.duration_sec)
        return [s for s in self.segments if s.start_seconds >= lo and s.start_seconds <= hi]


@dataclass(frozen=True)
class EvidenceData:
    source_type: str  # "transcript" | "none"
    transcript_segment_id: int | None
    speaker: str | None
    start_seconds: float | None
    end_seconds: float | None
    excerpt: str | None
    expected_value: str | None
    observed_value: str | None


@dataclass(frozen=True)
class CheckOutcome:
    status: str  # ResultStatus
    confidence: float
    observed: str | None
    expected: str | None
    rationale: str
    evidence: EvidenceData | None
    timestamp_seconds: float | None


class Evaluator(Protocol):
    def evaluate(self, check_config: dict, context: EvaluationContext) -> CheckOutcome: ...


def no_evidence_outcome(status: str, confidence: float, rationale: str) -> CheckOutcome:
    return CheckOutcome(
        status=status,
        confidence=confidence,
        observed=None,
        expected=None,
        rationale=rationale,
        evidence=EvidenceData(
            source_type="none",
            transcript_segment_id=None,
            speaker=None,
            start_seconds=None,
            end_seconds=None,
            excerpt=None,
            expected_value=None,
            observed_value=None,
        ),
        timestamp_seconds=None,
    )


__all__ = [
    "CheckOutcome",
    "EvaluationContext",
    "Evaluator",
    "EvidenceData",
    "TranscriptSegmentData",
    "ResultStatus",
    "no_evidence_outcome",
]
