import clsx from "clsx";
import type { ReactNode } from "react";

export type ChipTone = "pass" | "fail" | "review" | "accent" | "muted" | "ink";

const TEXT_TONE: Record<ChipTone, string> = {
  pass: "text-pass",
  fail: "text-fail",
  review: "text-review",
  accent: "text-accent",
  muted: "text-text-muted",
  ink: "text-text-2",
};

const DOT_TONE: Record<ChipTone, string> = {
  pass: "bg-pass",
  fail: "bg-fail",
  review: "bg-review",
  accent: "bg-accent",
  muted: "bg-text-muted",
  ink: "bg-text-2",
};

export function Dot({ tone, className }: { tone: ChipTone; className?: string }) {
  return <span aria-hidden className={clsx("block size-1.5 flex-none rounded-full", DOT_TONE[tone], className)} />;
}

/**
 * Status chip — border-radius: 100px, always (CLAUDE.md #2). Status is
 * never conveyed by color alone: pass a glyph or `dot` alongside the word.
 */
export default function Chip({
  tone,
  dot = false,
  children,
  className,
}: {
  tone: ChipTone;
  dot?: boolean;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-full bg-chip-bg px-2.5 py-1 font-mono text-xs uppercase tracking-[0.3px]",
        TEXT_TONE[tone],
        className,
      )}
    >
      {dot ? <Dot tone={tone} /> : null}
      {children}
    </span>
  );
}
