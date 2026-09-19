import clsx from "clsx";
import type { CSSProperties, ReactNode } from "react";

/** Shared shell for the dense mono data tables (queue, checklist, rules,
 * ledger): a bordered surface card that scrolls horizontally on its own
 * rather than breaking the page layout. */
export function TableCard({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={clsx("qa-scroll overflow-x-auto border border-ring bg-surface", className)}>{children}</div>;
}

export function gridColsStyle(cols: string, minWidth?: number): CSSProperties {
  return { gridTemplateColumns: cols, minWidth };
}

export function TableHeaderRow({
  cols,
  minWidth,
  children,
}: {
  cols: string;
  minWidth?: number;
  children: ReactNode;
}) {
  return (
    <div
      className="grid gap-3.5 border-b border-ring px-[18px] py-3 font-mono text-[11px] uppercase tracking-[1px] text-text-muted"
      style={gridColsStyle(cols, minWidth)}
    >
      {children}
    </div>
  );
}

/** Class string for a clickable data row — apply to a <button> or <Link>. */
export const TABLE_ROW_CLASS =
  "grid w-full items-center gap-3.5 border-b border-hairline px-[18px] py-[11px] text-left cursor-pointer bg-transparent hover:bg-surface-2";

export const TABLE_STATIC_ROW_CLASS = "grid items-center gap-3.5 border-b border-hairline px-[18px] py-[11px]";
