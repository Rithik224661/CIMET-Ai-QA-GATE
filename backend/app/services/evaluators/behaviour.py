"""
Behaviour evaluator (brief type C): transcript-only signals — rapport,
interruptions, dead air, objection handling. Never critical, never
blocking on its own (brief §15) — that's enforced by the Check's
`critical` flag feeding the gate, not by this evaluator, but this module
never manufactures a false critical regardless.

Every metric here is a genuinely computed, deterministic heuristic over
the transcript (crosstalk markers, turn-taking structure, talk-time
ratios, objection-language keyword matching followed by a response) — not
a fabricated "AI sentiment score" and not an LLM call. This is the
explicitly-requested middle ground: real transcript-derived signal,
honestly limited by what a short synthetic call can represent, documented
rather than dressed up as more sophisticated than it is (see
docs/DECISIONS.md).
"""

from __future__ import annotations

import re

from ...config import settings
from .base import CheckOutcome, EvaluationContext, EvidenceData, ResultStatus, not_evaluable_outcome

_DEAD_AIR_RE = re.compile(r"(\d+)\s*s\s+dead\s*air", re.IGNORECASE)
_CROSSTALK_RE = re.compile(r"crosstalk", re.IGNORECASE)
_OBJECTION_RE = re.compile(
    r"\b(not sure|too (expensive|much)|don'?t want|cancel|hesitant|actually|but i|reconsider|think about it)\b",
    re.IGNORECASE,
)


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


def _evaluate_interruptions(check_config: dict, context: EvaluationContext) -> CheckOutcome:
    """Counts turns carrying a `[crosstalk]` marker — the one genuine
    overlapping-speech signal this transcript format captures. A fuller
    implementation would use word-level timestamps to detect turn overlap
    directly; documented limitation, not a fabricated score."""
    threshold = check_config.get("threshold_count", 1)
    hits = [seg for seg in context.segments if _CROSSTALK_RE.search(seg.text)]

    if not hits:
        return CheckOutcome(
            status=ResultStatus.PASS,
            confidence=check_config.get("default_confidence", 0.9),
            observed="0 overlapping-speech events detected",
            expected=f"< {threshold + 1} events",
            rationale="No crosstalk/overlap markers found in the transcript.",
            evidence=None,
            timestamp_seconds=None,
        )

    worst = hits[0]
    status = ResultStatus.FAIL if len(hits) >= threshold else ResultStatus.PASS
    observed = f"{len(hits)} overlapping-speech event(s) detected, first at {int(worst.start_seconds // 60):02d}:{int(worst.start_seconds % 60):02d}"
    evidence = EvidenceData(
        source_type="transcript",
        transcript_segment_id=worst.id,
        speaker=worst.speaker,
        start_seconds=worst.start_seconds,
        end_seconds=worst.end_seconds,
        excerpt=worst.text,
        expected_value=f"< {threshold + 1} events",
        observed_value=observed,
    )
    return CheckOutcome(
        status=status,
        confidence=check_config.get("default_confidence", 0.9),
        observed=observed,
        expected=f"< {threshold + 1} events",
        rationale="Coaching note — overlapping speech can indicate the agent talking over the customer.",
        evidence=evidence,
        timestamp_seconds=worst.start_seconds,
    )


def _evaluate_rapport(check_config: dict, context: EvaluationContext) -> CheckOutcome:
    """Customer talk-time share as a crude, honestly-limited rapport
    proxy: a call where the customer barely speaks is a real (if weak)
    signal worth a coaching look, computed from actual segment durations
    — not an invented sentiment score."""
    min_customer_share = check_config.get("min_customer_share", 0.08)
    agent_time = sum(s.end_seconds - s.start_seconds for s in context.segments_by("AGENT"))
    customer_time = sum(s.end_seconds - s.start_seconds for s in context.segments_by("CUSTOMER"))
    total = agent_time + customer_time

    if total <= 0:
        return CheckOutcome(
            status=ResultStatus.PASS,
            confidence=check_config.get("default_confidence", 0.85),
            observed=None,
            expected=None,
            rationale="No agent/customer speech segments to measure talk-time share from.",
            evidence=None,
            timestamp_seconds=None,
        )

    share = customer_time / total
    status = ResultStatus.PASS if share >= min_customer_share else ResultStatus.FAIL
    observed = f"Customer spoke {share:.0%} of measured talk-time"
    expected = f">= {min_customer_share:.0%} customer talk-time share"
    return CheckOutcome(
        status=status,
        confidence=check_config.get("default_confidence", 0.85),
        observed=observed,
        expected=expected,
        rationale=(
            "Coaching note — a very one-sided call can indicate the agent isn't inviting the customer in."
            if status == ResultStatus.FAIL
            else "Talk-time share within the expected range for a two-way conversation."
        ),
        evidence=None,
        timestamp_seconds=None,
    )


def _evaluate_objection_handling(check_config: dict, context: EvaluationContext) -> CheckOutcome:
    """Looks for objection-language from the customer and whether the
    agent responded afterward. No objection language at all is a genuine
    PASS (nothing to handle), not a fabricated default."""
    customer_turns = [(i, s) for i, s in enumerate(context.segments) if s.speaker == "CUSTOMER"]
    objection_turns = [(i, s) for i, s in customer_turns if _OBJECTION_RE.search(s.text)]

    if not objection_turns:
        return CheckOutcome(
            status=ResultStatus.PASS,
            confidence=check_config.get("default_confidence", 0.86),
            observed=None,
            expected=None,
            rationale="No objection-language detected from the customer — nothing for the agent to handle.",
            evidence=None,
            timestamp_seconds=None,
        )

    idx, seg = objection_turns[0]
    followed_up = any(s.speaker == "AGENT" and s.start_seconds > seg.start_seconds for s in context.segments[idx + 1 :])
    status = ResultStatus.PASS if followed_up else ResultStatus.FAIL
    observed = f'Customer objection at {int(seg.start_seconds // 60):02d}:{int(seg.start_seconds % 60):02d}: "{seg.text}"'
    expected = "Agent responds to the objection before the call moves on"

    evidence = EvidenceData(
        source_type="transcript",
        transcript_segment_id=seg.id,
        speaker=seg.speaker,
        start_seconds=seg.start_seconds,
        end_seconds=seg.end_seconds,
        excerpt=seg.text,
        expected_value=expected,
        observed_value=observed,
    )
    return CheckOutcome(
        status=status,
        confidence=check_config.get("default_confidence", 0.86),
        observed=observed,
        expected=expected,
        rationale=(
            "Agent responded to the customer's objection." if followed_up else "No agent turn followed the customer's objection before the transcript ends."
        ),
        evidence=evidence,
        timestamp_seconds=seg.start_seconds,
    )


_METRIC_EVALUATORS = {
    "dead_air": _evaluate_dead_air,
    "interruptions": _evaluate_interruptions,
    "rapport": _evaluate_rapport,
    "objection_handling": _evaluate_objection_handling,
}


def evaluate_behaviour(check_config: dict, context: EvaluationContext) -> CheckOutcome:
    metric = check_config.get("metric")
    evaluator = _METRIC_EVALUATORS.get(metric)
    if evaluator is None:
        return not_evaluable_outcome(
            f"No behavioural metric configured for this check (got {metric!r}) — nothing to compute from the transcript."
        )
    return evaluator(check_config, context)
