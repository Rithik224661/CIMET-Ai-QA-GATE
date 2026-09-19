import { TableCard, TableHeaderRow, TABLE_STATIC_ROW_CLASS, gridColsStyle } from "@/components/ui/Table";
import type { CheckDefinition, RuleSetVersion } from "@/lib/types";

const COLS = "1.5fr 96px 96px 80px 1.4fr";

export default function RuleTable({ ruleSet, checks }: { ruleSet: RuleSetVersion; checks: CheckDefinition[] }) {
  return (
    <TableCard className="min-w-0">
      <div className="flex flex-wrap items-center gap-3 border-b border-ring px-5 py-4">
        <h2 className="text-[15px] font-medium tracking-[-0.3px]">
          {ruleSet.retailer} · {ruleSet.checklist}
        </h2>
        <span className="font-mono text-xs text-text-muted">
          {ruleSet.version} · effective {ruleSet.effectiveFrom}
          {ruleSet.live ? "" : " · superseded"}
        </span>
        <span className="ml-auto font-mono text-[11px] text-text-dim">{checks.length} checks · weights locked</span>
      </div>
      <TableHeaderRow cols={COLS} minWidth={760}>
        <span>Check</span>
        <span>Type</span>
        <span>Critical</span>
        <span>Weight</span>
        <span>Source of truth</span>
      </TableHeaderRow>
      {checks.map((c) => (
        <div key={c.code} className={TABLE_STATIC_ROW_CLASS} style={gridColsStyle(COLS, 760)}>
          <span className="font-mono text-xs text-text-2">{c.name}</span>
          <span className="font-mono text-xs text-text-muted">{c.type}</span>
          <span className={`font-mono text-xs ${c.critical ? "text-text-2" : "text-text-muted"}`}>{c.critical ? "YES" : "no"}</span>
          <span className="font-mono text-xs text-text-muted">{c.weight}</span>
          <span className="overflow-hidden text-ellipsis font-mono text-xs text-text-muted">{c.sourceOfTruth}</span>
        </div>
      ))}
    </TableCard>
  );
}
