"""
Synthetic demo data. The 9 named scenarios mirror the ones the frontend
Phase 1 build already shipped with (src/lib/fixtures/leads.ts) — same lead
ids, same narrative — but here the pass/fail/review outcome is not
hand-authored: it is genuinely computed by the check evaluators
(app/services/evaluators/*) from this transcript text and the crm_snapshot
"source of truth" below. One documented adaptation from the frontend
fixtures: numbers are written in digit form ("28.6 cents") rather than
spelled out ("twenty-eight point six cents") — realistic ASR output
renders numbers as digits, and it's what the deterministic regex
extractors in the factual evaluator actually parse. See docs/DECISIONS.md.

All data is synthetic. No real customer PII (CLAUDE.md #9).
"""

from __future__ import annotations

import datetime as dt
import random
from dataclasses import dataclass, field

DISCLAIMER_PHRASE = "This call is being recorded for quality and compliance purposes"
DMO_PHRASE = "I need to read you the Default Market Offer comparison in full before we go further"

DEFAULT_CRM = {
    "peak_rate_cents": 31.9,
    "email": "j.smith@gmail.com",
    "address": "Unit 7, 12 Barker Street",
}


@dataclass(frozen=True)
class TurnSeed:
    speaker: str
    start: float
    text: str
    kind: str = "pass"
    end: float | None = None

    @property
    def end_seconds(self) -> float:
        return self.end if self.end is not None else self.start + 6.0


@dataclass
class LeadSeed:
    id: str
    scenario_tag: str
    scenario_summary: str
    retailer: str
    product: str
    agent: str
    team_lead: str
    campaign: str
    site: str
    call_datetime: dt.datetime
    duration_sec: int
    state: str  # LeadState
    turns: list[TurnSeed] = field(default_factory=list)
    crm_snapshot: dict = field(default_factory=lambda: dict(DEFAULT_CRM))
    ingest_error: dict | None = None
    pre_seeded_override: dict | None = None  # {human_decision, reason, reviewer_name, reviewer_role, at}


_CALL_BASE_DATE = dt.date(2026, 9, 18)


def _dt(date: dt.date, hhmm: str) -> dt.datetime:
    hh, mm = hhmm.split(":")
    return dt.datetime.combine(date, dt.time(int(hh), int(mm)))


LEADS: list[LeadSeed] = [
    LeadSeed(
        id="3613742",
        scenario_tag="Lead A",
        scenario_summary="Clean call · auto-submit",
        retailer="Retailer 1",
        product="Energy",
        agent="Agent A · R. Kaul",
        team_lead="TL · M. Sethi",
        campaign="owned_site",
        site="Site A",
        call_datetime=_dt(_CALL_BASE_DATE, "09:12"),
        duration_sec=1620,
        state="scored",
        turns=[
            TurnSeed("AGENT", 12, DISCLAIMER_PHRASE + "."),
            TurnSeed("AGENT", 200, "That's unit 7, 12 Barker Street — correct?"),
            TurnSeed("AGENT", 595, DMO_PHRASE + "."),
            TurnSeed("AGENT", 842, "Peak is 31.9 cents per kilowatt hour, off-peak is lower."),
            TurnSeed("AGENT", 1330, "Reading your email back: j.smith@gmail.com."),
            TurnSeed("AGENT", 1540, "Here are the terms and conditions that apply to this plan."),
            TurnSeed("AGENT", 1618, "You have a ten business day cooling-off period from today."),
        ],
    ),
    LeadSeed(
        id="3613790",
        scenario_tag="Lead B",
        scenario_summary="Rate + email mismatch · hold",
        retailer="Retailer 1",
        product="Energy",
        agent="Agent A · R. Kaul",
        team_lead="TL · M. Sethi",
        campaign="affiliate",
        site="Site A",
        call_datetime=_dt(_CALL_BASE_DATE, "14:02"),
        duration_sec=1800,
        state="scored",
        turns=[
            TurnSeed(
                "AGENT", 12, DISCLAIMER_PHRASE + ". Do you consent to the recording?"
            ),
            TurnSeed("CUSTOMER", 161, "Yes, that's me — I'm the account holder on the bill."),
            TurnSeed("AGENT", 200, "That's unit 7, 12 Barker Street — correct?"),
            TurnSeed("AGENT", 595, DMO_PHRASE + "."),
            TurnSeed(
                "AGENT",
                842,
                "So your peak usage will be charged at 28.6 cents per kilowatt hour, and off-peak sits lower than that.",
                kind="fail",
            ),
            TurnSeed("SYSTEM", 1110, "[silence 18:30 → 19:17 · 47s dead air]", kind="note"),
            TurnSeed(
                "AGENT", 1330, "Let me read that back — j.smith@gmial.com, is that right?", kind="fail"
            ),
            TurnSeed("AGENT", 1540, "Here are the terms and conditions that apply to this plan."),
            TurnSeed("AGENT", 1618, "You have a ten business day cooling-off period from today."),
        ],
    ),
    LeadSeed(
        id="3613803",
        scenario_tag="Lead C",
        scenario_summary="Address mismatch · hold",
        retailer="Retailer 2",
        product="Energy",
        agent="Agent C · P. Nair",
        team_lead="TL · M. Sethi",
        campaign="paid_search",
        site="Site B",
        call_datetime=_dt(_CALL_BASE_DATE, "11:48"),
        duration_sec=1440,
        state="scored",
        turns=[
            TurnSeed("AGENT", 12, DISCLAIMER_PHRASE + "."),
            TurnSeed("AGENT", 200, "That's unit 4, 12 Barker Street — correct?", kind="fail"),
            TurnSeed("CUSTOMER", 245, "Date of birth is the 11th of March, 1988."),
            TurnSeed("AGENT", 595, DMO_PHRASE + "."),
            TurnSeed("AGENT", 842, "Peak is 31.9 cents per kilowatt hour, off-peak is lower."),
            TurnSeed("AGENT", 1330, "Reading your email back: j.smith@gmail.com."),
        ],
    ),
    LeadSeed(
        id="3613811",
        scenario_tag="Lead D",
        scenario_summary="Low confidence · QA review",
        retailer="Retailer 1",
        product="Energy",
        agent="Agent B · D. Aurora",
        team_lead="TL · K. Rao",
        campaign="inbound",
        site="Site A",
        call_datetime=_dt(_CALL_BASE_DATE, "13:20"),
        duration_sec=1680,
        state="scored",
        turns=[
            TurnSeed("AGENT", 12, DISCLAIMER_PHRASE + "."),
            TurnSeed("AGENT", 200, "That's unit 7, 12 Barker Street — correct?"),
            TurnSeed(
                "AGENT",
                588,
                "The Default Market Offer for your [crosstalk] compared to the plan we discussed…",
                kind="review",
            ),
            TurnSeed(
                "CUSTOMER", 606, "Sorry — say that again, the line dropped out for a second.", kind="review"
            ),
            TurnSeed("AGENT", 842, "Peak is 31.9 cents per kilowatt hour, off-peak is lower."),
            TurnSeed("AGENT", 1025, "Is anyone at the property registered for life support equipment?"),
            TurnSeed("AGENT", 1330, "Reading your email back: j.smith@gmail.com."),
        ],
    ),
    LeadSeed(
        id="3613824",
        scenario_tag="Lead E",
        scenario_summary="Behaviour note only · auto-submit",
        retailer="Retailer 3",
        product="Broadband",
        agent="Agent D · S. Iyer",
        team_lead="TL · K. Rao",
        campaign="owned_site",
        site="Site C",
        call_datetime=_dt(_CALL_BASE_DATE, "10:05"),
        duration_sec=1260,
        state="scored",
        turns=[
            TurnSeed("AGENT", 10, DISCLAIMER_PHRASE + "."),
            TurnSeed("AGENT", 200, "That's unit 7, 12 Barker Street — correct?"),
            TurnSeed("AGENT", 595, DMO_PHRASE + "."),
            TurnSeed("AGENT", 734, "[silence 12:14 → 12:52 · 38s dead air]", kind="note"),
            TurnSeed("SYSTEM", 734, "[silence 12:14 → 12:52 · 38s dead air]", kind="note"),
            TurnSeed("AGENT", 842, "Peak is 31.9 cents per kilowatt hour, off-peak is lower."),
            TurnSeed("AGENT", 1170, "Your connection date is confirmed for the 24th."),
            TurnSeed("AGENT", 1330, "Reading your email back: j.smith@gmail.com."),
        ],
    ),
    LeadSeed(
        id="3613766",
        scenario_tag="Lead F",
        scenario_summary="Human override · audit trail",
        retailer="Retailer 1",
        product="Energy",
        agent="Agent A · R. Kaul",
        team_lead="TL · M. Sethi",
        campaign="affiliate",
        site="Site A",
        call_datetime=_dt(dt.date(2026, 9, 17), "16:44"),
        duration_sec=1560,
        state="scored",
        turns=[
            TurnSeed("AGENT", 12, DISCLAIMER_PHRASE + "."),
            TurnSeed("AGENT", 200, "That's unit 7, 12 Barker Street — correct?"),
            TurnSeed("AGENT", 595, DMO_PHRASE + "."),
            TurnSeed("AGENT", 842, "Peak is 30.9 cents per kilowatt hour.", kind="fail"),
            TurnSeed("CUSTOMER", 1660, "My paperwork says 31.9, not 30.9.", kind="note"),
            TurnSeed("AGENT", 1672, "You're right — sorry, that's 31.9 cents peak.", kind="pass"),
            TurnSeed("AGENT", 1330, "Reading your email back: j.smith@gmail.com."),
        ],
        pre_seeded_override={
            "human_decision": "PASS",
            "reason": "Customer corrected the rate at 27:40 and the agent re-confirmed 31.9c. The failing line predates the correction.",
            "reviewer_name": "S. Bhandari",
            "reviewer_role": "QA Analyst",
            "at": _dt(dt.date(2026, 9, 17), "17:31"),
        },
    ),
    LeadSeed(
        id="3613778",
        scenario_tag="Lead G",
        scenario_summary="Repeat critical failure ×3",
        retailer="Retailer 1",
        product="Energy",
        agent="Agent B · D. Aurora",
        team_lead="TL · K. Rao",
        campaign="inbound",
        site="Site A",
        call_datetime=_dt(_CALL_BASE_DATE, "15:10"),
        duration_sec=1740,
        state="scored",
        turns=[
            TurnSeed(
                "AGENT",
                4,
                "Hi, am I speaking with the account holder? Great, let's look at your bill.",
                kind="fail",
            ),
            TurnSeed("CUSTOMER", 130, "Sure, I've got it here in front of me."),
            TurnSeed("AGENT", 200, "That's unit 7, 12 Barker Street — correct?"),
            TurnSeed("AGENT", 372, "Can you read me the NMI from the top right of that bill?"),
            TurnSeed("AGENT", 595, DMO_PHRASE + "."),
            TurnSeed("AGENT", 842, "Peak is 31.9 cents per kilowatt hour, off-peak is lower."),
            TurnSeed("AGENT", 1330, "Reading your email back: j.smith@gmail.com."),
        ],
    ),
    LeadSeed(
        id="3613830",
        scenario_tag="Lead H",
        scenario_summary="Scoring in progress",
        retailer="Retailer 2",
        product="Energy",
        agent="Agent C · P. Nair",
        team_lead="TL · M. Sethi",
        campaign="paid_search",
        site="Site B",
        call_datetime=_dt(_CALL_BASE_DATE, "15:38"),
        duration_sec=1500,
        state="processing",
    ),
    LeadSeed(
        id="3613834",
        scenario_tag="Lead I",
        scenario_summary="Ingest error · partial data",
        retailer="Retailer 3",
        product="Broadband",
        agent="Agent D · S. Iyer",
        team_lead="TL · K. Rao",
        campaign="owned_site",
        site="Site C",
        call_datetime=_dt(_CALL_BASE_DATE, "09:41"),
        duration_sec=0,
        state="error",
        ingest_error={
            "code": "E_EMPTY_MEDIA",
            "message": (
                "The dialler returned a 0-byte recording on the ingest callback. Nothing was scored, and the sale "
                "has not been submitted — it is held pending a usable artifact rather than passed by default."
            ),
            "retry": "2 of 3",
            "at": "09:41:06",
        },
    ),
]

# Two extra "history" calls for Agent B · D. Aurora, same critical check
# (Recording disclaimer) failing, dated inside the 7-day window before Lead
# G's call — so Lead G's repeat-offence flag is a genuinely computed rolling
# count (2 prior + Lead G itself = 3), not a hard-coded boolean.
REPEAT_OFFENCE_HISTORY: list[LeadSeed] = [
    LeadSeed(
        id="3613700",
        scenario_tag="",
        scenario_summary="",
        retailer="Retailer 1",
        product="Energy",
        agent="Agent B · D. Aurora",
        team_lead="TL · K. Rao",
        campaign="inbound",
        site="Site A",
        call_datetime=_dt(dt.date(2026, 9, 14), "10:00"),
        duration_sec=900,
        state="scored",
        turns=[
            TurnSeed("AGENT", 4, "Hi there, let's get started on your bill.", kind="fail"),
            TurnSeed("AGENT", 595, DMO_PHRASE + "."),
            TurnSeed("AGENT", 842, "Peak is 31.9 cents per kilowatt hour, off-peak is lower."),
        ],
    ),
    LeadSeed(
        id="3613715",
        scenario_tag="",
        scenario_summary="",
        retailer="Retailer 1",
        product="Energy",
        agent="Agent B · D. Aurora",
        team_lead="TL · K. Rao",
        campaign="inbound",
        site="Site A",
        call_datetime=_dt(dt.date(2026, 9, 16), "10:00"),
        duration_sec=900,
        state="scored",
        turns=[
            TurnSeed("AGENT", 4, "Morning, is this a good time to chat about your account?", kind="fail"),
            TurnSeed("AGENT", 595, DMO_PHRASE + "."),
            TurnSeed("AGENT", 842, "Peak is 31.9 cents per kilowatt hour, off-peak is lower."),
        ],
    ),
]


# ---- the one checklist export in hand: Retailer 1, Energy, v1.4 ----

CHECK_CATALOGUE: list[dict] = [
    {
        "code": "RET1-VB-001", "name": "Recording disclaimer", "type": "Verbatim", "critical": True,
        "source_of_truth": "Approved script v1.4 §1",
        "config": {"expected_phrase": DISCLAIMER_PHRASE, "expected_label": "Verbatim disclaimer before any capture",
                   "window_start": 0, "window_end": 60, "expected_timestamp": 12, "default_confidence": 0.97},
    },
    {
        "code": "RET1-FM-002", "name": "Account holder confirmed", "type": "Factual", "critical": True,
        "source_of_truth": "CRM · account_holder", "config": {"default_confidence": 0.99},
    },
    {
        "code": "RET1-FM-003", "name": "Address match", "type": "Factual", "critical": True,
        "source_of_truth": "CRM · service_address",
        "config": {"field": "address", "pattern": r"(unit\s*\d+,?\s*\d+\s+\w+\s+street)", "kind": "text",
                   "window_start": 150, "window_end": 300, "source_label": "CRM · service_address",
                   "extraction_confidence": 0.95},
    },
    {
        "code": "RET1-FM-004", "name": "DOB match", "type": "Factual", "critical": True,
        "source_of_truth": "CRM · date_of_birth", "config": {"default_confidence": 0.97},
    },
    {
        "code": "RET1-FM-005", "name": "Fuel type", "type": "Factual", "critical": True,
        "source_of_truth": "CRM · fuel_type", "config": {"default_confidence": 0.99},
    },
    {
        "code": "RET1-FM-006", "name": "NMI / MIRN verified", "type": "Factual", "critical": True,
        "source_of_truth": "CRM · nmi", "config": {"default_confidence": 0.93},
    },
    {
        "code": "RET1-VB-007", "name": "DMO read verbatim", "type": "Verbatim", "critical": True,
        "source_of_truth": "Approved script v1.4 §4",
        "config": {"expected_phrase": DMO_PHRASE, "expected_label": "DMO paragraph read verbatim",
                   "window_start": 500, "window_end": 700, "expected_timestamp": 595, "default_confidence": 0.97},
    },
    {
        "code": "RET1-FM-008", "name": "Rates and charges", "type": "Factual", "critical": True,
        "source_of_truth": "Retailer 1 rate card · plan EN-A2",
        "config": {"field": "peak_rate_cents", "pattern": r"(\d+\.?\d*)\s*cents?", "kind": "numeric",
                   "unit": "c / kWh peak", "tolerance": 0.0, "window_start": 700, "window_end": 1000,
                   "source_label": "Retailer 1 rate card · plan EN-A2", "extraction_confidence": 0.98},
    },
    {
        "code": "RET1-FM-009", "name": "Concession applied", "type": "Factual", "critical": False,
        "source_of_truth": "CRM · concession_flag", "config": {"default_confidence": 0.91},
    },
    {
        "code": "RET1-FM-010", "name": "Life support declared", "type": "Factual", "critical": True,
        "source_of_truth": "CRM · life_support", "config": {"default_confidence": 0.99},
    },
    {
        "code": "RET1-BH-011", "name": "Dead air", "type": "Behaviour", "critical": False,
        "source_of_truth": "Transcript only",
        "config": {"metric": "dead_air", "threshold_seconds": 30, "default_confidence": 0.94},
    },
    {
        "code": "RET1-FM-012", "name": "Move-in date", "type": "Factual", "critical": False,
        "source_of_truth": "CRM · move_in_date", "config": {"default_confidence": 0.95},
    },
    {
        "code": "RET1-FM-013", "name": "Email captured", "type": "Factual", "critical": True,
        "source_of_truth": "CRM · email",
        "config": {"field": "email", "pattern": r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", "kind": "email",
                   "window_start": 1200, "window_end": 1500, "source_label": "CRM · email",
                   "extraction_confidence": 0.96},
    },
    {
        "code": "RET1-FM-014", "name": "Gift card value", "type": "Factual", "critical": False,
        "source_of_truth": "Retailer 1 promo table", "config": {"default_confidence": 0.92},
    },
    {
        "code": "RET1-VB-015", "name": "T&Cs read", "type": "Verbatim", "critical": True,
        "source_of_truth": "Approved script v1.4 §9", "config": {"default_confidence": 0.96},
    },
    {
        "code": "RET1-VB-016", "name": "EIC provided", "type": "Verbatim", "critical": False,
        "source_of_truth": "Approved script v1.4 §10", "config": {"default_confidence": 0.94},
    },
    {
        "code": "RET1-VB-017", "name": "Cooling-off rights", "type": "Verbatim", "critical": True,
        "source_of_truth": "Approved script v1.4 §11", "config": {"default_confidence": 0.95},
    },
    {
        "code": "RET1-BH-018", "name": "Rapport", "type": "Behaviour", "critical": False,
        "source_of_truth": "Transcript only", "config": {"default_confidence": 0.88},
    },
    {
        "code": "RET1-BH-019", "name": "Interruptions", "type": "Behaviour", "critical": False,
        "source_of_truth": "Transcript only", "config": {"default_confidence": 0.90},
    },
    {
        "code": "RET1-BH-020", "name": "Objection handling", "type": "Behaviour", "critical": False,
        "source_of_truth": "Transcript only", "config": {"default_confidence": 0.86},
    },
]

WEIGHT_BY_TYPE = {"Verbatim": 8, "Factual": 10, "Behaviour": 3}

RETAILERS = ["Retailer 1", "Retailer 2", "Retailer 3"]

RULE_SETS = [
    {"retailer": "Retailer 1", "checklist": "Energy QA checklist", "version": "v1.4",
     "effective_from": dt.date(2026, 9, 1), "live": True, "has_checks": True},
    {"retailer": "Retailer 1", "checklist": "Energy QA checklist", "version": "v1.3",
     "effective_from": dt.date(2026, 6, 15), "live": False, "has_checks": False},
    {"retailer": "Retailer 2", "checklist": "Energy QA checklist", "version": "v2.1",
     "effective_from": dt.date(2026, 8, 12), "live": True, "has_checks": False},
    {"retailer": "Retailer 3", "checklist": "Broadband QA checklist", "version": "v1.0",
     "effective_from": dt.date(2026, 7, 1), "live": True, "has_checks": False},
]


# ---- bulk synthetic backfill, purely for realistic dashboard/calibration
# volume (brief §31: "computed from stored synthetic records rather than
# hard-coded dashboard numbers") ----

_AGENTS = [
    ("Agent A · R. Kaul", "TL · M. Sethi", "Retailer 1", "Energy"),
    ("Agent B · D. Aurora", "TL · K. Rao", "Retailer 1", "Energy"),
    ("Agent C · P. Nair", "TL · M. Sethi", "Retailer 2", "Energy"),
    ("Agent D · S. Iyer", "TL · K. Rao", "Retailer 3", "Broadband"),
    ("Agent E · N. Verma", "TL · M. Sethi", "Retailer 1", "Energy"),
]
_CAMPAIGNS = ["owned_site", "affiliate", "paid_search", "inbound"]
_SITES = ["Site A", "Site B", "Site C"]


def generate_bulk_leads(count: int, *, seed: int = 42, start_id: int = 4000000) -> list[LeadSeed]:
    """Lightweight synthetic leads (no rich transcript authored by hand) —
    just enough randomized-but-plausible check outcomes to make dashboard
    and calibration aggregates meaningful at more than a 9-row scale. These
    are evaluated the same way as the named scenarios, through the same
    pipeline, just seeded with a smaller synthetic transcript."""
    rng = random.Random(seed)
    leads: list[LeadSeed] = []
    for i in range(count):
        agent, tl, retailer, product = rng.choice(_AGENTS)
        campaign = rng.choice(_CAMPAIGNS)
        site = rng.choice(_SITES)
        day_offset = rng.randint(0, 6)
        call_dt = _dt(_CALL_BASE_DATE, "09:00") - dt.timedelta(days=day_offset, minutes=rng.randint(0, 500))
        lead_id = str(start_id + i)

        roll = rng.random()
        rate_spoken = 31.9 if roll > 0.15 else round(rng.uniform(25.0, 30.0), 1)
        email_spoken = "j.smith@gmail.com" if roll > 0.10 else "j.smith@gmial.com"
        address_spoken = "unit 7, 12 barker street" if roll > 0.08 else "unit 4, 12 barker street"
        add_dead_air = rng.random() < 0.12
        crosstalk = rng.random() < 0.08

        turns = [
            TurnSeed("AGENT", 12, DISCLAIMER_PHRASE + "."),
            TurnSeed("AGENT", 200, f"That's {address_spoken} — correct?"),
            TurnSeed(
                "AGENT",
                588 if crosstalk else 595,
                (f"The Default Market Offer for your [crosstalk] compared to the plan we discussed…" if crosstalk else DMO_PHRASE + "."),
            ),
            TurnSeed("AGENT", 842, f"Peak is {rate_spoken} cents per kilowatt hour, off-peak is lower."),
            TurnSeed("AGENT", 1330, f"Reading your email back: {email_spoken}."),
        ]
        if add_dead_air:
            turns.append(TurnSeed("SYSTEM", 1110, "[silence 18:30 → 19:17 · 45s dead air]", kind="note"))

        leads.append(
            LeadSeed(
                id=lead_id,
                scenario_tag="",
                scenario_summary="",
                retailer=retailer,
                product=product,
                agent=agent,
                team_lead=tl,
                campaign=campaign,
                site=site,
                call_datetime=call_dt,
                duration_sec=rng.randint(900, 1900),
                state="scored",
                turns=turns,
            )
        )
    return leads
