"""
Transcript ingestion/normalization boundary. Every transcript segment is
redacted before it is ever persisted — CLAUDE.md #9: redact before storage
AND before playback, not just before display.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session

from ..models import Lead, Transcript, TranscriptSegment
from .redaction import redact_card_numbers


def create_transcript(db: Session, lead: Lead, turns: list) -> Transcript:
    transcript = Transcript(lead_id=lead.id, status="ready", source="asr", version="asr-3.2", created_at=dt.datetime.now(dt.UTC))
    db.add(transcript)
    db.flush()

    for turn in turns:
        redacted_text, _violation = redact_card_numbers(turn.text)
        db.add(
            TranscriptSegment(
                transcript_id=transcript.id,
                speaker=turn.speaker,
                start_seconds=turn.start,
                end_seconds=turn.end_seconds,
                text=redacted_text,
                kind=turn.kind,
            )
        )
    db.flush()
    return transcript
