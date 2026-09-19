import { HairlineCell, HairlineGrid } from "@/components/ui/StatGrid";
import type { CalibrationKpi } from "@/lib/types";

const TONE_CLASS: Record<CalibrationKpi["tone"], string> = {
  default: "text-text",
  pass: "text-pass",
  review: "text-review",
};

export default function CalKpis({ kpis }: { kpis: CalibrationKpi[] }) {
  return (
    <HairlineGrid className="grid-cols-[repeat(auto-fit,minmax(200px,1fr))]">
      {kpis.map((k) => (
        <HairlineCell key={k.label}>
          <div className="font-mono text-[11px] uppercase tracking-[1px] text-text-muted">{k.label}</div>
          <div className="mt-3.5 flex items-baseline gap-1.5">
            <span className={`font-mono text-[36px] leading-none tracking-cal ${TONE_CLASS[k.tone]}`}>{k.value}</span>
            {k.unit ? <span className="font-mono text-[13px] text-text-muted">{k.unit}</span> : null}
          </div>
          <div className="mt-2.5 text-xs text-text-muted">{k.sub}</div>
        </HairlineCell>
      ))}
    </HairlineGrid>
  );
}
