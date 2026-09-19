# VerityGate — backend

FastAPI + SQLAlchemy + SQLite. Implements the evaluation pipeline
(ingest → normalize → extract → run checks → collect evidence → confidence
→ deterministic gate → persist → route), the rule library with historical
version resolution, the human-review/override workflow, the append-only
audit ledger, and dashboard/calibration aggregation — all computed from
real stored data, not hard-coded numbers. See `../docs/DECISIONS.md` for
every assumption made where the brief left something unspecified.

## Run it

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m app.seed          # wipes and reseeds cimet.db — 9 named scenarios
                             # + a 300-lead synthetic backfill for realistic
                             # dashboard/calibration volume
uvicorn app.main:app --reload --port 8000
```

API docs: `http://localhost:8000/docs`. Health check: `GET /api/health`.

The frontend (`../`) reads `BACKEND_URL` (default `http://localhost:8000`)
— see `../.env.local.example`.

## Tests

```bash
python -m pytest        # 124 tests: unit, API integration, the brief's 8
                         # end-to-end scenarios, adversarial cases, the
                         # AI behaviour layer (against a fake provider)
```

## Architecture

```
FastAPI routes (app/api/*)
  -> services (app/services/*)          the evaluation pipeline, gate,
                                         evaluators, audit, calibration
  -> SQLAlchemy models (app/models.py)  Lead, Transcript, Check, CheckResult,
                                         Evidence, GateDecision, HumanReview,
                                         AuditEvent, CalibrationSample, ...
  -> SQLite (cimet.db)
```

- **`app/services/gate.py`** — the SOLE AUTHORITATIVE deterministic gate
  (the frontend never independently decides a final business outcome; it
  only displays this outcome). Pure functions, no I/O, no model call:
  `criticalFails > 0 → HOLD; ANY check's confidence < floor → QA_REVIEW;
  else AUTO_SUBMIT`. A low-confidence non-critical check can still only
  ever produce `QA_REVIEW`, never `HOLD`. Mirrors the frontend's
  `src/lib/gate.ts` (kept as a pure, unit-tested reference, not on the
  live path).
- **`app/services/evaluators/`** — `verbatim.py` (normalized-text
  similarity, difflib), `factual.py` (regex extraction + tolerance
  comparison against a `crm_snapshot` source of truth; also `presence`
  and `skip_if_absent` modes), `behaviour.py` (dead air; real
  timestamp-overlap interruption detection with a weaker marker-only
  fallback; multi-signal rapport — talk-time share + turn-count share +
  acknowledgment-phrase rate; categorized objection-language detection +
  agent-follow-up check — never critical). All return a structured
  `CheckOutcome` (status, confidence, observed, expected, evidence,
  rationale) — never a bare pass/fail string, and never an LLM call by
  default. **20/20 checks in the catalogue resolve to a real evaluator
  strategy — zero unconditional-PASS pass-throughs.** See
  `../docs/CHECK_AUDIT.md` for the full per-check table. A check that
  genuinely can't be evaluated (misconfiguration, or an evaluator
  exception) becomes `not_evaluable_outcome` — REVIEW status at a
  confidence that always trips the gate floor — never a silent PASS.
- **`app/services/ai_behaviour.py`** — an OPTIONAL semantic refinement
  layer for exactly 3 non-critical checks (Rapport, Interruptions,
  Objection handling — never Dead air, never anything critical).
  `AI_PROVIDER=none` (the default the live demo runs on): a zero-cost
  no-op, deterministic result returned unchanged. When configured: asks
  for a schema-validated JSON result, verifies any cited evidence against
  the real transcript before trusting it at all, either averages
  confidence in on agreement or flags disagreement while keeping the
  deterministic status (never overrides it), and falls back to the
  deterministic result on any malformed output, schema violation, or
  provider exception. Tested against a fake provider
  (`tests/test_ai_behaviour.py`) since no real API key is configured for
  this build.
- **`app/services/pipeline.py`** — orchestrates the above per lead,
  persists `CheckResult`/`Evidence`/`GateDecision`, and writes the
  ingest + evaluation audit trail. Each check's evaluator call is wrapped
  so one evaluator's exception can't crash the whole lead's evaluation
  (degrades to `not_evaluable_outcome` instead). Idempotent: re-running a
  lead clears its previous result set (and any prior `Submission`) rather
  than accumulating duplicates (brief §41 idempotency).
- **`app/services/submission.py`** — the demonstrable submission boundary
  (brief §11): `GateDecision → Submission Service → SUBMITTED`. Only
  `AUTO_SUBMIT` ever produces a `Submission` row (enforced by a
  `ValueError` guard, not just convention) — HOLD/QA_REVIEW never submit.
  `MockSubmissionAdapter` is a clearly-labeled **DEMO/MOCK sandbox**
  (`"sandbox": "DEMO_MOCK"` on every payload) — no real CIMET CRM
  submission endpoint exists.
- **`app/services/rule_resolution.py`** — resolves a lead's checklist
  version by `(retailer, call_date)`, never "today's" version.
- **`app/services/repeat_offence.py`** — same critical check failing 3+
  times for an agent in a rolling 7-day window, computed from stored
  `CheckResult` history, not a hand-set flag.
- **`app/services/dashboard.py` / `calibration.py`** — every number is a
  real aggregate query (brief §31/§33).
- **`app/services/redaction.py`** — card numbers are redacted before a
  transcript segment is ever persisted (`app/services/transcript.py`).
- **`app/services/ai_provider.py`** — the `LLMProvider` abstraction
  `ai_behaviour.py` calls into. Not used anywhere in the critical-check
  path (`verbatim.py`/`factual.py` never import it). A provider failure
  or malformed output can never produce a PASS.
- **`app/services/ingestion.py`, `sandbox_adapter.py`** — the ingestion
  and CIMET-scoring-sandbox boundaries. `MockIngestionAdapter` is what
  every seeded lead runs through; `CIMETSandboxAdapter` and
  `parse_sandbox_payload()` are anti-corruption-layer stubs that raise
  clearly rather than pretending a real integration exists.

## Configuration

Every tunable the brief left unspecified lives in `app/config.py`
(env-overridable, `.env` supported): confidence floor, sample rate,
repeat-offence threshold/window, check weights, rate tolerance,
verbatim match thresholds, dead-air threshold, AI provider, CORS origins.

## Known limitations

- One checklist export in hand (Retailer 1, energy, v1.4) — every lead
  evaluates against it regardless of its own retailer field; the other
  rule-set rows exist for navigation only. `resolve_rule_version` itself
  is retailer/date-correct (tested with multiple retailers and versions)
  for when more checklist exports arrive.
- 3 of the 20 checks (Rapport, Interruptions, Objection handling) run on
  real, transcript-derived deterministic signal — talk-time/turn-count
  ratios, verified timestamp overlap, categorized keyword matching — with
  an *optional* AI layer (`ai_behaviour.py`) available to corroborate
  further when `AI_PROVIDER` is configured. Neither is a full
  sentiment/prosody classifier; both are honestly documented as limited
  rather than overstated. See `../docs/CHECK_AUDIT.md`.
- The AI layer has not been exercised against a real provider in this
  build (no API key configured) — only against a fake provider in tests.
  The plumbing (schema validation, evidence verification, every fallback
  path) is real and tested; a real model's actual output quality is
  unverified here.
- No real CIMET dialler/sandbox/CRM-submission integration —
  `MockIngestionAdapter` and `MockSubmissionAdapter` only, both clearly
  labeled DEMO/MOCK. `CIMETSandboxAdapter` is a boundary stub pending real
  credentials/schema.
- Redaction is regex-heuristic, not a PCI-grade DLP system.
- DOB comparison does light text normalization (case/whitespace), not
  full date-format parsing — a real system would want the latter.
