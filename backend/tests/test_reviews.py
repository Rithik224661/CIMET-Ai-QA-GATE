"""POST /api/reviews — the human-in-the-loop write path. Must append, never
mutate, the AI decision (CLAUDE.md #7)."""

from __future__ import annotations


def test_submitting_a_review_appends_without_mutating_the_ai_decision(client):
    before = client.get("/api/leads/3613790").json()
    assert before["decision"]["decision"] == "HOLD"

    res = client.post(
        "/api/reviews",
        json={"leadId": "3613790", "humanDecision": "PASS", "reason": "Customer re-confirmed the rate on a follow-up call."},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["review"]["humanDecision"] == "PASS"
    assert body["review"]["aiDecision"] == "HOLD"

    after = client.get("/api/leads/3613790").json()
    assert after["decision"]["decision"] == "HOLD", "the AI decision must never change because of a human review"
    assert after["override"]["humanDecision"] == "PASS"


def test_review_appears_in_the_audit_ledger_as_a_new_event(client):
    ledger_before = client.get("/api/audit/3613790").json()["events"]
    client.post("/api/reviews", json={"leadId": "3613790", "humanDecision": "PASS", "reason": "Confirmed correction on a later call."})
    ledger_after = client.get("/api/audit/3613790").json()["events"]
    assert len(ledger_after) == len(ledger_before) + 1
    assert ledger_after[-1]["event"] == "Human Override"
    assert ledger_after[-1]["resultingState"] == "PASS"
    # the original events are untouched, not rewritten
    assert ledger_after[: len(ledger_before)] == ledger_before


def test_review_requires_a_real_reason(client):
    res = client.post("/api/reviews", json={"leadId": "3613790", "humanDecision": "PASS", "reason": "ok"})
    assert res.status_code == 422


def test_review_rejects_an_invalid_decision_value(client):
    res = client.post(
        "/api/reviews", json={"leadId": "3613790", "humanDecision": "MAYBE", "reason": "this is not a valid decision value"}
    )
    assert res.status_code == 422


def test_review_404s_for_an_unknown_lead(client):
    res = client.post("/api/reviews", json={"leadId": "does-not-exist", "humanDecision": "PASS", "reason": "irrelevant but long enough"})
    assert res.status_code == 404


def test_review_refuses_a_lead_that_has_not_been_scored_yet(client):
    res = client.post(
        "/api/reviews", json={"leadId": "3613830", "humanDecision": "PASS", "reason": "irrelevant but long enough anyway"}
    )
    assert res.status_code == 400


def test_lead_scoped_override_alias_behaves_identically(client):
    res = client.post("/api/leads/3613803/override", json={"leadId": "3613803", "humanDecision": "HOLD", "reason": "Confirmed the address mismatch by callback."})
    assert res.status_code == 200
    assert res.json()["review"]["humanDecision"] == "HOLD"
