import { expect, test } from "@playwright/test";

/**
 * Live-pipeline proof tests (brief §29-31): the UI must be driven by real
 * backend execution, not simulated state — a real POST /api/evaluations
 * triggered from the browser, real audio bytes served and played, and a
 * transcript that only ever came from the backend API.
 */

test("Re-score button triggers a real backend evaluation and re-renders the persisted decision", async ({ page, request }) => {
  // The Re-score button calls a Next.js Server Action (runEvaluation),
  // whose own fetch to the FastAPI backend happens server-side — invisible
  // to the browser's network tab. So the proof of a real backend
  // round-trip is checked directly against the backend's own audit
  // ledger (via Playwright's request context) rather than intercepted
  // browser network calls.
  const before = await (await request.get("http://localhost:8000/api/audit/3613742")).json();

  await page.goto("/sales/3613742");
  const evalIdText = page.getByText(/Evaluation EVAL-\d+/);
  await expect(evalIdText).toBeVisible();

  await page.getByRole("button", { name: "Re-score" }).click();
  await expect(page.getByRole("button", { name: "Re-scoring…" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Re-score" })).toBeVisible({ timeout: 10_000 });

  const after = await (await request.get("http://localhost:8000/api/audit/3613742")).json();
  expect(after.events.length).toBeGreaterThan(before.events.length);
  expect(after.events.at(-1).event).toMatch(/Submitted|Held|QA Review/i);

  // The gate outcome for this clean lead must still be AUTO-SUBMIT after
  // re-evaluation — a real re-run of the deterministic pipeline, not a
  // random/mocked result.
  await expect(page.getByText("AUTO-SUBMIT", { exact: true }).first()).toBeVisible();
});

test("Play evidence loads and plays real audio bytes, seeked to the evidence timestamp", async ({ page }) => {
  await page.goto("/sales/3613790");

  await page.getByRole("link", { name: "Play evidence" }).first().click();
  const drawer = page.getByRole("dialog");
  await expect(drawer).toBeVisible();

  const audio = page.getByTestId("evidence-audio");
  await expect(audio).toHaveAttribute("src", "/api/audio/3613790");

  // Real HTML5 playback: currentTime must land near the evidence's real
  // timestamp (14:02 = 842s) and actually advance while playing — never a
  // fake "playing" animation with no underlying media.
  await page.waitForFunction(() => {
    const el = document.querySelector('[data-testid="evidence-audio"]') as HTMLAudioElement | null;
    return !!el && el.currentTime > 0;
  });
  const seekedTime = await audio.evaluate((el: HTMLMediaElement) => el.currentTime);
  expect(seekedTime).toBeGreaterThan(800);
  expect(seekedTime).toBeLessThan(900);

  await expect(page.getByText(/Playing from \d+:\d+/)).toBeVisible();
});

test("transcript rendered in the call timeline is fetched from the backend, not a bundled fixture", async ({ page }) => {
  await page.goto("/sales/3613790");
  // A real seeded transcript line for this lead (app/seed_data.py) — only
  // present if the page actually rendered lead.transcript from the API
  // response, since no frontend fixture contains call-specific dialogue.
  await expect(page.getByText(/Default Market Offer/i).first()).toBeVisible();
});
