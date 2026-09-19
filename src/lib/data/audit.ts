import { buildLineage } from "../audit";
import { gateForLead, getLead } from "./leads";
import type { AuditEvent } from "../types";

/** GET /audit/[leadId] — the full, append-only decision ledger for a lead. */
export async function getLedger(leadId: string): Promise<AuditEvent[] | null> {
  const lead = await getLead(leadId);
  if (!lead) return null;
  return buildLineage(lead, gateForLead(lead));
}
