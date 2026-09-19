# Decisions

The brief and design spec left some tolerances, weights, and thresholds
unspecified. This records every assumption made and why — so those
choices are visible and defensible, not silently arbitrary.

## Confidence floor — 0.85

`CONFIDENCE_FLOOR = 0.85` (`backend/app/config.py`, mirrored in
`src/lib/config.ts`). Below this, on **any** check — not only criticals —
the gate routes to `QA_REVIEW` rather than auto-passing. Taken from the
confidence-distribution histogram in the design spec, where buckets below
0.85 are drawn amber (never-auto-pass).

## Gate precedence — critical fail beats low confidence

`criticalFails > 0 → HOLD` is evaluated before `anyConfidence < floor →
QA_REVIEW`. A held sale is never simultaneously reported as "QA review" —
HOLD is the stronger signal. A low-confidence *non-critical* check can
only ever produce `QA_REVIEW`, never `HOLD` on its own. Exhaustively
covered in `src/lib/gate.test.ts` and `backend/tests/test_gate.py`.

## Low-confidence scoping — any check, not critical-only

The gate routes to `QA_REVIEW` when *any* check's confidence sits below
the floor, not just critical ones. This is a direct reading of the CIMET
brief's own text: "low confidence on any check — routed to QA rather than
auto-passed," with no critical-only qualifier. Practically, this means
every Behaviour heuristic (Rapport, Interruptions, Objection handling)
is tuned so its confidence on a clean, unambiguous read sits safely above
0.85 — a genuinely ambiguous signal (a weak objection-language match, an
unverifiable crosstalk marker, a rapport read from a single customer
turn) correctly reports confidence *below* the floor and routes the whole
call to a human, which is the intended behavior: when the evidence isn't
strong enough, the system does not pretend to know.

## Check weights — 8 / 10 / 3 by type

Weight 8 for Verbatim checks, 10 for Factual, 3 for Behaviour — uniform
within a type, matching the one checklist export provided with the
brief. Weights are shown on the Rules screen (the checklist export
defines them) but are not currently used in the gate decision itself,
which is pass/fail on criticals plus a confidence floor, not a weighted
score.

## Repeat-offence threshold — 3 failures in 7 days

`REPEAT_OFFENCE_THRESHOLD = 3`, `REPEAT_OFFENCE_WINDOW_DAYS = 7`, taken
directly from the brief ("the same critical check failing three or more
times in a rolling seven days flags the TL"). Computed live from stored
`CheckResult` history per agent/check (`count_recent_critical_failures`),
not a static flag — lead `3613778`'s repeat-offence badge is backed by
two genuinely seeded prior failures inside the rolling window, not a
hard-coded boolean.

## Sample rate — 5% of clean calls

`CLEAN_SAMPLE_RATE = 0.05`, taken directly from the brief.

## One checklist export covers every lead

The brief supplies one retailer's full checklist (Retailer 1, Energy,
v1.4). Every seeded lead evaluates against that same 20-check catalogue
regardless of its own `retailer` field, and the Rules screen's other
rule-set rows exist for navigation, not independent verification. A real
deployment would give each retailer its own checklist export and have
the Rules table filter accordingly — out of scope here because only one
export was ever provided to build against.

## Decision reason text is generated, not hand-authored

`describeDecision()` (`src/lib/gate.ts`, mirrored server-side) builds the
HOLD / QA_REVIEW / AUTO_SUBMIT sentence from the computed `GateOutcome`
itself, rather than storing a free-text reason per lead — so the copy
can never silently drift from what the gate actually computed.

## Deterministic evaluators, no LLM in the critical path

Every evaluator in `backend/app/services/evaluators/` is regex or
normalized-text-comparison based, not an LLM call — the brief's core
requirement is that this must not become "send transcript to LLM and ask
PASS/FAIL." All 20 checks in the one checklist export have real
extraction wired against each lead's `crm_snapshot` and transcript; see
`docs/CHECK_AUDIT.md` for the full per-check breakdown. The shared
`Evaluator` interface (a structured `CheckOutcome`, never a bare
pass/fail string) is what let the optional AI layer plug in later for
exactly three non-critical Behaviour checks without touching the gate.

## Behaviour heuristics are real signals, not LLM prompts dressed up as AI

Rapport, Interruptions, and Objection handling are deterministic,
transcript-derived signals, not LLM calls wearing an "AI evaluation"
label:

- **Interruptions**: primarily verified timestamp overlap between
  consecutive different-speaker segments (an exact, computed overlap
  duration); a `[crosstalk]` text marker with no verifiable timing is a
  secondary, lower-confidence fallback.
- **Rapport**: three combined signals — customer talk-time share,
  customer turn-count share, and an acknowledgment-phrase rate —
  with confidence lowered honestly when the sample is thin (fewer than 2
  customer turns).
- **Objection handling**: categorized objection language (price,
  not_interested, already_satisfied, time, hesitation — unambiguous
  phrase matches — vs. a weak bare hedge-word match) plus a check for
  whether an agent turn followed. A weak match reports low confidence
  regardless of PASS/FAIL, since text alone can't distinguish sarcasm
  from a real objection.

All three are fast, deterministic, and documented as honestly scoped — a
lightweight, genuinely-computed proxy, not a claim of a full
sentiment/prosody classifier. See each evaluator's docstring and
`docs/CHECK_AUDIT.md`.

## Optional AI semantic layer for Behaviour checks

`backend/app/services/ai_behaviour.py` is invoked only for the 3
AI-eligible Behaviour metrics (never `dead_air`, a hard duration
threshold with nothing semantic to interpret), and only when
`AI_PROVIDER` is configured to something other than `"none"`. The
default (`AI_PROVIDER=none`, what the live demo runs on) is a zero-cost
no-op — the deterministic outcome is returned unchanged, no network call.
This is a deliberate reliability choice: the demo must not depend on
external credentials or network availability.

When configured, the layer makes exactly **one** contextual call per
lead covering all three metrics together (not one call per check), asks
for a schema-validated JSON result, verifies any cited evidence against
the real transcript segments it was given before trusting it at all, and
can only refine confidence — never override the deterministic PASS/FAIL
status. Any failure (malformed JSON, a schema-invalid response, a
provider exception, a timeout, unverifiable evidence) falls back to the
deterministic outcome — never a crash, never a silent PASS. This is
tested against a fake provider implementing the same interface
(`backend/tests/test_ai_behaviour.py`) and against a genuine, unauthenticated
Anthropic configuration to verify the fallback path
(`backend/tests/test_ai_pipeline_integration.py`).

The layer cannot touch critical checks, rule versions, CRM fields,
retailer plan data, or the gate decision — structurally impossible, since
it's only ever called from the 3 non-critical Behaviour metrics, and
nothing in `verbatim.py`, `factual.py`, or `gate.py` imports it.

## Human override — persisted as an additive record

`HumanReviewForm` calls a server action that `POST`s to `/api/reviews`;
the backend persists a real `HumanReview` row plus a `HUMAN_OVERRIDE`
`AuditEvent`, and never mutates the original `GateDecision` row. The page
revalidates on success, so the override banner, decision lineage, and
full audit ledger all reflect it immediately. See
`backend/app/api/reviews.py`.

## Bulk synthetic backfill, separate from the 9 named scenarios

Dashboard and calibration figures are computed from stored records, not
hard-coded. With only the 9 named scenarios, those computed numbers would
be too small to look like a real production distribution.
`backend/app/seed_data.py`'s `generate_bulk_leads` adds ~300 lightweight
synthetic leads (randomized but plausible outcomes, fixed RNG seed for
reproducibility) purely so dashboard/calibration aggregates have
realistic volume. They're flagged `is_seed_scenario=False` and excluded
from the Sales rail and QA Queue, which are meant to show the small,
curated 9-scenario set — bulk leads are only ever read by the aggregation
services.

## Calibration disagreement is seeded directionally

A human overturning an AI `HOLD` (a critical false-fail — the AI was too
cautious) is seeded at a real, noticeable rate, matching normal QA
behavior. A human catching something critical the AI let through (a
critical false-pass — the metric that gates whether the system is safe
to run unattended) is seeded at a much lower rate, reflecting that this
is the case the whole system is designed to avoid. See
`backend/app/seed.py`'s `_seed_calibration_reviews`.

## SQLite, single-process, synchronous SQLAlchemy

The brief calls for SQLite for local/hackathon reliability, followed as
specified. No async DB driver, no connection-pool tuning — sized for a
live demo, not concurrent production traffic. A real multi-user
deployment would move to Postgres with an async driver first.

## `CheckResult`/`Evidence`/`GateDecision`/`Submission` reflect the latest evaluation, not a full history

Re-evaluating a lead replaces its prior check results, evidence, gate
decision, and submission rather than versioning them — so these tables
hold the current state of a lead, not every past evaluation of it. The
`AuditEvent` ledger is the actual permanent record: it is genuinely
append-only, and every override, submission, and gate decision — past and
present — is preserved there regardless of how many times a lead is
re-evaluated. See `docs/ARCHITECTURE.md` for the full data flow.

## Frontend/backend contract — no independent frontend gate

`src/lib/data/leads.ts`'s `gateForLead()` only ever reads the backend's
persisted `decision` field — it never calls `evaluateGate()` on the live
data path. `src/lib/gate.ts` exists solely as a pure, unit-tested
reference implementation kept in sync with the backend's actual rule:
having two independently-testable implementations of the same logic is
what caught the any-check-vs-critical-only gate-scoping question above
with real, distinguishable test cases on both sides.
