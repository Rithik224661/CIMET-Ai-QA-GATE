import clsx from "clsx";
import type { CSSProperties, ReactNode } from "react";

/**
 * The 1px hairline grid used by KPI rows, decision stats and the
 * observed/expected comparison panels — a `gap-px` grid over a `bg-ring`
 * backdrop so the grout line is exactly 1px. See design_handoff/README.md
 * "Shape & spacing".
 */
export function HairlineGrid({
  cols,
  className,
  children,
}: {
  /** Fixed grid-template-columns (inline style). Omit when the column
   * count is meant to vary responsively — pass a `grid-cols-[...]` /
   * `rail:grid-cols-*` className instead, since an inline style would
   * always beat those utilities. */
  cols?: string;
  className?: string;
  children: ReactNode;
}) {
  const style: CSSProperties | undefined = cols ? { gridTemplateColumns: cols } : undefined;
  return (
    <div className={clsx("grid gap-px bg-ring", className)} style={style}>
      {children}
    </div>
  );
}

export function HairlineCell({
  className,
  children,
  tight = false,
}: {
  className?: string;
  children: ReactNode;
  tight?: boolean;
}) {
  return <div className={clsx(tight ? "bg-bg p-3.5" : "bg-surface p-5", className)}>{children}</div>;
}
