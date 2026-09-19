# CLAUDE.md — VerityGate (CIMET AI QA Gate hackathon submission)

Project rules for Claude Code. See `README.md` (product/architecture overview), `docs/ARCHITECTURE.md`, `docs/DEMO.md`, and `docs/INTEGRATION.md` before writing code. The original design-handoff source files (HTML prototype, build plan) have been removed from the repository — the design they described has been fully implemented; see git history if the source is ever needed.

## What this is

A production Next.js rebuild of an approved, high-fidelity frontend design for an AI quality gate that scores sales calls against retailer checklists before the sale can submit in CRM.

## Non-negotiables

1. **The design is approved and final.** Recreate it pixel-close. Do not restyle, re-space, re-color, add gradients/shadows/rounded cards, or "improve" the layout. If something looks wrong, ask before changing.
2. `border-radius: 0` on every button. `border-radius: 100px` on every status chip.
3. Every ID, metric, data value, table row, timestamp, status word and code is set in **Geist Mono**. Headings and prose in **Inter**.
4. Only the palette in the design spec. No new colors.
5. Status is always a glyph **and** a word. Never color alone.
6. The gate logic (`criticalFails > 0 → HOLD`, `anyConfidence < floor → QA_REVIEW`, else `AUTO_SUBMIT`) is deterministic, pure, unit-tested, and never produced by a model.
7. A human override **appends** a record. It never mutates or hides the AI decision.
8. Every check result must carry: transcript quote, audio timestamp, rule version live on the call date, and a confidence value.
9. Synthetic data only. No real customer PII in any dev, demo or test environment. Redact card numbers before storage and before playback.
10. The system reports what failed and where. It does not rewrite the sale, correct the agent, or contact the customer.

## Conventions

- TypeScript strict; no `any`. Zod at every boundary.
- Server components by default; `"use client"` only for the evidence drawer, filters, timeline selection, override form, responsive rail.
- View state lives in the URL (`?filter=`, `?check=`, `?tab=`, `?t=`); only form and playback state is local.
- One source of truth for status → color/glyph mapping (`lib/status.ts`). No scattered ternaries.
- Tailwind tokens from `tailwind.config.ts`; no arbitrary hex values in components.
- Append-only tables: `CheckResult`, `GateDecision`, `HumanReview`, `AuditEvent`. Never `UPDATE`, never `DELETE`.
- Tests: Vitest for comparators and gate logic (exhaustive), Playwright for the demo flow (open lead → see HOLD → open evidence → override → see audit event).

## Workflow

- Work in phases from the build plan; one phase per branch, conventional commits.
- Run `pnpm typecheck && pnpm lint && pnpm test` before every commit.
- Keep `docs/DECISIONS.md` updated when an assumption is made — the brief left tolerances, weights and the confidence floor unspecified, and those choices must be visible.
- Never commit `.env`, recordings, transcripts, or any real customer data.
