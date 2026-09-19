"""Tests for the optional AI semantic layer on Behaviour checks
(app/services/ai_behaviour.py). Since AI_PROVIDER=none by default (the
live demo's actual configuration), these tests exercise the plumbing with
a FAKE provider implementing the same Protocol as a real one — proving
the integration, evidence verification, schema validation, and every
failure-mode fallback genuinely work, without needing real credentials."""

from __future__ import annotations

import json

from app.services.ai_behaviour import maybe_refine_with_ai
from app.services.evaluators.base import CheckOutcome, EvaluationContext, EvidenceData, TranscriptSegmentData


def seg(id_, speaker, start, text, end=None):
    return TranscriptSegmentData(id=id_, speaker=speaker, start_seconds=start, end_seconds=end or start + 6, text=text)


def ctx(segments):
    return EvaluationContext(lead_id="x", duration_sec=1800, segments=segments, crm_snapshot={})


def deterministic(status="PASS", confidence=0.9, evidence=None):
    return CheckOutcome(
        status=status, confidence=confidence, observed="observed", expected="expected",
        rationale="Deterministic baseline.", evidence=evidence, timestamp_seconds=10,
    )


class FakeResult:
    def __init__(self, value: str):
        self.value = value


class FakeProvider:
    """Implements the same duck-typed interface as NullLLMProvider /
    AnthropicLLMProvider (see ai_provider.py's LLMProvider Protocol)."""

    name = "fake"

    def __init__(self, response_value: str | None = None, raise_error: bool = False):
        self._response_value = response_value
        self._raise_error = raise_error

    def evaluate_structured(self, *, prompt, schema_description, context):
        if self._raise_error:
            raise RuntimeError("simulated provider failure")
        if self._response_value is None:
            return None
        return FakeResult(self._response_value)


def _patch_provider(monkeypatch, provider):
    monkeypatch.setattr("app.services.ai_behaviour.get_llm_provider", lambda: provider)


def test_ai_provider_none_is_a_zero_cost_noop(monkeypatch):
    """The default path: no provider configured -> deterministic outcome
    returned completely unchanged, no call attempted at all."""
    from app.services.ai_provider import NullLLMProvider

    _patch_provider(monkeypatch, NullLLMProvider())
    det = deterministic()
    result = maybe_refine_with_ai("rapport", {}, ctx([seg(1, "AGENT", 0, "hi")]), det)
    assert result is det


def test_ai_agreement_averages_confidence_and_notes_corroboration(monkeypatch):
    payload = json.dumps({"status": "PASS", "confidence": 0.8, "signals": ["steady turn-taking"], "evidence": [], "rationale": "Looks fine."})
    _patch_provider(monkeypatch, FakeProvider(payload))
    det = deterministic(status="PASS", confidence=0.9)
    result = maybe_refine_with_ai("rapport", {}, ctx([seg(1, "AGENT", 0, "hi")]), det)
    assert result.status == "PASS"
    assert result.confidence == 0.85  # (0.9 + 0.8) / 2
    assert "corroborated" in result.rationale


def test_ai_disagreement_never_overrides_deterministic_status(monkeypatch):
    """The AI layer can flag disagreement and lower confidence, but the
    deterministic status is never replaced (brief §9)."""
    payload = json.dumps({"status": "FAIL", "confidence": 0.9, "signals": [], "evidence": [], "rationale": "Seems off."})
    _patch_provider(monkeypatch, FakeProvider(payload))
    det = deterministic(status="PASS", confidence=0.9)
    result = maybe_refine_with_ai("rapport", {}, ctx([seg(1, "AGENT", 0, "hi")]), det)
    assert result.status == "PASS", "deterministic status must survive AI disagreement"
    assert result.confidence <= 0.75
    assert "disagreed" in result.rationale


def test_ai_low_confidence_status_counts_as_agreement_not_override(monkeypatch):
    payload = json.dumps({"status": "LOW_CONFIDENCE", "confidence": 0.5, "signals": [], "evidence": [], "rationale": "Ambiguous."})
    _patch_provider(monkeypatch, FakeProvider(payload))
    det = deterministic(status="PASS", confidence=0.9)
    result = maybe_refine_with_ai("rapport", {}, ctx([seg(1, "AGENT", 0, "hi")]), det)
    assert result.status == "PASS"
    assert result.confidence == 0.7  # (0.9 + 0.5) / 2


def test_malformed_json_falls_back_to_deterministic(monkeypatch):
    _patch_provider(monkeypatch, FakeProvider("this is not json{{{"))
    det = deterministic()
    result = maybe_refine_with_ai("rapport", {}, ctx([seg(1, "AGENT", 0, "hi")]), det)
    assert result is det


def test_schema_violation_falls_back_to_deterministic(monkeypatch):
    """Valid JSON, but the wrong shape (missing required fields / bad
    status enum) — must be rejected by schema validation, not accepted."""
    _patch_provider(monkeypatch, FakeProvider(json.dumps({"status": "MAYBE", "confidence": 2.0})))
    det = deterministic()
    result = maybe_refine_with_ai("rapport", {}, ctx([seg(1, "AGENT", 0, "hi")]), det)
    assert result is det


def test_provider_exception_falls_back_to_deterministic_never_crashes(monkeypatch):
    _patch_provider(monkeypatch, FakeProvider(raise_error=True))
    det = deterministic()
    result = maybe_refine_with_ai("rapport", {}, ctx([seg(1, "AGENT", 0, "hi")]), det)
    assert result is det


def test_provider_returning_none_falls_back_to_deterministic(monkeypatch):
    _patch_provider(monkeypatch, FakeProvider(None))
    det = deterministic()
    result = maybe_refine_with_ai("rapport", {}, ctx([seg(1, "AGENT", 0, "hi")]), det)
    assert result is det


def test_unverifiable_evidence_is_never_trusted(monkeypatch):
    """The model cites a segment id / quote that doesn't match anything it
    was actually given — the whole response must be discarded, not
    partially trusted (brief §11: never invent a transcript quotation)."""
    payload = json.dumps(
        {
            "status": "PASS", "confidence": 0.95, "signals": [],
            "evidence": [{"segmentId": 999, "quote": "something that was never said"}],
            "rationale": "Fabricated.",
        }
    )
    _patch_provider(monkeypatch, FakeProvider(payload))
    det = deterministic(status="PASS", confidence=0.6)
    result = maybe_refine_with_ai("rapport", {}, ctx([seg(1, "AGENT", 0, "hi there")]), det)
    assert result is det, "unverifiable evidence must not be allowed to inflate confidence"


def test_verifiable_evidence_is_accepted(monkeypatch):
    payload = json.dumps(
        {
            "status": "PASS", "confidence": 0.9, "signals": ["polite acknowledgment"],
            "evidence": [{"segmentId": 1, "quote": "sounds good"}],
            "rationale": "Customer engaged.",
        }
    )
    _patch_provider(monkeypatch, FakeProvider(payload))
    det = deterministic(status="PASS", confidence=0.9)
    result = maybe_refine_with_ai("rapport", {}, ctx([seg(1, "CUSTOMER", 0, "Yeah, sounds good to me")]), det)
    assert result.confidence == 0.9


def test_ai_never_called_for_dead_air():
    """dead_air is a hard duration threshold, not eligible for semantic
    refinement — sanity check on the eligibility set itself."""
    from app.services.evaluators.behaviour import AI_ELIGIBLE_METRICS

    assert "dead_air" not in AI_ELIGIBLE_METRICS
    assert {"rapport", "interruptions", "objection_handling"} <= AI_ELIGIBLE_METRICS
