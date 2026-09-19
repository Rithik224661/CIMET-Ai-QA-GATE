# CIMET AI QA Gate — Next.js build plan

The design prototype is frontend-only. This is the plan to turn it into a production Next.js application with a real backend, in order, without redesigning anything.

---

## 1. Target stack

| Concern | Choice | Why |
|---|---|---|
| Framework | **Next.js 15, App Router, TypeScript strict** | Server components for data-heavy tables; route handlers for the API surface |
| Styling | **Tailwind CSS** with the design tokens in `tailwind.config.ts` | The prototype is inline-styled by tool constraint; tokens make the same pixels maintainable |
| Data layer | **Prisma + PostgreSQL** | Relational, auditable, append-only ledger fits SQL |
| Auth | **Auth.js (NextAuth)** with your SSO provider; roles `agent`, `tl`, `qa_analyst`, `admin` | Overrides must be attributable |
| Validation | **Zod** at every boundary (API in/out, scoring payloads) | Payload shape is the brief's sandbox contract |
| Jobs | **Inngest** or a Postgres-backed queue (pg-boss) | Ingest → transcribe → score is async and retryable |
| Storage | S3-compatible bucket for recordings, signed URLs only | Audio never served from the app origin |
| Tests | Vitest (units: comparators, gate logic), Playwright (the demo flow) | Gate logic must be regression-proof |

Keep the app in one repo: `apps/web` (Next.js) and `packages/scoring` (pure comparison + gate logic, no I/O) if you want the engine reusable by workers; a single Next app is fine to start.

---

## 2. Route map

```
/                         → redirect to /dashboard
/dashboard                → Executive QA overview
/queue                    → QA/TL queue           ?filter=&retailer=&range=
/sales                    → scenario/lead list (redirects to first lead)
/sales/[leadId]           → Decision workspace     ?check=<checkId>&tab=<all|verbatim|factual|behaviour>&t=<mm:ss>
/rules                    → Check library          ?set=<ruleSetId>
/calibration              → Calibration
/audit/[leadId]           → Decision ledger
```

URL is the state store: retailer, range, queue filter, selected check (opens the drawer), checklist tab, selected transcript turn. Only the override form and playback are local component state. This makes every demo step linkable — a judge or a TL can paste a URL that opens the failing check.

---

## 3. Component map (prototype → React)

```
app/(app)/layout.tsx            → shell: Rail, TopBar, environment banner
components/nav/Rail.tsx         → numbered nav, badge from /api/queue/count
components/nav/TopBar.tsx       → crumb + title + RetailerSelect + RangeSelect (URL-writing)
components/ui/Chip.tsx          → 100px radius status chip (+ optional dot)
components/ui/Button.tsx        → 0 radius; variants primary | secondary | danger
components/ui/StatGrid.tsx      → the 1px hairline grid used by KPIs and decision stats
components/ui/DataTable.tsx     → mono table shell: sticky header, hairline rows, x-scroll
components/dashboard/*          → KpiGrid, DecisionDistribution, FailingChecks,
                                  RecentFailures, RecentOverrides
components/queue/QueueTable.tsx + QueueFilters.tsx
components/sale/DecisionHeader.tsx
components/sale/OverrideBanner.tsx
components/sale/FindingCard.tsx
components/sale/CallTimeline.tsx (+ TimelineMarkers, TranscriptList)
components/sale/ChecklistTable.tsx + ChecklistTabs.tsx
components/sale/HumanReview.tsx  (server action: submitOverride)
components/sale/Lineage.tsx
components/evidence/EvidenceDrawer.tsx (Radix Dialog; keeps aria + focus trap)
components/rules/RuleSetList.tsx + RuleTable.tsx
components/calibration/*        → CalKpis, ConfidenceHistogram, DisagreementBars
components/audit/LedgerTable.tsx
components/states/Processing.tsx, IngestError.tsx, EmptyFindings.tsx
```

Rules for the rebuild: server components for anything that only renders data; `"use client"` only for the drawer, filters, timeline selection, override form, and the responsive rail. Status→color mapping lives in one module (`lib/status.ts`) — never inline ternaries scattered across components.

---

## 4. Domain types

```ts
type Decision = 'AUTO_SUBMIT' | 'HOLD' | 'QA_REVIEW';
type CheckType = 'VERBATIM' | 'FACTUAL' | 'BEHAVIOUR';
type ResultStatus = 'PASS' | 'FAIL' | 'REVIEW';

interface Lead {
  id: string; retailerId: string; product: 'ENERGY' | 'BROADBAND';
  agentId: string; teamLeadId: string; callStartedAt: string; durationSec: number;
  crmSnapshot: Record<string, string>;      // authoritative field values at call time
  planId: string | null;                     // resolves the rate card
}

interface Recording { leadId: string; storageKey: string; receivedAt: string; bytes: number; }

interface Transcript {
  leadId: string; engine: string; engineVersion: string;
  turns: Array<{ startMs: number; endMs: number; speaker: 'AGENT'|'CUSTOMER'|'SYSTEM'; text: string; words?: Array<{t:number;w:string}> }>;
  silences: Array<{ startMs: number; endMs: number }>;
}

interface Check {                      // definition, versioned
  id: string; ruleSetVersionId: string; code: string;      // RET1-FM-008
  name: string; type: CheckType; critical: boolean; weight: number;
  sourceOfTruth: string;               // 'CRM.email' | 'RATECARD.plan.peak' | 'SCRIPT.v1_4.§4'
  params: Record<string, unknown>;     // tolerances, windows, thresholds
}

interface CheckResult {
  id: string; leadId: string; checkId: string; ruleSetVersionId: string;
  status: ResultStatus; confidence: number;               // 0..1
  observed: string | null; expected: string | null;
  evidence: { quote: string; startMs: number; endMs: number; turnIndex: number } | null;
  rationale: string;                   // "Evaluation — what the system determined"
  evaluatedAt: string;
}

interface GateDecision {
  leadId: string; decision: Decision; reason: string; ruleApplied: string;
  criticalFails: number; lowConfidence: number; sampledForAudit: boolean; decidedAt: string;
}

interface HumanReview {
  id: string; leadId: string; reviewerId: string; reviewerRole: string;
  aiDecision: Decision; humanDecision: 'PASS' | 'HOLD'; reason: string; createdAt: string;
}

interface AuditEvent {
  id: string; leadId: string; seq: number; at: string;
  event: string; actor: string; version: string | null; resultingState: string;
}
```

Append-only: `CheckResult`, `GateDecision`, `HumanReview`, `AuditEvent` are never updated or deleted. Re-scoring writes a new row with a new `ruleSetVersionId`.

---

## 5. API surface (route handlers)

```
GET  /api/leads?retailer=&range=&filter=      → queue rows (deciding-check confidence computed server-side)
GET  /api/leads/[id]                          → lead + decision + results + transcript + lineage
GET  /api/leads/[id]/audio?t=                 → 302 to a signed, time-bounded URL (redaction applied)
POST /api/leads/[id]/review                   → { humanDecision, reason } → HumanReview + AuditEvent
POST /api/leads/[id]/rescore                  → enqueue re-scoring (admin only)
GET  /api/rulesets                            → retailers → checklists → versions
GET  /api/rulesets/[versionId]/checks
GET  /api/metrics/dashboard?retailer=&range=
GET  /api/metrics/calibration?range=
POST /api/ingest/recording                    → dialler webhook: { leadId, mediaUrl, sha256 }
```

Every handler validates with Zod and returns the domain types above verbatim — the UI shape and the API shape are already the same, which is the point of the prototype's data separation.

---

## 6. Scoring pipeline (backend phases)

```
recording webhook → store → ASR (speaker diarisation + word timestamps) → normalise
→ resolve rule set version by (retailer, callStartedAt) → run checks → evidence extraction
→ confidence → gate decision → 5% sampling → persist + audit events → notify TL queue
```

Implementation notes that the design depends on:

1. **Rule resolution is by call date, not today.** `SELECT … WHERE retailer = ? AND effective_from <= callStartedAt ORDER BY effective_from DESC LIMIT 1`. The UI prints this version on every result.
2. **Three engines, one interface.** `evaluate(check, ctx) → CheckResult`:
   - *Verbatim*: align the required script paragraph against the transcript window; score by normalised edit distance / WER. Crosstalk or WER above threshold → `REVIEW`, never `FAIL`.
   - *Factual*: extract the spoken value (rate, email, NMI, DOB, address, date, gift-card amount), normalise both sides, compare with an explicit tolerance (rates: 0c). Mismatch → `FAIL` with observed + expected.
   - *Behaviour*: transcript/silence analytics only (dead air > 30s, interruption rate, rapport, objection handling). Never critical, never blocking.
3. **Confidence is per check** and must combine ASR confidence in the evidence window with extraction/match confidence. Below **0.85** on any check → route to QA. Tune the floor in config, not code.
4. **Gate** is deterministic and pure: `criticalFails > 0 → HOLD; anyConfidence < floor → QA_REVIEW; else AUTO_SUBMIT`. Unit-test it exhaustively; it must never be an LLM call.
5. **LLM usage** is confined to extraction and semantic judgement inside a check, always returning a structured result with a quote span. Comparison and gating stay deterministic. Log prompt + model version on the result for traceability.
6. **Guardrails**: PII redaction before storage and before playback (card numbers), consent verified as a check rather than assumed, no auto-correction of CRM data, overrides logged, synthetic data only until the gate is live.

---

## 7. Delivery phases

| Phase | Outcome |
|---|---|
| **0 · Scaffold** | Next.js + TS + Tailwind with tokens, shell, rail, top bar, fonts, CI lint/typecheck |
| **1 · UI on fixtures** | All 6 views + drawer + states rebuilt pixel-close, fed by the prototype's 9 leads as typed JSON fixtures under `lib/fixtures/` |
| **2 · Data layer** | Prisma schema, seed the same fixtures into Postgres, swap fixture imports for queries — UI untouched |
| **3 · API + auth** | Route handlers, Zod, Auth.js roles; override becomes a server action writing HumanReview + AuditEvent |
| **4 · Ingest + ASR** | Dialler webhook, storage, transcription with diarisation and word timestamps, normalisation |
| **5 · Scoring engine** | The three engines + confidence + deterministic gate, against one retailer's real checklist |
| **6 · Calibration** | Sampling job (5% of clean calls), agreement metrics computed from real reviews |
| **7 · Hardening** | Redaction, retention, audit export, load test on the queue, Playwright demo flow in CI |

Phase 1 is the natural first Claude Code session: it is pure UI recreation with no backend risk, and it makes the rest incremental.

---

## 8. What must not drift from the design

- Buttons `border-radius: 0`; chips `border-radius: 100px`.
- All data, IDs, metrics, timestamps and code in Geist Mono.
- Palette exactly as listed in `README.md` — no new brand colors.
- Status always glyph + word, never color alone.
- The gate decision is the largest element on the workspace.
- Observed / expected / evaluation / confidence / decision stay visually separated wherever a result is shown.
- An override never replaces the AI decision on screen or in the data.
