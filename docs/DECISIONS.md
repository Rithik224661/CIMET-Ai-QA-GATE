# Decisions

The brief and design spec left some tolerances, weights and thresholds
unspecified. Every assumption made while building Phase 1 (UI on fixtures)
is recorded here, per CLAUDE.md's workflow rule.

## Confidence floor — 0.85

`lib/config.ts` → `CONFIDENCE_FLOOR = 0.85`. Below this, on **any** check
(not only criticals), the gate routes to `QA_REVIEW` rather than
auto-passing. Value comes directly from the confidence-distribution
histogram in the design spec, where buckets below 0.85 are drawn amber
(never-auto-pass). Tunable in config, never in `lib/gate.ts` itself, per
NEXTJS_BUILD_PLAN.md §6.3.

## Gate precedence — critical fail beats low confidence

`criticalFails > 0 → HOLD` is evaluated before `anyConfidence < floor →
QA_REVIEW`. A held sale is never simultaneously reported as "QA review" —
HOLD is the stronger signal. Verified against every one of the brief's
9 scenario leads in `src/lib/gate.test.ts`.

## Check weights — 8 / 10 / 3 by type

`lib/fixtures/checks.ts` assigns weight 8 to Verbatim checks, 10 to
Factual, 3 to Behaviour — uniform within a type, matching the one
checklist export provided with the brief. Weights are not currently used
in the gate decision itself (the gate is pass/fail on criticals plus a
confidence floor, not a weighted score) but are shown on the Rules screen
because the checklist export defines them and Phase 5 (the real scoring
engine) may use them for the "score with and without fatal factors"
metric the brief asks for on the agent dashboards.

## One checklist for every retailer and rule-set version (fixture phase only)

The brief supplied one retailer's full checklist (Retailer 1, energy,
v1.4). The design prototype's mock data reuses that same 20-check
catalogue for every lead regardless of the lead's own `retailer` field,
and the Rules screen's check table doesn't actually change when a
different rule-set row is selected. This build preserves that behavior
exactly for fidelity. It is a fixture-phase simplification, not a product
decision: Phase 2 (Prisma + seed data) should give Retailer 2 and
Retailer 3 their own checklists once real check-library exports exist for
them, and the Rules table should then filter by the selected rule set.

## Repeat-offence threshold — 3 failures in 7 days

`lib/config.ts` → `REPEAT_OFFENCE_THRESHOLD = 3`,
`REPEAT_OFFENCE_WINDOW_DAYS = 7`. Taken verbatim from the brief ("the same
critical check failing three or more times in a rolling seven days flags
the TL"). In the fixture phase this is a static flag on one lead
(`3613778`) rather than a live rolling calculation — Phase 2+ should
compute it from real `CheckResult` history per agent/check.

## Sample rate — 5% of clean calls

`lib/config.ts` → `CLEAN_SAMPLE_RATE = 0.05`, from the brief directly.

## Decision reason text is generated, not hand-authored

`lib/gate.ts` → `describeDecision()` builds the HOLD / QA_REVIEW /
AUTO_SUBMIT sentence from the computed `GateOutcome` (plus whether the
lead is a repeat offence or has been overridden), rather than storing a
free-text `reason` string per fixture lead. This was worth the extra
indirection specifically because CLAUDE.md non-negotiable #6 requires the
gate to be deterministic and never a hand-waved copy — if the sentence
were hand-authored per lead, it could silently drift from what the gate
actually computed.

## Human override — now persisted for real (superseded)

~~Phase 1 note: the Human Review form was local-state-only.~~ As of the
backend build, `HumanReviewForm` calls the `submitOverride` server action
(`src/lib/actions/review.ts`), which `POST`s to `/api/reviews`, and the
FastAPI backend persists a real `HumanReview` row + a `HUMAN_OVERRIDE`
`AuditEvent` (append-only, never mutates the `GateDecision` row — CLAUDE.md
#7). The page revalidates on success, so the override banner, lineage
sidebar and full ledger all reflect it immediately. See
`backend/app/api/reviews.py`.

## Rail badge count ignores the retailer filter

The QA Queue nav badge is computed once, in the shared `(app)/layout.tsx`,
across all retailers — Next.js layouts (unlike pages) don't receive
`searchParams`, so it can't react live to the TopBar's retailer select
without an extra client fetch. The design's prototype badge does react to
the retailer filter. Acceptable for Phase 1; revisit with a small
`/api/queue/count` route (already anticipated in
NEXTJS_BUILD_PLAN.md's component map) if this needs to be live.

## Retailer/Range top-bar selects only actually filter the Queue

Matches the prototype exactly: `retailer` and `range` are written to the
URL from every view's top bar, but only the Queue view's rows and counts
read them. `range` doesn't filter anything anywhere yet, in the prototype
or here — it's state that a future metrics endpoint should start honoring.

---

# Backend decisions

## Deterministic evaluators, no LLM in the critical path

`backend/app/services/evaluators/*` are regex/normalized-text-comparison
based, not LLM calls — this is the brief's core requirement (§04: "this
must NOT become 'send transcript to LLM and ask PASS/FAIL'"). The 6 checks
that anchor the brief's worked example and the 9 demo scenarios (Recording
disclaimer, DMO read verbatim, Rates and charges, Email captured, Address
match, Dead air) have real extraction configured against each lead's
`crm_snapshot`; the other 14 of the 20 checks in the one checklist export
have no bespoke extraction wired and return a documented pass-through
default (their catalogue-default confidence, `PASS`, no fabricated
evidence). Building bespoke NLP for all 20 fields wasn't a good time
trade-off for a 12-hour build; the architecture (a common `Evaluator`
interface returning a structured `CheckOutcome`) supports wiring the rest
the same way later without touching the gate.

## Transcripts use digit-form numbers, not spelled-out words

The original frontend fixtures spelled numbers out ("twenty-eight point
six cents") for prototype readability. The backend's seed transcripts use
digit form ("28.6 cents") instead — both because real ASR output
typically renders recognized numbers as digits, and because the factual
evaluator's regex extraction needs a machine-parseable form. Check
outcomes (PASS/FAIL/REVIEW) match the original narrative; exact confidence
values may differ slightly from the old hand-authored fixtures now that
they're genuinely computed — expected, and the point of this phase.

## AI provider defaults to "none" — zero external calls, zero credentials

`backend/app/services/ai_provider.py`'s `LLMProvider` abstraction exists
per the brief (§43), but nothing in this build's evaluators calls it: every
check evaluator is fully deterministic. This was a deliberate reliability
choice for a live, timed hackathon demo — the gate must work with no
network dependency and no API key. An `AnthropicLLMProvider` stub is wired
for a future semantic-extraction step (e.g. paraphrase-tolerant script
matching on messier real call audio) behind `AI_PROVIDER=anthropic` +
`ANTHROPIC_API_KEY`; a provider failure or malformed output there is
required to degrade to low-confidence/REVIEW, never a silent PASS.

## Bulk synthetic backfill, separate from the 9 named scenarios

The brief requires dashboard/calibration figures to be computed from
stored records, not hard-coded (§31/§33). With only the 9 named leads,
those computed numbers would be tiny and not resemble the approved
design's mockup figures. `backend/app/seed_data.py`'s `generate_bulk_leads`
adds ~300 lightweight synthetic leads (randomized but plausible check
outcomes, fixed RNG seed for reproducibility) purely so dashboard and
calibration aggregates have realistic volume. They are flagged
`is_seed_scenario=False` and are deliberately **excluded** from
`GET /api/leads`'s list response — the Sales scenario rail and QA Queue
were always meant to show the small, curated 9-scenario set (matching the
approved design's "Scenario rows" in a 248px rail, not a live
production-scale queue), so only named scenarios are ever navigable;
bulk leads are queried directly by the aggregation services and never
otherwise surfaced.

## Calibration disagreement is seeded directionally, not as a coin flip

A human overturning an AI `HOLD` (critical false-fail) is normal QA
behavior and seeded at a real, noticeable rate. A human catching something
critical the AI let through (critical false-pass — "the release-blocking
metric" per the brief, and the one judged on "essentially never false-
pass") is seeded at a much lower rate (~0.6% vs ~12%), not the same
probability as the benign direction — a naive symmetric coin-flip produced
a double-digit false-pass count that contradicted the entire premise of
the calibration screen. See `backend/app/seed.py`'s `_seed_calibration_reviews`.

## Repeat-offence history is seeded, not hard-coded

Lead `3613778`'s `repeatOffence` flag is computed for real by
`count_recent_critical_failures` — two synthetic prior calls for the same
agent, same critical check (`RET1-VB-001`), dated inside the rolling
7-day window, are seeded in `REPEAT_OFFENCE_HISTORY` specifically so the
count reaches the configured threshold (3) genuinely, rather than setting
the boolean directly.

## SQLite, single-process, synchronous SQLAlchemy

Brief §3 calls for "SQLite for local/hackathon reliability" explicitly —
followed as specified. No async DB driver, no connection pool tuning: this
is sized for a live demo, not concurrent production traffic. Revisit
(Postgres, async SQLAlchemy) before any real multi-user deployment.

---

# Phase 3 decisions (rubric closure / false-pass elimination)

See `docs/CHECK_AUDIT.md` for the full per-check table. Summary of what
changed and why.

## Low-confidence gate scoping — critical checks only (SUPERSEDED, see Phase 4)

~~`evaluate_gate()`'s QA_REVIEW branch now only counts critical checks
with confidence below the floor, not any check.~~ This was corrected back
in Phase 4: the CIMET spec's literal text is "low confidence on **any**
check — routed to QA rather than auto-passed", with no critical-only
qualifier, and that reading is authoritative over the judgment call made
here. See Phase 4's "Gate scoping reverted to ANY check" entry below for
the current, correct behavior and how the demo stayed stable despite the
change (by making sure the Behaviour heuristics' clean-case confidence
sits safely above the floor, rather than by narrowing what the gate
counts).

## NOT_EVALUABLE is REVIEW + confidence always below the floor, not a new status

Rather than add a fourth `ResultStatus` value (which would have required
a frontend change, explicitly out of scope for this pass), "genuinely
could not evaluate this check" is represented as `REVIEW` status at a
fixed sub-floor confidence (`NOT_EVALUABLE_CONFIDENCE = 0.4`, see
`evaluators/base.py`). For a critical check this routes the gate to
QA_REVIEW; for a non-critical check it's a visible, honest "couldn't
verify" note that never blocks. This reuses the frontend's existing
approved PASS/FAIL/REVIEW vocabulary and glyphs unchanged.

## Presence-mode and skip_if_absent are new factual evaluator modes, not new checks

Two checks ("Account holder confirmed", "Life support declared") aren't
value comparisons — they're "was this confirmed at all". A new `kind:
"presence"` mode searches for a configured confirmation pattern; found →
PASS, not found → NOT_EVALUABLE (never FAIL — a keyword miss isn't proof
the confirmation didn't happen, and this check must never manufacture a
false critical failure on phrasing alone).

Two other checks ("Concession applied", "Gift card value") only apply
when the CRM source of truth says something was actually offered. A new
`skip_if_absent: true` flag makes PASS the *correct* answer when the field
is empty/falsy (nothing to verify against), falling through to normal
extraction+comparison when it isn't — this is not the same as the old
dangerous default: the old default PASSed regardless of whether the field
existed; this only PASSes when the source of truth itself says there's
nothing to check.

## Behaviour heuristics are real, not LLM prompts, and honestly limited

Per explicit instruction, the 3 previously-pass-through Behaviour checks
were NOT replaced with LLM calls dressed up as "AI evaluation" — that
would trade demo reliability (network dependency, latency, a possible API
key requirement) for the appearance of sophistication without actually
being more trustworthy. Instead:

- **Interruptions**: counts `[crosstalk]` markers in the transcript — the
  one genuine overlapping-speech signal this transcript format captures.
- **Rapport**: customer-vs-agent talk-time share from real segment
  durations — a crude but genuinely-computed engagement proxy.
- **Objection handling**: objection-language keyword match on a customer
  turn, followed by a check for whether an agent turn came after it.

All three are deterministic, fast, and documented as honestly limited
(see each evaluator's docstring and `docs/CHECK_AUDIT.md`) rather than
overstated as a "semantic classifier" with more sophistication than a
short synthetic transcript can actually support.

## The submission boundary is a labeled DEMO/MOCK sandbox

`app/services/submission.py`'s `MockSubmissionAdapter` is the only
adapter wired up — no real CIMET CRM submission endpoint exists. Every
payload it produces carries `"sandbox": "DEMO_MOCK"` explicitly, and only
an `AUTO_SUBMIT` `GateDecision` ever reaches it (enforced by a `ValueError`
guard in `submit_if_auto_submitted`, not just by convention) — HOLD and
QA_REVIEW have no code path that creates a `Submission` row. Idempotent:
re-evaluating a lead replaces its prior `Submission` rather than
accumulating duplicates, matching the existing `CheckResult`/`GateDecision`
re-evaluation behavior.

## Evaluator exceptions degrade to NOT_EVALUABLE, never crash or silently pass

`pipeline.run_evaluation()` now wraps each check's evaluator call in a
try/except; a raised exception becomes the same `not_evaluable_outcome`
(REVIEW, sub-floor confidence) as a genuinely missing input, logged via
the standard `logging` module (never printing transcript content or
secrets). One broken evaluator can no longer take down the whole lead's
evaluation, and can never silently resolve to PASS.

## Digit-form transcript numbers, extended with more CRM fields

The transcript-authoring helper (`seed_data.py`'s `common_turns()`) now
generates the compliant baseline for every one of the newly-wired checks
(account-holder confirmation, DOB, fuel type, NMI, life-support Q&A,
move-in date, T&Cs, EIC, cooling-off) alongside the original 6. Every
named scenario calls it with only the parameters its own narrative
overrides, so every check *other than* the one(s) a scenario is about
genuinely evaluates from real transcript content — not a status set by
hand. `crm_snapshot["date_of_birth"]` is stored pre-normalized
("11th of march, 1988") to match the transcript's natural phrasing exactly
— the DOB evaluator does light case/whitespace normalization, not full
date-format parsing (a real system would want the latter; out of scope for
this pass).

---

# Phase 4 decisions (behaviour intelligence, AI augmentation, gate correction)

## Gate scoping reverted to ANY check, per the spec's literal text

Phase 3 scoped `QA_REVIEW`'s low-confidence trigger to critical checks
only, reasoning that once all 20 checks were genuinely evaluated, the 3
heuristic Behaviour checks would otherwise flood every call into review.
That reasoning was overridden: the CIMET spec's own words are "low
confidence on any check — routed to QA rather than auto-passed", with no
critical-only qualifier, and that's authoritative. `evaluate_gate()` (and
`src/lib/gate.ts`, its pure reference) now scores **any** check's
confidence against the floor again. The demo stayed stable through this
change for a different reason than the one Phase 3 relied on: every
Behaviour evaluator's "nothing wrong" confidence was tuned to sit safely
above 0.85 (Dead air 0.94, Rapport 0.90, Interruptions 0.92, Objection
handling 0.90), so a clean call's non-critical checks don't trip the
floor — but a genuinely ambiguous one (a weak objection-language match, a
marker-only interruption signal with no verifiable timing, a rapport
read from a single customer turn) correctly reports confidence *below*
the floor and routes the whole call to a human, exactly matching this
build's stated demo story: "when the evidence isn't strong enough, the
system does not pretend to know — it routes the case to QA." A
low-confidence non-critical check still can never produce a `HOLD` on its
own — only `QA_REVIEW` — that part was never in question.

## Behaviour heuristics gained real corroborating signals, not just a pass/fail line

Per audit, the Phase 3 Behaviour heuristics were genuine but single-signal
(one ratio, one marker count, one keyword match). Phase 4 adds real
corroborating signals and lets confidence reflect how much of them was
actually available:

- **Interruptions** now primarily detects **verified timestamp overlap**
  between consecutive different-speaker segments (`a.end_seconds >
  b.start_seconds`, reported as an exact overlap duration) — the `
  [crosstalk]` text marker is now the *secondary*, weaker signal, used
  only when no timing-verified overlap exists, and reported at
  materially lower confidence (0.7 vs 0.92) since it can't be
  independently verified. Lead `3613811`'s crosstalk turns were given
  real overlapping start/end timestamps (588.0–595.0s agent,
  593.0–598.0s customer → a genuine, computed 2.0s overlap) so this
  primary signal is actually exercised, not just the fallback.
- **Rapport** now combines three signals — customer talk-time share,
  customer turn-*count* share, and an acknowledgment-phrase rate — and
  lowers confidence honestly when the sample is thin (fewer than 2
  customer turns), rather than reporting the same confidence regardless
  of how much data backed the number.
- **Objection handling** now categorizes the objection (`price`,
  `not_interested`, `already_satisfied`, `time`, `hesitation` — all
  "strong", unambiguous phrase matches — vs. `uncertainty`, a "weak"
  bare hedge-word match like "actually"/"um"). A weak match reports low
  confidence *regardless of PASS/FAIL* — brief §28's "customer mentions
  it jokingly" case: the system can't tell sarcasm from a real objection
  from text alone, so it says so, rather than confidently asserting
  either outcome. Lead `3613824` was given a real price-objection +
  agent-response exchange so this evaluator has a positive example to
  demonstrate, not just the default "nothing to handle" PASS on every
  lead.

## Optional AI semantic layer for Behaviour checks — `app/services/ai_behaviour.py`

A new module, invoked only for the 3 AI-eligible Behaviour metrics
(`rapport`, `interruptions`, `objection_handling` — never `dead_air`,
which is a hard duration threshold with nothing semantic to interpret),
and only when `AI_PROVIDER` is configured to something other than
`"none"`. With the default (`AI_PROVIDER=none`, what the live demo
actually runs on), `maybe_refine_with_ai()` is a zero-cost no-op — it
returns the deterministic outcome completely unchanged, no network call,
no latency added. This was a deliberate reliability choice, unchanged
from Phase 3's reasoning: the demo must not depend on external credentials
or network availability.

When configured, the AI layer:

- Is asked for a structured JSON result (`status`, `confidence`,
  `signals[]`, `evidence[]`, `rationale`) via the existing `LLMProvider`
  abstraction — never free-form text accepted directly.
- Has its `evidence` verified against the real transcript segments it was
  given (`segmentId` + `quote` must actually match) before being trusted
  at all; if it cites anything unverifiable, the entire response is
  discarded and the deterministic outcome is used instead — the model may
  never invent a transcript quotation.
- Can never override the deterministic evaluator's PASS/FAIL status — see
  `_combine()`: agreement averages confidence between the two; a
  disagreement lowers confidence (genuine ambiguity) but keeps the
  deterministic status. This is enforced by this module's own logic, not
  merely by convention.
- Falls back to the deterministic outcome on literally anything else that
  can go wrong — malformed JSON, a schema-invalid response (wrong status
  enum, out-of-range confidence), a provider exception, a timeout, or the
  provider simply returning nothing — never a crash, never a silent PASS.
  All of this is tested against a fake provider implementing the same
  interface (`tests/test_ai_behaviour.py`), since no real API key is
  configured for this build.
- Cannot touch critical checks, rule versions, CRM fields, retailer plan
  data, or the gate decision — structurally impossible, since this module
  is only ever called from the 3 non-critical Behaviour metrics, and nothing
  in `verbatim.py`, `factual.py`, or `gate.py` imports it.

## Frontend/backend contract — no independent frontend gate, reaffirmed

No change was needed here: `src/lib/data/leads.ts`'s `gateForLead()`
already only reads the backend's persisted `decision` field (see Phase 2's
"wire frontend to the live backend API" work) — it does not call
`evaluateGate()` on the live data path. `src/lib/gate.ts` continues to
exist solely as a pure, unit-tested reference implementation kept in sync
with the backend's actual rule, for exactly the reason this pass's gate
scoping correction proved valuable: having *two* independently-testable
implementations of the same rule caught the critical-only/any-check
question exercising real, distinguishable test cases on both sides.
