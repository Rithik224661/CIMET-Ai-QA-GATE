from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import GateDecision, Lead
from ..schemas import EvaluationOut, EvaluationRequestIn
from ..serializers import serialize_gate_decision
from ..services.pipeline import run_evaluation

router = APIRouter(tags=["evaluations"])


@router.post("/api/evaluations", response_model=EvaluationOut)
def create_evaluation(body: EvaluationRequestIn, db: Session = Depends(get_db)):
    lead = db.get(Lead, body.lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="lead not found")
    if lead.state == "error":
        raise HTTPException(status_code=409, detail="lead has an ingest error — nothing to evaluate")

    try:
        decision = run_evaluation(db, lead)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    db.commit()
    db.refresh(decision)
    return EvaluationOut(lead_id=lead.id, decision=serialize_gate_decision(decision), checks_run=decision.checks_run)


@router.get("/api/evaluations/{evaluation_id}", response_model=EvaluationOut)
def get_evaluation(evaluation_id: int, db: Session = Depends(get_db)):
    decision = db.get(GateDecision, evaluation_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="evaluation not found")
    return EvaluationOut(lead_id=decision.lead_id, decision=serialize_gate_decision(decision), checks_run=decision.checks_run)
