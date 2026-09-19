"""
Ingestion abstraction (brief §25). The dialler pushes a recording to CRM by
API, keyed on Lead ID, within minutes of hangup (brief §02) — this module
is the boundary that isolates the rest of the system from *how* that
recording actually arrives. `MockIngestionAdapter` is what every seeded
demo lead runs through today; a `CIMETSandboxAdapter` slots in later
without the pipeline, evaluators, or gate changing at all.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class IngestedRecording:
    lead_id: str
    storage_reference: str
    duration_seconds: int
    mime_type: str
    sha256: str | None = None


class IngestionAdapter(Protocol):
    def fetch_recording(self, lead_id: str) -> IngestedRecording | None:
        """Returns None if no usable recording exists yet (or ever) for
        this lead — callers must route to the ingest-error state, never
        silently proceed as if scoring happened."""
        ...


class MockIngestionAdapter:
    """The only adapter wired up in this build. Recordings are synthetic —
    see app/seed_data.py — and this adapter simply looks them up rather
    than calling any dialler API."""

    def __init__(self, recordings: dict[str, IngestedRecording]) -> None:
        self._recordings = recordings

    def fetch_recording(self, lead_id: str) -> IngestedRecording | None:
        return self._recordings.get(lead_id)


class CIMETSandboxAdapter:
    """Not implemented: no real CIMET dialler endpoint, schema, or
    credentials have been provided yet. This class exists so the adapter
    boundary is visible in the codebase — wiring it up is a follow-up once
    those are available, not a blocker for the rest of the system."""

    def fetch_recording(self, lead_id: str) -> IngestedRecording | None:
        raise NotImplementedError(
            "CIMETSandboxAdapter requires real dialler API credentials/schema, "
            "which have not been provided. Use MockIngestionAdapter for demo/dev."
        )
