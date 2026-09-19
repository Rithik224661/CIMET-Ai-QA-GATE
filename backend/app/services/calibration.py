"""
Calibration metrics, computed from stored HumanReview / GateDecision /
CheckResult data (brief §33). Critical false-pass is treated as the
release-blocking metric per the brief and is never allowed to look
better than what the stored reviews actually show.
"""

from __future__ import annotations

from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..enums import Decision, ResultStatus
from ..models import CheckResult, HumanReview

_BUCKET_EDGES = [0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 1.0]


def _agrees(ai_decision: str, human_decision: str) -> bool:
    """AI's decision maps to a binary PASS/HOLD for agreement purposes: a
    HOLD agrees with a human HOLD; anything else (AUTO_SUBMIT/QA_REVIEW)
    agrees with a human PASS."""
    ai_binary = "HOLD" if ai_decision == Decision.HOLD else "PASS"
    return ai_binary == human_decision


def get_calibration(db: Session) -> dict:
    reviews = db.execute(select(HumanReview)).scalars().all()
    total_reviews = len(reviews)

    agreements = sum(1 for r in reviews if _agrees(r.ai_decision, r.human_decision))
    agreement_pct = round((agreements / total_reviews) * 100, 1) if total_reviews else 0.0

    # critical false-pass: AI let it through (not HOLD) but a human review
    # on that lead said HOLD — the release-blocking failure mode.
    critical_false_pass = sum(1 for r in reviews if r.ai_decision != Decision.HOLD and r.human_decision == "HOLD")
    # critical false-fail: AI held it, a human reviewed and passed it anyway.
    critical_false_fail = sum(1 for r in reviews if r.ai_decision == Decision.HOLD and r.human_decision == "PASS")

    # auditor-to-auditor: leads with >=2 independent reviews (double-audited
    # calibration samples) — agreement between the first two reviewers.
    by_lead: dict[str, list[HumanReview]] = {}
    for r in reviews:
        by_lead.setdefault(r.lead_id, []).append(r)
    double_audited = [v for v in by_lead.values() if len(v) >= 2]
    if double_audited:
        auditor_agreements = sum(1 for pair in double_audited if pair[0].human_decision == pair[1].human_decision)
        auditor_pct = round((auditor_agreements / len(double_audited)) * 100, 1)
    else:
        auditor_pct = 0.0

    kpis = [
        {"label": "AI / auditor agreement", "value": f"{agreement_pct}", "unit": "%", "sub": f"{total_reviews} sampled calls", "tone": "pass"},
        {"label": "Critical false-pass", "value": str(critical_false_pass), "unit": "", "sub": "The release-blocking metric", "tone": "pass" if critical_false_pass == 0 else "review"},
        {"label": "Critical false-fail", "value": str(critical_false_fail), "unit": "", "sub": "Held sales a human then passed", "tone": "review"},
        {"label": "Auditor-to-auditor", "value": f"{auditor_pct}", "unit": "%", "sub": "Humans disagree with each other too", "tone": "default"},
    ]

    conf_rows = db.execute(select(CheckResult.confidence)).scalars().all()
    buckets = []
    bucket_max = 1
    for i, edge in enumerate(_BUCKET_EDGES):
        upper = _BUCKET_EDGES[i + 1] if i + 1 < len(_BUCKET_EDGES) else None
        if upper is None:
            count = sum(1 for c in conf_rows if c >= edge)
        else:
            count = sum(1 for c in conf_rows if edge <= c < upper)
        buckets.append({"label": str(edge), "count": count, "belowFloor": edge < settings.confidence_floor})
        bucket_max = max(bucket_max, count)
    buckets = [{"label": b["label"], "count": b["count"], "below_floor": b.pop("belowFloor")} for b in buckets]

    disagreeing = [r for r in reviews if not _agrees(r.ai_decision, r.human_decision)]
    category_counts: Counter[str] = Counter()
    for r in disagreeing:
        lead = r.lead
        deciding = next((res for res in lead.results if res.check.critical and res.status == ResultStatus.FAIL), None) or next(
            (res for res in lead.results if res.status == ResultStatus.REVIEW), None
        )
        label = f"{deciding.check.type} · {deciding.check.name.lower()}" if deciding else "Unclassified"
        category_counts[label] += 1

    disagreements = [{"name": name, "count": n} for name, n in category_counts.most_common(6)]
    disagreement_max = max([d["count"] for d in disagreements], default=1)

    return {
        "kpis": kpis,
        "confidence_buckets": buckets,
        "confidence_bucket_max": bucket_max,
        "disagreements": disagreements,
        "disagreement_max": disagreement_max,
        "sampled_calls_total": total_reviews,
        "sampled_disagreements_total": len(disagreeing),
    }
