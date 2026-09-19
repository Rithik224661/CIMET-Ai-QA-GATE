# CIMET AI QA Gate

An evidence-backed AI quality gate that sits between a completed sales
call and submission of the sale in CRM. Every sale is scored automatically
against the retailer's checklist: all criticals green auto-submits, any
critical fail holds the sale for the TL queue, low confidence on any
check routes to QA rather than auto-passing. Every result resolves to a
transcript line, an audio timestamp and the check-library version that
was live on the call date.

Built for CIMET's QA Automation engineering brief (`Docs/QA-Automation-Handout.pdf`).

This is **Phase 1** of the build: the full production UI, pixel-close to
the approved design, running on typed fixtures — no backend yet. See
[`design_handoff/NEXTJS_BUILD_PLAN.md`](design_handoff/NEXTJS_BUILD_PLAN.md)
for the full phase plan (Prisma + Postgres, route handlers + auth,
ingestion, the scoring engine, calibration, hardening).

## Stack

Next.js 16 (App Router) · TypeScript strict · Tailwind CSS v4 · Radix UI
(evidence drawer) · Vitest (gate-logic unit tests) · Playwright (demo
e2e flow).

## Getting started

```bash
pnpm install
pnpm dev          # http://localhost:3000 (redirects to /dashboard)
```

```bash
pnpm typecheck    # tsc --noEmit
pnpm lint         # eslint
pnpm test         # vitest — exhaustive gate-logic tests
pnpm test:e2e     # playwright — open lead → HOLD → evidence → override → audit event
pnpm build        # production build
```

## What's here

- **Six views**: Dashboard, QA Queue, Sales (decision workspace), Rules
  (check library), Calibration, Audit (decision ledger) — plus the
  evidence inspector drawer and the processing / ingest-error / empty-
  findings states.
- **Nine scenario leads** (clean auto-submit, rate + email mismatch hold —
  the brief's worked example, address mismatch, low-confidence QA review,
  behaviour-note-only auto-submit, human override with audit trail, repeat
  critical failure, processing, ingest error) against a 20-check Retailer 1
  energy checklist. See `src/lib/fixtures/`.
- **A pure, deterministic gate** (`src/lib/gate.ts`): `criticalFails > 0 →
  HOLD; anyConfidence < floor → QA_REVIEW; else AUTO_SUBMIT`. Never a model
  call, unit-tested exhaustively in `src/lib/gate.test.ts`.
- **URL-driven view state** (`?filter=`, `?check=`, `?tab=`, `?t=`) — only
  form and playback state is local component state.

## Project structure

```
src/
  app/(app)/             route segments: dashboard, queue, sales/[leadId], rules, calibration, audit/[leadId]
  components/            ui/, nav/, layout/, dashboard/, queue/, sale/, evidence/, rules/, calibration/, audit/, states/
  lib/
    types.ts             domain types (Lead, CheckResult, GateDecision, AuditEvent, …)
    gate.ts              the pure gate + decision-copy generator
    status.ts             single source of truth for status → color/glyph
    config.ts             tunables the brief left unspecified (see docs/DECISIONS.md)
    fixtures/              the 9 leads, 20-check catalogue, transcripts, rule sets, dashboard/calibration numbers
    data/                  repository layer — reads fixtures now, swaps for Prisma queries in Phase 2 without touching components
docs/DECISIONS.md         every assumption made where the brief left something unspecified
design_handoff/            the approved design spec, the interactive HTML prototype, and the Next.js build plan
```

## Design fidelity

The design is approved and final — see `CLAUDE.md` at the repo root for
the non-negotiables (zero-radius buttons, 100px-radius chips, Geist Mono
for all data, the exact palette, glyph + word for every status, the
append-only audit trail). `design_handoff/README.md` is the design spec;
`design_handoff/CIMET AI QA Gate.dc.html` is the original interactive
prototype these fixtures and this copy were extracted from.
