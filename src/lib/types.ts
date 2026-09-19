/**
 * Domain types — see design_handoff/NEXTJS_BUILD_PLAN.md §4.
 * These are the entities the backend will own; the fixture layer under
 * lib/fixtures/ populates them for Phase 1 (UI on fixtures).
 */

import type { GateOutcome } from "./gate";

export type Decision = "AUTO_SUBMIT" | "HOLD" | "QA_REVIEW";
export type CheckType = "Verbatim" | "Factual" | "Behaviour";
export type ResultStatus = "PASS" | "FAIL" | "REVIEW";
export type LeadState = "scored" | "processing" | "error";
export type Speaker = "AGENT" | "CUSTOMER" | "SYSTEM";

export interface CheckDefinition {
  code: string;
  name: string;
  type: CheckType;
  critical: boolean;
  weight: number;
  sourceOfTruth: string;
}

export interface CheckResult {
  checkCode: string;
  name: string;
  type: CheckType;
  critical: boolean;
  status: ResultStatus;
  confidence: number;
  timestamp: string | null;
  ruleVersion: string;
  sourceOfTruth: string;
  observed: string | null;
  expected: string | null;
  evidenceQuote: string | null;
  rationale: string | null;
}

export interface HumanOverride {
  aiDecision: Decision;
  humanDecision: "PASS" | "HOLD";
  reason: string;
  reviewerRole: string;
  reviewerName: string;
  at: string;
}

export interface TranscriptTurn {
  timestamp: string;
  speaker: Speaker;
  text: string;
  kind: "pass" | "fail" | "review" | "note";
}

export interface Lead {
  id: string;
  scenarioTag: string;
  scenarioSummary: string;
  retailer: "Retailer 1" | "Retailer 2" | "Retailer 3";
  product: "Energy" | "Broadband";
  agent: string;
  teamLead: string;
  callDate: string;
  durationSec: number;
  checklistVersion: string;
  state: LeadState;
  repeatOffence: boolean;
  results: CheckResult[];
  transcript: TranscriptTurn[];
  override: HumanOverride | null;
  ingestError: {
    code: string;
    message: string;
    retry: string;
    at: string;
  } | null;
  /** Backend-computed gate outcome (GateOutcomeDTO), including the
   * persisted `reason`/`ruleApplied` copy. Null/absent while `state` is
   * "processing" or "error" — never present on those states. */
  decision?: GateOutcome | null;
}

export interface GateDecision {
  leadId: string;
  decision: Decision;
  reason: string;
  ruleApplied: string;
  criticalFails: number;
  lowConfidence: number;
  checksRun: number;
  criticalChecks: number;
  decidedAt: string;
}

export interface AuditEvent {
  time: string;
  event: string;
  actor: string;
  version: string | null;
  resultingState: string;
}

export interface RuleSetVersion {
  retailer: string;
  checklist: string;
  version: string;
  effectiveFrom: string;
  live: boolean;
}

export interface DashboardKpi {
  label: string;
  value: string;
  unit: string;
  sub: string;
  tone: "default" | "pass" | "fail" | "review" | "accent";
}

export interface CalibrationKpi {
  label: string;
  value: string;
  unit: string;
  sub: string;
  tone: "default" | "pass" | "review";
}
