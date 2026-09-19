"""
Factual match evaluator (brief type B): transcript-derived value vs. CRM /
retailer plan / rate-card fields. Structured extraction, never a prose
answer (brief §14) — the regex pull-out and the comparison are both
deterministic; only the *source of truth* (crm_snapshot) is authoritative,
never an LLM's inference (brief §13 "Do not let LLM inference replace
authoritative structured data").

Three evaluation modes, selected by `check_config`:

- **value comparison** (`field` + `pattern` + `kind` in {numeric,email,text}):
  extract a value, normalize, compare to `crm_snapshot[field]` with
  `tolerance`. PASS/FAIL on a clean match/mismatch; REVIEW when nothing
  could be reliably extracted (never assumed correct).
- **presence** (`kind: "presence"`): the check is "was X confirmed/
  declared", not a value comparison — e.g. "Account holder confirmed",
  "Life support declared". A configured pattern is searched for; found ->
  PASS. Not found -> genuinely NOT_EVALUABLE (a human needs to confirm),
  never FAIL — absence of a keyword match is not proof the confirmation
  didn't happen, and this check type must never manufacture a false
  critical failure on phrasing alone.
- **conditional not-applicable** (`skip_if_absent: true`, e.g. "Gift card
  value"): when the CRM source of truth itself says nothing applies
  (no gift card on this plan), PASS is the CORRECT answer — there is
  nothing to mismatch — not a fabricated default. Falls through to normal
  value comparison when the field IS present.

A check with no `field`/`pattern`/`kind` configured at all is NOT a silent
PASS (brief §3: "if an input genuinely does not exist, do not return
PASS") — it is `not_evaluable_outcome`. In this build every check in the
20-check catalogue has one of the three modes above configured; this path
is a defensive fallback, not a relied-upon default.
"""

from __future__ import annotations

import re

from .base import CheckOutcome, EvaluationContext, EvidenceData, ResultStatus, not_evaluable_outcome


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


def _candidates(check_config: dict, context: EvaluationContext) -> list:
    speaker = check_config.get("speaker", "AGENT")
    window_start = check_config.get("window_start")
    window_end = check_config.get("window_end")
    in_window = context.segments_in_window(window_start, window_end)
    if speaker == "ANY":
        return in_window
    return [s for s in in_window if s.speaker == speaker]


def _evaluate_presence(check_config: dict, context: EvaluationContext) -> CheckOutcome:
    pattern = check_config.get("pattern")
    expected_label = check_config.get("expected_label", "Confirmed in the transcript")
    confidence = check_config.get("extraction_confidence", 0.97)
    regex = re.compile(pattern, re.IGNORECASE) if pattern else None

    if regex is not None:
        for seg in _candidates(check_config, context):
            if regex.search(seg.text):
                evidence = EvidenceData(
                    source_type="transcript",
                    transcript_segment_id=seg.id,
                    speaker=seg.speaker,
                    start_seconds=seg.start_seconds,
                    end_seconds=seg.end_seconds,
                    excerpt=f'"{seg.text}"',
                    expected_value=expected_label,
                    observed_value=seg.text,
                )
                return CheckOutcome(
                    status=ResultStatus.PASS,
                    confidence=confidence,
                    observed=seg.text,
                    expected=expected_label,
                    rationale=f"Matched the required confirmation at {int(seg.start_seconds // 60):02d}:{int(seg.start_seconds % 60):02d}.",
                    evidence=evidence,
                    timestamp_seconds=seg.start_seconds,
                )

    return not_evaluable_outcome(
        "No utterance in the transcript clearly confirmed this — absence of a keyword match isn't proof it "
        "didn't happen, so this is routed to a human rather than failed or assumed on phrasing alone.",
        expected=expected_label,
    )


def evaluate_factual(check_config: dict, context: EvaluationContext) -> CheckOutcome:
    if check_config.get("kind") == "presence":
        return _evaluate_presence(check_config, context)

    field = check_config.get("field")
    pattern = check_config.get("pattern")
    kind = check_config.get("kind", "text")
    unit = check_config.get("unit", "")
    tolerance = check_config.get("tolerance", 0.0)
    extraction_confidence = check_config.get("extraction_confidence", 0.97)

    expected_raw = context.crm_snapshot.get(field) if field else None

    if check_config.get("skip_if_absent") and not expected_raw:
        return CheckOutcome(
            status=ResultStatus.PASS,
            confidence=check_config.get("default_confidence", 0.97),
            observed=None,
            expected="Not applicable to this plan",
            rationale=f"{check_config.get('source_label', field)} has no value for this lead — nothing was offered, so there is nothing to verify against the transcript.",
            evidence=None,
            timestamp_seconds=None,
        )

    if not field or not pattern or expected_raw is None:
        return not_evaluable_outcome(
            "This check has no source-of-truth field or extraction pattern configured, so it cannot be "
            "independently verified from the data available in this demo."
        )

    candidates = _candidates(check_config, context)
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
        f"Value extracted from the transcript at {int(match_segment.start_seconds // 60):02d}:{int(match_segment.start_seconds % 60):02d} "
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
