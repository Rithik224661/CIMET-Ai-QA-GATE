# CIMET AI QA Gate — backend

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
python -m pytest        # 81 tests: unit, API integration, the brief's 8
                         # end-to-end scenarios, adversarial cases
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

- **`app/services/gate.py`** — the deterministic gate. Pure functions, no
  I/O, no model call: `criticalFails > 0 → HOLD; anyConfidence < floor →
  QA_REVIEW; else AUTO_SUBMIT`. Mirrors the frontend's
  `src/lib/gate.ts` so both are independently testable against the same
  rule.
- **`app/services/evaluators/`** — `verbatim.py` (normalized-text
  similarity, difflib), `factual.py` (regex extraction + tolerance
  comparison against a `crm_snapshot` source of truth), `behaviour.py`
  (transcript-only heuristics, never critical). All three return a
  structured `CheckOutcome` (status, confidence, observed, expected,
  evidence, rationale) — never a bare pass/fail string, and never an LLM
  call. See the module docstrings for exactly what's genuinely extracted
  vs. a documented pass-through default (14 of the 20 checks in the one
  checklist export don't have bespoke extraction configured — see
  `app/seed_data.py`'s `CHECK_CATALOGUE` and `../docs/DECISIONS.md`).
- **`app/services/pipeline.py`** — orchestrates the above per lead,
  persists `CheckResult`/`Evidence`/`GateDecision`, and writes the
  ingest + evaluation audit trail. Idempotent: re-running a lead clears
  its previous result set rather than accumulating duplicates (brief
  §41 idempotency).
- **`app/services/rule_resolution.py`** — resolves a lead's checklist
  version by `(retailer, call_date)`, never "today's" version.
- **`app/services/repeat_offence.py`** — same critical check failing 3+
  times for an agent in a rolling 7-day window, computed from stored
  `CheckResult` history, not a hand-set flag.
- **`app/services/dashboard.py` / `calibration.py`** — every number is a
  real aggregate query (brief §31/§33).
- **`app/services/redaction.py`** — card numbers are redacted before a
  transcript segment is ever persisted (`app/services/transcript.py`).
- **`app/services/ai_provider.py`** — an `LLMProvider` abstraction, not
  used by any evaluator by default (`AI_PROVIDER=none`, zero external
  calls, zero credentials needed). Wired for a future semantic-extraction
  step; a provider failure or malformed output can never produce a PASS.
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
- 14 of the 20 checks have no bespoke extraction wired (documented
  pass-through, not a fabricated PASS — see the evaluator docstrings);
  the 6 that anchor the brief's worked example (disclaimer, DMO, rate,
  email, address, dead air) are genuinely computed from transcript text
  against a `crm_snapshot` source of truth.
- No real CIMET dialler/sandbox integration — `MockIngestionAdapter` only.
  `CIMETSandboxAdapter` is a boundary stub pending real credentials/schema.
- Redaction is regex-heuristic, not a PCI-grade DLP system.
