import type { RuleSetVersion } from "../types";

/**
 * Retailer → checklist → version. The brief provided one retailer's full
 * checklist export (Retailer 1 energy, v1.4); the other rows are shown for
 * navigation fidelity but resolve to the same 20-check catalogue in this
 * fixture phase — see docs/DECISIONS.md.
 */
export const RULE_SETS: RuleSetVersion[] = [
  { retailer: "Retailer 1", checklist: "Energy QA checklist", version: "v1.4", effectiveFrom: "2026-09-01", live: true },
  { retailer: "Retailer 1", checklist: "Energy QA checklist", version: "v1.3", effectiveFrom: "2026-06-15", live: false },
  { retailer: "Retailer 2", checklist: "Energy QA checklist", version: "v2.1", effectiveFrom: "2026-08-12", live: true },
  { retailer: "Retailer 3", checklist: "Broadband QA checklist", version: "v1.0", effectiveFrom: "2026-07-01", live: true },
];
