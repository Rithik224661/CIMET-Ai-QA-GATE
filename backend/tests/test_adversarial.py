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
