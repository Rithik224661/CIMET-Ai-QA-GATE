import { describe, expect, it } from "vitest";
import { deriveFindings } from "./sale";
import type { CheckResult, Lead } from "./types";

function result(overrides: Partial<CheckResult> = {}): CheckResult {
  return {
    checkCode: "X",
    name: "Some check",
    type: "Verbatim",
    critical: true,
    status: "FAIL",
    confidence: 0.9,
    timestamp: "00:12",
    ruleVersion: "v1.4",
    sourceOfTruth: "Approved script",
    observed: "something",
    expected: "something else",
    evidenceQuote: "a real quote",
    rationale: "a rationale",
    ...overrides,
  };
}

function lead(results: CheckResult[]): Lead {
  return {
    id: "x",
    scenarioTag: "",
    scenarioSummary: "",
    retailer: "Retailer 1",
    product: "Energy",
    agent: "Agent",
    teamLead: "TL",
    callDate: "2026-01-01",
    durationSec: 1800,
    checklistVersion: "v1.4",
    state: "scored",
    repeatOffence: false,
    results,
    transcript: [],
    override: null,
    ingestError: null,
  };
}

describe("deriveFindings", () => {
  it("surfaces a critical FAIL even when evidenceQuote is null (an absence, not a bug)", () => {
    // A verbatim check that fails because nothing matched has no quote to
    // show — that must never cause the finding to be silently dropped
    // (regression: it used to fall through to a false "no critical
    // findings" success card on a HOLD lead — see git history).
    const findings = deriveFindings(lead([result({ status: "FAIL", evidenceQuote: null, observed: null })]));
    expect(findings).toHaveLength(1);
    expect(findings[0].tone).toBe("fail");
  });

  it("surfaces a critical REVIEW with a null evidenceQuote", () => {
    const findings = deriveFindings(lead([result({ status: "REVIEW", confidence: 0.4, evidenceQuote: null })]));
    expect(findings).toHaveLength(1);
    expect(findings[0].tone).toBe("review");
  });

  it("still excludes PASS results", () => {
    const findings = deriveFindings(lead([result({ status: "PASS" })]));
    expect(findings).toHaveLength(0);
  });

  it("sorts critical findings before non-critical ones", () => {
    const findings = deriveFindings(
      lead([
        result({ checkCode: "A", critical: false, status: "FAIL" }),
        result({ checkCode: "B", critical: true, status: "FAIL" }),
      ]),
    );
    expect(findings.map((f) => f.result.checkCode)).toEqual(["B", "A"]);
  });
});
