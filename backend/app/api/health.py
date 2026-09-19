from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import Lead
from ..schemas import HealthOut
from ..services.audio_storage import RECORDINGS_DIR

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

    recordings_available = len(list(RECORDINGS_DIR.glob("*.wav"))) if RECORDINGS_DIR.is_dir() else 0

    return HealthOut(
        status="ok" if database_status == "connected" else "degraded",
        database=database_status,
        data_mode=settings.data_mode,
        ai_provider=settings.ai_provider,
        ai_provider_configured=settings.ai_provider == "anthropic" and bool(settings.anthropic_api_key),
        seeded=seeded,
        recordings_available=recordings_available,
        # No real CIMET sandbox schema/credentials exist yet (see
        # app/services/sandbox_adapter.py) — always False until one is
        # actually wired up. Never inferred from data_mode alone, so this
        # can't silently start claiming "sandbox" before it's real.
        sandbox_configured=False,
    )
