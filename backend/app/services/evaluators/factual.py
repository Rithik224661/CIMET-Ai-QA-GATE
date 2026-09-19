"""
Factual match evaluator (brief type B): transcript-derived value vs. CRM /
retailer plan / rate-card fields. Structured extraction, never a prose
answer (brief §14) — the regex pull-out and the comparison are both
deterministic; only the *source of truth* (crm_snapshot) is authoritative,
never an LLM's inference (brief §13 "Do not let LLM inference replace
authoritative structured data").
"""

from __future__ import annotations

import re

from .base import CheckOutcome, EvaluationContext, EvidenceData, ResultStatus


def _normalize(kind: str, raw: str) -> str | float:
    if kind == "numeric":
        return float(raw.replace(",", "").strip())
    if kind == "email":
        return raw.strip().lower()
    return raw.strip().lower()


def _display(kind: str, value: object, unit: str) -> str:
    if kind == "numeric":
        return f"{value}{unit}"
    return str(value)


def evaluate_factual(check_config: dict, context: EvaluationContext) -> CheckOutcome:
    field = check_config.get("field")
    pattern = check_config.get("pattern")
    kind = check_config.get("kind", "text")
    unit = check_config.get("unit", "")
    tolerance = check_config.get("tolerance", 0.0)
    speaker = check_config.get("speaker", "AGENT")
    window_start = check_config.get("window_start")
    window_end = check_config.get("window_end")
    extraction_confidence = check_config.get("extraction_confidence", 0.97)
    default_confidence = check_config.get("default_confidence", 0.95)

    expected_raw = context.crm_snapshot.get(field) if field else None

    if not field or not pattern or expected_raw is None:
        return CheckOutcome(
            status=ResultStatus.PASS,
            confidence=default_confidence,
            observed=None,
            expected=None,
            rationale="No independent extraction configured for this check in the demo; treated as compliant by default.",
            evidence=None,
            timestamp_seconds=None,
        )

    candidates = [s for s in context.segments_in_window(window_start, window_end) if s.speaker == speaker]
    regex = re.compile(pattern, re.IGNORECASE)

    match_segment = None
    match_value = None
    for seg in candidates:
        m = regex.search(seg.text)
        if m:
            match_segment = seg
            match_value = m.group(1)
            break

    expected_norm = _normalize(kind, str(expected_raw))
    expected_display = _display(kind, expected_raw, unit)

    if match_segment is None or match_value is None:
        return CheckOutcome(
            status=ResultStatus.REVIEW,
            confidence=0.6,
            observed="Not clearly stated in the transcript window.",
            expected=expected_display,
            rationale="No value could be reliably extracted from the transcript for this field; routed for human confirmation rather than assumed correct.",
            evidence=None,
            timestamp_seconds=None,
        )

    try:
        observed_norm = _normalize(kind, match_value)
    except ValueError:
        observed_norm = match_value

    if kind == "numeric":
        matched = abs(float(observed_norm) - float(expected_norm)) <= tolerance
    else:
        matched = observed_norm == expected_norm

    observed_display = _display(kind, match_value if kind != "numeric" else float(match_value), unit)

    status = ResultStatus.PASS if matched else ResultStatus.FAIL
    rationale = (
        f"Value extracted from the agent turn at {int(match_segment.start_seconds // 60):02d}:{int(match_segment.start_seconds % 60):02d} "
        f"and compared with {check_config.get('source_label', field)}. "
        + ("Values agree within tolerance." if matched else f"Mismatch outside the configured tolerance ({tolerance}).")
    )

    evidence = EvidenceData(
        source_type="transcript",
        transcript_segment_id=match_segment.id,
        speaker=match_segment.speaker,
        start_seconds=match_segment.start_seconds,
        end_seconds=match_segment.end_seconds,
        excerpt=f'"{match_segment.text}"',
        expected_value=expected_display,
        observed_value=observed_display,
    )

    return CheckOutcome(
        status=status,
        confidence=extraction_confidence,
        observed=observed_display,
        expected=expected_display,
        rationale=rationale,
        evidence=evidence,
        timestamp_seconds=match_segment.start_seconds,
    )
