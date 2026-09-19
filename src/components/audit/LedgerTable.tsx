import { TableCard, TableHeaderRow, TABLE_STATIC_ROW_CLASS, gridColsStyle } from "@/components/ui/Table";
import { auditStateTone } from "@/lib/audit";
import type { AuditEvent } from "@/lib/types";

const COLS = "110px 1.1fr 1.3fr 150px 140px";
const TONE_CLASS = { pass: "text-pass", fail: "text-fail", review: "text-review", muted: "text-text-muted" } as const;

export default function LedgerTable({ events }: { events: AuditEvent[] }) {
  return (
    <TableCard>
      <TableHeaderRow cols={COLS} minWidth={860}>
        <span>Timestamp</span>
        <span>Event</span>
        <span>Actor / system</span>
        <span>Version</span>
        <span>Resulting state</span>
      </TableHeaderRow>
      {events.map((e, i) => (
        <div key={`${e.time}-${i}`} className={TABLE_STATIC_ROW_CLASS} style={gridColsStyle(COLS, 860)}>
          <span className="font-mono text-xs text-text-muted">{e.time}</span>
          <span className="font-mono text-xs text-text-2">{e.event}</span>
          <span className="font-mono text-xs text-text-muted">{e.actor}</span>
          <span className="font-mono text-xs text-text-muted">{e.version ?? "—"}</span>
          <span className={`font-mono text-xs ${TONE_CLASS[auditStateTone(e.resultingState)]}`}>{e.resultingState}</span>
        </div>
      ))}
    </TableCard>
  );
}
