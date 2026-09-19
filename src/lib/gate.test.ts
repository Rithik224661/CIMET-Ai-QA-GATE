import { describe, expect, it } from "vitest";
import { CONFIDENCE_FLOOR } from "./config";
import { describeDecision, evaluateGate, gateRuleCopy, type GateInput } from "./gate";

function check(overrides: Partial<GateInput> = {}): GateInput {
  return { critical: true, status: "PASS", confidence: 0.99, ...overrides };
}

describe("evaluateGate", () => {
  it("AUTO_SUBMITs a clean call with no checks at all", () => {
    const outcome = evaluateGate([]);
    expect(outcome.decision).toBe("AUTO_SUBMIT");
    expect(outcome.checksRun).toBe(0);
    expect(outcome.criticalFails).toBe(0);
    expect(outcome.lowConfidence).toBe(0);
  });

  it("AUTO_SUBMITs when every check passes above the confidence floor", () => {
    const outcome = evaluateGate([
      check({ critical: true, status: "PASS", confidence: 0.99 }),
      check({ critical: false, status: "PASS", confidence: 0.86 }),
    ]);
    expect(outcome.decision).toBe("AUTO_SUBMIT");
  });

  it("HOLDs on a single critical FAIL", () => {
    const outcome = evaluateGate([check({ critical: true, status: "FAIL", confidence: 0.98 })]);
    expect(outcome.decision).toBe("HOLD");
    expect(outcome.criticalFails).toBe(1);
  });

  it("counts every critical FAIL, not just whether one exists", () => {
    const outcome = evaluateGate([
      check({ critical: true, status: "FAIL" }),
      check({ critical: true, status: "FAIL" }),
      check({ critical: true, status: "PASS" }),
    ]);
    expect(outcome.criticalFails).toBe(2);
    expect(outcome.decision).toBe("HOLD");
  });

  it("does not HOLD on a non-critical FAIL", () => {
    const outcome = evaluateGate([check({ critical: false, status: "FAIL", confidence: 0.95 })]);
    expect(outcome.decision).toBe("AUTO_SUBMIT");
    expect(outcome.criticalFails).toBe(0);
    expect(outcome.nonCriticalFails).toBe(1);
  });

  it("routes to QA_REVIEW when any check's confidence is below the floor, even if PASS/REVIEW not FAIL", () => {
    const outcome = evaluateGate([
      check({ critical: true, status: "REVIEW", confidence: 0.61 }),
      check({ critical: true, status: "PASS", confidence: 0.99 }),
    ]);
    expect(outcome.decision).toBe("QA_REVIEW");
    expect(outcome.lowConfidence).toBe(1);
  });

  it("a low-confidence NON-critical check also routes to QA_REVIEW (any check, not just criticals)", () => {
    const outcome = evaluateGate([check({ critical: false, status: "PASS", confidence: 0.5 })]);
    expect(outcome.decision).toBe("QA_REVIEW");
  });

  it("treats confidence exactly at the floor as NOT low (boundary is exclusive)", () => {
    const outcome = evaluateGate([check({ confidence: CONFIDENCE_FLOOR })]);
    expect(outcome.lowConfidence).toBe(0);
    expect(outcome.decision).toBe("AUTO_SUBMIT");
  });

  it("treats confidence one hundredth below the floor as low", () => {
    const outcome = evaluateGate([check({ confidence: CONFIDENCE_FLOOR - 0.01 })]);
    expect(outcome.lowConfidence).toBe(1);
    expect(outcome.decision).toBe("QA_REVIEW");
  });

  it("HOLD takes precedence over QA_REVIEW when both conditions are present", () => {
    const outcome = evaluateGate([
      check({ critical: true, status: "FAIL", confidence: 0.98 }),
      check({ critical: true, status: "PASS", confidence: 0.5 }),
    ]);
    expect(outcome.decision).toBe("HOLD");
  });

  it("counts criticalChecks independent of status", () => {
    const outcome = evaluateGate([
      check({ critical: true, status: "PASS" }),
      check({ critical: true, status: "FAIL" }),
      check({ critical: false, status: "PASS" }),
    ]);
    expect(outcome.criticalChecks).toBe(2);
    expect(outcome.checksRun).toBe(3);
  });
});

describe("describeDecision", () => {
  it("describes a plain HOLD", () => {
    const outcome = evaluateGate([check({ status: "FAIL" })]);
    expect(describeDecision(outcome)).toBe("1 critical check failed. Sale held and routed to the TL queue.");
  });

  it("pluralises multiple critical fails", () => {
    const outcome = evaluateGate([check({ status: "FAIL" }), check({ status: "FAIL" })]);
    expect(describeDecision(outcome)).toContain("2 critical checks failed.");
  });

  it("flags a repeat offence", () => {
    const outcome = evaluateGate([check({ status: "FAIL" })]);
    expect(describeDecision(outcome, { repeatOffence: true })).toContain("Third failure of this check in a rolling 7 days");
  });

  it("notes an overridden HOLD", () => {
    const outcome = evaluateGate([check({ status: "FAIL" })]);
    expect(describeDecision(outcome, { overridden: true })).toContain("Overturned by a human reviewer.");
  });

  it("describes QA_REVIEW for a single low-confidence check", () => {
    const outcome = evaluateGate([check({ confidence: 0.5 })]);
    expect(describeDecision(outcome)).toBe("Insufficient confidence on a critical check. Never auto-passed.");
  });

  it("describes QA_REVIEW for multiple low-confidence checks", () => {
    const outcome = evaluateGate([check({ confidence: 0.5 }), check({ confidence: 0.5, critical: false })]);
    expect(describeDecision(outcome)).toBe("Insufficient confidence on 2 checks. Never auto-passed.");
  });

  it("describes a clean AUTO_SUBMIT", () => {
    const outcome = evaluateGate([check(), check()]);
    expect(describeDecision(outcome)).toBe("All 2 critical checks passed. No human touch required.");
  });

  it("describes AUTO_SUBMIT with a non-critical coaching note", () => {
    const outcome = evaluateGate([check(), check({ critical: false, status: "FAIL", confidence: 0.92 })]);
    expect(describeDecision(outcome)).toBe("All 1 critical checks passed. 1 non-critical behaviour note raised for coaching.");
  });
});

describe("gateRuleCopy", () => {
  it("has copy for every decision", () => {
    expect(gateRuleCopy("AUTO_SUBMIT")).toMatch(/submit without human touch/);
    expect(gateRuleCopy("HOLD")).toMatch(/hold, route to the TL queue/);
    expect(gateRuleCopy("QA_REVIEW")).toMatch(/route to QA, never auto-pass/);
  });
});
