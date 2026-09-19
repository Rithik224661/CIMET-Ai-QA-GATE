from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import CalibrationOut
from ..services.calibration import get_calibration

router = APIRouter(tags=["calibration"])


@router.get("/api/calibration", response_model=CalibrationOut)
def calibration(db: Session = Depends(get_db)):
    return CalibrationOut(**get_calibration(db))
