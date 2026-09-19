"""
Dashboard aggregation, computed from stored records — never hard-coded
numbers (brief §31). Every figure below is a real query over the seeded
Lead/CheckResult/GateDecision/HumanReview tables.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..enums import Decision, LeadState, ResultStatus
from ..models import CalibrationSample, Check, CheckResult, GateDecision, HumanReview, Lead


def _fmt_int(n: int) -> str:
    return f"{n:,}"


def _pct(part: int, total: int) -> float:
    return round((part / total) * 100, 1) if total else 0.0


def get_dashboard(db: Session) -> dict:
    total_scored = db.execute(select(func.count(Lead.id)).where(Lead.state == LeadState.SCORED)).scalar_one()

    decision_counts: dict[str, int] = {d: 0 for d in (Decision.AUTO_SUBMIT, Decision.HOLD, Decision.QA_REVIEW)}
    for decision, count in db.execute(
        select(GateDecision.decision, func.count(GateDecision.id)).group_by(GateDecision.decision)
    ):
        decision_counts[decision] = count

    auto_submitted = decision_counts[Decision.AUTO_SUBMIT]
    held = decision_counts[Decision.HOLD]
    qa_review = decision_counts[Decision.QA_REVIEW]

    total_checks = db.execute(select(func.count(CheckResult.id))).scalar_one()
    low_conf_checks = db.execute(
        select(func.count(CheckResult.id)).where(CheckResult.confidence < settings.confidence_floor)
    ).scalar_one()

    repeat_agents = db.execute(
        select(func.count(func.distinct(Lead.agent))).where(Lead.repeat_offence.is_(True))
    ).scalar_one()

    sampled_count = db.execute(select(func.count(CalibrationSample.id))).scalar_one()

    kpis = [
        {"label": "Sales scored", "value": _fmt_int(total_scored), "unit": "", "sub": "Automatically, before submission", "tone": "default"},
        {"label": "Auto-submitted", "value": _fmt_int(auto_submitted), "unit": f"{_pct(auto_submitted, total_scored)}%", "sub": "First-pass yield, no rework", "tone": "pass"},
        {"label": "Held", "value": _fmt_int(held), "unit": f"{_pct(held, total_scored)}%", "sub": "Critical fail → TL queue", "tone": "fail"},
        {"label": "QA review", "value": _fmt_int(qa_review), "unit": f"{_pct(qa_review, total_scored)}%", "sub": "Low confidence, never auto-passed", "tone": "review"},
        {"label": "Critical fail rate", "value": f"{_pct(held, total_scored)}", "unit": "%", "sub": "Rates and email lead the failures", "tone": "default"},
        {"label": "Low-confidence checks", "value": f"{_pct(low_conf_checks, total_checks)}", "unit": "%", "sub": f"Of {_fmt_int(total_checks)} checks executed", "tone": "default"},
        {"label": "Repeat offences", "value": _fmt_int(repeat_agents), "unit": "agents", "sub": "Same critical failing 3+ times in 7 days", "tone": "fail"},
        {"label": "Sampled clean calls", "value": _fmt_int(sampled_count), "unit": f"{int(settings.clean_sample_rate * 100)}%", "sub": "Human-audited for calibration", "tone": "accent"},
    ]

    distribution = [
        {"label": "AUTO-SUBMIT", "count": _fmt_int(auto_submitted), "pct": f"{_pct(auto_submitted, total_scored)}%", "pctValue": _pct(auto_submitted, total_scored), "tone": "pass"},
        {"label": "HOLD", "count": _fmt_int(held), "pct": f"{_pct(held, total_scored)}%", "pctValue": _pct(held, total_scored), "tone": "fail"},
        {"label": "QA REVIEW", "count": _fmt_int(qa_review), "pct": f"{_pct(qa_review, total_scored)}%", "pctValue": _pct(qa_review, total_scored), "tone": "review"},
    ]
    distribution = [{**row, "pct_value": row.pop("pctValue")} for row in distribution]

    failing_rows = db.execute(
        select(Check.name, Check.type, func.count(CheckResult.id).label("n"))
        .join(CheckResult, CheckResult.check_id == Check.id)
        .where(CheckResult.status == ResultStatus.FAIL)
        .group_by(Check.name, Check.type)
        .order_by(func.count(CheckResult.id).desc())
        .limit(5)
    ).all()
    failing_checks = [{"name": name, "type": type_, "count": n} for name, type_, n in failing_rows]

    recent_fail_leads = db.execute(
        select(Lead)
        .join(GateDecision, GateDecision.lead_id == Lead.id)
        .where(GateDecision.decision == Decision.HOLD)
        .order_by(Lead.call_datetime.desc())
        .limit(4)
    ).scalars().all()
    now = dt.datetime.fromisoformat(settings.demo_now)
    recent_failures = []
    for lead in recent_fail_leads:
        crit_fail = next((r for r in lead.results if r.check.critical and r.status == ResultStatus.FAIL), None)
        if crit_fail is None:
            continue
        mins = max(1, round((now - lead.call_datetime).total_seconds() / 60))
        age = f"{mins}m" if mins < 60 else (f"{round(mins/60)}h" if mins < 1440 else f"{round(mins/1440)}d")
        meta = f"{lead.retailer.name} · {lead.agent.split(' · ')[0]}"
        if lead.repeat_offence:
            meta += " · repeat ×3"
        elif lead.reviews:
            meta += " · overridden"
        recent_failures.append({"leadId": lead.id, "check": crit_fail.check.name, "meta": meta, "age": age})
    recent_failures = [{"lead_id": r.pop("leadId"), **r} for r in recent_failures]

    # "Recent human overrides" means genuine disagreements — a human
    # decision that actually differs from the AI's — not the routine
    # audits that simply confirmed the AI was right.
    candidate_reviews = db.execute(select(HumanReview).order_by(HumanReview.created_at.desc()).limit(50)).scalars().all()
    recent_review_rows = [r for r in candidate_reviews if _is_override(r.ai_decision, r.human_decision)][:3]
    recent_overrides = []
    for review in recent_review_rows:
        recent_overrides.append(
            {
                "lead_id": review.lead_id,
                "ai": _decision_label(review.ai_decision),
                "human": review.human_decision,
                "reason": review.reason,
                "who": review.reviewer_name,
                "time": review.created_at.strftime("%H:%M"),
            }
        )

    return {
        "kpis": kpis,
        "distribution": distribution,
        "failing_checks": failing_checks,
        "recent_failures": recent_failures,
        "recent_overrides": recent_overrides,
    }


def _decision_label(decision: str) -> str:
    return {"AUTO_SUBMIT": "AUTO-SUBMIT", "HOLD": "HOLD", "QA_REVIEW": "QA REVIEW"}.get(decision, decision)


def _is_override(ai_decision: str, human_decision: str) -> bool:
    ai_binary = "HOLD" if ai_decision == Decision.HOLD else "PASS"
    return ai_binary != human_decision
