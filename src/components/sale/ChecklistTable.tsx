import clsx from "clsx";
import Link from "next/link";
import StatusWord from "@/components/ui/StatusWord";
import { TableCard, TableHeaderRow, TABLE_ROW_CLASS, gridColsStyle } from "@/components/ui/Table";
import { confidenceTextClass, formatConfidence } from "@/lib/status";
import { buildHref, type SearchParamsRecord } from "@/lib/url";
import type { CheckResult } from "@/lib/types";

const COLS = "104px 1.4fr 96px 118px 100px 70px 116px";

export default function ChecklistTable({
  rows,
  pathname,
  searchParams,
  activeCheckCode,
}: {
  rows: CheckResult[];
  pathname: string;
  searchParams: SearchParamsRecord;
  activeCheckCode: string | null;
}) {
  return (
    <TableCard>
      <TableHeaderRow cols={COLS} minWidth={820}>
        <span>Status</span>
        <span>Check</span>
        <span>Type</span>
        <span>Criticality</span>
        <span>Confidence</span>
        <span>Time</span>
        <span className="text-right">Evidence</span>
      </TableHeaderRow>
      {rows.map((r) => (
        <Link
          key={r.checkCode}
          href={buildHref(pathname, searchParams, { check: r.checkCode, play: null })}
          className={clsx(TABLE_ROW_CLASS, activeCheckCode === r.checkCode && "bg-surface-2")}
          style={gridColsStyle(COLS, 820)}
        >
          <StatusWord status={r.status} />
          <span className="overflow-hidden text-ellipsis font-mono text-xs text-text-2">{r.name}</span>
          <span className="font-mono text-xs text-text-muted">{r.type}</span>
          <span className={clsx("font-mono text-xs", r.critical ? "text-text-2" : "text-text-muted")}>
            {r.critical ? "CRITICAL" : "non-critical"}
          </span>
          <span className={clsx("font-mono text-xs", confidenceTextClass(r.confidence))}>{formatConfidence(r.confidence)}</span>
          <span className="font-mono text-xs text-text-muted">{r.timestamp ?? "—"}</span>
          <span className="text-right font-mono text-xs text-accent">{r.evidenceQuote ? "Inspect →" : "Transcript →"}</span>
        </Link>
      ))}
    </TableCard>
  );
}
