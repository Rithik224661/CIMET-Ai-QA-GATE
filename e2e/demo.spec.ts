import { expect, test } from "@playwright/test";

/**
 * The hackathon/demo flow from CLAUDE.md: open lead → see HOLD → open
 * evidence → override → see audit event. Exercises the worked example from
 * the brief (lead 3613790: rate + email mismatch).
 */
test("open lead, see HOLD, inspect evidence, override, see audit event", async ({ page }) => {
  await page.goto("/queue");
  await page.getByRole("link", { name: /3613790/ }).click();

  await expect(page).toHaveURL(/\/sales\/3613790/);
  await expect(page.getByText("HOLD", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("2 critical checks failed.")).toBeVisible();

  await page.getByRole("link", { name: "Inspect evidence" }).first().click();
  const drawer = page.getByRole("dialog");
  await expect(drawer).toBeVisible();
  await expect(drawer.getByText("Evidence inspector")).toBeVisible();
  await expect(drawer.getByRole("heading", { name: "Rates and charges" })).toBeVisible();
  await expect(drawer.getByText("28.6c / kWh peak")).toBeVisible();
  await expect(drawer.getByText("31.9c / kWh peak")).toBeVisible();
  await drawer.getByRole("button", { name: "Close" }).click();
  await expect(drawer).not.toBeVisible();

  await page.getByRole("button", { name: /Override → PASS/ }).click();
  await page.getByPlaceholder(/Customer corrected the rate/).fill("Customer corrected the rate on a follow-up call.");
  await page.getByRole("button", { name: "Confirm decision" }).click();

  await expect(page.getByText("Audit event written")).toBeVisible();
  await expect(page.getByText(/Human: PASS/)).toBeVisible();
});
