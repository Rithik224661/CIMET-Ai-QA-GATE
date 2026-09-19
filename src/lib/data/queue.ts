import { apiGet } from "../api/client";
import { gateForLead } from "./leads";
import { relativeAge } from "../format";
import { decisionLabel } from "../status";
import type { Decision, Lead } from "../types";

export const QUEUE_FILTERS = [
  "All",
  "Critical holds",
  "Low confidence",
  "Repeat offences",
  "Human overrides",
  "Sampled clean",
] as const;

export type QueueFilter = (typeof QUEUE_FILTERS)[number];
export const DEFAULT_QUEUE_FILTER: QueueFilter = "All";
export const ALL_RETAILERS = "All retailers" as const;

export interface QueueRow {
  lead: Lead;
  reason: string;
  decidingConfidence: number | null;
  age: string;
  displayDecision: string;
  decision: Decision | "ERROR";
}

/**
 * Client-side re-derivation of the "which filter bucket does this lead fall
 * into" predicate, used only to compute all 6 filter counts from a single
 * unfiltered-by-filter payload (see getQueueCounts below). The backend now
 * owns this matching for the actual queue listing (getQueueRows passes
 * `filter`/`retailer` through as query params) — this copy mirrors that
 * same logic so counts don't require 6 round trips.
 */
function matchesFilter(lead: Lead, filter: QueueFilter): boolean {
  if (filter === "All") return lead.state === "scored" || lead.state === "error";
  if (lead.state !== "scored") return false;
  const gate = gateForLead(lead);
  if (!gate) return false;
  if (filter === "Critical holds") return gate.decision === "HOLD" && !lead.override;
  if (filter === "Low confidence") return gate.decision === "QA_REVIEW";
  if (filter === "Repeat offences") return lead.repeatOffence;
  if (filter === "Human overrides") return !!lead.override;
  return gate.decision === "AUTO_SUBMIT"; // Sampled clean
}

function reasonFor(lead: Lead): string {
  if (lead.state === "error") return "Ingest error — no transcript";
  const gate = gateForLead(lead);
  if (!gate) return "—";
  const criticalFails = lead.results.filter((r) => r.critical && r.status === "FAIL");
  if (criticalFails.length) return criticalFails.map((r) => r.name).join(", ");
  const reviews = lead.results.filter((r) => r.status === "REVIEW");
  if (reviews.length) return `Low confidence · ${reviews[0].name}`;
  if (lead.override) return "Override recorded";
  return "Sampled clean call";
}

function decidingConfidenceFor(lead: Lead): number | null {
  if (lead.state !== "scored") return null;
  const criticalFails = lead.results.filter((r) => r.critical && r.status === "FAIL");
  const reviews = lead.results.filter((r) => r.status === "REVIEW");
  const deciding = criticalFails.length ? criticalFails : reviews.length ? reviews : lead.results.filter((r) => r.critical);
  if (!deciding.length) return null;
  return Math.min(...deciding.map((r) => r.confidence));
}

async function fetchLeads(opts: { retailer?: string; filter?: string }): Promise<Lead[]> {
  const { leads } = await apiGet<{ leads: Lead[] }>("/api/leads", {
    retailer: opts.retailer,
    filter: opts.filter,
  });
  return leads;
}

export async function getQueueRows(opts: { retailer: string; filter: QueueFilter; now: Date }): Promise<QueueRow[]> {
  const leads = await fetchLeads({ retailer: opts.retailer, filter: opts.filter });
  return leads.map((lead) => {
    const gate = gateForLead(lead);
    const decision: Decision | "ERROR" = lead.state === "error" ? "ERROR" : gate ? gate.decision : "AUTO_SUBMIT";
    return {
      lead,
      reason: reasonFor(lead),
      decidingConfidence: decidingConfidenceFor(lead),
      age: relativeAge(lead.callDate, opts.now),
      displayDecision: lead.state === "error" ? "ERROR" : decisionLabel(gate!.decision),
      decision,
    };
  });
}

export async function getQueueCounts(retailer: string): Promise<Record<QueueFilter, number>> {
  const leads = await fetchLeads({ retailer });
  const counts = {} as Record<QueueFilter, number>;
  for (const filter of QUEUE_FILTERS) {
    counts[filter] = leads.filter((l) => matchesFilter(l, filter)).length;
  }
  return counts;
}

export async function getQueueBadgeCount(retailer: string): Promise<number> {
  const leads = await fetchLeads({ retailer });
  return leads.filter((l) => l.state === "scored" || l.state === "error").length;
}
