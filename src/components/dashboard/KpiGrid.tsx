import { HairlineCell, HairlineGrid } from "@/components/ui/StatGrid";
import type { DashboardKpi } from "@/lib/types";

const TONE_CLASS: Record<DashboardKpi["tone"], string> = {
  default: "text-text",
  pass: "text-pass",
  fail: "text-fail",
  review: "text-review",
  accent: "text-accent",
};

export default function KpiGrid({ kpis }: { kpis: DashboardKpi[] }) {
  return (
    <HairlineGrid className="grid-cols-[repeat(auto-fit,minmax(180px,1fr))] rail:grid-cols-4">
      {kpis.map((k) => (
        <HairlineCell key={k.label} className="pb-6">
          <div className="font-mono text-[11px] uppercase tracking-[1px] text-text-muted">{k.label}</div>
          <div className="mt-3.5 flex items-baseline gap-1.5">
            <span className={`font-mono text-4xl leading-none tracking-kpi ${TONE_CLASS[k.tone]}`}>{k.value}</span>
            {k.unit ? <span className="font-mono text-sm text-text-muted">{k.unit}</span> : null}
          </div>
          <div className="mt-2.5 text-xs text-text-muted">{k.sub}</div>
        </HairlineCell>
      ))}
    </HairlineGrid>
  );
}
