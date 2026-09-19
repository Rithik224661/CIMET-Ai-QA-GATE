import Chip from "@/components/ui/Chip";
import { HairlineCell, HairlineGrid } from "@/components/ui/StatGrid";
import { formatDurationMinutes } from "@/lib/format";
import type { GateOutcome } from "@/lib/gate";
import { decisionLabel, decisionTone } from "@/lib/status";
import type { Lead } from "@/lib/types";

const DECISION_TEXT_TONE = { pass: "text-pass", fail: "text-fail", review: "text-review" } as const;
const DECISION_BORDER_TONE = { pass: "border-l-pass", fail: "border-l-fail", review: "border-l-review" } as const;

export default function DecisionHeader({ lead, gate }: { lead: Lead; gate: GateOutcome }) {
  const tone = decisionTone(gate.decision);
  // gate.reason / gate.ruleApplied are computed server-side, from the same
  // gate outcome shown here — never regenerated client-side, so the copy
  // can't drift from what actually decided the sale.
  const reason = gate.reason;

  const stats = [
    { label: "Checks run", value: gate.checksRun, dim: false },
    { label: "Critical", value: gate.criticalChecks, dim: false },
    { label: "Critical fails", value: gate.criticalFails, dim: gate.criticalFails === 0 },
    { label: "Low conf.", value: gate.lowConfidence, dim: gate.lowConfidence === 0 },
  ];

  const meta = [
    { k: "Lead", v: lead.id },
    { k: "Retailer", v: `${lead.retailer} · ${lead.product}` },
    { k: "Agent", v: lead.agent },
    { k: "Team lead", v: lead.teamLead },
    { k: "Call", v: `${lead.callDate} · ${formatDurationMinutes(lead.durationSec)}` },
    { k: "Checklist", v: `${lead.checklistVersion} · eff. 2026-09-01` },
  ];

  return (
    <div className={`border border-ring border-l-[3px] bg-surface p-6 ${DECISION_BORDER_TONE[tone]}`}>
      <div className="flex flex-wrap items-start gap-5">
        <div className="min-w-[240px] flex-1">
          <Chip tone={tone} dot>
            Gate decision
          </Chip>
          <div
            className={`mt-4 font-mono text-[clamp(34px,4.4vw,52px)] leading-none tracking-decision ${DECISION_TEXT_TONE[tone]}`}
          >
            {decisionLabel(gate.decision)}
          </div>
          <div className="mt-4 max-w-[460px] text-[15px] leading-normal text-text-2">{reason}</div>
          <div className="mt-3.5 max-w-[460px] font-mono text-xs leading-relaxed text-text-muted">
            {gate.ruleApplied}
          </div>
        </div>

        <HairlineGrid cols="repeat(2,minmax(0,1fr))" className="min-w-[240px] max-w-[420px] flex-1 self-start border border-ring">
          {stats.map((s) => (
            <HairlineCell key={s.label} tight>
              <div className={`font-mono text-[22px] tracking-[-1px] ${s.dim ? "text-text-muted" : "text-text"}`}>{s.value}</div>
              <div className="mt-1.5 font-mono text-[10px] uppercase tracking-[0.5px] text-text-muted">{s.label}</div>
            </HairlineCell>
          ))}
        </HairlineGrid>
      </div>

      <div className="mt-[22px] flex flex-wrap gap-x-5 gap-y-2.5 border-t border-ring pt-[18px]">
        {meta.map((m) => (
          <div key={m.k} className="flex gap-2">
            <span className="font-mono text-[11px] uppercase tracking-[0.5px] text-text-dim">{m.k}</span>
            <span className="font-mono text-[11px] text-text-2">{m.v}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
