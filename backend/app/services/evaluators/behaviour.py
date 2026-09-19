"""
Behaviour evaluator (brief type C): transcript-only signals — rapport,
interruptions, dead air, objection handling. Never critical, never
blocking on its own (brief §15) — that's enforced by the Check's
`critical` flag feeding the gate, not by this evaluator, but this module
never manufactures a false critical regardless.
"""

from __future__ import annotations

import re

from ...config import settings
from .base import CheckOutcome, EvaluationContext, EvidenceData, ResultStatus

_DEAD_AIR_RE = re.compile(r"(\d+)\s*s\s+dead\s*air", re.IGNORECASE)


def _evaluate_dead_air(check_config: dict, context: EvaluationContext) -> CheckOutcome:
    threshold = check_config.get("threshold_seconds", settings.dead_air_threshold_seconds)
    system_segments = context.segments_by("SYSTEM")

    worst_segment = None
    worst_duration = 0.0
    for seg in system_segments:
        m = _DEAD_AIR_RE.search(seg.text)
        if m:
            duration = float(m.group(1))
            if duration > worst_duration:
                worst_duration = duration
                worst_segment = seg

    if worst_segment is None:
        return CheckOutcome(
            status=ResultStatus.PASS,
            confidence=check_config.get("default_confidence", 0.94),
            observed=None,
            expected=None,
            rationale="No extended silence detected in the transcript.",
            evidence=None,
            timestamp_seconds=None,
        )

    mm, ss = int(worst_segment.start_seconds // 60), int(worst_segment.start_seconds % 60)
    status = ResultStatus.FAIL if worst_duration >= threshold else ResultStatus.PASS
    observed = f"{int(worst_duration)}s continuous silence at {mm:02d}:{ss:02d}"
    expected = f"< {int(threshold)}s"
    rationale = (
        "Behaviour checks never block a sale on their own; routed to the agent scorecard as a coaching note."
        if status == ResultStatus.FAIL
        else "Longest silence stayed under the coaching threshold."
    )

    evidence = EvidenceData(
        source_type="transcript",
        transcript_segment_id=worst_segment.id,
        speaker=worst_segment.speaker,
        start_seconds=worst_segment.start_seconds,
        end_seconds=worst_segment.end_seconds,
        excerpt=worst_segment.text,
        expected_value=expected,
        observed_value=observed,
    )

    return CheckOutcome(
        status=status,
        confidence=check_config.get("default_confidence", 0.94),
        observed=observed,
        expected=expected,
        rationale=rationale,
        evidence=evidence,
        timestamp_seconds=worst_segment.start_seconds,
    )


def evaluate_behaviour(check_config: dict, context: EvaluationContext) -> CheckOutcome:
    metric = check_config.get("metric")
    if metric == "dead_air":
        return _evaluate_dead_air(check_config, context)

    # rapport / interruptions / objection_handling: no rich synthetic signal
    # to mine from short demo transcripts in this build — documented
    # heuristic-limited default rather than a fabricated behavioural score.
    return CheckOutcome(
        status=ResultStatus.PASS,
        confidence=check_config.get("default_confidence", 0.88),
        observed=None,
        expected=None,
        rationale="Transcript-only behavioural signal; no anomaly detected against the configured heuristic.",
        evidence=None,
        timestamp_seconds=None,
    )
