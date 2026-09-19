import clsx from "clsx";
import { resultGlyph, resultTone } from "@/lib/status";
import type { ResultStatus } from "@/lib/types";

const TEXT_TONE = { pass: "text-pass", fail: "text-fail", review: "text-review" } as const;

/** Glyph + word, never color alone (CLAUDE.md #5). */
export default function StatusWord({ status, className }: { status: ResultStatus; className?: string }) {
  return (
    <span className={clsx("inline-flex items-center gap-1.5 font-mono text-xs", TEXT_TONE[resultTone(status)], className)}>
      <span aria-hidden>{resultGlyph(status)}</span>
      {status}
    </span>
  );
}
