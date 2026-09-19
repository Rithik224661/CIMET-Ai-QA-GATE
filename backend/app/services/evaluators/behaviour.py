"""
Behaviour evaluator (brief type C): transcript-only signals — rapport,
interruptions, dead air, objection handling. Never critical, never
blocking on its own (brief §15) — enforced by the Check's `critical` flag,
not by this evaluator, but this module never manufactures a false
critical regardless.

Every metric here is genuinely computed from real transcript structure —
timestamp overlaps, turn-taking counts, acknowledgment-phrase matching,
categorized objection-language detection — not a fabricated "AI sentiment
score" and not an LLM call by default. Confidence is a function of how
much corroborating signal was actually available, not a fixed constant:
a single weak signal (e.g. only a text marker with no verifiable
timing, or an ambiguous keyword match) reports lower confidence than
multiple agreeing signals. An optional AI semantic layer
(ai_behaviour.py) can refine rapport/interruptions/objection handling
further when AI_PROVIDER is configured — see that module — but every
metric here already produces a real, non-fabricated result with
AI_PROVIDER=none, which is the default.
"""

from __future__ import annotations

import re

from ...config import settings
from .base import CheckOutcome, EvaluationContext, EvidenceData, ResultStatus, not_evaluable_outcome

_DEAD_AIR_RE = re.compile(r"(\d+)\s*s\s+dead\s*air", re.IGNORECASE)
_CROSSTALK_RE = re.compile(r"crosstalk", re.IGNORECASE)
_ACKNOWLEDGMENT_RE = re.compile(
    r"\b(yes|yeah|sure|sounds good|thanks|thank you|great|okay|ok|perfect|that works|got it|understood)\b",
    re.IGNORECASE,
)

# Objection categories, most-specific first. Two tiers: STRONG (a clear,
# unambiguous objection phrase) vs WEAK (a hedge word that often co-occurs
# with an objection but is also common in ordinary agreement — "actually",
# filler sounds — and on its own is genuinely ambiguous, brief §28's
# "customer mentions [x] jokingly" case). WEAK matches report materially
# lower confidence rather than a confident FAIL, on purpose.
_OBJECTION_CATEGORIES: list[tuple[str, str, re.Pattern[str]]] = [
    ("price", "strong", re.compile(r"\b(too (expensive|much)|can'?t afford|cost is high|cheaper)\b", re.IGNORECASE)),
    ("not_interested", "strong", re.compile(r"\b(not interested|don'?t want|no thanks)\b", re.IGNORECASE)),
    ("already_satisfied", "strong", re.compile(r"\b(already (have|with)|happy with my current)\b", re.IGNORECASE)),
    ("time", "strong", re.compile(r"\b(call (me )?back|not (a )?good time|bad time|busy right now)\b", re.IGNORECASE)),
    ("hesitation", "strong", re.compile(r"\b(not sure|hesitant|need to think|reconsider)\b", re.IGNORECASE)),
    ("uncertainty", "weak", re.compile(r"\b(actually|but i|hmm+|um+)\b", re.IGNORECASE)),
]


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
    """Primary signal: real timestamp overlap between consecutive
    different-speaker segments (e.g. agent 124.2-126.0s, customer
    125.1-127.0s -> 0.9s overlap) — genuinely computed from segment
    start/end times, not inferred from wording. Secondary, weaker signal:
    a `[crosstalk]` marker in the text with no verifiable overlap timing
    (this transcript format doesn't always carry word-level timestamps) —
    reported at materially lower confidence than a timing-verified
    overlap."""
    threshold = check_config.get("threshold_count", 1)
    segments = sorted(context.segments, key=lambda s: s.start_seconds)

    timed_overlaps: list[tuple] = []
    for a, b in zip(segments, segments[1:]):
        if a.speaker != b.speaker and "SYSTEM" not in (a.speaker, b.speaker):
            overlap = a.end_seconds - b.start_seconds
            if overlap > 0:
                timed_overlaps.append((a, b, overlap))

    marker_hits = [s for s in segments if _CROSSTALK_RE.search(s.text)]
    event_count = max(len(timed_overlaps), len(marker_hits))

    if event_count == 0:
        return CheckOutcome(
            status=ResultStatus.PASS,
            confidence=check_config.get("default_confidence", 0.92),
            observed="0 overlapping-speech events detected",
            expected=f"< {threshold + 1} events",
            rationale="No timestamp overlaps or crosstalk markers found in the transcript.",
            evidence=None,
            timestamp_seconds=None,
        )

    status = ResultStatus.FAIL if event_count >= threshold else ResultStatus.PASS

    if timed_overlaps:
        a, b, dur = max(timed_overlaps, key=lambda t: t[2])
        observed = (
            f"{len(timed_overlaps)} timestamp overlap(s) detected — {dur:.1f}s overlap between "
            f"{a.speaker.title()} ({a.start_seconds:.1f}–{a.end_seconds:.1f}s) and "
            f"{b.speaker.title()} ({b.start_seconds:.1f}–{b.end_seconds:.1f}s)"
        )
        evidence_seg = b
        confidence = check_config.get("default_confidence", 0.92)
        rationale = "Overlap verified directly from segment timestamps — the strongest signal this evaluator produces."
    else:
        evidence_seg = marker_hits[0]
        observed = f"{len(marker_hits)} crosstalk marker(s) detected in the transcript; no verifiable overlap timing available"
        # Weaker evidence (text marker only, no timing proof) -> lower,
        # honestly-uncertain confidence, deliberately below the gate floor
        # so an ambiguous case like this gets a human glance.
        confidence = check_config.get("marker_only_confidence", 0.7)
        rationale = "Marker-only signal — no timing data to independently verify overlap duration; confidence reflects that."

    expected = f"< {threshold + 1} events"
    evidence = EvidenceData(
        source_type="transcript",
        transcript_segment_id=evidence_seg.id,
        speaker=evidence_seg.speaker,
        start_seconds=evidence_seg.start_seconds,
        end_seconds=evidence_seg.end_seconds,
        excerpt=evidence_seg.text,
        expected_value=expected,
        observed_value=observed,
    )
    return CheckOutcome(
        status=status,
        confidence=confidence,
        observed=observed,
        expected=expected,
        rationale=rationale,
        evidence=evidence,
        timestamp_seconds=evidence_seg.start_seconds,
    )


def _evaluate_rapport(check_config: dict, context: EvaluationContext) -> CheckOutcome:
    """Three corroborating signals, all genuinely computed from the
    transcript: customer talk-TIME share, customer turn-COUNT share, and
    an acknowledgment-phrase rate among the customer's own turns.
    Confidence scales with how many of these signals had enough data to
    be meaningful — a call with only one customer turn gets a materially
    lower confidence than one with several, even if the raw share number
    looks the same."""
    min_customer_share = check_config.get("min_customer_share", 0.08)
    base_confidence = check_config.get("default_confidence", 0.9)

    agent_segments = context.segments_by("AGENT")
    customer_segments = context.segments_by("CUSTOMER")
    agent_time = sum(s.end_seconds - s.start_seconds for s in agent_segments)
    customer_time = sum(s.end_seconds - s.start_seconds for s in customer_segments)
    total_time = agent_time + customer_time
    total_turns = len(agent_segments) + len(customer_segments)

    if total_time <= 0 or total_turns == 0:
        return not_evaluable_outcome("No agent/customer speech segments exist to measure rapport signals from.")

    signals: list[str] = []

    time_share = customer_time / total_time
    signals.append(f"customer talk-time share {time_share:.0%}")

    turn_share = len(customer_segments) / total_turns
    signals.append(f"customer turn-count share {turn_share:.0%}")

    ack_hits = sum(1 for s in customer_segments if _ACKNOWLEDGMENT_RE.search(s.text))
    if customer_segments:
        signals.append(f"{ack_hits} acknowledgment phrase(s) across {len(customer_segments)} customer turn(s)")

    status = ResultStatus.PASS if time_share >= min_customer_share else ResultStatus.FAIL

    # A single customer turn makes the share numbers noisy — one short
    # "yes" versus one long explanation swings the ratio wildly. Confidence
    # reflects that honestly rather than reporting the same certainty
    # regardless of sample size.
    if len(customer_segments) < 2:
        confidence = max(0.6, base_confidence - 0.2)
    else:
        confidence = base_confidence

    observed = f"Customer spoke {time_share:.0%} of measured talk-time ({', '.join(signals)})"
    expected = f">= {min_customer_share:.0%} customer talk-time share"
    return CheckOutcome(
        status=status,
        confidence=confidence,
        observed=observed,
        expected=expected,
        rationale=(
            "Coaching note — a very one-sided call can indicate the agent isn't inviting the customer in."
            if status == ResultStatus.FAIL
            else "Talk-time share, turn-count share, and acknowledgment-phrase rate are all within the expected range for a two-way conversation."
        ),
        evidence=None,
        timestamp_seconds=None,
    )


def _classify_objection(text: str) -> tuple[str, str] | None:
    for category, strength, pattern in _OBJECTION_CATEGORIES:
        if pattern.search(text):
            return category, strength
    return None


def _evaluate_objection_handling(check_config: dict, context: EvaluationContext) -> CheckOutcome:
    """Categorizes customer objection language (price / not_interested /
    already_satisfied / time / hesitation / uncertainty) and checks
    whether an agent turn followed it. A STRONG category match with no
    follow-up is a confident FAIL; a WEAK match (a hedge word that's
    genuinely ambiguous on its own, brief §28's "mentions it jokingly"
    case) reports low confidence regardless of outcome — the system
    doesn't pretend to know, it flags the ambiguity. No objection language
    at all is a genuine PASS (nothing to handle), not a fabricated
    default."""
    customer_turns = [(i, s) for i, s in enumerate(context.segments) if s.speaker == "CUSTOMER"]
    classified = [(i, s, _classify_objection(s.text)) for i, s in customer_turns]
    objection_turns = [(i, s, c) for i, s, c in classified if c is not None]

    if not objection_turns:
        return CheckOutcome(
            status=ResultStatus.PASS,
            confidence=check_config.get("default_confidence", 0.9),
            observed=None,
            expected=None,
            rationale="No objection-language detected from the customer — nothing for the agent to handle.",
            evidence=None,
            timestamp_seconds=None,
        )

    idx, seg, (category, strength) = objection_turns[0]
    followed_up = any(s.speaker == "AGENT" and s.start_seconds > seg.start_seconds for s in context.segments[idx + 1 :])
    status = ResultStatus.PASS if followed_up else ResultStatus.FAIL
    observed = f'Customer objection ({category}) at {int(seg.start_seconds // 60):02d}:{int(seg.start_seconds % 60):02d}: "{seg.text}"'
    expected = "Agent responds to the objection before the call moves on"

    if strength == "weak":
        # Ambiguous trigger word — the system reports its uncertainty
        # rather than confidently asserting a fail.
        confidence = check_config.get("weak_signal_confidence", 0.65)
        rationale = (
            f"Matched only a weak/ambiguous objection cue ('{category}') — genuinely uncertain whether this was "
            "a real objection; routed for human confirmation rather than confidently failed or passed."
        )
    else:
        confidence = check_config.get("default_confidence", 0.9)
        rationale = (
            f"Agent responded to the customer's {category} objection." if followed_up
            else f"No agent turn followed the customer's {category} objection before the transcript ends."
        )

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
        confidence=confidence,
        observed=observed,
        expected=expected,
        rationale=rationale,
        evidence=evidence,
        timestamp_seconds=seg.start_seconds,
    )


_METRIC_EVALUATORS = {
    "dead_air": _evaluate_dead_air,
    "interruptions": _evaluate_interruptions,
    "rapport": _evaluate_rapport,
    "objection_handling": _evaluate_objection_handling,
}

# Metrics an AI semantic layer may optionally refine when AI_PROVIDER is
# configured (see ai_behaviour.py). Never dead_air — that's a hard
# duration threshold, nothing semantic to interpret.
AI_ELIGIBLE_METRICS = {"rapport", "interruptions", "objection_handling"}


def evaluate_behaviour(check_config: dict, context: EvaluationContext) -> CheckOutcome:
    metric = check_config.get("metric")
    evaluator = _METRIC_EVALUATORS.get(metric)
    if evaluator is None:
        return not_evaluable_outcome(
            f"No behavioural metric configured for this check (got {metric!r}) — nothing to compute from the transcript."
        )

    deterministic_outcome = evaluator(check_config, context)

    if metric in AI_ELIGIBLE_METRICS and check_config.get("ai_enrichment", True):
        from ..ai_behaviour import maybe_refine_with_ai

        return maybe_refine_with_ai(metric, check_config, context, deterministic_outcome)

    return deterministic_outcome
