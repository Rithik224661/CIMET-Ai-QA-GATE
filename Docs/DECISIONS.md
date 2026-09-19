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

## Human override is local-only in Phase 1 (no persistence yet)

Confirming a review in the Human Review form shows the "Audit event
written" confirmation panel using transient client state (CLAUDE.md:
"only form and playback state is local"). It does **not** yet append a row
to the Decision lineage sidebar or the full ledger, because Phase 1 has no
data layer to write to — `HumanReview` and `AuditEvent` are append-only
tables that don't exist until Phase 2/3. The two pre-seeded fixture leads
that already carry a `HumanOverride` (lead `3613766`) show what a
*persisted* override looks like everywhere (banner, lineage, ledger), so
the shape is fully exercised even though the live form's own submission
isn't wired to storage yet. Phase 3 wires the form to a server action that
writes both rows for real, at which point this note should be deleted.

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
or here — it's state that Phase 2's real metrics endpoints should start
honoring.
