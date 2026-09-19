import { formatConfidence } from "./status";
import type { AuditEvent, Lead } from "./types";
import { decisionLabel } from "./status";
import type { GateOutcome } from "./gate";

/**
 * Builds the append-only decision lineage for a lead from what is actually
 * known about it — never a hand-authored string per lead. A human override
 * is a real row here (CLAUDE.md #7: it appends, it never replaces the AI
 * decision above it).
 *
 * Phase 1 (fixtures, no persistence layer) stops at what the pipeline and
 * any *existing* fixture override produced; a review submitted from the
 * Human review form in this session is shown as its own confirmation panel
 * but does not yet append here — Phase 3 wires the override to a server
 * action that writes the AuditEvent for real. See docs/DECISIONS.md.
 */
export function buildLineage(lead: Lead, gate: GateOutcome | null): AuditEvent[] {
  const events: AuditEvent[] = [{ time: "09:02:14", event: "Lead created", actor: "CRM", version: null, resultingState: "OPEN" }];

  if (lead.state === "error" && lead.ingestError) {
    events.push({
      time: lead.ingestError.at,
      event: "Recording ingest failed",
      actor: "Dialler API · lead-keyed",
      version: "ingest v2",
      resultingState: lead.ingestError.code,
    });
    return events;
  }

  events.push(
    { time: "14:32:06", event: "Recording received", actor: "Dialler API · lead-keyed", version: "ingest v2", resultingState: "MEDIA_OK" },
    { time: "14:32:51", event: "Transcript generated", actor: "ASR · speaker-separated", version: "asr v3.2", resultingState: "TRANSCRIPT_OK" },
    { time: "14:33:02", event: "Transcript normalised", actor: "Pipeline", version: "norm v1.1", resultingState: "NORMALISED" },
    { time: "14:33:03", event: "Rule set loaded", actor: "Check library", version: `${lead.retailer} ${lead.checklistVersion}`, resultingState: "RULES_PINNED" },
  );

  if (lead.state === "processing") {
    events.push({ time: "14:33:07", event: "Checks executing", actor: "Scoring engine", version: "engine v0.9", resultingState: "14 of 20" });
    return events;
  }

  if (lead.state === "scored" && gate) {
    const minConfidence = lead.results.length ? Math.min(...lead.results.map((r) => r.confidence)) : null;
    events.push(
      { time: "14:33:09", event: "Checks executed", actor: "Scoring engine", version: "engine v0.9", resultingState: `${gate.checksRun} RESULTS` },
      { time: "14:33:09", event: "Evidence captured", actor: "Scoring engine", version: null, resultingState: "EVIDENCE_OK" },
      {
        time: "14:33:10",
        event: "Confidence evaluated",
        actor: "Scoring engine",
        version: null,
        resultingState: minConfidence != null ? `MIN ${formatConfidence(minConfidence)}` : "—",
      },
      { time: "14:33:10", event: "Gate decision", actor: "Gate", version: "gate v1.0", resultingState: decisionLabel(gate.decision) },
    );
  }

  if (lead.override) {
    events.push({
      time: lead.override.at.slice(-5) + ":40",
      event: "Human override",
      actor: `${lead.override.reviewerRole} · ${lead.override.reviewerName}`,
      version: null,
      resultingState: lead.override.humanDecision,
    });
  }

  return events;
}

/** Tone for the *final* ledger row only — every earlier row is neutral ink
 * regardless of its resultingState (it's a pipeline step, not a verdict). */
export function auditStateTone(state: string): "pass" | "fail" | "review" | "muted" {
  if (state === "HOLD" || state.includes("ERROR") || state.includes("FAILED")) return "fail";
  if (state === "AUTO-SUBMIT" || state === "PASS") return "pass";
  if (state === "QA REVIEW") return "review";
  return "muted";
}
