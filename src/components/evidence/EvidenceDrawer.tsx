"use client";

import * as Dialog from "@radix-ui/react-dialog";
import clsx from "clsx";
import { useCallback, useEffect, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import Chip from "@/components/ui/Chip";
import { buttonClass } from "@/components/ui/Button";
import { HairlineCell, HairlineGrid } from "@/components/ui/StatGrid";
import { confidenceTextClass, confidenceTone, formatConfidence, resultTone } from "@/lib/status";
import { timestampToSeconds } from "@/lib/format";
import { buildHref } from "@/lib/url";
import type { CheckResult } from "@/lib/types";

const CONF_BAR_CLASS = { strong: "bg-text-2", adequate: "bg-text-muted", low: "bg-review" } as const;

function formatSeconds(total: number): string {
  const mm = Math.floor(total / 60);
  const ss = Math.floor(total % 60);
  return `${mm}:${ss.toString().padStart(2, "0")}`;
}

export default function EvidenceDrawer({
  results,
  leadId,
  hasAudio,
}: {
  results: CheckResult[];
  leadId: string;
  hasAudio: boolean;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  // The <audio> element is mounted inside a Radix Dialog.Portal, which can
  // commit its children a tick after the rest of this component's render —
  // a plain useRef alone would leave the play-trigger effect below reading
  // a still-null ref on its first run. `mounted` (state) exists purely to
  // make the effect re-fire once the element actually attaches; the node
  // itself stays a plain mutable ref (nodeRef) so imperative DOM calls
  // (currentTime/play/pause) aren't flagged as mutating React state.
  const nodeRef = useRef<HTMLAudioElement | null>(null);
  const [mounted, setMounted] = useState(false);
  const audioElRef = useCallback((node: HTMLAudioElement | null) => {
    nodeRef.current = node;
    setMounted(node != null);
  }, []);

  const checkCode = searchParams.get("check");
  const result = checkCode ? (results.find((r) => r.checkCode === checkCode) ?? null) : null;
  const isOpen = !!result;

  // Seed local playback state from the URL when a *different* check opens —
  // adjusted during render (React's documented pattern for this), not in an
  // effect, so opening the drawer via "Play evidence" never flashes closed
  // first. Once open, Play/Mark reviewed only touch local state.
  const [playRequested, setPlayRequested] = useState(false);
  const [seededFor, setSeededFor] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [audioError, setAudioError] = useState(false);
  if (checkCode !== seededFor) {
    setSeededFor(checkCode);
    setPlayRequested(checkCode != null && searchParams.get("play") === "1");
    setAudioError(false);
  }

  // Real playback against the backend's actual audio bytes — never a
  // simulated "playing" animation (brief §6/§28: no fake success). Seeks
  // to the evidence's real timestamp, then plays.
  useEffect(() => {
    const audio = nodeRef.current;
    if (!audio || !mounted || !playRequested || !hasAudio || !result) return;
    const seconds = timestampToSeconds(result.timestamp);
    if (seconds != null) audio.currentTime = seconds;
    audio.play().catch(() => setAudioError(true));
    // Only re-seek when the drawer opens for a (possibly new) check, not
    // on every re-render while already playing.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mounted, playRequested, checkCode, hasAudio]);

  function close() {
    nodeRef.current?.pause();
    const current = Object.fromEntries(searchParams.entries());
    router.push(buildHref(pathname, current, { check: null, play: null }), { scroll: false });
  }

  function playFromEvidence() {
    setAudioError(false);
    setPlayRequested(true);
    const audio = nodeRef.current;
    if (!audio || !result) return;
    const seconds = timestampToSeconds(result.timestamp);
    if (seconds != null) audio.currentTime = seconds;
    audio.play().catch(() => setAudioError(true));
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
                    {result.observed ?? (result.status === "PASS" ? "Matched the approved value in the transcript." : "Nothing in the transcript matched — no value was found to compare.")}
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
                      (result.status === "PASS"
                        ? `Compared the transcript against ${result.sourceOfTruth} under ${result.ruleVersion}. Values agree within tolerance, so the check passes and contributes no block to the gate.`
                        : `Compared the transcript against ${result.sourceOfTruth} under ${result.ruleVersion}. No matching value was found, so this could not be confirmed.`)}
                  </div>
                </HairlineCell>
              </HairlineGrid>

              <div className="mt-5">
                <div className="font-mono text-[10px] uppercase tracking-[0.5px] text-text-dim">Transcript evidence · {displayTs}</div>
                <div className="mt-2.5 border-l-2 border-accent bg-bg py-2.5 pl-3">
                  <p className="font-mono text-xs leading-relaxed text-text-2">
                    {result.evidenceQuote ??
                      (result.status === "PASS"
                        ? "No exception captured — the check passed against the source of truth."
                        : "No transcript quote — nothing matched the expected phrase in the required window.")}
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
                <button
                  type="button"
                  data-testid="play-evidence-button"
                  disabled={!hasAudio}
                  onClick={isPlaying ? () => nodeRef.current?.pause() : playFromEvidence}
                  className={clsx(buttonClass("primary"), !hasAudio && "cursor-not-allowed opacity-40")}
                >
                  {!hasAudio ? "Audio unavailable" : isPlaying ? "⏸ Pause" : `▶ Play audio · ${displayTs}`}
                </button>
                <Dialog.Close className={buttonClass("secondary")}>Mark reviewed</Dialog.Close>
              </div>

              {hasAudio ? (
                <audio
                  ref={audioElRef}
                  data-testid="evidence-audio"
                  src={`/api/audio/${leadId}`}
                  preload="none"
                  className="hidden"
                  onPlay={() => setIsPlaying(true)}
                  onPause={() => setIsPlaying(false)}
                  onEnded={() => setIsPlaying(false)}
                  onError={() => setAudioError(true)}
                  onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
                />
              ) : null}

              {audioError ? (
                <div className="mt-4 border border-ring p-3.5">
                  <span className="font-mono text-xs text-fail">
                    Playback did not start — click Play audio to try again (some browsers block autoplay on
                    navigation).
                  </span>
                </div>
              ) : !hasAudio ? (
                <div className="mt-4 border border-ring p-3.5">
                  <span className="font-mono text-xs text-text-dim">
                    No recording stored for this lead — evidence remains transcript-only.
                  </span>
                </div>
              ) : isPlaying ? (
                <div className="mt-4 flex items-center gap-2.5 border border-ring p-3.5">
                  <span className="block size-1.5 animate-qapulse rounded-full bg-accent" />
                  <span className="font-mono text-xs text-text-muted">
                    Playing from {formatSeconds(currentTime)} — card numbers redacted in this stream
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
