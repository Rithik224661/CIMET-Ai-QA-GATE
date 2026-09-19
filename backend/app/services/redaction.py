"""
Redaction layer. Card numbers never reach ordinary transcript presentation
— CLAUDE.md #9 / brief §07 "No card data surfaced": if a card number is
spoken, the transcript view redacts it before anyone sees it; the score
flags the violation rather than showing the number.

This is heuristic (regex-based), not a PCI-grade DLP system — documented
limitation, appropriate for a hackathon prototype. It runs on every
transcript segment's text before it is ever persisted or returned by the
API, so redaction happens once, at the boundary, not scattered through
every consumer.
"""

from __future__ import annotations

import re

# 13-19 digits, optionally grouped by spaces/dashes in blocks of 3-6 —
# covers spoken-and-transcribed card numbers like "4111 1111 1111 1111" or
# "4111-1111-1111-1111" without also eating ordinary short numbers.
_CARD_NUMBER_RE = re.compile(r"\b(?:\d[ -]?){13,19}\b")


def looks_like_card_number(candidate: str) -> bool:
    digits = re.sub(r"[^0-9]", "", candidate)
    return 13 <= len(digits) <= 19


def redact_card_numbers(text: str) -> tuple[str, bool]:
    """Returns (redacted_text, violation_detected)."""
    violation = False

    def _replace(match: re.Match[str]) -> str:
        nonlocal violation
        if looks_like_card_number(match.group(0)):
            violation = True
            return "[REDACTED CARD NUMBER]"
        return match.group(0)

    redacted = _CARD_NUMBER_RE.sub(_replace, text)
    return redacted, violation
