import { formatConfidence } from "./status";
import type { CheckResult, Lead } from "./types";

export interface FindingView {
  result: CheckResult;
  banner: string;
  tone: "fail" | "review" | "muted";
  confidenceLabel: string;
  sourceShort: string;
}

/** Findings are every non-passing check that carries evidence, criticals
 * surfaced first — never re-derived per lead by hand, always from the
 * check results themselves. */
export function deriveFindings(lead: Lead): FindingView[] {
  return lead.results
    .filter((r) => r.status !== "PASS" && r.evidenceQuote)
    .sort((a, b) => Number(b.critical) - Number(a.critical))
    .map((result) => {
      const tone: FindingView["tone"] = result.status === "REVIEW" ? "review" : result.critical ? "fail" : "muted";
      const banner =
        result.status === "REVIEW"
          ? "Low confidence — routed to QA"
          : result.critical
            ? "Critical failure"
            : "Coaching note — does not block";
      return {
        result,
        banner,
        tone,
        confidenceLabel: formatConfidence(result.confidence),
        sourceShort: result.sourceOfTruth.split(" · ")[0],
      };
    });
}
