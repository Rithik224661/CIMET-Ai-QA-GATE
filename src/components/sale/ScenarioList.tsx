import clsx from "clsx";
import Link from "next/link";
import { Dot } from "@/components/ui/Chip";
import { decisionTone } from "@/lib/status";
import { gateForLead } from "@/lib/data/leads";
import type { Lead } from "@/lib/types";

export default function ScenarioList({ leads, activeLeadId }: { leads: Lead[]; activeLeadId: string }) {
  return (
    <div className="qa-scroll border border-ring bg-surface rail:sticky rail:top-[84px] rail:max-h-[calc(100vh-140px)] rail:overflow-auto">
      <div className="px-3.5 pb-2.5 pt-3.5 font-mono text-[11px] uppercase tracking-[1px] text-text-dim">Scenarios</div>
      {leads.map((lead) => {
        const active = lead.id === activeLeadId;
        const tone =
          lead.state === "processing" ? "accent" : lead.state === "error" ? "fail" : decisionTone(gateForLead(lead)!.decision);
        return (
          <Link
            key={lead.id}
            href={`/sales/${lead.id}`}
            aria-current={active ? "true" : undefined}
            className={clsx(
              "block w-full border-b border-hairline border-l-2 px-3.5 py-2.5 text-left hover:bg-surface-2",
              active ? "border-l-accent bg-surface-2" : "border-l-transparent",
            )}
          >
            <div className="flex items-center gap-2">
              <Dot tone={tone} />
              <span className="font-mono text-[13px] text-text-2">{lead.id}</span>
              <span className="ml-auto font-mono text-[10px] uppercase text-text-dim">{lead.scenarioTag}</span>
            </div>
            <div className="mt-1 pl-3.5 font-mono text-[11px] text-text-muted">{lead.scenarioSummary}</div>
          </Link>
        );
      })}
    </div>
  );
}
