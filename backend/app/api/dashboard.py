from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import DashboardOut
from ..services.dashboard import get_dashboard

router = APIRouter(tags=["dashboard"])


@router.get("/api/dashboard", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db)):
    return DashboardOut(**get_dashboard(db))
