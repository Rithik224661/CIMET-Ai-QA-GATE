"""
ASR provider abstraction (brief §21-22). No CIMET-supplied recording or ASR
vendor/credentials exist in this environment — see docs/CHECK_AUDIT.md's
live-path audit. `transcribe()` is the boundary a real speech-to-text
adapter would implement; `MockTranscriptProvider` never invents a
transcription result. It returns the transcript this lead was already
ingested with (from app/seed_data.py, standing in for "the sanitized
transcript CIMET supplied"), which is exactly the "reuse what's already
authoritative, never fabricate" pattern `IngestionAdapter`
(app/services/ingestion.py) and `CIMETSandboxAdapter` already use for
recordings/sandbox payloads.

This module is not wired into the live evaluation pipeline: in this build,
ingestion (recording + transcript arriving together, keyed by lead id) has
already happened by the time `run_evaluation()` runs — the same "Recording
+ Supplied Transcript, no pretended ASR" flow the brief calls out as
acceptable when a sanitized transcript is the authoritative development
artifact. It exists so the ASR boundary is visible and swappable, the same
way ingestion.py's CIMETSandboxAdapter is visible and swappable without
being called from anywhere yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.orm import Session

from ..models import Lead


@dataclass(frozen=True)
class TranscribedSegment:
    speaker: str
    start_seconds: float
    end_seconds: float
    text: str


class ASRProvider(Protocol):
    def transcribe(self, db: Session, lead: Lead) -> list[TranscribedSegment] | None:
        """Returns None if no transcript is available for this lead —
        callers must route to the ingest-error state, never silently
        proceed as if transcription happened."""
        ...


class MockTranscriptProvider:
    """The only provider wired up in this build. Does not run ASR — it
    returns the transcript already attached to the lead. See module
    docstring for why this is not a fabricated transcription."""

    name = "mock"

    def transcribe(self, db: Session, lead: Lead) -> list[TranscribedSegment] | None:
        if lead.transcript is None:
            return None
        return [
            TranscribedSegment(
                speaker=s.speaker, start_seconds=s.start_seconds, end_seconds=s.end_seconds, text=s.text
            )
            for s in lead.transcript.segments
        ]


class CIMETASRAdapter:
    """Not implemented: no real ASR vendor or credentials have been
    provided. Exists so the boundary is visible in the codebase — wiring a
    real vendor is a follow-up once one is specified, not a blocker for
    the rest of the system (mirrors CIMETSandboxAdapter in
    sandbox_adapter.py and CIMETSandboxAdapter in ingestion.py)."""

    def transcribe(self, db: Session, lead: Lead) -> list[TranscribedSegment] | None:
        raise NotImplementedError(
            "CIMETASRAdapter requires a real ASR vendor/credentials, which have not been provided. "
            "Use MockTranscriptProvider for demo/dev."
        )


def get_asr_provider() -> ASRProvider:
    return MockTranscriptProvider()
