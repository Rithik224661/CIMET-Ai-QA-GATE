import clsx from "clsx";
import Link from "next/link";
import { Dot } from "@/components/ui/Chip";
import { buttonClass } from "@/components/ui/Button";
import { HairlineCell, HairlineGrid } from "@/components/ui/StatGrid";
import { confidenceTone } from "@/lib/status";
import { buildHref, type SearchParamsRecord } from "@/lib/url";
import type { FindingView } from "@/lib/sale";

const TOP_BORDER_TONE = { fail: "border-t-fail", review: "border-t-review", muted: "border-t-bar-muted" } as const;
const BANNER_TONE = { fail: "text-fail", review: "text-review", muted: "text-text-muted" } as const;
/** Mirrors lib/status.ts confidenceTone, mapped to the 3-tier dot used
 * next to a CONF chip: strong → ink, adequate → muted, low → review. */
const CONFIDENCE_DOT_TONE = { strong: "ink", adequate: "muted", low: "review" } as const;

export default function FindingCard({
  finding,
  pathname,
  searchParams,
}: {
  finding: FindingView;
  pathname: string;
  searchParams: SearchParamsRecord;
}) {
  const { result, banner, tone, confidenceLabel, sourceShort } = finding;
  const observedTextTone = result.status === "REVIEW" ? "text-review" : "text-fail";
  const confDotTone = CONFIDENCE_DOT_TONE[confidenceTone(result.confidence)];

  return (
    <div className={clsx("border border-ring border-t-2 bg-surface p-5", TOP_BORDER_TONE[tone])}>
      <div className="flex items-center justify-between gap-2.5">
        <span className={clsx("font-mono text-[11px] uppercase tracking-[1px]", BANNER_TONE[tone])}>{banner}</span>
        <span className="font-mono text-[11px] text-text-dim">{result.timestamp ?? "whole call"}</span>
      </div>
      <h3 className="mt-3 mb-1 text-[19px] font-medium tracking-[-0.5px]">{result.name}</h3>
      <div className="font-mono text-xs uppercase tracking-[0.5px] text-text-muted">
        {result.type} · {result.critical ? "CRITICAL" : "NON-CRITICAL"}
      </div>

      <HairlineGrid cols="1fr 1fr" className="mt-4 border border-ring">
        <HairlineCell tight>
          <div className="font-mono text-[10px] uppercase tracking-[0.5px] text-text-dim">Observed (transcript)</div>
          <div className={clsx("mt-2 break-words font-mono text-sm", observedTextTone)}>
            {result.observed ?? "Nothing in the transcript matched — no value was found to compare."}
          </div>
        </HairlineCell>
        <HairlineCell tight>
          <div className="font-mono text-[10px] uppercase tracking-[0.5px] text-text-dim">Expected ({sourceShort})</div>
          <div className="mt-2 break-words font-mono text-sm text-pass">{result.expected}</div>
        </HairlineCell>
      </HairlineGrid>

      <div className="mt-4 border-l-2 border-bar-muted pl-3 py-0.5">
        <div className="font-mono text-[10px] uppercase tracking-[0.5px] text-text-dim">Evidence</div>
        <p className="mt-2 font-mono text-xs leading-relaxed text-text-2">
          {result.evidenceQuote ?? "No transcript quote — nothing matched the expected phrase in the required window."}
        </p>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-chip-bg px-2.5 py-1">
          <Dot tone={confDotTone} />
          <span className="font-mono text-xs text-text-muted">CONF {confidenceLabel}</span>
        </span>
        <span className="inline-flex items-center rounded-full bg-chip-bg px-2.5 py-1">
          <span className="font-mono text-xs text-text-muted">{result.ruleVersion}</span>
        </span>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <Link
          href={buildHref(pathname, searchParams, { check: result.checkCode, play: "1" })}
          className={buttonClass("primary")}
        >
          ▶ Play evidence · {result.timestamp ?? "whole call"}
        </Link>
        <Link href={buildHref(pathname, searchParams, { check: result.checkCode, play: null })} className={buttonClass("secondary")}>
          Inspect evidence
        </Link>
      </div>
    </div>
  );
}
