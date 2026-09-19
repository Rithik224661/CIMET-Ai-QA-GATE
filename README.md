# CIMET AI QA Gate

An evidence-backed AI quality gate that sits between a completed sales
call and submission of the sale in CRM. Every sale is scored automatically
against the retailer's checklist: all criticals green auto-submits, any
critical fail holds the sale for the TL queue, low confidence on any
check routes to QA rather than auto-passing. Every result resolves to a
transcript line, an audio timestamp and the check-library version that
was live on the call date.

Built for CIMET's QA Automation engineering brief (`docs/QA-Automation-Handout.pdf`).

A working end-to-end system: a Next.js frontend (pixel-close to the
approved design) backed by a real FastAPI service that ingests a
transcript, runs it through deterministic verbatim/factual/behaviour
evaluators against a CRM source of truth, computes and persists a
deterministic gate decision, and supports a real human-review/override
workflow with an append-only audit ledger. See
[`design_handoff/NEXTJS_BUILD_PLAN.md`](design_handoff/NEXTJS_BUILD_PLAN.md)
for the original phase plan and [`backend/README.md`](backend/README.md)
for the backend architecture in depth.

## Stack

**Frontend:** Next.js 16 (App Router) · TypeScript strict · Tailwind CSS v4
· Radix UI (evidence drawer) · Vitest (gate-logic unit tests) · Playwright
(demo e2e flow).

**Backend:** Python · FastAPI · SQLAlchemy · SQLite · Pytest (81 tests:
unit, API integration, the brief's 8 end-to-end scenarios, adversarial
cases).

## Getting started

```bash
# backend — http://localhost:8000
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload --port 8000

# frontend — http://localhost:3000 (in a second terminal, from the repo root)
pnpm install
pnpm dev
```

The frontend reads `BACKEND_URL` (default `http://localhost:8000`) — see
`.env.local.example`.

```bash
# frontend checks
pnpm typecheck && pnpm lint && pnpm test && pnpm test:e2e

# backend checks
cd backend && python -m pytest
```

## What's here

- **Six views**: Dashboard, QA Queue, Sales (decision workspace), Rules
  (check library), Calibration, Audit (decision ledger) — plus the
  evidence inspector drawer and the processing / ingest-error / empty-
  findings states, all backed by the real API.
- **Nine scenario leads** (clean auto-submit, rate + email mismatch hold —
  the brief's worked example, address mismatch, low-confidence QA review,
  behaviour-note-only auto-submit, human override with audit trail, repeat
  critical failure, processing, ingest error), each genuinely evaluated
  from transcript text against a `crm_snapshot` source of truth — not
  hand-authored outcomes. See `backend/app/seed_data.py`.
- **A pure, deterministic gate**, implemented independently in both
  layers and tested against the same rule: `backend/app/services/gate.py`
  (backend, authoritative — computes and persists the decision) and
  `src/lib/gate.ts` (frontend, unit-tested reference). `criticalFails > 0
  → HOLD; anyConfidence < floor → QA_REVIEW; else AUTO_SUBMIT`. Never a
  model call.
- **Three real evaluators** (`backend/app/services/evaluators/`):
  normalized-text verbatim matching, regex-based factual extraction +
  tolerance comparison, transcript-only behaviour heuristics — every
  result carries observed/expected/evidence/confidence, never a bare
  pass/fail string.
- **A real human-review workflow**: the override form calls a Next.js
  server action → `POST /api/reviews` → a persisted `HumanReview` +
  `AuditEvent`, appended alongside the AI decision, never replacing it.
- **URL-driven view state** (`?filter=`, `?check=`, `?tab=`, `?t=`) — only
  form and playback state is local component state.

## Project structure

```
src/                        Next.js frontend (see above)
  app/(app)/                 route segments: dashboard, queue, sales/[leadId], rules, calibration, audit/[leadId]
  components/                 ui/, nav/, layout/, dashboard/, queue/, sale/, evidence/, rules/, calibration/, audit/, states/
  lib/
    types.ts, gate.ts, status.ts, config.ts   domain types, pure gate reference, status→color/glyph, tunables
    api/client.ts             the one place the frontend calls the backend
    actions/review.ts         the override server action
    data/                     repository layer — fetches from the backend API
    fixtures/                  original Phase-1 typed fixtures, kept for reference/tests

backend/                    FastAPI backend — see backend/README.md
  app/
    models.py, schemas.py, enums.py, config.py
    services/                 rule resolution, evaluators/, evidence, gate, pipeline, audit, calibration,
                               dashboard, repeat_offence, redaction, ingestion, sandbox_adapter, ai_provider
    api/                       FastAPI routers
    seed_data.py, seed.py       the 9 named scenarios + bulk synthetic backfill
  tests/                       81 pytest cases

docs/DECISIONS.md            every assumption made where the brief left something unspecified
design_handoff/               the approved design spec, the interactive HTML prototype, and the Next.js build plan
```

## Design fidelity

The design is approved and final — see `CLAUDE.md` at the repo root for
the non-negotiables (zero-radius buttons, 100px-radius chips, Geist Mono
for all data, the exact palette, glyph + word for every status, the
append-only audit trail). `design_handoff/README.md` is the design spec;
`design_handoff/CIMET AI QA Gate.dc.html` is the original interactive
prototype these fixtures and this copy were extracted from.
