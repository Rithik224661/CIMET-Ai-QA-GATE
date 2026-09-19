"""
Scoring-sandbox anti-corruption layer (brief §26, §55). The frontend
design explicitly anticipates a CIMET-provided scoring sandbox payload
whose schema may not match our internal domain model. This module is
where that translation happens — the evaluation engine (app/services/
pipeline.py, evaluators/*) never sees the external shape directly.

No real sandbox schema has been provided yet, so `SandboxPayload` below is
a reasonable placeholder shape (lead id, retailer, transcript turns, CRM
snapshot) inferred from the brief's own description of what it hands
over: "a scoring sandbox with the expected payload shape" (brief §09).
Replace `SandboxPayload`'s fields with the real schema once it exists —
callers only ever interact with `to_domain_lead_input()`'s output, so nothing
outside this file should need to change.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field, ValidationError


class SandboxTranscriptTurn(BaseModel):
    speaker: str
    start_seconds: float = Field(alias="start")
    end_seconds: float = Field(alias="end")
    text: str

    model_config = {"populate_by_name": True}


class SandboxPayload(BaseModel):
    lead_id: str
    retailer: str
    product: str
    agent: str
    team_lead: str
    call_datetime: str
    duration_seconds: int
    crm_snapshot: dict[str, object] = Field(default_factory=dict)
    transcript: list[SandboxTranscriptTurn] = Field(default_factory=list)


@dataclass(frozen=True)
class DomainLeadInput:
    lead_id: str
    retailer_name: str
    product: str
    agent: str
    team_lead: str
    call_datetime: str
    duration_seconds: int
    crm_snapshot: dict[str, object]
    transcript: list[SandboxTranscriptTurn]


class SandboxAdapterError(Exception):
    pass


def parse_sandbox_payload(raw: dict) -> SandboxPayload:
    try:
        return SandboxPayload.model_validate(raw)
    except ValidationError as exc:
        raise SandboxAdapterError(f"Invalid scoring sandbox payload: {exc}") from exc


def to_domain_lead_input(payload: SandboxPayload) -> DomainLeadInput:
    return DomainLeadInput(
        lead_id=payload.lead_id,
        retailer_name=payload.retailer,
        product=payload.product,
        agent=payload.agent,
        team_lead=payload.team_lead,
        call_datetime=payload.call_datetime,
        duration_seconds=payload.duration_seconds,
        crm_snapshot=payload.crm_snapshot,
        transcript=payload.transcript,
    )
