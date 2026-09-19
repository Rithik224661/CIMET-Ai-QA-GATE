"""Unit tests for the three deterministic check evaluators. Every case
asserts on structured output (status, observed, expected, confidence) —
never "it returned some text", per the brief's "no evaluator may return
only natural language" rule."""

from __future__ import annotations

from app.services.evaluators.base import EvaluationContext, TranscriptSegmentData
from app.services.evaluators.behaviour import evaluate_behaviour
from app.services.evaluators.factual import evaluate_factual
from app.services.evaluators.verbatim import evaluate_verbatim

DISCLAIMER = "This call is being recorded for quality and compliance purposes"


def seg(id_, speaker, start, text, end=None):
    return TranscriptSegmentData(id=id_, speaker=speaker, start_seconds=start, end_seconds=end or start + 6, text=text)


def ctx(segments, duration=1800, crm=None):
    return EvaluationContext(lead_id="test", duration_sec=duration, segments=segments, crm_snapshot=crm or {})


# ---- verbatim ----


def test_verbatim_passes_on_a_clean_match():
    outcome = evaluate_verbatim(
        {"expected_phrase": DISCLAIMER, "window_start": 0, "window_end": 60},
        ctx([seg(1, "AGENT", 12, DISCLAIMER + ".")]),
    )
    assert outcome.status == "PASS"
    assert outcome.confidence >= 0.9


def test_verbatim_fails_when_absent_and_does_not_invent_a_match():
    outcome = evaluate_verbatim(
        {"expected_phrase": DISCLAIMER, "window_start": 0, "window_end": 60, "default_confidence": 0.97},
        ctx([seg(1, "AGENT", 4, "Hi, am I speaking with the account holder?")]),
    )
    assert outcome.status == "FAIL"
    assert outcome.confidence == 0.97
    assert outcome.evidence.transcript_segment_id is None, "a FAIL must not cite a transcript span as if it matched"


def test_verbatim_routes_crosstalk_to_review_never_asserts_pass_or_fail():
    outcome = evaluate_verbatim(
        {"expected_phrase": "Default Market Offer comparison in full", "window_start": 500, "window_end": 700},
        ctx(
            [
                seg(1, "AGENT", 588, "The Default Market Offer for your [crosstalk] compared to the plan we discussed"),
                seg(2, "CUSTOMER", 606, "Sorry, say that again."),
            ]
        ),
    )
    assert outcome.status == "REVIEW"
    assert outcome.confidence < 0.85, "a degraded-audio REVIEW must land below the confidence floor so the gate routes it to QA"


def test_verbatim_with_no_config_is_a_documented_pass_through():
    outcome = evaluate_verbatim({}, ctx([seg(1, "AGENT", 0, "anything")]))
    assert outcome.status == "PASS"
    assert outcome.evidence is None


# ---- factual ----

RATE_CONFIG = {
    "field": "peak_rate_cents", "pattern": r"(\d+\.?\d*)\s*cents?", "kind": "numeric", "unit": "c/kWh",
    "tolerance": 0.0, "window_start": 700, "window_end": 1000, "extraction_confidence": 0.98,
}


def test_factual_passes_when_extracted_value_matches_source_of_truth():
    outcome = evaluate_factual(RATE_CONFIG, ctx([seg(1, "AGENT", 842, "Peak is 31.9 cents per kilowatt hour.")], crm={"peak_rate_cents": 31.9}))
    assert outcome.status == "PASS"
    assert outcome.observed == "31.9c/kWh"
    assert outcome.expected == "31.9c/kWh"


def test_factual_fails_on_mismatch_and_shows_both_values():
    outcome = evaluate_factual(RATE_CONFIG, ctx([seg(1, "AGENT", 842, "Peak is 28.6 cents per kilowatt hour.")], crm={"peak_rate_cents": 31.9}))
    assert outcome.status == "FAIL"
    assert outcome.observed == "28.6c/kWh"
    assert outcome.expected == "31.9c/kWh"
    assert outcome.evidence.observed_value == "28.6c/kWh"
    assert outcome.evidence.expected_value == "31.9c/kWh"


def test_factual_email_mismatch_is_case_and_whitespace_normalized_before_compare():
    config = {"field": "email", "pattern": r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", "kind": "email", "extraction_confidence": 0.96}
    outcome = evaluate_factual(config, ctx([seg(1, "AGENT", 1330, "Reading back:  J.Smith@Gmail.com ")], crm={"email": "j.smith@gmail.com"}))
    assert outcome.status == "PASS", "normalization must treat case/whitespace differences as equal, not a mismatch"


def test_factual_reviews_rather_than_assumes_when_nothing_extractable():
    outcome = evaluate_factual(RATE_CONFIG, ctx([seg(1, "AGENT", 842, "We'll sort the rate out later.")], crm={"peak_rate_cents": 31.9}))
    assert outcome.status == "REVIEW"
    assert outcome.confidence < 0.85


def test_factual_with_no_field_configured_is_a_documented_pass_through():
    outcome = evaluate_factual({}, ctx([seg(1, "AGENT", 0, "anything")]))
    assert outcome.status == "PASS"
    assert outcome.evidence is None


def test_factual_rate_tolerance_is_configurable_and_honored():
    config = {**RATE_CONFIG, "tolerance": 0.5}
    outcome = evaluate_factual(config, ctx([seg(1, "AGENT", 842, "Peak is 31.95 cents per kilowatt hour.")], crm={"peak_rate_cents": 31.9}))
    assert outcome.status == "PASS", "a 0.05c difference is within a configured 0.5c tolerance"


# ---- behaviour ----


def test_dead_air_fails_over_threshold():
    outcome = evaluate_behaviour(
        {"metric": "dead_air", "threshold_seconds": 30}, ctx([seg(1, "SYSTEM", 1110, "[silence 18:30 → 19:17 · 47s dead air]")])
    )
    assert outcome.status == "FAIL"
    assert "47s" in outcome.observed


def test_dead_air_passes_under_threshold():
    outcome = evaluate_behaviour(
        {"metric": "dead_air", "threshold_seconds": 30}, ctx([seg(1, "SYSTEM", 1110, "[silence 18:30 → 18:42 · 12s dead air]")])
    )
    assert outcome.status == "PASS"


def test_dead_air_passes_when_no_silence_segment_exists():
    outcome = evaluate_behaviour({"metric": "dead_air", "threshold_seconds": 30}, ctx([seg(1, "AGENT", 10, "Hello there.")]))
    assert outcome.status == "PASS"


def test_behaviour_never_returns_a_fabricated_critical_signal():
    outcome = evaluate_behaviour({"metric": "rapport"}, ctx([seg(1, "AGENT", 10, "Hello there.")]))
    assert outcome.status == "PASS"
    assert outcome.evidence is None
