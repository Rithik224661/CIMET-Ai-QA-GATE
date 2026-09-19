import { apiGet } from "../api/client";
import type { CheckDefinition, RuleSetVersion } from "../types";

/** GET /api/rules — returned in a stable order the backend guarantees, so
 * the existing index-based `?set=` URL param selection keeps working. */
export async function getRuleSets(): Promise<RuleSetVersion[]> {
  const { ruleSets } = await apiGet<{ ruleSets: RuleSetVersion[] }>("/api/rules");
  return ruleSets;
}

/**
 * GET /api/checks — every rule set version currently resolves to the one
 * checklist shared across the app (documented simplification, see
 * docs/DECISIONS.md); the ruleSet param is intentionally unused.
 */
export async function getChecksForRuleSet(ruleSet: RuleSetVersion): Promise<CheckDefinition[]> {
  void ruleSet;
  const { checks } = await apiGet<{ checks: CheckDefinition[] }>("/api/checks");
  return checks;
}
