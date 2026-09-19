"""
Real audio playback boundary (brief §5). Serves actual WAV bytes for the
named demo leads' synthetic recordings — never a silent/fake success. The
path is derived purely from `lead_id` (validated against the Lead table),
never from a client-supplied path, so this cannot be used to read
arbitrary files off disk.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Lead
from ..services.audio_storage import recording_path

router = APIRouter(tags=["audio"])


@router.get("/api/leads/{lead_id}/audio")
def get_lead_audio(lead_id: str, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="lead not found")

    path = recording_path(lead_id)
    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail="no recording available for this lead — synthetic demo audio is only generated for the named seed scenarios",
        )

    # Starlette's FileResponse natively handles Range requests (206 partial
    # content), which is what lets the browser <audio> element seek.
    # content_disposition_type="inline" so <audio src=...> plays it rather
    # than the browser treating the fetch as a download.
    return FileResponse(path, media_type="audio/wav", filename=f"{lead_id}.wav", content_disposition_type="inline")
