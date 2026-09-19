import { evaluateGate, type GateOutcome } from "../gate";
import { allLeads, findLead } from "../fixtures/leads";
import type { Lead } from "../types";

/**
 * Repository layer — Phase 1 reads fixtures; Phase 2 swaps these bodies for
 * Prisma queries without touching any component. See
 * design_handoff/NEXTJS_BUILD_PLAN.md §7.
 */
export async function getLeads(): Promise<Lead[]> {
  return allLeads();
}

export async function getLead(id: string): Promise<Lead | undefined> {
  return findLead(id);
}

/** Gate outcome is only meaningful once a lead has been scored. */
export function gateForLead(lead: Lead): GateOutcome | null {
  if (lead.state !== "scored") return null;
  return evaluateGate(lead.results);
}
