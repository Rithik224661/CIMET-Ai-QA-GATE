# Demo script — VerityGate

## Pre-demo setup

```bash
# Backend — fresh, deterministic reset
cd backend
rm -f cimet.db
python -m app.seed 300      # → "Seeded 311 leads (309 scored) against 20 check rows."
uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# Frontend
cd ..
pnpm dev -p 3001 &
```

Open `http://localhost:3001` — it redirects to `/dashboard`.

`python -m app.seed 300` is fully deterministic: re-running it against an empty database reproduces the same lead count, same named scenarios, same check results every time. Use it to reset between demo runs.

## Demo order (≈5 minutes)

Run through in this order — each step builds on the last.

### 1. Clean → AUTO_SUBMIT (`3613742`)

Open `/sales/3613742`. All 20 checks pass. Decision: `AUTO-SUBMIT`. Scroll to the submission line — it's a real persisted `Submission` record labeled `DEMO_MOCK`, not a UI toggle. Optionally click **Re-score** (top of the decision header) — this fires a real `POST /api/evaluations`, and the audit ledger (`/audit/3613742`) gains new entries from the fresh run.

**Say:** "This isn't a mock state switch — the Re-score button hits the real backend pipeline, and the submission you see is a genuine database record."

### 2. Worked example → HOLD (`3613790`)

Open `/sales/3613790`. Two critical failures:

| Check | Observed | Expected |
|---|---|---|
| Rates and charges | `28.6c / kWh peak` | `31.9c / kWh peak` |
| Email captured | `j.smith@gmial.com` | `j.smith@gmail.com` |

Click **Play evidence** on the "Rates and charges" finding. The evidence drawer opens, transcript highlights, and real audio loads and plays, seeked to 14:02.

**Say:** "The audio is real — it's an actual WAV file served with Range-request support, seeked to the exact evidence timestamp, not a canned animation."

### 3. Low confidence → QA_REVIEW (`3613811`)

Open `/sales/3613811`. Decision: `QA_REVIEW`, reason states insufficient confidence on a check. No submission exists.

**Say:** "Confidence below the floor never auto-passes, critical or not — it always routes to a human."

### 4. Behaviour signal (`3613824`)

Open `/sales/3613824`. Open the Objection handling / Rapport checks in the checklist table — the evidence quote is the real customer pushback line from the transcript, and the rationale cites real measured percentages (talk-time share, turn-count share), not a placeholder.

**Say:** "Behaviour checks never block a sale, but they're not a silent pass either — this is a real transcript-derived signal."

### 5. Human override (`3613766`)

Open `/sales/3613766`, then `/audit/3613766`. The AI decision (`HOLD`) is still shown; a separate human override (`PASS`) is stored alongside it, with its own audit event.

**Say:** "The AI decision is never erased or edited — the human decision sits next to it, and the override itself is an audit event."

### 6. Calibration (`/calibration`)

**Say:** "This is computed from ~300 synthetic backfill leads generated at seed time — it's demo data illustrating what a calibration dashboard would show, not real CIMET call volume."

## What not to claim

- **Do not** say a real Anthropic API call ran in this demo — the live default (`AI_PROVIDER=none`) makes zero external calls. If asked "where's the AI," show the AI architecture section of the README and the `AI_EVALUATION` audit-event mechanism instead (see the fallback smoke test below).
- **Do not** present calibration numbers as real CIMET performance data.
- **Do not** claim the synthetic audio is a real call recording — say so if asked directly.

## Fallback if AI_PROVIDER=anthropic is asked about

No real Anthropic key was available in this environment. What *was* verified live: starting the backend with `AI_PROVIDER=anthropic` and no valid key, then evaluating a lead, produces a real `AI_EVALUATION` audit event with `used: false` and a `fallbackReason`, and the gate decision is provably unaffected. This proves the safety architecture (never crash, never fabricate a pass) without needing a live credentialed call:

```bash
AI_PROVIDER=anthropic uvicorn app.main:app --port 8000 &
curl -X POST localhost:8000/api/evaluations -H "Content-Type: application/json" -d '{"leadId":"3613824"}'
curl localhost:8000/api/audit/3613824   # look for the "Ai Evaluation" / AI_FALLBACK entry
```

If a real `ANTHROPIC_API_KEY` is supplied, the exact same code path makes one real contextual call per lead instead — see `docs/CHECK_AUDIT.md`.

## Reset between runs

```bash
cd backend && rm -f cimet.db && python -m app.seed 300
```

Restart both servers after reseeding so nothing is holding a stale in-memory SQLAlchemy session.
