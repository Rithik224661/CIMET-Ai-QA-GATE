"use client";

import * as Dialog from "@radix-ui/react-dialog";
import clsx from "clsx";
import { useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import Chip from "@/components/ui/Chip";
import { buttonClass } from "@/components/ui/Button";
import { HairlineCell, HairlineGrid } from "@/components/ui/StatGrid";
import { confidenceTextClass, confidenceTone, formatConfidence, resultTone } from "@/lib/status";
import { buildHref } from "@/lib/url";
import type { CheckResult } from "@/lib/types";

const CONF_BAR_CLASS = { strong: "bg-text-2", adequate: "bg-text-muted", low: "bg-review" } as const;

export default function EvidenceDrawer({ results }: { results: CheckResult[] }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const checkCode = searchParams.get("check");
  const result = checkCode ? (results.find((r) => r.checkCode === checkCode) ?? null) : null;
  const isOpen = !!result;

  // Seed local playback state from the URL when a *different* check opens —
  // adjusted during render (React's documented pattern for this), not in an
  // effect, so opening the drawer via "Play evidence" never flashes closed
  // first. Once open, Play/Mark reviewed only touch local state.
  const [playing, setPlaying] = useState(false);
  const [seededFor, setSeededFor] = useState<string | null>(null);
  if (checkCode !== seededFor) {
    setSeededFor(checkCode);
    setPlaying(checkCode != null && searchParams.get("play") === "1");
  }

  function close() {
    const current = Object.fromEntries(searchParams.entries());
    router.push(buildHref(pathname, current, { check: null, play: null }), { scroll: false });
  }

  const displayTs = result?.timestamp ?? "whole call";

  return (
    <Dialog.Root open={isOpen} onOpenChange={(open) => !open && close()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-[80] bg-[rgba(0,0,0,0.72)]" />
        <Dialog.Content
          aria-describedby={undefined}
          className="fixed inset-y-0 right-0 z-[80] w-full max-w-[460px] animate-qaslide overflow-auto border-l border-ring bg-surface p-6 qa-scroll focus:outline-none"
        >
          {result ? (
            <>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="font-mono text-[11px] uppercase tracking-[1px] text-text-dim">Evidence inspector</div>
                  <Dialog.Title className="mt-2 text-[22px] font-medium tracking-[-0.8px]">{result.name}</Dialog.Title>
                </div>
                <Dialog.Close
                  aria-label="Close"
                  className="flex size-8 flex-none items-center justify-center border border-ring text-text-2"
                >
                  ×
                </Dialog.Close>
              </div>

              <div className="mt-3.5 flex flex-wrap gap-2">
                <Chip tone={resultTone(result.status)} dot>
                  {result.status}
                </Chip>
                <Chip tone="muted">{result.type}</Chip>
                <Chip tone={result.critical ? "ink" : "muted"}>{result.critical ? "CRITICAL" : "NON-CRITICAL"}</Chip>
              </div>

              <HairlineGrid className="mt-5 grid-cols-1 border border-ring">
                <HairlineCell tight>
                  <div className="font-mono text-[10px] uppercase tracking-[0.5px] text-text-dim">
                    Observed — what the transcript contains
                  </div>
                  <div className={clsx("mt-2 font-mono text-sm", resultTone(result.status) === "pass" ? "text-pass" : resultTone(result.status) === "review" ? "text-review" : "text-fail")}>
                    {result.observed ?? "Matched the approved value in the transcript."}
                  </div>
                </HairlineCell>
                <HairlineCell tight>
                  <div className="font-mono text-[10px] uppercase tracking-[0.5px] text-text-dim">Expected — authoritative source</div>
                  <div className="mt-2 font-mono text-sm text-pass">{result.expected ?? "As defined by the check source."}</div>
                  <div className="mt-2 font-mono text-[11px] text-text-dim">{result.sourceOfTruth}</div>
                </HairlineCell>
                <HairlineCell tight>
                  <div className="font-mono text-[10px] uppercase tracking-[0.5px] text-text-dim">
                    Evaluation — what the system determined
                  </div>
                  <div className="mt-2 text-[13px] leading-relaxed text-text-2">
                    {result.rationale ??
                      `Compared the transcript against ${result.sourceOfTruth} under ${result.ruleVersion}. Values agree within tolerance, so the check passes and contributes no block to the gate.`}
                  </div>
                </HairlineCell>
              </HairlineGrid>

              <div className="mt-5">
                <div className="font-mono text-[10px] uppercase tracking-[0.5px] text-text-dim">Transcript evidence · {displayTs}</div>
                <div className="mt-2.5 border-l-2 border-accent bg-bg py-2.5 pl-3">
                  <p className="font-mono text-xs leading-relaxed text-text-2">
                    {result.evidenceQuote ?? "No exception captured — the check passed against the source of truth."}
                  </p>
                </div>
              </div>

              <div className="mt-5 grid grid-cols-2 gap-3">
                <div>
                  <div className="font-mono text-[10px] uppercase tracking-[0.5px] text-text-dim">Confidence</div>
                  <div className={clsx("mt-2 font-mono text-[22px]", confidenceTextClass(result.confidence))}>
                    {formatConfidence(result.confidence)}
                  </div>
                  <div className="relative mt-2 h-1.5 w-full bg-track">
                    <div
                      className={clsx("absolute inset-y-0 left-0", CONF_BAR_CLASS[confidenceTone(result.confidence)])}
                      style={{ width: `${result.confidence * 100}%` }}
                    />
                  </div>
                </div>
                <div>
                  <div className="font-mono text-[10px] uppercase tracking-[0.5px] text-text-dim">Rule version</div>
                  <div className="mt-2.5 font-mono text-[13px] text-text-2">{result.ruleVersion}</div>
                  <div className="mt-1.5 font-mono text-[11px] text-text-dim">live on call date</div>
                </div>
              </div>

              <div className="mt-6 flex flex-wrap gap-2">
                <button type="button" onClick={() => setPlaying(true)} className={buttonClass("primary")}>
                  ▶ Play audio · {displayTs}
                </button>
                <Dialog.Close className={buttonClass("secondary")}>Mark reviewed</Dialog.Close>
              </div>

              {playing ? (
                <div className="mt-4 flex items-center gap-2.5 border border-ring p-3.5">
                  <span className="block size-1.5 animate-qapulse rounded-full bg-accent" />
                  <span className="font-mono text-xs text-text-muted">
                    Playing 20s from {displayTs} — card numbers redacted in this stream
                  </span>
                </div>
              ) : null}

              <p className="mt-5 font-mono text-[11px] leading-relaxed text-text-dim">
                The system reports what failed and where. It does not rewrite the sale, correct the agent, or contact
                the customer.
              </p>
            </>
          ) : null}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
