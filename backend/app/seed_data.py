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
TCS_PHRASE = "Here are the terms and conditions that apply to this plan"
EIC_PHRASE = "I confirm you understand and want to proceed with this offer today"
COOLING_OFF_PHRASE = "You have a ten business day cooling-off period from today"

DEFAULT_CRM = {
    "peak_rate_cents": 31.9,
    "email": "j.smith@gmail.com",
    "address": "Unit 7, 12 Barker Street",
    "date_of_birth": "11th of march, 1988",
    "fuel_type": "electricity",
    "nmi": "6305432101",
    "life_support": False,
    "move_in_date": "24",
    "concession_flag": False,
    "gift_card_value": None,
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


def common_turns(
    *,
    disclaimer: str | None = DISCLAIMER_PHRASE + ".",
    disclaimer_start: float = 12,
    account_holder: str | None = "Yes, that's me — I'm the account holder on the bill.",
    address: str | None = "Unit 7, 12 Barker Street",
    dob: str | None = "Date of birth is the 11th of March, 1988.",
    dmo_mode: str = "pass",  # "pass" | "crosstalk" | "absent"
    fuel_type: str | None = "electricity",
    nmi: str | None = "6305432101",
    rate_value: str | None = "31.9",
    life_support_asked: bool = True,
    life_support_answered: bool = True,
    dead_air_seconds: int | None = None,
    dead_air_start: str = "18:30",
    dead_air_end: str = "19:17",
    move_in_day: str | None = "24",
    email_value: str | None = "j.smith@gmail.com",
    gift_card_line: str | None = None,
    objection: str | None = None,
    objection_response: str | None = None,
    tcs: bool = True,
    eic: bool = True,
    cooling_off: bool = True,
) -> list[TurnSeed]:
    """The boilerplate, ordinarily-compliant turns shared by every lead's
    call flow. Each named scenario below calls this with only the
    parameters its narrative actually overrides — everything else stays
    at the "clean call" default, so every check other than the one(s) the
    scenario is about genuinely evaluates to PASS from real transcript
    content, not a hand-set status."""
    turns: list[TurnSeed] = []

    if disclaimer is not None:
        turns.append(TurnSeed("AGENT", disclaimer_start, disclaimer, kind="fail" if disclaimer_start != 12 else "pass"))

    if account_holder is not None:
        turns.append(TurnSeed("CUSTOMER", 150, account_holder))

    if address is not None:
        turns.append(TurnSeed("AGENT", 200, f"That's {address} — correct?"))

    if dob is not None:
        turns.append(TurnSeed("CUSTOMER", 245, dob))

    if fuel_type is not None:
        turns.append(TurnSeed("AGENT", 280, f"Just confirming this connection is for {fuel_type} — that's right?"))

    if nmi is not None:
        turns.append(TurnSeed("CUSTOMER", 320, f"The NMI is {nmi}."))

    if dmo_mode == "pass":
        turns.append(TurnSeed("AGENT", 595, DMO_PHRASE + "."))
    elif dmo_mode == "crosstalk":
        # Genuine overlapping timestamps (not just a text marker): the
        # customer's turn starts before the agent's turn ends, a real,
        # directly-measurable 2.0s overlap — the primary signal the
        # interruptions evaluator looks for.
        turns.append(
            TurnSeed(
                "AGENT", 588, "The Default Market Offer for your [crosstalk] compared to the plan we discussed…",
                kind="review", end=595.0,
            )
        )
        turns.append(
            TurnSeed(
                "CUSTOMER", 593.0, "Sorry — say that again, the line dropped out for a second.",
                kind="review", end=598.0,
            )
        )
    # dmo_mode == "absent": no DMO turn at all

    if rate_value is not None:
        turns.append(TurnSeed("AGENT", 842, f"Peak is {rate_value} cents per kilowatt hour, off-peak is lower."))

    if life_support_asked:
        turns.append(TurnSeed("AGENT", 1025, "Is anyone at the property registered for life support equipment?"))
        if life_support_answered:
            turns.append(TurnSeed("CUSTOMER", 1032, "No, nobody here needs that."))

    if dead_air_seconds:
        turns.append(
            TurnSeed(
                "SYSTEM", 1110, f"[silence {dead_air_start} → {dead_air_end} · {dead_air_seconds}s dead air]", kind="note"
            )
        )

    if move_in_day is not None:
        turns.append(TurnSeed("AGENT", 1170, f"Your connection date is confirmed for the {move_in_day}th."))

    if email_value is not None:
        turns.append(TurnSeed("AGENT", 1330, f"Reading your email back: {email_value}."))

    if gift_card_line is not None:
        turns.append(TurnSeed("AGENT", 1450, gift_card_line))

    if objection is not None:
        turns.append(TurnSeed("CUSTOMER", 1230, objection, kind="note"))
        if objection_response is not None:
            turns.append(TurnSeed("AGENT", 1245, objection_response))

    if tcs:
        turns.append(TurnSeed("AGENT", 1540, TCS_PHRASE + "."))

    if eic:
        turns.append(TurnSeed("AGENT", 1560, EIC_PHRASE + "."))

    if cooling_off:
        turns.append(TurnSeed("AGENT", 1618, COOLING_OFF_PHRASE + "."))

    return sorted(turns, key=lambda t: t.start)


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
        duration_sec=1700,
        state="scored",
        turns=common_turns(),
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
            *common_turns(
                rate_value="28.6",
                dead_air_seconds=47,
                email_value="j.smith@gmial.com",
            )
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
        duration_sec=1700,
        state="scored",
        turns=common_turns(address="Unit 4, 12 Barker Street"),
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
        turns=common_turns(dmo_mode="crosstalk"),
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
        duration_sec=1700,
        state="scored",
        turns=common_turns(
            disclaimer_start=10, dead_air_seconds=38, dead_air_start="12:14", dead_air_end="12:52",
            objection="Actually, that sounds too expensive for what we're using right now.",
            objection_response="I understand — let me show you the lower-usage plan that would cut that down.",
        ),
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
        duration_sec=1740,
        state="scored",
        turns=[
            *common_turns(rate_value="30.9"),
            TurnSeed("CUSTOMER", 1660, "My paperwork says 31.9, not 30.9.", kind="note"),
            TurnSeed("AGENT", 1672, "You're right — sorry, that's 31.9 cents peak.", kind="pass"),
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
        # The opening never reads the approved disclaimer AND never gets a
        # clean account-holder confirmation either — both are genuinely
        # absent from this transcript, not hand-flagged: disclaimer FAILs
        # (confidently absent), account-holder-confirmed correctly comes
        # back NOT_EVALUABLE/REVIEW (a keyword miss isn't proof it didn't
        # happen) rather than a fabricated FAIL or PASS.
        turns=common_turns(
            disclaimer="Hi, am I speaking with the account holder? Great, let's look at your bill.",
            disclaimer_start=4,
            account_holder=None,
        ),
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
        turns=common_turns(disclaimer="Hi there, let's get started on your bill.", disclaimer_start=4, account_holder=None),
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
        turns=common_turns(
            disclaimer="Morning, is this a good time to chat about your account?", disclaimer_start=4, account_holder=None
        ),
    ),
]


# ---- the one checklist export in hand: Retailer 1, Energy, v1.4 ----
#
# All 20 checks resolve to a real evaluator strategy + configuration —
# none silently defaults to PASS. Where the supplied synthetic data
# genuinely can't support bespoke verification (the three "Behaviour"
# heuristics below are honestly limited, not fabricated — see
# evaluators/behaviour.py), the check still runs a real, documented,
# non-fabricated computation, never a placeholder.

CHECK_CATALOGUE: list[dict] = [
    {
        "code": "RET1-VB-001", "name": "Recording disclaimer", "type": "Verbatim", "critical": True,
        "source_of_truth": "Approved script v1.4 §1",
        "config": {"expected_phrase": DISCLAIMER_PHRASE, "expected_label": "Verbatim disclaimer before any capture",
                   "window_start": 0, "window_end": 60, "expected_timestamp": 12, "default_confidence": 0.97},
    },
    {
        "code": "RET1-FM-002", "name": "Account holder confirmed", "type": "Factual", "critical": True,
        "source_of_truth": "CRM · account_holder",
        "config": {"kind": "presence", "pattern": r"(that'?s me|i'?m the account holder|yes,?\s*(that'?s|this is) (me|correct))",
                   "speaker": "CUSTOMER", "window_start": 0, "window_end": 400,
                   "expected_label": "Customer confirms they are the account holder", "extraction_confidence": 0.97},
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
        "source_of_truth": "CRM · date_of_birth",
        "config": {"field": "date_of_birth", "kind": "text", "speaker": "CUSTOMER", "window_start": 200, "window_end": 320,
                   "pattern": r"(\d{1,2}(?:st|nd|rd|th)?\s+of\s+\w+,?\s+\d{4}|\d{1,2}\s+\w+\s+\d{4})",
                   "source_label": "CRM · date_of_birth", "extraction_confidence": 0.9},
    },
    {
        "code": "RET1-FM-005", "name": "Fuel type", "type": "Factual", "critical": True,
        "source_of_truth": "CRM · fuel_type",
        "config": {"field": "fuel_type", "pattern": r"\b(electricity|gas|dual fuel)\b", "kind": "text",
                   "speaker": "ANY", "window_start": 250, "window_end": 350, "source_label": "CRM · fuel_type",
                   "extraction_confidence": 0.96},
    },
    {
        "code": "RET1-FM-006", "name": "NMI / MIRN verified", "type": "Factual", "critical": True,
        "source_of_truth": "CRM · nmi",
        "config": {"field": "nmi", "pattern": r"\b(\d{10,11})\b", "kind": "text", "speaker": "ANY",
                   "window_start": 280, "window_end": 400, "source_label": "CRM · nmi", "extraction_confidence": 0.93},
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
        "source_of_truth": "CRM · concession_flag",
        "config": {"field": "concession_flag", "pattern": r"(concession|pensioner|health care card)", "kind": "text",
                   "speaker": "ANY", "skip_if_absent": True, "source_label": "CRM · concession_flag",
                   "default_confidence": 0.91, "extraction_confidence": 0.9},
    },
    {
        "code": "RET1-FM-010", "name": "Life support declared", "type": "Factual", "critical": True,
        "source_of_truth": "CRM · life_support",
        "config": {"kind": "presence",
                   "pattern": r"(no,?\s*nobody|no one (here|at the property)|yes,?\s*(i|someone|my \w+) (do|does|is|am))",
                   "speaker": "CUSTOMER", "window_start": 1000, "window_end": 1060,
                   "expected_label": "Customer answers the life-support question (asked alone isn't enough)",
                   "extraction_confidence": 0.98},
    },
    {
        "code": "RET1-BH-011", "name": "Dead air", "type": "Behaviour", "critical": False,
        "source_of_truth": "Transcript only",
        "config": {"metric": "dead_air", "threshold_seconds": 30, "default_confidence": 0.94},
    },
    {
        "code": "RET1-FM-012", "name": "Move-in date", "type": "Factual", "critical": False,
        "source_of_truth": "CRM · move_in_date",
        "config": {"field": "move_in_date", "pattern": r"confirmed for the (\d{1,2})(?:st|nd|rd|th)?",
                   "kind": "text", "speaker": "AGENT", "window_start": 1100, "window_end": 1250,
                   "source_label": "CRM · move_in_date", "extraction_confidence": 0.95},
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
        "source_of_truth": "Retailer 1 promo table",
        "config": {"field": "gift_card_value", "pattern": r"\$(\d+)\s*gift card", "kind": "numeric", "unit": " gift card",
                   "tolerance": 0, "speaker": "ANY", "skip_if_absent": True, "source_label": "Retailer 1 promo table",
                   "default_confidence": 0.92, "extraction_confidence": 0.9},
    },
    {
        "code": "RET1-VB-015", "name": "T&Cs read", "type": "Verbatim", "critical": True,
        "source_of_truth": "Approved script v1.4 §9",
        "config": {"expected_phrase": TCS_PHRASE, "expected_label": "T&Cs statement read verbatim",
                   "window_start": 1500, "window_end": 1600, "expected_timestamp": 1540, "default_confidence": 0.96},
    },
    {
        "code": "RET1-VB-016", "name": "EIC provided", "type": "Verbatim", "critical": False,
        "source_of_truth": "Approved script v1.4 §10",
        "config": {"expected_phrase": EIC_PHRASE, "expected_label": "Explicit informed consent statement read",
                   "window_start": 1500, "window_end": 1620, "expected_timestamp": 1560, "default_confidence": 0.94},
    },
    {
        "code": "RET1-VB-017", "name": "Cooling-off rights", "type": "Verbatim", "critical": True,
        "source_of_truth": "Approved script v1.4 §11",
        "config": {"expected_phrase": COOLING_OFF_PHRASE, "expected_label": "Cooling-off rights read verbatim",
                   "window_start": 1580, "window_end": 1700, "expected_timestamp": 1618, "default_confidence": 0.95},
    },
    {
        "code": "RET1-BH-018", "name": "Rapport", "type": "Behaviour", "critical": False,
        "source_of_truth": "Transcript only",
        "config": {"metric": "rapport", "min_customer_share": 0.08, "default_confidence": 0.88},
    },
    {
        "code": "RET1-BH-019", "name": "Interruptions", "type": "Behaviour", "critical": False,
        "source_of_truth": "Transcript only",
        "config": {"metric": "interruptions", "threshold_count": 2, "default_confidence": 0.9},
    },
    {
        "code": "RET1-BH-020", "name": "Objection handling", "type": "Behaviour", "critical": False,
        "source_of_truth": "Transcript only",
        "config": {"metric": "objection_handling", "default_confidence": 0.86},
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
    """Lightweight synthetic leads (no rich hand-authored narrative) — just
    enough randomized-but-plausible check outcomes to make dashboard and
    calibration aggregates meaningful at more than a 9-row scale. Run
    through the same `common_turns` builder and the same real pipeline as
    the named scenarios."""
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
        rate_spoken = "31.9" if roll > 0.15 else str(round(rng.uniform(25.0, 30.0), 1))
        email_spoken = "j.smith@gmail.com" if roll > 0.10 else "j.smith@gmial.com"
        address_spoken = "Unit 7, 12 Barker Street" if roll > 0.08 else "Unit 4, 12 Barker Street"
        dmo_mode = "crosstalk" if rng.random() < 0.05 else "pass"
        dead_air = 45 if rng.random() < 0.12 else None

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
                turns=common_turns(
                    rate_value=rate_spoken, email_value=email_spoken, address=address_spoken,
                    dmo_mode=dmo_mode, dead_air_seconds=dead_air,
                ),
            )
        )
    return leads
