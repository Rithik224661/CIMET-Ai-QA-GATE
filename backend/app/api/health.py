from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import Lead
from ..schemas import HealthOut

router = APIRouter(tags=["health"])


@router.get("/api/health", response_model=HealthOut)
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        database_status = "connected"
    except Exception:
        database_status = "unreachable"

    seeded = False
    if database_status == "connected":
        try:
            seeded = db.execute(select(func.count(Lead.id))).scalar_one() > 0
        except Exception:
            seeded = False

    return HealthOut(
        status="ok" if database_status == "connected" else "degraded",
        database=database_status,
        data_mode=settings.data_mode,
        ai_provider=settings.ai_provider,
        seeded=seeded,
    )
