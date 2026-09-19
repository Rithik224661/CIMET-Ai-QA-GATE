"""End-to-end scenario coverage against the real API + real pipeline output
(no mocking of the evaluators) — the 8 scenarios called for in the brief."""

from __future__ import annotations


def test_scenario_1_clean_call_auto_submits(client):
    body = client.get("/api/leads/3613742").json()
    assert body["decision"]["decision"] == "AUTO_SUBMIT"
    assert body["decision"]["criticalFails"] == 0
    assert body["decision"]["lowConfidence"] == 0
    # Genuinely 20/20 checks executed and evaluated — zero dangerous
    # pass-throughs (every result has a real status, not a placeholder).
    assert body["decision"]["checksRun"] == 20
    assert len(body["results"]) == 20
    assert all(r["status"] in ("PASS", "FAIL", "REVIEW") for r in body["results"])
    # The submission boundary: only AUTO_SUBMIT ever gets a submission.
    assert body["submission"] is not None
    assert body["submission"]["status"] == "SUBMITTED"
    assert body["submission"]["sandbox"] == "DEMO_MOCK"
    assert body["submission"]["payload"]["decision"] == "AUTO_SUBMIT"


def test_scenario_1b_no_check_in_the_catalogue_is_a_dangerous_silent_pass(client):
    """Every one of the 20 checks resolves to a real evaluator strategy —
    none defaults to an unconditional PASS with no evidence and no
    rationale tied to actual input (the exact anti-pattern this hardening
    pass eliminates). A PASS with no evidence span is only legitimate for
    a specific, named set of checks — aggregate transcript-wide behaviour
    heuristics (no single quotable moment to cite) and the two
    genuinely-not-applicable-to-this-plan factual checks — never any
    check whose job is to compare against a specific piece of input."""
    NO_EVIDENCE_PASS_ALLOWED = {
        "RET1-BH-011",  # Dead air — PASS-with-no-silence has nothing to quote
        "RET1-BH-018",  # Rapport — aggregate talk-time ratio, not one moment
        "RET1-BH-019",  # Interruptions — PASS-with-none has nothing to quote
        "RET1-BH-020",  # Objection handling — nothing raised, nothing to quote
        "RET1-FM-009",  # Concession applied — not applicable to this lead's plan
        "RET1-FM-014",  # Gift card value — not applicable to this lead's plan
    }
    body = client.get("/api/leads/3613742").json()
    for r in body["results"]:
        assert r["rationale"], f"{r['checkCode']} has no rationale — cannot prove why it passed"
        if r["status"] == "PASS" and r["evidenceQuote"] is None:
            assert r["checkCode"] in NO_EVIDENCE_PASS_ALLOWED, (
                f"{r['checkCode']} PASSed with no evidence and isn't on the allowed list: {r['rationale']}"
            )


def test_scenario_2_critical_rate_mismatch_holds(client):
    body = client.get("/api/leads/3613790").json()
    assert body["decision"]["decision"] == "HOLD"
    rate = next(c for c in body["results"] if c["checkCode"] == "RET1-FM-008")
    assert rate["status"] == "FAIL"
    assert rate["critical"] is True
    assert rate["observed"] == "28.6c / kWh peak"
    assert rate["expected"] == "31.9c / kWh peak"
    assert rate["evidenceQuote"] and "14:02" in rate["timestamp"]
    assert rate["ruleVersion"].startswith("RET1-FM-008")
    # HOLD must never submit — the mock sandbox boundary is respected.
    assert body["submission"] is None


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
    assert dmo["critical"] is True
    assert body["decision"]["criticalFails"] == 0, "QA_REVIEW here is about confidence, not a critical failure"
    assert body["submission"] is None


def test_scenario_5_behaviour_only_does_not_unnecessarily_block(client):
    body = client.get("/api/leads/3613824").json()
    assert body["decision"]["decision"] == "AUTO_SUBMIT"
    dead_air = next(c for c in body["results"] if c["checkCode"] == "RET1-BH-011")
    assert dead_air["status"] == "FAIL"
    assert dead_air["critical"] is False
    # A non-critical FAIL must never contribute to a HOLD or a QA_REVIEW.
    assert body["decision"]["criticalFails"] == 0
    assert body["decision"]["lowConfidence"] == 0
    assert body["submission"] is not None, "non-critical coaching notes must not block the submission boundary"


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
    assert body["submission"] is None, "an ingest-error lead must never reach the submission boundary"


def test_get_submission_404s_for_a_lead_that_was_never_auto_submitted(client):
    res = client.get("/api/leads/3613790/submission")  # HOLD
    assert res.status_code == 404


def test_repeat_offence_flags_the_third_failure_in_the_rolling_window(client):
    body = client.get("/api/leads/3613778").json()
    assert body["repeatOffence"] is True
    assert body["decision"]["decision"] == "HOLD"
    assert "Third failure" in body["decision"]["reason"]
