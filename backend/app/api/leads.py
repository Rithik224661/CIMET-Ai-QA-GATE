from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..db import get_db
from ..enums import Decision, LeadState
from ..models import Lead
from ..schemas import LeadOut, LeadsListOut, SubmissionOut
from ..serializers import serialize_lead, serialize_submission

router = APIRouter(tags=["leads"])

ALL_RETAILERS = "All retailers"
QUEUE_FILTERS = ("All", "Critical holds", "Low confidence", "Repeat offences", "Human overrides", "Sampled clean")


def _lead_query(db: Session):
    return select(Lead).options(
        joinedload(Lead.retailer),
        joinedload(Lead.checklist_version),
        joinedload(Lead.transcript),
        joinedload(Lead.decision),
        joinedload(Lead.submission_record),
        joinedload(Lead.ingest_error),
        joinedload(Lead.reviews),
        joinedload(Lead.results),
    )


def _matches_retailer(lead: Lead, retailer: str | None) -> bool:
    return not retailer or retailer == ALL_RETAILERS or lead.retailer.name == retailer


def _matches_filter(lead: Lead, filter_: str | None) -> bool:
    # No filter param at all (the Sales scenario rail's plain `getLeads()`
    # call) means "every scenario, including in-progress ones" — distinct
    # from the Queue's explicit "All" chip, which means "every *scored or
    # errored* lead" (nothing to action on a still-processing lead yet).
    if filter_ is None:
        return True
    if filter_ == "All":
        return lead.state in (LeadState.SCORED, LeadState.ERROR)
    if lead.state != LeadState.SCORED or lead.decision is None:
        return False
    if filter_ == "Critical holds":
        return lead.decision.decision == Decision.HOLD and not lead.reviews
    if filter_ == "Low confidence":
        return lead.decision.decision == Decision.QA_REVIEW
    if filter_ == "Repeat offences":
        return lead.repeat_offence
    if filter_ == "Human overrides":
        return bool(lead.reviews)
    return lead.decision.decision == Decision.AUTO_SUBMIT  # "Sampled clean"


@router.get("/api/leads", response_model=LeadsListOut)
def list_leads(retailer: str | None = None, range: str | None = None, filter: str | None = None, db: Session = Depends(get_db)):
    # Only the curated named demo scenarios are ever listed/navigable here
    # (Sales scenario rail, QA Queue) — matching the approved design, which
    # was always built around a small, deliberate scenario set, not a live
    # production-scale queue. The bulk synthetic backfill exists purely so
    # dashboard/calibration aggregates have realistic volume to compute
    # over; it's queried directly by those services, never listed here.
    # See docs/DECISIONS.md.
    query = _lead_query(db).where(Lead.is_seed_scenario.is_(True)).order_by(Lead.call_datetime.desc())
    leads = db.execute(query).unique().scalars().all()
    filtered = [lead for lead in leads if _matches_retailer(lead, retailer) and _matches_filter(lead, filter)]
    return LeadsListOut(leads=[serialize_lead(lead) for lead in filtered])


@router.get("/api/leads/{lead_id}", response_model=LeadOut)
def get_lead(lead_id: str, db: Session = Depends(get_db)):
    lead = db.execute(_lead_query(db).where(Lead.id == lead_id)).unique().scalar_one_or_none()
    if lead is None:
        raise HTTPException(status_code=404, detail="lead not found")
    return serialize_lead(lead)


@router.get("/api/leads/{lead_id}/checks", response_model=LeadOut)
def get_lead_checks(lead_id: str, db: Session = Depends(get_db)):
    """Convenience alias — the full lead payload already embeds `results`;
    exposed as its own path per the brief's endpoint list (§29)."""
    return get_lead(lead_id, db)


@router.get("/api/leads/{lead_id}/evidence", response_model=LeadOut)
def get_lead_evidence(lead_id: str, db: Session = Depends(get_db)):
    """Alias of GET /api/leads/{lead_id} per the brief's endpoint list
    (§29) — every CheckResult already embeds its Evidence (evidenceQuote,
    observed, expected), so there is one canonical evidence structure
    (brief §17) rather than a second, divergent representation."""
    return get_lead(lead_id, db)


@router.get("/api/leads/{lead_id}/timeline", response_model=LeadOut)
def get_lead_timeline(lead_id: str, db: Session = Depends(get_db)):
    """Alias of GET /api/leads/{lead_id} per the brief's endpoint list
    (§29) — the `transcript` array (speaker, timestamp, text) IS the
    timeline; the frontend derives markers from `results[].timestamp`
    against it."""
    return get_lead(lead_id, db)


@router.get("/api/leads/{lead_id}/submission", response_model=SubmissionOut)
def get_lead_submission(lead_id: str, db: Session = Depends(get_db)):
    """The submission boundary (brief §11) — 404 until (unless) the lead's
    decision is AUTO_SUBMIT, since HOLD/QA_REVIEW leads never submit."""
    lead = db.execute(_lead_query(db).where(Lead.id == lead_id)).unique().scalar_one_or_none()
    if lead is None:
        raise HTTPException(status_code=404, detail="lead not found")
    if lead.submission_record is None:
        raise HTTPException(status_code=404, detail="lead has not been submitted (decision is not AUTO_SUBMIT)")
    return serialize_submission(lead.submission_record)
