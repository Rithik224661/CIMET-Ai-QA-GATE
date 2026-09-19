"""
Optional AI semantic layer for the 3 Behaviour checks that benefit from
interpretation rather than exact comparison — rapport, interruptions,
objection handling (brief §8-12). Structurally NON-CRITICAL and additive
only:

- It is only ever invoked from evaluate_behaviour() for
  `AI_ELIGIBLE_METRICS`, which never includes a critical check (Behaviour
  checks are never critical in the 20-check catalogue — enforced by data,
  not by this module).
- It can REFINE the deterministic result's confidence/rationale; it can
  never flip PASS/FAIL against the deterministic heuristic's own
  disagreement being silently hidden (see `_combine` below) — the two are
  shown as agreeing or disagreeing, never one replacing the other.
- It cannot touch critical checks, rule versions, CRM fields, retailer
  plan data, or the gate decision. Those live entirely in
  verbatim.py/factual.py and gate.py, which never import this module.

AI_PROVIDER=none (the default): `maybe_refine_with_ai` is a zero-cost
no-op — returns the deterministic outcome unchanged, no network call.
This is what the live demo runs on; nothing here is required for a
correct, complete evaluation.

AI_PROVIDER=<configured>: the model is asked for a structured JSON result
or nothing at all. It may only cite transcript segments it was actually
given (evidence is verified against the real segment text before being
trusted at all — see `_verify_evidence`); a malformed response, an
unverifiable evidence citation, a timeout, or any other provider failure
degrades to the deterministic outcome — never a crash, never a silent
PASS.
"""

from __future__ import annotations

import json
import logging
from dataclasses import replace
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from .ai_provider import NullLLMProvider, get_llm_provider
from .evaluators.base import CheckOutcome, EvaluationContext

logger = logging.getLogger(__name__)

_SCHEMA_DESCRIPTION = (
    'JSON object: {"status": "PASS"|"FAIL"|"LOW_CONFIDENCE", "confidence": 0.0-1.0, '
    '"signals": [string, ...], "evidence": [{"segmentId": int, "quote": string}, ...], "rationale": string}. '
    "evidence.segmentId and evidence.quote MUST correspond exactly to a transcript segment you were given below "
    "— never invent a quotation or a segment id."
)


class _AIEvidenceItem(BaseModel):
    segment_id: int = Field(alias="segmentId")
    quote: str

    model_config = {"populate_by_name": True}


class AIBehaviourResult(BaseModel):
    status: Literal["PASS", "FAIL", "LOW_CONFIDENCE"]
    confidence: float = Field(ge=0.0, le=1.0)
    signals: list[str] = Field(default_factory=list)
    evidence: list[_AIEvidenceItem] = Field(default_factory=list)
    rationale: str


def _build_context_text(context: EvaluationContext) -> str:
    lines = [f"[{s.id}] {s.speaker} ({s.start_seconds:.1f}-{s.end_seconds:.1f}s): {s.text}" for s in context.segments]
    return "\n".join(lines)


def _verify_evidence(items: list[_AIEvidenceItem], context: EvaluationContext) -> list[_AIEvidenceItem]:
    """Only evidence that actually matches a real transcript segment is
    trusted — the model may only point at what it was given, never invent
    a quotation (brief §11)."""
    by_id = {s.id: s for s in context.segments}
    verified = []
    for item in items:
        segment = by_id.get(item.segment_id)
        if segment is not None and item.quote.strip().lower() in segment.text.lower():
            verified.append(item)
    return verified


def _call_ai(metric: str, check_config: dict, context: EvaluationContext) -> AIBehaviourResult | None:
    provider = get_llm_provider()
    prompt = (
        f"Assess the '{metric}' behavioural signal in this sales call transcript excerpt. "
        "This is a NON-CRITICAL coaching assessment, not a compliance check — never claim more certainty than the "
        "transcript actually supports; use LOW_CONFIDENCE whenever the evidence is ambiguous."
    )
    result = provider.evaluate_structured(prompt=prompt, schema_description=_SCHEMA_DESCRIPTION, context=_build_context_text(context))
    if result is None:
        return None
    try:
        return AIBehaviourResult.model_validate(json.loads(result.value))
    except (json.JSONDecodeError, ValidationError, TypeError):
        logger.warning("AI behaviour evaluator returned unparseable/invalid output for metric=%s", metric)
        return None


def _combine(deterministic: CheckOutcome, ai: AIBehaviourResult) -> CheckOutcome:
    ai_status = "REVIEW" if ai.status == "LOW_CONFIDENCE" else ai.status
    agrees = ai_status == deterministic.status or ai_status == "REVIEW"

    signals_note = f" AI signals: {'; '.join(ai.signals)}." if ai.signals else ""

    if not agrees:
        # The AI layer can never override the deterministic status — it
        # can only flag disagreement, which itself lowers confidence
        # (genuine ambiguity is exactly when neither side should sound
        # certain).
        combined_confidence = min(deterministic.confidence, ai.confidence, 0.75)
        rationale = (
            f"{deterministic.rationale} AI semantic layer disagreed (reported {ai.status} at "
            f"{ai.confidence:.0%}) — deterministic status retained since the AI layer cannot override it; "
            f"confidence lowered to reflect the disagreement.{signals_note}"
        )
        return replace(deterministic, confidence=combined_confidence, rationale=rationale)

    combined_confidence = round((deterministic.confidence + ai.confidence) / 2, 4)
    rationale = f"{deterministic.rationale} AI semantic layer corroborated this at {ai.confidence:.0%} confidence.{signals_note}"
    return replace(deterministic, confidence=combined_confidence, rationale=rationale)


def maybe_refine_with_ai(
    metric: str, check_config: dict, context: EvaluationContext, deterministic_outcome: CheckOutcome
) -> CheckOutcome:
    provider = get_llm_provider()
    if isinstance(provider, NullLLMProvider):
        return deterministic_outcome  # the default, zero-cost path — no network call

    try:
        ai_result = _call_ai(metric, check_config, context)
    except Exception:
        # A provider exception (timeout, network error, whatever) must
        # degrade to the deterministic result, never crash the check and
        # never silently produce a PASS.
        logger.exception("AI behaviour evaluator raised for metric=%s", metric)
        return deterministic_outcome

    if ai_result is None:
        return deterministic_outcome

    if ai_result.evidence:
        verified = _verify_evidence(ai_result.evidence, context)
        if not verified:
            # The model cited evidence that doesn't exist in the transcript
            # it was given — treat the whole response as unreliable rather
            # than trust the status/confidence it came with.
            logger.warning("AI behaviour evaluator cited unverifiable evidence for metric=%s; discarding", metric)
            return deterministic_outcome

    return _combine(deterministic_outcome, ai_result)
