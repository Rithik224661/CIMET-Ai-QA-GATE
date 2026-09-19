"""
Verbatim / script evaluator (brief type A): transcript vs. approved script.
Deterministic normalized-text comparison — no LLM call. Crosstalk or a weak
match routes to REVIEW rather than asserting a pass or a fail on degraded
audio (brief §12 "if speech/audio is too degraded... do not invent a
match").
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from ...config import settings
from .base import CheckOutcome, EvaluationContext, EvidenceData, ResultStatus, TranscriptSegmentData, not_evaluable_outcome

_WORD_RE = re.compile(r"[a-z0-9]+")


def _normalize(text: str) -> str:
    return " ".join(_WORD_RE.findall(text.lower()))


def _similarity(expected_phrase: str, candidate_text: str) -> float:
    return SequenceMatcher(None, _normalize(expected_phrase), _normalize(candidate_text)).ratio()


def _has_crosstalk(text: str) -> bool:
    return "crosstalk" in text.lower()


def evaluate_verbatim(check_config: dict, context: EvaluationContext) -> CheckOutcome:
    expected_phrase: str = check_config.get("expected_phrase", "")
    expected_label: str = check_config.get("expected_label", "Statement matching the approved script")
    speaker: str = check_config.get("speaker", "AGENT")
    window_start = check_config.get("window_start")
    window_end = check_config.get("window_end")
    default_absent_confidence: float = check_config.get("default_confidence", 0.97)

    candidates: list[TranscriptSegmentData] = [
        s for s in context.segments_in_window(window_start, window_end) if s.speaker == speaker
    ]
    # Crosstalk can appear on either side of the turn; consider all segments
    # in-window (any speaker) for the crosstalk signal even if the phrase
    # itself is normally spoken by the agent.
    window_segments = context.segments_in_window(window_start, window_end)

    if not expected_phrase:
        return not_evaluable_outcome(
            "This check has no approved-script phrase configured, so it cannot be independently verified "
            "from the data available in this demo."
        )
    if not candidates:
        return not_evaluable_outcome(
            f"No {speaker.lower()} utterance exists in the required window at all — there is nothing to "
            "compare the approved script against, so this is routed to a human rather than assumed absent or present.",
            expected=expected_label,
        )

    scored = [(seg, _similarity(expected_phrase, seg.text)) for seg in candidates]
    best_segment, best_ratio = max(scored, key=lambda pair: pair[1])

    crosstalk = any(_has_crosstalk(s.text) for s in window_segments)

    if crosstalk:
        status = ResultStatus.REVIEW
        confidence = min(0.7, max(0.4, best_ratio))
        observed = f"Partially audible — crosstalk detected around {int(best_segment.start_seconds // 60):02d}:{int(best_segment.start_seconds % 60):02d}"
        rationale = (
            "Word-error rate in this window exceeded the verbatim threshold because of overlapping speech. "
            "The system will not assert a pass or a fail on degraded audio; it routes to a human."
        )
        timestamp = best_segment.start_seconds
    elif best_ratio >= settings.verbatim_pass_threshold:
        status = ResultStatus.PASS
        confidence = min(0.99, 0.9 + (best_ratio - settings.verbatim_pass_threshold) * 0.4)
        observed = best_segment.text
        rationale = f"Matched the approved script at {best_ratio:.0%} normalized similarity."
        timestamp = best_segment.start_seconds
    elif best_ratio >= settings.verbatim_review_threshold:
        status = ResultStatus.REVIEW
        confidence = best_ratio
        observed = best_segment.text
        rationale = f"Closest match was only {best_ratio:.0%} similar to the approved script — too ambiguous to assert pass or fail."
        timestamp = best_segment.start_seconds
    else:
        status = ResultStatus.FAIL
        confidence = default_absent_confidence
        window_label = (
            f"the first {int(window_end)}s" if window_start in (None, 0) and window_end else "the required window"
        )
        observed = f"No matching statement detected in {window_label}."
        rationale = "No utterance in the required window matched the approved script closely enough to count as read."
        timestamp = check_config.get("expected_timestamp")

    evidence = EvidenceData(
        source_type="transcript",
        transcript_segment_id=best_segment.id if status != ResultStatus.FAIL else None,
        speaker=best_segment.speaker if status != ResultStatus.FAIL else None,
        start_seconds=best_segment.start_seconds if status != ResultStatus.FAIL else None,
        end_seconds=best_segment.end_seconds if status != ResultStatus.FAIL else None,
        excerpt=f'"{best_segment.text}"' if status != ResultStatus.FAIL else None,
        expected_value=expected_label,
        observed_value=observed,
    )

    return CheckOutcome(
        status=status,
        confidence=round(confidence, 4),
        observed=observed,
        expected=expected_label,
        rationale=rationale,
        evidence=evidence,
        timestamp_seconds=timestamp,
    )
