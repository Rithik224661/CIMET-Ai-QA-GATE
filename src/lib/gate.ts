import { CONFIDENCE_FLOOR } from "./config";
import type { CheckResult, Decision } from "./types";

export interface GateInput {
  critical: boolean;
  status: CheckResult["status"];
  confidence: number;
}

/**
 * `reason` and `ruleApplied` are required going forward: the live backend
 * always supplies them (persisted alongside the decision — see
 * GateOutcomeDTO in lib/data/leads.ts). evaluateGate() below still fills
 * them in via describeDecision()/gateRuleCopy() for the pure/unit-tested
 * path (lib/gate.test.ts), but the live data path now just displays what
 * the backend already computed rather than regenerating this copy.
 */
export interface GateOutcome {
  decision: Decision;
  criticalFails: number;
  lowConfidence: number;
  checksRun: number;
  criticalChecks: number;
  nonCriticalFails: number;
  reason: string;
  ruleApplied: string;
}

/**
 * The gate: criticalFails > 0 → HOLD; anyConfidence < floor → QA_REVIEW;
 * else AUTO_SUBMIT. Pure and deterministic — never an LLM call. See
 * CLAUDE.md non-negotiable #6 and design_handoff/NEXTJS_BUILD_PLAN.md §6.4.
 */
export function evaluateGate(
  checks: readonly GateInput[],
  opts: { repeatOffence?: boolean; overridden?: boolean } = {},
): GateOutcome {
  const criticalFails = checks.filter((c) => c.critical && c.status === "FAIL").length;
  const lowConfidence = checks.filter((c) => c.confidence < CONFIDENCE_FLOOR).length;

  const decision: Decision =
    criticalFails > 0 ? "HOLD" : lowConfidence > 0 ? "QA_REVIEW" : "AUTO_SUBMIT";

  const outcome: GateOutcome = {
    decision,
    criticalFails,
    lowConfidence,
    checksRun: checks.length,
    criticalChecks: checks.filter((c) => c.critical).length,
    nonCriticalFails: checks.filter((c) => !c.critical && c.status === "FAIL").length,
    reason: "",
    ruleApplied: gateRuleCopy(decision),
  };
  outcome.reason = describeDecision(outcome, opts);
  return outcome;
}

/** Human-readable sentence for the decision header — generated from the
 * outcome, never hand-authored per lead, so copy can't drift from logic. */
export function describeDecision(
  outcome: GateOutcome,
  opts: { repeatOffence?: boolean; overridden?: boolean } = {},
): string {
  const { decision, criticalFails, criticalChecks, lowConfidence, nonCriticalFails } = outcome;

  if (decision === "HOLD") {
    const base = `${criticalFails} critical check${criticalFails === 1 ? "" : "s"} failed.`;
    if (opts.overridden) return `${base} Overturned by a human reviewer.`;
    if (opts.repeatOffence)
      return `${base} Third failure of this check in a rolling 7 days — TL flagged.`;
    return `${base} Sale held and routed to the TL queue.`;
  }

  if (decision === "QA_REVIEW") {
    return lowConfidence === 1
      ? "Insufficient confidence on a critical check. Never auto-passed."
      : `Insufficient confidence on ${lowConfidence} checks. Never auto-passed.`;
  }

  const base =
    criticalChecks > 0
      ? `All ${criticalChecks} critical checks passed.`
      : "All critical checks passed.";

  if (nonCriticalFails > 0) {
    return `${base} ${nonCriticalFails} non-critical behaviour note${nonCriticalFails === 1 ? "" : "s"} raised for coaching.`;
  }
  return `${base} No human touch required.`;
}

const GATE_RULES: Record<Decision, string> = {
  AUTO_SUBMIT: "Gate rule: all criticals pass → submit without human touch.",
  QA_REVIEW: "Gate rule: low confidence on any check → route to QA, never auto-pass.",
  HOLD: "Gate rule: any critical fail → hold, route to the TL queue.",
};

export function gateRuleCopy(decision: Decision): string {
  return GATE_RULES[decision];
}
