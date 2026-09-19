# Check audit

Full audit of all 20 configured checks in the one checklist export in hand
(Retailer 1, Energy, v1.4) — what each one actually does, whether AI is
ever involved, and its exact effect on the gate.

| # | Check | Type | Critical? | Implementation | AI used? | Evidence? | Confidence? | Gate effect | Tested? |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Recording disclaimer | Verbatim | **Yes** | Normalized text similarity vs. approved phrase, 0–60s window | No | Yes (transcript span) | Similarity-derived | FAIL → HOLD | ✅ |
| 2 | Account holder confirmed | Factual (presence) | **Yes** | Presence-match a customer confirmation phrase, 0–400s | No | Yes when found | Fixed high on match; sub-floor REVIEW when absent | Absent → QA_REVIEW (never FAIL on a keyword miss) | ✅ |
| 3 | Address match | Factual | **Yes** | Regex-extracted address vs. CRM, exact-match | No | Yes | Extraction-derived | FAIL → HOLD | ✅ |
| 4 | DOB match | Factual | **Yes** | Regex-extracted date vs. CRM, text-normalized compare | No | Yes | Extraction-derived | FAIL → HOLD | ✅ |
| 5 | Fuel type | Factual | **Yes** | Keyword extraction vs. CRM | No | Yes | Extraction-derived | FAIL → HOLD | ✅ |
| 6 | NMI / MIRN verified | Factual | **Yes** | Digit-run regex vs. CRM | No | Yes | Extraction-derived | FAIL → HOLD | ✅ |
| 7 | DMO read verbatim | Verbatim | **Yes** | Normalized similarity; crosstalk → REVIEW | No | Yes | Similarity-derived; sub-floor on crosstalk | REVIEW+low-conf → QA_REVIEW | ✅ |
| 8 | Rates and charges | Factual | **Yes** | Numeric extraction, 0c tolerance vs. rate card | No | Yes | Extraction-derived | FAIL → HOLD | ✅ |
| 9 | Concession applied | Factual | No | `skip_if_absent`: correct PASS when nothing was offered; keyword-compare when the CRM flag is set | No | Yes when applicable | Fixed / extraction-derived | Any status → coaching only, never blocks | ✅ |
| 10 | Life support declared | Factual (presence) | **Yes** | Presence-match the customer's *answer* (not just the agent asking), 1000–1060s | No | Yes when found | Fixed high on match; sub-floor REVIEW when unanswered | Unanswered → QA_REVIEW | ✅ |
| 11 | Dead air | Behaviour | No | Silence-duration regex vs. threshold | No (not AI-eligible — hard duration threshold) | Yes | Fixed (0.94) | Low confidence here can route to QA_REVIEW (any-check scoping) but never HOLD | ✅ |
| 12 | Move-in date | Factual | No | Regex-extracted day vs. CRM | No | Yes | Extraction-derived | Coaching only | ✅ |
| 13 | Email captured | Factual | **Yes** | Regex-extracted email, normalized, vs. CRM | No | Yes | Extraction-derived | FAIL → HOLD | ✅ |
| 14 | Gift card value | Factual | No | `skip_if_absent`: correct PASS when no gift card on this plan; numeric-compare when the CRM value is set | No | Yes when applicable | Fixed / extraction-derived | Coaching only | ✅ |
| 15 | T&Cs read | Verbatim | **Yes** | Normalized similarity vs. approved phrase | No | Yes | Similarity-derived | FAIL → HOLD | ✅ |
| 16 | EIC provided | Verbatim | No | Normalized similarity vs. approved phrase | No | Yes | Similarity-derived | Coaching only | ✅ |
| 17 | Cooling-off rights | Verbatim | **Yes** | Normalized similarity vs. approved phrase | No | Yes | Similarity-derived | FAIL → HOLD | ✅ |
| 18 | Rapport | Behaviour | No | 3 signals: customer talk-time share, customer turn-count share, acknowledgment-phrase rate; confidence lowered when sample is thin (<2 customer turns) | **Optional** (`AI_PROVIDER` configured only; no-op by default) | Deterministic: aggregate, no single span. AI (if enabled): verified span(s) or discarded | Signal-count-derived; AI averages in when it agrees, never inflates alone | Low-confidence non-critical → QA_REVIEW only, never HOLD | ✅ |
| 19 | Interruptions | Behaviour | No | Primary: verified timestamp overlap between consecutive different-speaker segments (exact duration reported). Secondary/weaker: `[crosstalk]` text marker with no verifiable timing | **Optional** (as above) | Yes — overlapping segment pair or marker segment | High (0.92) on timing-verified overlap; lower (0.7) on marker-only | Low-confidence non-critical → QA_REVIEW only, never HOLD | ✅ |
| 20 | Objection handling | Behaviour | No | Categorized customer objection language (price / not_interested / already_satisfied / time / hesitation = strong; bare hedge words = weak) + agent-follow-up detection | **Optional** (as above) | Yes — the objection turn (+ verified AI evidence if enabled) | High (0.90) on a strong category match; low (0.65) on a weak/ambiguous one, regardless of PASS/FAIL | Low-confidence non-critical → QA_REVIEW only, never HOLD | ✅ |

## Summary

```
20 checks
├── 20 genuinely evaluated — every one runs real logic against the
│      transcript/CRM, none defaults to an unconditional PASS
├── 12 critical, all genuinely enforced — each can independently produce
│      FAIL from real transcript+CRM comparison, verified in
│      tests/test_scenarios_e2e.py and tests/test_api_leads.py
├── 8 non-critical, all genuinely computed
├── 3 checks (Rapport, Interruptions, Objection handling) are eligible
│      for an OPTIONAL AI semantic refinement layer
│      (app/services/ai_behaviour.py) — a no-op with AI_PROVIDER=none
│      (the live demo's actual configuration), tested against a fake
│      provider otherwise (tests/test_ai_behaviour.py, 11 cases)
├── 0 checks let AI touch a critical result, a rule version, CRM data, or
│      the gate decision — structurally impossible (ai_behaviour.py is
│      only ever called from the 3 non-critical metrics above)
└── The NOT_EVALUABLE path (REVIEW + confidence always below the floor)
       is live: lead 3613778's "Account holder confirmed" check
       resolves to it from the actual transcript content on each run
```

## Gate scoping

`criticalFails > 0 → HOLD; ANY check's confidence < floor → QA_REVIEW;
else AUTO_SUBMIT` (`backend/app/services/gate.py`). A low-confidence
non-critical check (including all 3 Behaviour heuristics above) can only
ever produce `QA_REVIEW`, never `HOLD` — the `critical_fails` count that
drives `HOLD` only ever counts critical checks. See `docs/DECISIONS.md`
for the rationale behind scoping the confidence floor to every check
rather than critical ones only.

## Deterministic vs. AI-eligible, by check

```
Critical compliance (12 checks: disclaimer, account holder, address,
DOB, fuel type, NMI, DMO, rates, life support, email, T&Cs, cooling-off)
  -> 100% deterministic. No AI involvement of any kind, ever.
  -> This is what the gate decision is actually made from.

Non-critical Factual/Verbatim (Concession, Move-in date, Gift card,
EIC) -> 100% deterministic. Not AI-eligible (no semantic ambiguity to
interpret — they're value comparisons or verbatim matches like the
critical ones, just not gate-blocking).

Behaviour (Dead air, Rapport, Interruptions, Objection handling)
  -> Deterministic heuristic always computed first.
  -> Rapport / Interruptions / Objection handling ONLY may be refined by
     an optional AI layer, additive, never authoritative on its own,
     never able to override the deterministic status.
  -> Dead air is never AI-eligible (a duration threshold has nothing
     semantic to interpret).
```
