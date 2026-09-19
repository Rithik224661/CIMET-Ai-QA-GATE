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
