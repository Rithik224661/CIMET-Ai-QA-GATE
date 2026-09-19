"""
End-to-end AI-failure test at the pipeline level (brief §19): with
AI_PROVIDER configured but the provider unavailable/erroring, the whole
lead evaluation must still complete correctly — critical evaluators
unaffected, gate decision correct, no fake PASS, no crash — and the
AI_EVALUATION audit event must record the fallback honestly (brief §18
observability: provider/model/used/latencyMs/fallbackReason).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.enums import AuditEventType
from app.models import AuditEvent, Lead
from app.services.pipeline import run_evaluation


def _ai_events(db: Session, lead_id: str) -> list[AuditEvent]:
    return list(
        db.execute(
            select(AuditEvent)
            .where(AuditEvent.lead_id == lead_id, AuditEvent.event_type == AuditEventType.AI_EVALUATION)
            .order_by(AuditEvent.seq)
        ).scalars()
    )


def test_ai_provider_configured_but_erroring_falls_back_safely(seeded_db: Session, monkeypatch):
    monkeypatch.setattr(settings, "ai_provider", "anthropic")
    monkeypatch.setattr(settings, "anthropic_api_key", "sk-fake-not-real")

    def _raise(*args, **kwargs):
        raise RuntimeError("simulated Anthropic outage")

    monkeypatch.setattr("app.services.ai_provider.AnthropicLLMProvider.evaluate_structured", _raise)

    lead = seeded_db.get(Lead, "3613824")  # Lead E: clean AUTO_SUBMIT with real behaviour signal
    decision = run_evaluation(seeded_db, lead)
    seeded_db.commit()

    assert decision.decision == "AUTO_SUBMIT", "an AI provider outage must never change the deterministic gate outcome"

    events = _ai_events(seeded_db, "3613824")
    assert len(events) == 1
    assert events[-1].resulting_state == "AI_FALLBACK"
    assert events[-1].event_metadata["used"] is False
    assert events[-1].event_metadata["provider"] == "anthropic"
    assert "sk-fake-not-real" not in str(events[-1].event_metadata), "never leak the API key into audit metadata"


def test_ai_provider_none_never_writes_an_ai_audit_event(seeded_db: Session):
    """AI_PROVIDER=none (the live demo default) — no AI call is even
    attempted, so no AI_EVALUATION event should appear at all."""
    assert settings.ai_provider == "none"
    lead = seeded_db.get(Lead, "3613790")
    run_evaluation(seeded_db, lead)
    seeded_db.commit()
    assert _ai_events(seeded_db, "3613790") == []


def test_ai_provider_configured_with_working_fake_uses_one_combined_call(seeded_db: Session, monkeypatch):
    """Sanity check that a *working* provider does get used end-to-end
    through the real pipeline (not just the unit-level ai_behaviour.py
    tests), and only ever makes ONE call for the whole lead (brief §37)."""
    import json

    from app.services.ai_provider import NullLLMProvider, StructuredExtractionResult

    calls = {"count": 0}
    # High AI confidence (0.98) so averaging with the deterministic
    # confidences (already tuned above the 0.85 floor for this lead) stays
    # above the floor too — this test is about the one-call consolidation
    # and end-to-end wiring, not about confidence-averaging arithmetic.
    payload = json.dumps(
        {
            "rapport": {"status": "PASS", "confidence": 0.98, "signals": [], "evidence": [], "rationale": "Fine."},
            "interruptions": {"status": "PASS", "confidence": 0.98, "signals": [], "evidence": [], "rationale": "Fine."},
            "objection_handling": {"status": "PASS", "confidence": 0.98, "signals": [], "evidence": [], "rationale": "Fine."},
        }
    )

    class WorkingFakeProvider:
        name = "fake"

        def evaluate_structured(self, *, prompt, schema_description, context):
            calls["count"] += 1
            return StructuredExtractionResult(value=payload, confidence=0.98, rationale="fake")

    monkeypatch.setattr(settings, "ai_provider", "anthropic")
    monkeypatch.setattr("app.services.ai_behaviour.get_llm_provider", lambda: WorkingFakeProvider())
    monkeypatch.setattr("app.services.ai_provider.NullLLMProvider", NullLLMProvider)

    lead = seeded_db.get(Lead, "3613824")
    decision = run_evaluation(seeded_db, lead)
    seeded_db.commit()

    assert decision.decision == "AUTO_SUBMIT"
    assert calls["count"] == 1, "exactly one AI call for the whole lead, not one per behaviour check"

    events = _ai_events(seeded_db, "3613824")
    assert events[-1].resulting_state == "AI_USED"
    assert set(events[-1].event_metadata["metricsCovered"]) == {"rapport", "interruptions", "objection_handling"}
