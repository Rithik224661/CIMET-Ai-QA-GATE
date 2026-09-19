import Link from "next/link";
import Chip from "@/components/ui/Chip";
import { TableCard, TableHeaderRow, TABLE_ROW_CLASS, gridColsStyle } from "@/components/ui/Table";
import { confidenceTextClass, decisionTone, formatConfidence } from "@/lib/status";
import type { QueueRow } from "@/lib/data/queue";

const COLS = "150px 1.1fr 1.4fr 110px 80px 150px";

export default function QueueTable({ rows }: { rows: QueueRow[] }) {
  return (
    <TableCard>
      <TableHeaderRow cols={COLS} minWidth={900}>
        <span>Lead</span>
        <span>Retailer / agent</span>
        <span>Reason</span>
        <span>Confidence</span>
        <span>Age</span>
        <span className="text-right">Decision</span>
      </TableHeaderRow>
      {rows.map(({ lead, reason, decidingConfidence, age, displayDecision, decision }) => (
        <Link key={lead.id} href={`/sales/${lead.id}`} className={TABLE_ROW_CLASS} style={gridColsStyle(COLS, 900)}>
          <span className="flex items-center gap-2 font-mono text-[13px] text-text-2">
            {lead.id}
            {lead.repeatOffence ? (
              <span className="border border-fail px-1 font-mono text-[10px] text-fail">×3</span>
            ) : null}
          </span>
          <span className="font-mono text-xs text-text-muted">
            {lead.retailer} · {lead.agent.split(" · ")[0]}
          </span>
          <span className="overflow-hidden text-ellipsis font-mono text-xs text-text-2">{reason}</span>
          <span className={`font-mono text-xs ${decidingConfidence != null ? confidenceTextClass(decidingConfidence) : "text-text-dim"}`}>
            {decidingConfidence != null ? formatConfidence(decidingConfidence) : "—"}
          </span>
          <span className="font-mono text-xs text-text-muted">{age}</span>
          <span className="justify-self-end">
            <Chip tone={decision === "ERROR" ? "fail" : decisionTone(decision)} dot>
              {displayDecision}
            </Chip>
          </span>
        </Link>
      ))}
    </TableCard>
  );
}
