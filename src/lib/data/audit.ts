import { apiGet, ApiError } from "../api/client";
import type { AuditEvent } from "../types";

/** GET /audit/[leadId] — the full, append-only decision ledger for a lead. */
export async function getLedger(leadId: string): Promise<AuditEvent[] | null> {
  try {
    const { events } = await apiGet<{ events: AuditEvent[] }>(`/api/audit/${leadId}`);
    return events;
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  }
}
