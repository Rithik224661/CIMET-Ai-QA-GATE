# Check audit — Phase 3 hardening

Full audit of all 20 configured checks in the one checklist export in hand
(Retailer 1, Energy, v1.4). Produced before touching code, per the Phase 3
hardening prompt's requirement to inspect the repository first rather than
assume passing tests prove correctness.

**Before this pass:** 6/20 checks had real evaluator logic; 14/20 silently
returned `PASS` with a fabricated default confidence whenever no
field/pattern was configured — the exact "dangerous pass-through" pattern
this audit exists to eliminate.

**After this pass:** 20/20 checks resolve to a real, structured evaluator
strategy. Nothing in the catalogue relies on the old silent-PASS fallback
path anymore (it still exists in code as a defensive fallback — see
`not_evaluable_outcome` — but is dead code against the current 20-check
catalogue; a `NOT_EVALUABLE` result is now REVIEW + confidence below the
floor, never PASS).

| # | Check | Type | Critical | Evaluation strategy | Real / Pass-through | Tested | Evidence | Risk (before) | Action |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Recording disclaimer | Verbatim | **Yes** | Normalized text similarity vs. approved phrase, 0–60s window | Real (unchanged) | ✅ | ✅ | none | kept |
| 2 | Account holder confirmed | Factual (presence) | **Yes** | Presence-match a customer confirmation phrase, 0–400s | **Real (new)** | ✅ | ✅ | **High** — was silent PASS | Implemented; absence → NOT_EVALUABLE (REVIEW), never FAIL or PASS |
| 3 | Address match | Factual | **Yes** | Regex-extracted address vs. CRM, exact-match | Real (unchanged) | ✅ | ✅ | none | kept |
| 4 | DOB match | Factual | **Yes** | Regex-extracted date vs. CRM | **Real (new)** | ✅ | ✅ | **High** | Implemented |
| 5 | Fuel type | Factual | **Yes** | Keyword-extracted fuel type vs. CRM | **Real (new)** | ✅ | ✅ | **High** | Implemented |
| 6 | NMI / MIRN verified | Factual | **Yes** | Digit-run regex vs. CRM | **Real (new)** | ✅ | ✅ | **High** | Implemented |
| 7 | DMO read verbatim | Verbatim | **Yes** | Normalized similarity; crosstalk → REVIEW | Real (unchanged) | ✅ | ✅ | none | kept |
| 8 | Rates and charges | Factual | **Yes** | Numeric extraction, 0c tolerance vs. rate card | Real (unchanged) | ✅ | ✅ | none | kept |
| 9 | Concession applied | Factual | No | `skip_if_absent`: PASS is correct when nothing was offered; keyword-compare when the CRM flag is set | **Real (new)** | ✅ | ✅ (N/A-safe) | Medium | Implemented conditional not-applicable |
| 10 | Life support declared | Factual (presence) | **Yes** | Presence-match the *customer's answer* (not just the agent asking), 1000–1060s | **Real (new)** | ✅ | ✅ | **High** | Implemented; asked-but-unanswered → NOT_EVALUABLE |
| 11 | Dead air | Behaviour | No | Silence-duration regex vs. threshold | Real (unchanged) | ✅ | ✅ | none | kept |
| 12 | Move-in date | Factual | No | Regex-extracted day vs. CRM | **Real (new)** | ✅ | ✅ | Medium | Implemented |
| 13 | Email captured | Factual | **Yes** | Regex-extracted email, normalized, vs. CRM | Real (unchanged) | ✅ | ✅ | none | kept |
| 14 | Gift card value | Factual | No | `skip_if_absent`: PASS is correct when no gift card on this plan; numeric-compare when the CRM value is set | **Real (new)** | ✅ | ✅ (N/A-safe) | Medium | Implemented conditional not-applicable |
| 15 | T&Cs read | Verbatim | **Yes** | Normalized similarity vs. approved phrase | **Real (new)** | ✅ | ✅ | **High** | Implemented |
| 16 | EIC provided | Verbatim | No | Normalized similarity vs. approved phrase | **Real (new)** | ✅ | ✅ | Medium | Implemented |
| 17 | Cooling-off rights | Verbatim | **Yes** | Normalized similarity vs. approved phrase | **Real (new)** | ✅ | ✅ | **High** | Implemented |
| 18 | Rapport | Behaviour | No | Customer/agent talk-time share (real, honestly heuristic-limited) | **Real, heuristic-limited (new)** | ✅ | partial (aggregate, no single quotable span) | Medium | Implemented documented heuristic — NOT an LLM call, NOT a fabricated sentiment score |
| 19 | Interruptions | Behaviour | No | Crosstalk-marker count (real, honestly heuristic-limited) | **Real, heuristic-limited (new)** | ✅ | ✅ | Medium | Implemented documented heuristic |
| 20 | Objection handling | Behaviour | No | Objection-keyword + agent-follow-up detection (real, honestly heuristic-limited) | **Real, heuristic-limited (new)** | ✅ | ✅ | Medium | Implemented documented heuristic |

## Summary

```
20 checks
├── 20 executable (0 unconditional-PASS pass-throughs)
├── 12 critical, all genuinely enforced (can FAIL or REVIEW from real
│      transcript + CRM comparison — verified in tests/test_scenarios_e2e.py
│      and tests/test_api_leads.py)
├── 8 non-critical, all genuinely computed (2 conditional-not-applicable,
│      correctly PASS only when the CRM source of truth says nothing
│      applies — not a fabricated default)
├── 3 "Behaviour" checks (Rapport, Interruptions, Objection handling) are
│      real deterministic heuristics — talk-time share, crosstalk-marker
│      counting, objection-keyword-plus-response detection — not an LLM
│      call and not a fabricated AI score. Honestly documented as
│      limited: a short synthetic transcript can't represent everything a
│      real sentiment/prosody classifier would use as evidence.
└── The NOT_EVALUABLE path (REVIEW + confidence always below the
       floor) is real and exercised live: Lead 3613778's "Account holder
       confirmed" genuinely resolves to it, not a hardcoded case.
```

## Why the 3 heuristic Behaviour checks aren't "20/20 fully NLP-verified"

Per the brief's own architecture split (Verbatim = deterministic text
comparison, Factual = structured extraction + authoritative-source
comparison, Behaviour = semantic classifier), a real sentiment/rapport
classifier is a materially different kind of system than the other 17
checks — and per this hardening pass's own explicit instruction, it was
NOT replaced with "14 fake LLM prompts" for reliability reasons (no
network dependency, no API key required for the demo, deterministic and
fast). What's shipped is a genuine, transcript-derived, non-fabricated
signal for all three; the honest limitation is documented here and in each
evaluator's docstring rather than hidden.
