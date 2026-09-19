# Handoff: CIMET AI QA Gate

## Overview

An evidence-backed AI quality gate that sits between a completed sales call and submission of the sale in CRM. Every sale is scored automatically against the retailer's checklist; all criticals green → auto-submit, any critical fail → hold in the TL queue, low confidence → QA review. Every result resolves to a transcript line, an audio timestamp and the check-library version that was live on the call date.

This bundle documents the **frontend product design**. Target implementation: **Next.js (App Router) + TypeScript**, with a real backend wired in afterwards. See `NEXTJS_BUILD_PLAN.md` for the architecture and phasing, `GETTING_STARTED.md` for the Claude Code / GitHub workflow.

## About the design files

The files in this bundle are **design references created in HTML** — a working prototype showing intended look, structure and behaviour. They are **not production code to copy directly**.

`CIMET AI QA Gate.dc.html` is a single-file prototype written in a streaming HTML component format with an embedded logic class and **inline styles only** (no stylesheets, no CSS classes). That constraint belongs to the prototype tool, not to the product. In Next.js, rebuild the same visual design using the codebase's real patterns: React components, Tailwind (or CSS Modules), typed props, server components where the data is server-owned.

Recreate the design faithfully — the prototype is the source of truth for layout, palette, typography and interaction — but implement it idiomatically.

## Fidelity

**High-fidelity.** Colors, typography, spacing, density, states and copy are final. Rebuild pixel-close. Where the prototype's inline styles conflict with production practice (e.g. repeated literals), extract tokens — but do not change the resulting pixels.

---

## Design tokens

### Color

| Token | Value | Use |
|---|---|---|
| `bg` | `#000000` | Page background |
| `surface` | `#0a0a0a` | Cards, sidebar, table bodies |
| `surface-2` | `#121212` | Hover / selected row, active nav |
| `chip-bg` | `#1f1f1f` | Status chip background |
| `ring` | `rgba(255,255,255,0.145)` | 1px borders on every card and table |
| `hairline` | `rgba(255,255,255,0.08)` | Row dividers inside cards |
| `track` | `rgba(255,255,255,0.08)` | Bar-chart / progress track |
| `bar-muted` | `rgba(255,255,255,0.18)` – `0.35` | Inactive bars, timeline default |
| `text` | `#ffffff` | Headings, primary numerics |
| `text-2` | `#ededed` | Body data text |
| `text-muted` | `#999999` | Labels, secondary data |
| `text-dim` | `#666666` | Kickers, meta, disabled |
| `cta-ink` | `#121212` | Text on white buttons |
| `pass` | `#62c073` | PASS, AUTO-SUBMIT |
| `fail` | `#f2685c` | FAIL, HOLD, ERROR |
| `review` | `#e0a341` | REVIEW, low confidence, demo-data flag |
| `accent` | `#52a8ff` | Active/selected, evidence highlight, links |

No other colors. Status is never conveyed by color alone — every status carries a glyph (`✓` / `✕` / `⚠`) and a word.

### Typography

- **Inter** (400/500/600) — headings, body copy, buttons, nav.
- **Geist Mono** (400/500) — every ID, metric, data value, table row, status text, timestamp, rule version, code. Non-negotiable: data is never set in a proportional face.

| Role | Size | Weight | Tracking |
|---|---|---|---|
| Gate decision | `clamp(34px, 4.4vw, 52px)` mono | 400 | `-2.6px` |
| KPI value | 40px mono | 400 | `-2.2px` |
| Calibration KPI | 36px mono | 400 | `-2px` |
| View title (h1) | 18px Inter | 500 | `-0.5px` |
| Card title (h2/h3) | 15px / 18–19px Inter | 500 | `-0.3px` / `-0.5px` |
| Body copy | 13–15px Inter | 400 | — |
| Table / data row | 12–13px mono | 400 | — |
| Column header, kicker | 11px mono, uppercase | 400 | `+1px` |
| Micro label | 10px mono, uppercase | 400 | `+0.5px` |

### Shape & spacing

- **Buttons: `border-radius: 0`, always.** Primary = `#fff` bg / `#121212` text; secondary = transparent with `1px solid ring`, hover `rgba(255,255,255,0.4)`.
- **Status chips: `border-radius: 100px`, always.** `background:#1f1f1f; padding:4px 10px; gap:6px; font-size:12px` mono uppercase, with an optional `6×6px` round status dot.
- Cards: `#0a0a0a` + `1px solid ring`, no radius, no shadow.
- Emphasis borders: `border-left: 3px` (decision card, colored by decision), `border-left: 2px` (active list row, override banner, evidence quote), `border-top: 2px` (finding card, colored by severity).
- Section padding `clamp(16px, 2.4vw, 28px)`; card padding 20–24px; table row padding 11px (compact) / 16px (comfortable) × 18–20px.
- Grid/flex with `gap` everywhere; 1px "hairline grids" are made with `gap:1px` over a `ring`-colored background.

### Motion

Three keyframes only: `qaspin` (900ms linear, processing spinner), `qapulse` (1s ease-in-out, live/processing dot), `qaslide` (180ms ease-out, drawer + audit confirmation). Hover changes are instant background/border swaps. Nothing else animates.

---

## Information architecture

Left rail, 208px, `#0a0a0a`, numbered items; collapses to a horizontal scrolling bar below 1040px viewport width.

`01 Dashboard · 02 QA Queue (badge = open items) · 03 Sales · 04 Calibration · 05 Rules · 06 Audit`

Sticky top bar on every view: crumb (small mono, uppercase) + view title, then a Retailer select (`All retailers` / `Retailer 1–3`) and a Range select (`Today` / `7 days` / `30 days`) right-aligned.

Rail footer: a `Demo data` chip (review amber) and the line "Synthetic leads and sanitised transcripts. No customer PII." Keep an equivalent environment banner in production for non-prod environments.

---

## Screens

### 1. Dashboard — "Executive QA overview"

Purpose: a QA lead sees operational health in seconds.

- **KPI grid**: 4 columns × 2 rows (`repeat(4, minmax(0,1fr))`; auto-fit `minmax(180px,1fr)` when narrow), hairline grid, each cell `#0a0a0a`, 20px padding. Cells: Sales scored `1,284`; Auto-submitted `1,019 / 79.4%` (pass); Held `168 / 13.1%` (fail); QA review `97 / 7.5%` (review); Critical fail rate `13.1%`; Low-confidence checks `2.1%`; Repeat offences `6 agents` (fail); Sampled clean calls `51 / 5%` (accent). Each cell: uppercase mono label, big mono value + small unit, 12px muted subline.
- **Decision distribution** card: a 10px stacked bar (79.4 / 13.1 / 7.5), then three rows (dot, label, count, percent), then the gate rule in 12px muted copy.
- **Which check is failing** card: five horizontal bars, width proportional to the top value (62), top two in `fail`, rest in `rgba(255,255,255,0.35)`; label + "N fails · Type" above each.
- **Recent critical failures**: four clickable rows (lead id, `✕ check name` in fail, meta, age) → opens that lead's workspace.
- **Recent human overrides**: lead id, `AI <decision>` in fail → `Human <decision>` in pass, reason, reviewer · time.

### 2. QA Queue — "Work queue"

Filter chips: `All`, `Critical holds`, `Low confidence`, `Repeat offences`, `Human overrides`, `Sampled clean` — each with a live count; selected chip gets `accent` border + `#121212` fill. Table columns `150px 1.1fr 1.4fr 110px 80px 150px`: Lead (with a `×3` outlined badge for repeat offenders), Retailer · agent, Reason, Confidence (the **deciding** check's confidence — failing criticals, else low-confidence checks, else the weakest critical; `—` when the lead was never scored), Age (relative: `42m`, `2h`, `1d`), Decision chip. Rows are buttons; min-width 900px with horizontal scroll inside the card.

### 3. Sales — Decision workspace (the centerpiece)

Two columns: a 248px sticky scenario list and the workspace. Scenario rows: status dot, lead id, `LEAD A…I` tag, one-line description; selected row gets `#121212` + 2px accent left border.

**Decision header** — `#0a0a0a`, 3px left border in the decision color:
- `GATE DECISION` chip with a dot in the decision color
- The decision itself in mono at up to 52px (`AUTO-SUBMIT` / `HOLD` / `QA REVIEW`)
- One-sentence reason, then the gate rule that produced it in mono muted
- A 2×2 hairline stat grid: Checks run, Critical, Critical fails, Low conf.
- A meta row (Lead, Retailer · product, Agent, Team lead, Call date · duration, Checklist version)

**Override banner** (only when a human already decided): accent left border, `AI decision` vs `Human decision` side by side, the reason, reviewer · time, and the line "both decisions retained in the ledger".

**Critical findings**: auto-fit cards, `minmax(320px,1fr)`, each with a 2px top border (fail / review / muted). Card contents in order: severity banner + timestamp; check name; `Type · CRITICAL|NON-CRITICAL`; a two-cell hairline grid `OBSERVED (transcript)` in fail vs `EXPECTED (source)` in pass, with the source named; the verbatim evidence quote behind a 2px left border; `CONF nn%` and rule-version chips; `▶ Play evidence · mm:ss` (primary) and `Inspect evidence` (secondary). Empty state when there are none: centered `✓`, "No critical findings", and a note that the sale stays eligible for the 5% sample.

**Call timeline**: a 34px band containing a 6px track, a dead-air region as a translucent block, and one square marker per timestamped check positioned by `left: (seconds / duration) × 100%` — 12px for fails/reviews, 8px for passes, colored by status, each a button with an aria-label. Under it: `00:00` / duration, a legend, then the speaker-separated transcript (max-height 300px, scroll): time, speaker (agent = accent, customer = muted, system = dim), text colored by kind (fail = red, review = amber, note = muted). Clicking a marker opens that check's evidence and selects the turn; clicking a turn selects it.

**Full checklist**: tabs `All / Verbatim / Factual / Behaviour` with counts. Columns `104px 1.4fr 96px 118px 100px 70px 116px`: Status (`✓ PASS` / `✕ FAIL` / `⚠ REVIEW`), Check, Type, Criticality, Confidence, Time, Evidence link. Rows open the inspector; the row matching the open inspector stays highlighted.

**Human review** (left) and **Decision lineage** (right):
- Review: AI decision restated, two choice buttons (`Agree with AI`, `Override → PASS|HOLD`), a required reason textarea, and a Confirm button that stays disabled until a choice and >3 characters of reason exist. On confirm, an accent-bordered "Audit event written" block appears listing AI decision, human decision, reviewer, reason, time.
- Lineage: time, rail marker, event label, actor · version — last event colored by resulting state, plus a `Full ledger` button.

### 4. Evidence inspector (drawer)

Right-side dialog, `min(460px, 100%)`, `#0a0a0a`, 1px left ring, `qaslide` in, scrim `rgba(0,0,0,0.72)` that closes on click; `role="dialog" aria-modal="true"`.

Contents in fixed order: kicker, check name, three chips (status / type / criticality), then a stacked hairline grid of **Observed — what the transcript contains**, **Expected — authoritative source** (with the source named beneath), **Evaluation — what the system determined**; then the transcript evidence quote behind a 2px accent border with its timestamp; then Confidence (value + bar) and Rule version (`RET1-FM-008 · v1.4`, "live on call date") side by side; then `▶ Play audio · mm:ss` and `Mark reviewed`. Playing shows a pulsing dot and "Playing 20s from mm:ss — card numbers redacted in this stream". Footer line: the system reports what failed and where; it does not rewrite the sale, correct the agent, or contact the customer.

### 5. Rules — check library

Left: retailer → checklist → version cards (`Retailer 1 · Energy QA checklist · v1.4 · eff. 2026-09-01`, plus a superseded v1.3, Retailer 2 v2.1, Retailer 3 Broadband v1.0). Live versions get a pass-colored chip, superseded a muted one. Right: the 20 checks with Type, Critical, Weight, Source of truth. Footer note: every score resolves to the version live on the call date.

### 6. Calibration

`Synthetic calibration data` chip, then four KPIs (AI/auditor agreement `94.2%`, critical false-pass `0`, critical false-fail `3`, auditor-to-auditor `91.6%`), a confidence-distribution histogram where buckets below 0.85 are amber, and a disagreement-category bar list. Copy states critical false-pass is the release-blocking metric.

### 7. Audit — decision ledger

Columns `110px 1.1fr 1.3fr 150px 140px`: Timestamp, Event, Actor / system, Version, Resulting state (colored). Append-only; overrides add an event rather than rewriting the decision.

### 8. Non-happy states

- **Processing**: spinner + `PROCESSING` kicker, "Scoring <lead>", pipeline list with per-step dots (done = pass, running = pulsing accent, queued = dim) and states (`complete` / `14 of 20` / `pending`).
- **Ingest error**: fail-colored card border, `PROCESSING FAILED` chip, explanation that nothing was scored and the sale is held rather than passed, two recovery actions (`Re-request recording`, `Route to manual QA`), and an error code line.
- **Empty findings**: as described in the workspace section.

---

## Interactions & behavior

- Nav switches views; all state (selected lead, tab, filters) survives view changes.
- Dashboard failure rows and queue rows open the lead workspace.
- Finding cards, checklist rows and timeline markers all open the same inspector; `Play evidence` opens it with playback active.
- Drawer closes on scrim click, `×`, or `Mark reviewed`.
- Override is a two-step commit (choice + reason) and appends an event; it never mutates the AI decision.
- Filters (retailer, range, queue chips, checklist tabs) recompute counts live.
- Responsive: below 1040px the rail becomes a horizontal bar and the workspace/rules become single-column; wide tables scroll horizontally inside their card rather than breaking.

## Accessibility

`aria-current` on nav and list selection, `aria-pressed` on filter chips and override choices, `aria-label` on timeline markers and the drawer close, `role="dialog" aria-modal` on the inspector, visible focus ring (`2px solid #52a8ff`, 2px offset), status never encoded in color alone, minimum body text 12px mono / 13px Inter.

## State (prototype → production)

Prototype component state: `view`, `leadId`, `tab`, `drawerKey`, `playing`, `seg`, `queueFilter`, `retailer`, `range`, `ruleSet`, `choice`, `reason`, `saved`, `narrow`.

In Next.js most of this becomes URL state (`/sales/[leadId]?check=…&tab=…`) with only transient form state local. See `NEXTJS_BUILD_PLAN.md`.

## Data model

The prototype already separates the entities the backend will own: `Lead`, `Recording`, `Transcript`, `Check`, `CheckResult`, `Evidence`, `RuleVersion`, `Decision`, `AuditEvent`, `HumanReview`, `CalibrationMetric`. Typed definitions and API contracts are in `NEXTJS_BUILD_PLAN.md`.

## Mock data

Nine scenario leads (A–I): clean auto-submit; rate + email mismatch hold (the brief's worked example, lead `3613790`); address mismatch hold; low-confidence QA review from crosstalk; behaviour-note-only auto-submit; human override with audit trail; repeat critical failure ×3; processing; ingest error. A 20-check Retailer 1 energy checklist with per-lead result patches. All synthetic — no real PII, no real CIMET statistics.

## Assets

None. No images, no icon library: the only graphics are two inline SVGs (the square logo mark and the diagonal arrow) and CSS-drawn bars, dots and markers. Fonts load from Google Fonts (Inter, Geist Mono).

## Files in this bundle

| File | What it is |
|---|---|
| `CIMET AI QA Gate.dc.html` | The interactive prototype — open in a browser; all 6 views and 9 scenarios work |
| `CIMET-QA-Gate-Walkthrough.html` | 19-page landscape walkthrough document (screenshots + annotations), printable to PDF |
| `NEXTJS_BUILD_PLAN.md` | Target architecture, route map, component map, data contracts, backend phases |
| `CLAUDE.md` | Drop into the new repo root — rules Claude Code should follow while building |
| `GETTING_STARTED.md` | Step-by-step: repo, Claude Code access, prompts, first push |
