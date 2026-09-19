# Architecture — VerityGate

Concise system reference. For the product pitch, see the root `README.md`.

## System overview

Two processes: a Next.js 16 frontend (server components read from the backend on every request — no client-side caching of the gate decision) and a FastAPI backend owning all persistence and the gate logic. SQLite is the only datastore; no message queue, no separate worker process — evaluation is synchronous.

```
Browser → Next.js (App Router, server components) → FastAPI → SQLite
                    │
                    └─ /api/audio/[leadId] route proxies WAV bytes from the backend
                       (keeps BACKEND_URL server-only)
```

## Components

| Component | Location | Responsibility |
|---|---|---|
| Ingestion adapter | `backend/app/services/ingestion.py` | Recording arrival boundary. `MockIngestionAdapter` is the only one wired up; `CIMETSandboxAdapter` is a visible, unimplemented real boundary. |
| ASR provider | `backend/app/services/asr_provider.py` | Transcription boundary. `MockTranscriptProvider` returns the transcript already ingested — never fabricates a transcription. |
| Evaluators | `backend/app/services/evaluators/{verbatim,factual,behaviour}.py` | The three check types. Deterministic by construction. |
| AI behaviour layer | `backend/app/services/ai_behaviour.py`, `ai_provider.py` | Optional, non-critical-only semantic corroboration. See "AI boundary" below. |
| Gate | `backend/app/services/gate.py` | Pure function: check statuses/confidences → `Decision`. Exhaustively unit-tested (`tests/test_gate.py`). |
| Pipeline orchestration | `backend/app/services/pipeline.py` | `run_evaluation()` — the one place all evaluators + the gate + persistence + submission are wired together. |
| Submission adapter | `backend/app/services/submission.py` | `MockSubmissionAdapter`, only reachable from `AUTO_SUBMIT` (enforced by a `ValueError` guard, not convention). |
| Sandbox adapter | `backend/app/services/sandbox_adapter.py` | Anti-corruption layer for a future CIMET-supplied scoring-sandbox payload shape. No real schema supplied. |
| Redaction | `backend/app/services/redaction.py` | Card-number regex redaction, applied before persistence. |
| Audit | `backend/app/services/audit.py` | Append-only `AuditEvent` writer. |

## Data flow (one evaluation)

```
run_evaluation(db, lead)
  1. Resolve rule version (docs/DECISIONS.md §rule resolution)
  2. Build EvaluationContext (transcript segments + crm_snapshot)
  3. If AI_PROVIDER != none: ONE combined AI call for rapport/interruptions/
     objection_handling (ai_behaviour.evaluate_all_behaviour_metrics) — not
     one call per check
  4. Clear this lead's prior CheckResult/Evidence/GateDecision/Submission
     (relationship-mutated, not just re-added — avoids stale in-memory
     SQLAlchemy caches)
  5. For each Check: evaluate_verbatim | evaluate_factual | evaluate_behaviour
     (the latter optionally refined by the AI layer's precomputed result)
     — any evaluator exception degrades to a REVIEW outcome, never a crash
       or a silent pass
  6. evaluate_gate(check_results) → Decision
  7. Persist GateDecision + write GATE_DECIDED / SALE_HELD / SALE_AUTO_
     SUBMITTED AuditEvents
  8. If AUTO_SUBMIT: submit_if_auto_submitted() → Submission row
```

## Evaluation flow (per check type)

- **Verbatim**: normalized text similarity (`difflib`) between the transcript span and the approved script phrase, thresholded into PASS / REVIEW / FAIL.
- **Factual**: regex-extracted value from the transcript compared against `crm_snapshot` or the rate card, with a configurable tolerance; `presence`/`skip_if_absent` modes for checks that are about *whether something was said* rather than a value match.
- **Behaviour**: transcript-derived heuristics (dead-air duration, timestamp-overlap interruption detection, talk-time/turn-count/acknowledgment-based rapport, categorized objection-language matching). Never critical. Eligible for the optional AI layer (except `dead_air`, a hard threshold with nothing semantic to interpret).

## AI boundary

The AI layer is reachable from exactly one call site: `evaluate_behaviour()` for `metric in {rapport, interruptions, objection_handling}`. It:

- never receives a critical check's data (critical checks are Verbatim/Factual only, and neither evaluator imports the AI module)
- can only **refine confidence and rationale** of an already-computed deterministic outcome — `_combine()` in `ai_behaviour.py` never lets the AI's status replace the deterministic status
- must cite evidence that is verified against the real transcript segments it was given (`_verify_evidence`); unverifiable evidence discards the whole AI response
- degrades to the deterministic outcome on any exception, malformed JSON, or schema violation (`AIBehaviourResult` Pydantic model)
- is observed: every attempted call (success or fallback) writes an `AI_EVALUATION` AuditEvent with `provider`, `model`, `used`, `latencyMs`, `fallbackReason` — never the API key

## Gate boundary

`backend/app/services/gate.py`'s `evaluate_gate()` is a pure function with no I/O, no randomness, no model call. It is the **only** place a `Decision` is produced. The frontend's `src/lib/gate.ts` mirrors the same logic for unit-testing purposes but is never called on the live data path — `gateForLead()` (`src/lib/data/leads.ts`) only ever reads `lead.decision` as returned by the API.

## Data model

```
Retailer 1───* Checklist 1───* RuleVersion 1───* Check
Lead 1───1 Recording
Lead 1───1 Transcript 1───* TranscriptSegment
Lead 1───* CheckResult 1───* Evidence
Lead 1───1 GateDecision 1───0/1 Submission
Lead 1───* HumanReview
Lead 1───* AuditEvent
```

`is_seed_scenario` distinguishes the 9 named, individually-inspectable demo leads from the ~300 bulk synthetic backfill leads (dashboard/calibration volume only — never listed in the Queue or Sales rail).

## Integration boundaries

See `docs/INTEGRATION.md` for the full IMPLEMENTED / READY FOR INTEGRATION / NOT AVAILABLE breakdown of ingestion, ASR, sandbox, and submission.

## Failure handling

- Missing transcript / missing rule version: `run_evaluation` raises `ValueError` before any check runs — never a partial/garbage evaluation.
- Evaluator exception: caught per-check in `pipeline.py`'s loop, degraded to a sub-floor-confidence REVIEW outcome — never crashes the whole lead's evaluation, never silently passes.
- AI provider exception/timeout/malformed output: degrades to the deterministic outcome, logged, never crashes, never fabricates a pass (`ai_behaviour.maybe_refine_with_ai`).
- Ingest error state (`Lead.state == "error"`): the lead is visibly flagged, never silently scored.
- `submit_if_auto_submitted` raises if called with a non-`AUTO_SUBMIT` decision — a HOLD/QA_REVIEW lead cannot be submitted by any code path, not just by omission.

## Security considerations

- `ANTHROPIC_API_KEY` and `BACKEND_URL` are read only in backend code / Next.js server components — never serialized into a client bundle.
- Card numbers are redacted (`redaction.py`) before a transcript segment is ever persisted.
- The `/api/leads/{id}/audio` endpoint derives its file path purely from the validated `lead_id`, never from a client-supplied path — no arbitrary file read is possible.
- CORS origins are an explicit allowlist (`Settings.cors_origins`), not a wildcard.
- API error responses carry a `detail` string only — no stack traces or filesystem paths are returned to the client (`HTTPException` usage throughout `app/api/*.py`).

## Scalability path

See "Production path" in the root README — this section is intentionally vision-only, since none of it is implemented in this prototype.
