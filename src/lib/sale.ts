import { formatConfidence } from "./status";
import type { CheckResult, Lead } from "./types";

export interface FindingView {
  result: CheckResult;
  banner: string;
  tone: "fail" | "review" | "muted";
  confidenceLabel: string;
  sourceShort: string;
}

/** Findings are every non-passing check, criticals surfaced first — never
 * re-derived per lead by hand, always from the check results themselves.
 *
 * Deliberately does NOT require a non-null evidenceQuote: a genuine
 * failure can be an absence (e.g. "no matching statement found in the
 * required window" — there's nothing to quote because nothing was said).
 * Dropping those would silently hide real critical failures behind a
 * false "no critical findings" success card — see FindingCard's fallback
 * copy for how an absent quote is presented instead. */
export function deriveFindings(lead: Lead): FindingView[] {
  return lead.results
    .filter((r) => r.status !== "PASS")
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
