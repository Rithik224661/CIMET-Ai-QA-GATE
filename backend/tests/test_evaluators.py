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


def test_verbatim_with_no_script_configured_is_not_evaluable_never_a_silent_pass():
    """A misconfigured/unwired check must never default to PASS (brief §3)
    — it's REVIEW at a confidence that always trips the gate floor."""
    outcome = evaluate_verbatim({}, ctx([seg(1, "AGENT", 0, "anything")]))
    assert outcome.status == "REVIEW"
    assert outcome.confidence < 0.85


def test_verbatim_with_no_candidate_segments_at_all_is_not_evaluable():
    """The expected speaker never appears in the required window at all —
    genuinely nothing to compare against, so this must not be silently
    treated as either a pass or a confident fail."""
    outcome = evaluate_verbatim(
        {"expected_phrase": DISCLAIMER, "window_start": 0, "window_end": 60},
        ctx([seg(1, "CUSTOMER", 5, "Hello?")]),  # only a CUSTOMER turn; AGENT is the configured speaker
    )
    assert outcome.status == "REVIEW"
    assert outcome.confidence < 0.85


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


def test_factual_with_no_field_configured_is_not_evaluable_never_a_silent_pass():
    outcome = evaluate_factual({}, ctx([seg(1, "AGENT", 0, "anything")]))
    assert outcome.status == "REVIEW"
    assert outcome.confidence < 0.85


def test_factual_rate_tolerance_is_configurable_and_honored():
    config = {**RATE_CONFIG, "tolerance": 0.5}
    outcome = evaluate_factual(config, ctx([seg(1, "AGENT", 842, "Peak is 31.95 cents per kilowatt hour.")], crm={"peak_rate_cents": 31.9}))
    assert outcome.status == "PASS", "a 0.05c difference is within a configured 0.5c tolerance"


# ---- factual: presence mode ----


def test_presence_passes_when_the_confirmation_is_found():
    config = {"kind": "presence", "pattern": r"that'?s me", "speaker": "CUSTOMER", "expected_label": "Account holder confirmed"}
    outcome = evaluate_factual(config, ctx([seg(1, "CUSTOMER", 150, "Yes, that's me on the account.")]))
    assert outcome.status == "PASS"
    assert outcome.confidence >= 0.9
    assert outcome.evidence is not None


def test_presence_is_not_evaluable_not_failed_when_the_confirmation_is_absent():
    """A critical presence check (e.g. Account holder confirmed) with no
    matching utterance must route to a human, not manufacture a critical
    FAIL from a keyword miss."""
    config = {"kind": "presence", "pattern": r"that'?s me", "speaker": "CUSTOMER", "expected_label": "Account holder confirmed"}
    outcome = evaluate_factual(config, ctx([seg(1, "AGENT", 10, "Can I confirm who I'm speaking with?")]))
    assert outcome.status == "REVIEW"
    assert outcome.confidence < 0.85
    assert outcome.evidence is None, "must not fabricate an evidence span for something that wasn't found"


# ---- factual: conditional not-applicable (skip_if_absent) ----


def test_skip_if_absent_passes_correctly_when_source_of_truth_says_nothing_applies():
    """Gift card value: no gift card on this plan (crm value falsy) means
    PASS is the CORRECT answer — nothing to mismatch — not a fabricated
    default."""
    config = {"field": "gift_card_value", "pattern": r"\$(\d+)", "kind": "numeric", "skip_if_absent": True}
    outcome = evaluate_factual(config, ctx([seg(1, "AGENT", 10, "No promotional offers on this plan.")], crm={"gift_card_value": None}))
    assert outcome.status == "PASS"
    assert outcome.expected == "Not applicable to this plan"


def test_skip_if_absent_still_verifies_normally_when_the_source_of_truth_has_a_value():
    config = {"field": "gift_card_value", "pattern": r"\$(\d+)\s*gift card", "kind": "numeric", "unit": "", "tolerance": 0, "skip_if_absent": True}
    outcome = evaluate_factual(config, ctx([seg(1, "AGENT", 10, "You'll receive a $50 gift card with this plan.")], crm={"gift_card_value": 100}))
    assert outcome.status == "FAIL", "a real mismatch must still be caught even though the field supports skip_if_absent"


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


def test_unconfigured_behaviour_metric_is_not_evaluable_never_a_silent_pass():
    outcome = evaluate_behaviour({"metric": "unknown_thing"}, ctx([seg(1, "AGENT", 10, "Hello there.")]))
    assert outcome.status == "REVIEW"
    assert outcome.confidence < 0.85


# ---- behaviour: interruptions (real crosstalk-marker signal) ----


def test_interruptions_passes_with_no_crosstalk_markers():
    outcome = evaluate_behaviour({"metric": "interruptions", "threshold_count": 2}, ctx([seg(1, "AGENT", 10, "Hello there.")]))
    assert outcome.status == "PASS"


def test_interruptions_fails_when_crosstalk_markers_reach_the_threshold():
    outcome = evaluate_behaviour(
        {"metric": "interruptions", "threshold_count": 1},
        ctx([seg(1, "AGENT", 588, "for your [crosstalk] plan"), seg(2, "CUSTOMER", 606, "sorry, say that again")]),
    )
    assert outcome.status == "FAIL"
    assert "1" in outcome.observed


# ---- behaviour: rapport (real talk-time-share signal) ----


def test_rapport_passes_with_a_reasonable_two_way_conversation():
    segments = [
        seg(1, "AGENT", 0, "Hello, how are you today?", end=5),
        seg(2, "CUSTOMER", 5, "Good thanks, how are you?", end=10),
        seg(3, "AGENT", 10, "Great, let's get started.", end=15),
        seg(4, "CUSTOMER", 15, "Sounds good to me.", end=20),
    ]
    outcome = evaluate_behaviour({"metric": "rapport", "min_customer_share": 0.3}, ctx(segments))
    assert outcome.status == "PASS"


def test_rapport_flags_a_call_where_the_customer_almost_never_speaks():
    segments = [seg(1, "AGENT", 0, "Long monologue.", end=100), seg(2, "CUSTOMER", 100, "Mm.", end=101)]
    outcome = evaluate_behaviour({"metric": "rapport", "min_customer_share": 0.08}, ctx(segments))
    assert outcome.status == "FAIL"
    assert "customer" in outcome.observed.lower()


# ---- behaviour: objection handling (real keyword + follow-up signal) ----


def test_objection_handling_passes_when_nothing_to_handle():
    outcome = evaluate_behaviour({"metric": "objection_handling"}, ctx([seg(1, "AGENT", 10, "Everything sounds great."), seg(2, "CUSTOMER", 16, "Yes, let's proceed.")]))
    assert outcome.status == "PASS"


def test_objection_handling_passes_when_the_agent_responds():
    segments = [
        seg(1, "CUSTOMER", 10, "I'm not sure about this, it sounds too expensive."),
        seg(2, "AGENT", 16, "I understand — let me explain the savings involved."),
    ]
    outcome = evaluate_behaviour({"metric": "objection_handling"}, ctx(segments))
    assert outcome.status == "PASS"


def test_objection_handling_fails_when_the_objection_is_never_addressed():
    segments = [seg(1, "CUSTOMER", 10, "Actually I don't want to proceed with this.")]
    outcome = evaluate_behaviour({"metric": "objection_handling"}, ctx(segments))
    assert outcome.status == "FAIL"


def test_objection_handling_categorizes_the_objection_type():
    segments = [
        seg(1, "CUSTOMER", 10, "I'm not interested, thanks."),
        seg(2, "AGENT", 16, "No problem — thanks for your time."),
    ]
    outcome = evaluate_behaviour({"metric": "objection_handling"}, ctx(segments))
    assert "not_interested" in outcome.observed


def test_objection_handling_weak_signal_reports_low_confidence_not_a_confident_verdict():
    """Brief §28's adversarial case: a customer mentioning something
    offhand ('not interested', said jokingly, or a bare hedge word like
    'actually') is genuinely ambiguous from text alone — the system must
    report its uncertainty rather than confidently fail or pass."""
    segments = [seg(1, "CUSTOMER", 10, "Actually, hmm, let me think about the colour options too.")]
    outcome = evaluate_behaviour({"metric": "objection_handling"}, ctx(segments))
    assert outcome.confidence < 0.85, "an ambiguous hedge-word-only match must not be reported at full confidence"


def test_objection_handling_counts_a_long_delayed_agent_response_as_addressed():
    """Documented limitation: this evaluator checks WHETHER the agent
    responded at all, not HOW promptly — a real system might also score
    response latency, out of scope here."""
    segments = [
        seg(1, "CUSTOMER", 10, "I'm not interested, this seems like a waste of money."),
        seg(2, "AGENT", 400, "Sorry for the pause — let me address that concern now."),
    ]
    outcome = evaluate_behaviour({"metric": "objection_handling"}, ctx(segments))
    assert outcome.status == "PASS"


def test_objection_handling_with_no_transcript_segments_is_a_clean_pass_nothing_to_handle():
    outcome = evaluate_behaviour({"metric": "objection_handling"}, ctx([]))
    assert outcome.status == "PASS"


# ---- behaviour: real timestamp-overlap interruption detection ----


def test_interruptions_detects_a_genuine_timestamp_overlap_with_exact_duration():
    segments = [
        seg(1, "AGENT", 124.2, "So as I was explaining about the plan details", end=126.0),
        seg(2, "CUSTOMER", 125.1, "Sorry, can I just ask something quickly?", end=127.0),
    ]
    outcome = evaluate_behaviour({"metric": "interruptions", "threshold_count": 1}, ctx(segments))
    assert outcome.status == "FAIL"
    assert "0.9s overlap" in outcome.observed
    assert outcome.confidence >= 0.85, "a timing-verified overlap is the strongest signal this evaluator has"


def test_interruptions_marker_only_signal_is_reported_at_lower_confidence_than_a_timed_overlap():
    timed = evaluate_behaviour(
        {"metric": "interruptions", "threshold_count": 1},
        ctx([seg(1, "AGENT", 100, "talking", end=106), seg(2, "CUSTOMER", 103, "interrupting", end=108)]),
    )
    marker_only = evaluate_behaviour(
        {"metric": "interruptions", "threshold_count": 1},
        ctx([seg(1, "AGENT", 100, "talking over [crosstalk] here", end=106), seg(2, "CUSTOMER", 200, "later reply", end=206)]),
    )
    assert marker_only.confidence < timed.confidence


def test_interruptions_with_a_single_segment_cannot_overlap_with_anything():
    outcome = evaluate_behaviour({"metric": "interruptions"}, ctx([seg(1, "AGENT", 10, "Hello.")]))
    assert outcome.status == "PASS"


# ---- behaviour: missing/empty transcript ----


def test_rapport_with_no_segments_at_all_is_not_evaluable():
    outcome = evaluate_behaviour({"metric": "rapport"}, ctx([]))
    assert outcome.status == "REVIEW"
    assert outcome.confidence < 0.85
