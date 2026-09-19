"use client";

import clsx from "clsx";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { formatDurationLabel, timestampToSeconds } from "@/lib/format";
import { buildHref } from "@/lib/url";
import { resultTone } from "@/lib/status";
import type { CheckResult, TranscriptTurn } from "@/lib/types";

const DOT_TONE_CLASS = { pass: "bg-pass", fail: "bg-fail", review: "bg-review" } as const;
const TEXT_KIND_CLASS = { pass: "text-text-2", fail: "text-fail", review: "text-review", note: "text-text-muted" } as const;
const SPEAKER_LABEL = { AGENT: "Agent", CUSTOMER: "Customer", SYSTEM: "System" } as const;

export default function CallTimeline({
  durationSec,
  results,
  transcript,
}: {
  durationSec: number;
  results: CheckResult[];
  transcript: TranscriptTurn[];
}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const searchParamsRecord = Object.fromEntries(searchParams.entries());
  const selectedTurn = searchParams.get("t");

  const markers = results
    .filter((r) => timestampToSeconds(r.timestamp) != null)
    .map((r) => {
      const pct = (timestampToSeconds(r.timestamp)! / durationSec) * 100;
      const big = r.status !== "PASS";
      return { result: r, pct, big };
    });

  const deadAir = results.find((r) => r.name === "Dead air" && r.status === "FAIL" && r.timestamp);
  const deadAirPct = deadAir ? (timestampToSeconds(deadAir.timestamp)! / durationSec) * 100 : null;

  function openMarker(result: CheckResult) {
    router.push(buildHref(pathname, searchParamsRecord, { check: result.checkCode, t: result.timestamp, play: null }), {
      scroll: false,
    });
  }

  function selectTurn(ts: string) {
    router.push(buildHref(pathname, searchParamsRecord, { t: ts }), { scroll: false });
  }

  return (
    <div className="border border-ring bg-surface p-5">
      <div className="relative mb-1.5 h-[34px]">
        <div className="absolute inset-x-0 top-3.5 h-1.5 bg-track" />
        {deadAirPct != null ? (
          <div
            className="absolute top-3.5 h-1.5 bg-[rgba(255,255,255,0.22)]"
            style={{ left: `${deadAirPct}%`, width: "3%" }}
            title="dead air"
          />
        ) : null}
        {markers.map(({ result, pct, big }) => (
          <button
            key={result.checkCode}
            type="button"
            onClick={() => openMarker(result)}
            aria-label={`${result.name} · ${result.status} at ${result.timestamp}`}
            title={`${result.name} · ${result.status} at ${result.timestamp}`}
            className={clsx("absolute -translate-x-1/2 border-0 p-0 cursor-pointer", DOT_TONE_CLASS[resultTone(result.status)])}
            style={{ top: big ? 8 : 12, left: `${pct}%`, width: big ? 12 : 8, height: big ? 12 : 8 }}
          />
        ))}
      </div>
      <div className="flex justify-between font-mono text-[10px] text-text-dim">
        <span>00:00</span>
        <span>{formatDurationLabel(durationSec)}</span>
      </div>
      <div className="mt-3.5 flex flex-wrap gap-3.5 font-mono text-[11px] text-text-muted">
        <span className="inline-flex items-center gap-1.5">
          <span className="block size-2 bg-pass" />
          pass marker
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="block size-2 bg-fail" />
          critical fail
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="block size-2 bg-review" />
          low confidence
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="block h-1.5 w-3.5 bg-[rgba(255,255,255,0.22)]" />
          dead air
        </span>
      </div>
      <div className="qa-scroll mt-[18px] max-h-[300px] overflow-auto border-t border-ring">
        {transcript.map((turn) => {
          const on = selectedTurn === turn.timestamp;
          return (
            <button
              key={turn.timestamp}
              type="button"
              onClick={() => selectTurn(turn.timestamp)}
              className={clsx(
                "flex w-full items-start gap-3 border-b border-hairline border-l-2 px-3 py-2.5 text-left hover:bg-surface-2",
                on ? "border-l-accent bg-surface-2" : "border-l-transparent",
              )}
            >
              <span className="w-12 flex-none font-mono text-[11px] text-text-dim">{turn.timestamp}</span>
              <span
                className={clsx(
                  "w-[72px] flex-none font-mono text-[11px] uppercase",
                  turn.speaker === "AGENT" ? "text-accent" : turn.speaker === "CUSTOMER" ? "text-text-muted" : "text-text-dim",
                )}
              >
                {SPEAKER_LABEL[turn.speaker]}
              </span>
              <span className={clsx("font-mono text-xs leading-relaxed", TEXT_KIND_CLASS[turn.kind])}>{turn.text}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
