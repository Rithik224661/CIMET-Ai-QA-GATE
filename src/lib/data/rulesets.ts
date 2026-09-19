import { retailer1CheckDefinitions } from "../fixtures/checks";
import { RULE_SETS } from "../fixtures/rulesets";
import type { CheckDefinition, RuleSetVersion } from "../types";

/** GET /api/rulesets */
export async function getRuleSets(): Promise<RuleSetVersion[]> {
  return RULE_SETS;
}

/**
 * GET /api/rulesets/[versionId]/checks — every rule set version currently
 * resolves to the one checklist export provided with the brief (Retailer 1
 * energy, v1.4); see docs/DECISIONS.md.
 */
export async function getChecksForRuleSet(ruleSet: RuleSetVersion): Promise<CheckDefinition[]> {
  void ruleSet;
  return retailer1CheckDefinitions();
}
