# Getting started — from this design to a Next.js repo with Claude Code

You do not convert the HTML file. You hand the design bundle to Claude Code and have it **build a Next.js app that matches it**, phase by phase. The prototype stays in the repo as the visual reference.

---

## Step 1 — Create the repo

```bash
mkdir cimet-qa-gate && cd cimet-qa-gate
git init
npx create-next-app@latest . --ts --app --tailwind --eslint --src-dir --use-pnpm
```

Create it on GitHub (private) and connect:

```bash
gh repo create cimet-qa-gate --private --source=. --remote=origin
# or: git remote add origin git@github.com:<you>/cimet-qa-gate.git
git add -A && git commit -m "chore: scaffold next.js app"
git push -u origin main
```

## Step 2 — Drop the design bundle in

Unzip this handoff into the repo:

```
cimet-qa-gate/
├─ design_handoff/
│  ├─ README.md                        ← design spec (tokens, screens, components)
│  ├─ NEXTJS_BUILD_PLAN.md             ← architecture, routes, types, API, phases
│  ├─ CIMET AI QA Gate.dc.html         ← the interactive prototype (open in a browser)
│  └─ CIMET-QA-Gate-Walkthrough.html   ← 19-page annotated walkthrough
├─ CLAUDE.md                           ← move the bundle's CLAUDE.md to the repo ROOT
└─ …
```

`CLAUDE.md` must sit at the repo root — Claude Code reads it automatically on every session.

```bash
git add -A && git commit -m "docs: add design handoff and project rules" && git push
```

## Step 3 — Give Claude Code access

```bash
npm install -g @anthropic-ai/claude-code   # once
cd cimet-qa-gate
claude
```

Claude Code works inside the directory you launch it in — that is the access. It reads `CLAUDE.md` and anything you point it at. For GitHub work:

- `gh auth login` once, so Claude Code can create branches and open PRs through the `gh` CLI.
- Optionally `/install-github-app` inside Claude Code to get PR reviews and `@claude` mentions on issues.
- Keep secrets in `.env.local` (git-ignored). Never paste live credentials into a prompt.

## Step 4 — First session prompt (Phase 1: UI on fixtures)

> Read `CLAUDE.md`, `design_handoff/README.md` and `design_handoff/NEXTJS_BUILD_PLAN.md`. Open `design_handoff/CIMET AI QA Gate.dc.html` in a browser to see the working prototype — it is the visual source of truth.
>
> Build **Phase 1** only: the full UI on typed fixtures, no backend.
>
> 1. Put the design tokens in `tailwind.config.ts` and load Inter + Geist Mono.
> 2. Port the prototype's nine scenario leads and 20-check library into typed fixtures under `src/lib/fixtures/`, using the domain types in the build plan.
> 3. Build the app shell (rail, top bar) and the six views, plus the evidence drawer and the processing / ingest-error / empty states.
> 4. URL-driven state as specified; server components except where the plan says client.
> 5. Pixel-close to the prototype: zero-radius buttons, 100px chips, Geist Mono for all data, the exact palette, glyph + word for status.
>
> Work on a branch `feat/phase-1-ui`, commit per view, run typecheck and lint before each commit, and open a PR when the six views render.

Then review the PR against the walkthrough document page by page.

## Step 5 — Subsequent sessions

One phase per session, each its own branch and PR:

| Session | Prompt in one line |
|---|---|
| 2 | "Phase 2: Prisma schema + Postgres, seed the fixtures, swap fixture imports for queries. UI must not change." |
| 3 | "Phase 3: route handlers from the API surface + Zod + Auth.js roles; make the override a server action writing HumanReview and AuditEvent." |
| 4 | "Phase 4: dialler webhook, S3 storage, ASR with diarisation and word timestamps, normalisation, retries." |
| 5 | "Phase 5: the three check engines, per-check confidence, deterministic gate, unit tests for every gate branch." |
| 6 | "Phase 6: 5% sampling job and calibration metrics computed from real reviews." |
| 7 | "Phase 7: redaction, retention, audit export, Playwright demo flow in CI." |

Useful habits: ask for a **plan first** on anything non-trivial; keep each PR to one phase; make Claude Code run `pnpm typecheck && pnpm lint && pnpm test` before it commits; have it append every assumption to `docs/DECISIONS.md`.

## Step 6 — Keep the design in sync

If the design changes later, a new version of the prototype and walkthrough drops into `design_handoff/`, and the prompt is "diff the new prototype against the current UI and update only what changed".

---

### What not to do

- Do not paste the `.dc.html` into the app or try to convert it mechanically — its inline-style, single-file form is a prototype constraint, not the product's architecture.
- Do not let the rebuild "modernise" the visual design; it is approved.
- Do not put real recordings, transcripts or customer data in the repo.
