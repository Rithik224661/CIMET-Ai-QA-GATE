"""Adversarial cases (brief §47/§42): the goal is not just passing the
happy path — it's proving messy input can't manufacture a false pass."""

from __future__ import annotations

import pytest

from app.services.evaluators.base import EvaluationContext, TranscriptSegmentData
from app.services.evaluators.factual import evaluate_factual
from app.services.pipeline import run_evaluation


def seg(id_, speaker, start, text):
    return TranscriptSegmentData(id=id_, speaker=speaker, start_seconds=start, end_seconds=start + 6, text=text)


def test_number_confusion_is_caught_not_smoothed_over():
    """A near-miss number (31.19 vs 31.9) must still fail at zero
    tolerance — the evaluator doesn't "round in the agent's favor"."""
    config = {"field": "peak_rate_cents", "pattern": r"(\d+\.?\d*)\s*cents?", "kind": "numeric", "tolerance": 0.0}
    ctx = EvaluationContext(lead_id="x", duration_sec=100, segments=[seg(1, "AGENT", 10, "Peak is 31.19 cents.")], crm_snapshot={"peak_rate_cents": 31.9})
    outcome = evaluate_factual(config, ctx)
    assert outcome.status == "FAIL"


def test_customer_correction_later_in_the_call_does_not_retroactively_fix_the_agent_misstatement():
    """Lead 3613766's real scenario: the agent misstates the rate, and only
    a LATER turn (outside the configured extraction window) corrects it.
    The check must still fail on the turn it's actually scoped to
    evaluate — the brief is explicit that this is why a human reviews it,
    not something the evaluator should paper over."""
    config = {"field": "peak_rate_cents", "pattern": r"(\d+\.?\d*)\s*cents?", "kind": "numeric", "unit": "c/kWh", "tolerance": 0.0, "window_start": 700, "window_end": 1000}
    ctx = EvaluationContext(
        lead_id="x",
        duration_sec=2000,
        segments=[
            seg(1, "AGENT", 842, "Peak is 30.9 cents per kilowatt hour."),
            seg(2, "AGENT", 1672, "Sorry, that's 31.9 cents peak."),  # outside the window — correctly ignored
        ],
        crm_snapshot={"peak_rate_cents": 31.9},
    )
    outcome = evaluate_factual(config, ctx)
    assert outcome.status == "FAIL"
    assert outcome.observed == "30.9c/kWh"


def test_missing_transcript_refuses_to_evaluate_rather_than_guessing(seeded_db):
    from app.models import Lead

    lead = seeded_db.get(Lead, "3613830")  # processing state — has no transcript yet
    with pytest.raises(ValueError, match="no transcript"):
        run_evaluation(seeded_db, lead)


def test_re_evaluation_is_idempotent_not_additive(seeded_db):
    """Running the pipeline twice on the same lead must replace, not
    duplicate, its results — otherwise a retried/duplicate webhook could
    silently double up CheckResult rows (brief §41 idempotency)."""
    from app.models import Lead

    lead = seeded_db.get(Lead, "3613790")
    first_count = len(lead.results)
    run_evaluation(seeded_db, lead)
    seeded_db.commit()
    seeded_db.refresh(lead)
    assert len(lead.results) == first_count, "re-running must not accumulate duplicate CheckResult rows"
    assert lead.decision is not None


def test_low_confidence_extraction_never_silently_becomes_a_pass():
    config = {"field": "peak_rate_cents", "pattern": r"(\d+\.?\d*)\s*cents?", "kind": "numeric", "tolerance": 0.0}
    ctx = EvaluationContext(lead_id="x", duration_sec=100, segments=[seg(1, "AGENT", 10, "We'll come back to pricing.")], crm_snapshot={"peak_rate_cents": 31.9})
    outcome = evaluate_factual(config, ctx)
    assert outcome.status != "PASS"
    assert outcome.confidence < 0.85


def test_a_scored_lead_with_ingest_error_state_is_impossible_via_the_api(client):
    """An ingest-error lead must never carry a completed gate decision —
    the two states are mutually exclusive by construction."""
    body = client.get("/api/leads/3613834").json()
    assert body["state"] == "error"
    assert body["decision"] is None
    assert body["results"] == []


def test_an_evaluator_exception_degrades_to_review_not_a_crash_or_a_pass(seeded_db, monkeypatch):
    """If a single check's evaluator raises, the whole lead must still get
    scored — the broken check becomes REVIEW (sub-floor confidence), not a
    crashed evaluation and not a silent PASS (brief §42/§16)."""
    from app.models import Lead
    from app.services import pipeline

    def _boom(check_config, context):
        raise RuntimeError("simulated evaluator bug")

    monkeypatch.setattr(pipeline, "evaluate_verbatim", _boom)

    lead = seeded_db.get(Lead, "3613742")  # Lead A — would otherwise be a clean AUTO_SUBMIT
    decision = pipeline.run_evaluation(seeded_db, lead)
    seeded_db.commit()
    seeded_db.refresh(lead)

    verbatim_results = [r for r in lead.results if r.check.type == "Verbatim"]
    assert verbatim_results, "sanity: there should be Verbatim checks to break"
    assert all(r.status == "REVIEW" and r.confidence < 0.85 for r in verbatim_results)
    # Several of those are critical, so the lead must route to QA_REVIEW —
    # never silently keep its old clean AUTO_SUBMIT decision.
    assert decision.decision == "QA_REVIEW"


def test_submission_is_idempotent_on_re_evaluation(seeded_db):
    """Re-evaluating an AUTO_SUBMIT lead must replace its Submission, not
    accumulate a second one — the same duplicate-webhook concern as
    CheckResult rows (brief §41/§23)."""
    from app.models import Lead, Submission

    lead = seeded_db.get(Lead, "3613742")
    assert lead.submission_record is not None
    first_submission_id = lead.submission_record.id

    run_evaluation(seeded_db, lead)
    seeded_db.commit()
    seeded_db.refresh(lead)

    assert lead.submission_record is not None
    assert lead.submission_record.id != first_submission_id, "a fresh evaluation should produce a fresh submission row"
    count = seeded_db.query(Submission).filter(Submission.lead_id == lead.id).count()
    assert count == 1, "must never leave more than one live submission for a lead"


def test_submission_service_refuses_to_submit_a_non_auto_submit_decision(seeded_db):
    from app.models import Lead
    from app.services.submission import submit_if_auto_submitted

    lead = seeded_db.get(Lead, "3613790")  # HOLD
    assert lead.decision.decision == "HOLD"
    with pytest.raises(ValueError, match="only AUTO_SUBMIT may submit"):
        submit_if_auto_submitted(seeded_db, lead, lead.decision)


def test_duplicate_evaluation_requests_never_produce_contradictory_decisions(client):
    """Simulates a duplicate ingest/evaluation callback hitting the API
    twice in a row for the same lead — the second call must leave the
    lead in a single, consistent state, not two conflicting rows."""
    first = client.post("/api/evaluations", json={"leadId": "3613790"})
    second = client.post("/api/evaluations", json={"leadId": "3613790"})
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["decision"]["decision"] == second.json()["decision"]["decision"] == "HOLD"

    body = client.get("/api/leads/3613790").json()
    rate_results = [r for r in body["results"] if r["checkCode"] == "RET1-FM-008"]
    assert len(rate_results) == 1, "must never accumulate duplicate CheckResult rows for the same check"


def test_ai_provider_defaults_to_none_and_never_fabricates_an_extraction():
    """AI_PROVIDER=none (the default) makes zero external calls and always
    reports it cannot extract — proving nothing downstream could receive a
    fabricated value from it even if a caller mistakenly relied on it."""
    from app.services.ai_provider import NullLLMProvider, get_llm_provider

    provider = get_llm_provider()
    assert isinstance(provider, NullLLMProvider)
    result = provider.evaluate_structured(prompt="anything", schema_description="anything", context="anything")
    assert result is None


def test_anthropic_provider_failure_returns_none_never_raises_or_fabricates():
    """A provider-side exception (network error, bad response, whatever)
    must degrade to 'could not extract', never propagate as a crash and
    never be mistaken for a successful extraction."""
    from app.services.ai_provider import AnthropicLLMProvider

    provider = AnthropicLLMProvider(api_key="invalid-test-key", model="does-not-matter")
    result = provider.evaluate_structured(prompt="x", schema_description="x", context="x")
    assert result is None
