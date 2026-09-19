"""End-to-end scenario coverage against the real API + real pipeline output
(no mocking of the evaluators) — the 8 scenarios called for in the brief."""

from __future__ import annotations


def test_scenario_1_clean_call_auto_submits(client):
    body = client.get("/api/leads/3613742").json()
    assert body["decision"]["decision"] == "AUTO_SUBMIT"
    assert body["decision"]["criticalFails"] == 0


def test_scenario_2_critical_rate_mismatch_holds(client):
    body = client.get("/api/leads/3613790").json()
    assert body["decision"]["decision"] == "HOLD"
    rate = next(c for c in body["results"] if c["checkCode"] == "RET1-FM-008")
    assert rate["status"] == "FAIL"


def test_scenario_3_email_mismatch_holds(client):
    body = client.get("/api/leads/3613790").json()
    email = next(c for c in body["results"] if c["checkCode"] == "RET1-FM-013")
    assert email["status"] == "FAIL"
    assert body["decision"]["decision"] == "HOLD"


def test_scenario_4_low_confidence_crosstalk_routes_to_qa_review(client):
    body = client.get("/api/leads/3613811").json()
    assert body["decision"]["decision"] == "QA_REVIEW"
    dmo = next(c for c in body["results"] if c["checkCode"] == "RET1-VB-007")
    assert dmo["status"] == "REVIEW"
    assert dmo["confidence"] < 0.85


def test_scenario_5_behaviour_only_does_not_unnecessarily_block(client):
    body = client.get("/api/leads/3613824").json()
    assert body["decision"]["decision"] == "AUTO_SUBMIT"
    dead_air = next(c for c in body["results"] if c["checkCode"] == "RET1-BH-011")
    assert dead_air["status"] == "FAIL"
    assert dead_air["critical"] is False


def test_scenario_6_human_override_preserved_alongside_ai_decision(client):
    body = client.get("/api/leads/3613766").json()
    assert body["decision"]["decision"] == "HOLD", "the AI decision is untouched by the override"
    assert body["override"]["humanDecision"] == "PASS"
    assert body["override"]["aiDecision"] == "HOLD"


def test_scenario_7_historical_rule_version_resolved_correctly(client):
    body = client.get("/api/leads/3613790").json()
    assert body["checklistVersion"] == "v1.4"
    for result in body["results"]:
        assert result["ruleVersion"].endswith("v1.4")


def test_scenario_8_invalid_recording_routes_to_safe_hold_review_never_auto_submit(client):
    body = client.get("/api/leads/3613834").json()
    assert body["state"] == "error"
    assert body["decision"] is None, "an ingest failure must never look like a completed AUTO_SUBMIT decision"
    assert body["ingestError"] is not None


def test_repeat_offence_flags_the_third_failure_in_the_rolling_window(client):
    body = client.get("/api/leads/3613778").json()
    assert body["repeatOffence"] is True
    assert body["decision"]["decision"] == "HOLD"
    assert "Third failure" in body["decision"]["reason"]
