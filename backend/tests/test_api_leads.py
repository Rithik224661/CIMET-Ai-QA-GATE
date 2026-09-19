from __future__ import annotations


def test_health_reports_connected_and_seeded(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["database"] == "connected"
    assert body["seeded"] is True


def test_list_leads_with_no_filter_returns_every_named_scenario_including_processing(client):
    res = client.get("/api/leads")
    assert res.status_code == 200
    leads = res.json()["leads"]
    ids = {lead["id"] for lead in leads}
    assert ids == {"3613742", "3613790", "3613803", "3613811", "3613824", "3613766", "3613778", "3613830", "3613834"}


def test_queue_all_filter_excludes_still_processing_leads(client):
    res = client.get("/api/leads", params={"filter": "All"})
    leads = res.json()["leads"]
    states = {lead["state"] for lead in leads}
    assert "processing" not in states
    assert len(leads) == 8


def test_critical_holds_filter_excludes_the_overridden_lead(client):
    res = client.get("/api/leads", params={"filter": "Critical holds"})
    ids = {lead["id"] for lead in res.json()["leads"]}
    assert "3613790" in ids  # Lead B: HOLD, no override
    assert "3613766" not in ids  # Lead F: HOLD but overridden — excluded from this filter


def test_get_single_lead_404s_cleanly_for_unknown_id(client):
    res = client.get("/api/leads/does-not-exist")
    assert res.status_code == 404


def test_get_lead_returns_gate_decision_matching_worked_example(client):
    res = client.get("/api/leads/3613790")
    body = res.json()
    assert body["decision"]["decision"] == "HOLD"
    assert body["decision"]["criticalFails"] == 2
    rate_check = next(c for c in body["results"] if c["checkCode"] == "RET1-FM-008")
    assert rate_check["status"] == "FAIL"
    assert rate_check["observed"] == "28.6c / kWh peak"
    assert rate_check["expected"] == "31.9c / kWh peak"
    email_check = next(c for c in body["results"] if c["checkCode"] == "RET1-FM-013")
    assert email_check["status"] == "FAIL"
    assert email_check["observed"] == "j.smith@gmial.com"


def test_processing_lead_has_no_results_and_no_decision(client):
    res = client.get("/api/leads/3613830")
    body = res.json()
    assert body["state"] == "processing"
    assert body["results"] == []
    assert body["decision"] is None


def test_error_lead_has_ingest_error_and_no_decision(client):
    res = client.get("/api/leads/3613834")
    body = res.json()
    assert body["state"] == "error"
    assert body["ingestError"]["code"] == "E_EMPTY_MEDIA"
    assert body["decision"] is None


def test_rules_endpoint_returns_stable_order_for_index_based_selection(client):
    res = client.get("/api/rules")
    rule_sets = res.json()["ruleSets"]
    assert rule_sets[0]["retailer"] == "Retailer 1"
    assert rule_sets[0]["version"] == "v1.4"
    assert rule_sets[0]["live"] is True


def test_checks_endpoint_returns_the_twenty_check_catalogue(client):
    res = client.get("/api/checks")
    checks = res.json()["checks"]
    assert len(checks) == 20
    assert {c["code"] for c in checks if c["critical"]}.issuperset({"RET1-VB-001", "RET1-FM-008", "RET1-FM-013"})


def test_audit_ledger_is_append_only_ordered_and_ends_on_the_gate_decision(client):
    res = client.get("/api/audit/3613790")
    events = res.json()["events"]
    assert events[0]["event"] == "Lead Created"
    assert events[-1]["resultingState"] == "HOLD"
