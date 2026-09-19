"""
AI provider abstraction (brief §43-45). Semantic evaluation, where it is
used at all, goes through this interface — never hard-coded to one vendor,
and its output is always schema-validated before anything downstream can
use it. If a provider call fails or returns malformed output, callers must
fall back to a low-confidence / REVIEW result — never a silent PASS
(brief §45: "Never allow malformed AI output directly to determine a gate
decision").

The default provider ("none") makes zero external calls and needs zero
credentials: every evaluator in this build (verbatim/factual/behaviour) is
fully deterministic and does not require this provider to function at all.
It exists so a real semantic-extraction step can be dropped in later
(e.g. for messier real call transcripts) without touching the gate.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel

from ..config import settings


class StructuredExtractionResult(BaseModel):
    value: str
    confidence: float
    rationale: str


class LLMProvider(Protocol):
    name: str

    def evaluate_structured(
        self, *, prompt: str, schema_description: str, context: str
    ) -> StructuredExtractionResult | None:
        """Returns None on any failure — callers must treat that as
        "could not extract", never as a pass."""
        ...


class NullLLMProvider:
    """No external calls. Always reports it cannot extract, so any caller
    that (incorrectly) depended on it degrades to REVIEW rather than a
    fabricated PASS."""

    name = "none"

    def evaluate_structured(
        self, *, prompt: str, schema_description: str, context: str
    ) -> StructuredExtractionResult | None:
        return None


class AnthropicLLMProvider:
    """Opt-in only (AI_PROVIDER=anthropic + ANTHROPIC_API_KEY set). Not used
    by any check evaluator in this build by default — wired for future
    semantic-judgment steps (e.g. paraphrase-tolerant script matching) that
    still feed into, but never replace, the deterministic gate."""

    name = "anthropic"

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    def evaluate_structured(
        self, *, prompt: str, schema_description: str, context: str
    ) -> StructuredExtractionResult | None:
        try:
            import anthropic  # type: ignore[import-not-found]
        except ImportError:
            return None

        try:
            client = anthropic.Anthropic(api_key=self._api_key)
            message = client.messages.create(
                model=self._model,
                max_tokens=512,
                system=(
                    "You extract a single structured value from a call transcript excerpt. "
                    f"Output schema: {schema_description}. "
                    "If the value is not clearly present, respond with exactly: NOT_FOUND."
                ),
                messages=[{"role": "user", "content": f"{prompt}\n\nTranscript context:\n{context}"}],
            )
            text = "".join(block.text for block in message.content if hasattr(block, "text")).strip()
            if not text or text == "NOT_FOUND":
                return None
            return StructuredExtractionResult(value=text, confidence=0.8, rationale="Anthropic structured extraction.")
        except Exception:
            # Provider failure must never manufacture a pass.
            return None


def get_llm_provider() -> LLMProvider:
    if settings.ai_provider == "anthropic" and settings.anthropic_api_key:
        return AnthropicLLMProvider(settings.anthropic_api_key, settings.anthropic_model)
    return NullLLMProvider()
