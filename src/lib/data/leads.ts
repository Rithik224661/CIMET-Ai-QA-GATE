import { apiGet, ApiError } from "../api/client";
import type { GateOutcome } from "../gate";
import type { Lead } from "../types";

/**
 * Repository layer — Phase 2 now reads the FastAPI backend (`BACKEND_URL`)
 * instead of the fixture bundle. Every exported function keeps its Phase 1
 * name/signature/return shape so components under src/components/ and
 * src/app/ are untouched. See design_handoff/NEXTJS_BUILD_PLAN.md §7.
 */
export async function getLeads(): Promise<Lead[]> {
  const { leads } = await apiGet<{ leads: Lead[] }>("/api/leads");
  return leads;
}

export async function getLead(id: string): Promise<Lead | undefined> {
  try {
    return await apiGet<Lead>(`/api/leads/${id}`);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return undefined;
    throw err;
  }
}

/**
 * Gate outcome is only meaningful once a lead has been scored. The backend
 * now computes and persists the decision (including `reason`/`ruleApplied`
 * copy) alongside the lead, so this just surfaces what's already there —
 * it no longer calls evaluateGate() itself (see CLAUDE.md #6: the gate is
 * deterministic and lives server-side now, not re-derived in the UI).
 */
export function gateForLead(lead: Lead): GateOutcome | null {
  if (lead.state !== "scored" || !lead.decision) return null;
  return lead.decision;
}
