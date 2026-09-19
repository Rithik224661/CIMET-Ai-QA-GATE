import { Dot } from "@/components/ui/Chip";
import type { ChipTone } from "@/components/ui/Chip";

interface DistributionRow {
  label: string;
  count: string;
  pct: string;
  pctValue: number;
  tone: "pass" | "fail" | "review";
}

const BAR_TONE: Record<DistributionRow["tone"], string> = { pass: "bg-pass", fail: "bg-fail", review: "bg-review" };

export default function DecisionDistribution({
  rows,
  totalLabel,
}: {
  rows: DistributionRow[];
  totalLabel: string;
}) {
  return (
    <div className="border border-ring bg-surface p-5">
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="text-[15px] font-medium tracking-[-0.3px]">Decision distribution</h2>
        <span className="font-mono text-[11px] text-text-dim">{totalLabel}</span>
      </div>
      <div className="mt-5 mb-4 flex h-2.5 w-full gap-0.5">
        {rows.map((r) => (
          <div key={r.label} className={BAR_TONE[r.tone]} style={{ width: `${r.pctValue}%` }} title={r.label} />
        ))}
      </div>
      {rows.map((r) => (
        <div key={r.label} className="flex items-center gap-2.5 border-b border-hairline py-2.5 last:border-b-0">
          <Dot tone={r.tone as ChipTone} />
          <span className="font-mono text-xs text-text-2">{r.label}</span>
          <span className="ml-auto font-mono text-xs text-text-muted">{r.count}</span>
          <span className="w-14 text-right font-mono text-xs text-text-2">{r.pct}</span>
        </div>
      ))}
      <p className="mt-4 text-xs leading-relaxed text-text-muted">
        Gate rule: all criticals pass → auto-submit. Any critical fail → TL queue. Low confidence on any check →
        QA, never auto-pass.
      </p>
    </div>
  );
}
