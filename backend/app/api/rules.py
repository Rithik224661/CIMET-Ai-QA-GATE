from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..db import get_db
from ..models import Checklist, RuleVersion
from ..schemas import ChecksOut, CheckDefinitionOut, RuleSetsOut, RuleSetVersionOut

router = APIRouter(tags=["rules"])


def _rule_set_query():
    return (
        select(RuleVersion)
        .options(joinedload(RuleVersion.checklist).joinedload(Checklist.retailer), joinedload(RuleVersion.checks))
        .order_by(RuleVersion.id)
    )


@router.get("/api/rules", response_model=RuleSetsOut)
def list_rule_sets(db: Session = Depends(get_db)):
    versions = db.execute(_rule_set_query()).unique().scalars().all()
    return RuleSetsOut(
        rule_sets=[
            RuleSetVersionOut(
                retailer=v.checklist.retailer.name,
                checklist=v.checklist.name,
                version=v.version,
                effective_from=v.effective_from.isoformat(),
                live=v.live,
            )
            for v in versions
        ]
    )


@router.get("/api/rules/{rule_version_id}", response_model=RuleSetVersionOut)
def get_rule_set(rule_version_id: int, db: Session = Depends(get_db)):
    v = db.execute(_rule_set_query().where(RuleVersion.id == rule_version_id)).unique().scalar_one_or_none()
    if v is None:
        raise HTTPException(status_code=404, detail="rule version not found")
    return RuleSetVersionOut(
        retailer=v.checklist.retailer.name,
        checklist=v.checklist.name,
        version=v.version,
        effective_from=v.effective_from.isoformat(),
        live=v.live,
    )


@router.get("/api/checks", response_model=ChecksOut)
def list_checks(db: Session = Depends(get_db)):
    """The one checklist export in hand (Retailer 1 energy, v1.4) — every
    rule set currently resolves to it in this build, matching the
    frontend's Phase 1 fixture behavior. See docs/DECISIONS.md."""
    live_version = db.execute(
        select(RuleVersion).options(joinedload(RuleVersion.checks)).where(RuleVersion.live.is_(True)).order_by(RuleVersion.id)
    ).unique().scalars().first()
    if live_version is None:
        return ChecksOut(checks=[])
    return ChecksOut(
        checks=[
            CheckDefinitionOut(
                code=c.code, name=c.name, type=c.type, critical=c.critical, weight=c.weight, source_of_truth=c.source_of_truth
            )
            for c in live_version.checks
        ]
    )
