import { notFound } from "next/navigation";
import ViewShell from "@/components/layout/ViewShell";
import ScenarioList from "@/components/sale/ScenarioList";
import DecisionHeader from "@/components/sale/DecisionHeader";
import OverrideBanner from "@/components/sale/OverrideBanner";
import FindingCard from "@/components/sale/FindingCard";
import CallTimeline from "@/components/sale/CallTimeline";
import ChecklistTabs from "@/components/sale/ChecklistTabs";
import { CHECKLIST_TABS, DEFAULT_CHECKLIST_TAB, tabMatches, type ChecklistTab } from "@/lib/checklist";
import ChecklistTable from "@/components/sale/ChecklistTable";
import HumanReviewForm from "@/components/sale/HumanReviewForm";
import Lineage from "@/components/sale/Lineage";
import EvidenceDrawer from "@/components/evidence/EvidenceDrawer";
import EvaluationBar from "@/components/sale/EvaluationBar";
import Processing from "@/components/states/Processing";
import IngestError from "@/components/states/IngestError";
import EmptyFindings from "@/components/states/EmptyFindings";
import { gateForLead, getLead, getLeads } from "@/lib/data/leads";
import { buildLineage } from "@/lib/audit";
import { decisionLabel } from "@/lib/status";
import { deriveFindings } from "@/lib/sale";

export async function generateMetadata({ params }: { params: Promise<{ leadId: string }> }) {
  const { leadId } = await params;
  return { title: `Sale QA · ${leadId} · VerityGate` };
}

export default async function SalePage({
  params,
  searchParams,
}: {
  params: Promise<{ leadId: string }>;
  searchParams: Promise<{ check?: string; tab?: string; t?: string; play?: string }>;
}) {
  const { leadId } = await params;
  const sp = await searchParams;
  const [lead, leads] = await Promise.all([getLead(leadId), getLeads()]);
  if (!lead) notFound();

  const pathname = `/sales/${lead.id}`;
  const gate = gateForLead(lead);

  return (
    <ViewShell crumb={`${lead.retailer} · ${lead.product}`} title={`Sale QA · ${lead.id}`}>
      <div className="grid grid-cols-1 items-start gap-4 rail:grid-cols-[248px_minmax(0,1fr)]">
        <ScenarioList leads={leads} activeLeadId={lead.id} />

        <div className="min-w-0">
          {lead.state === "processing" ? (
            <Processing leadId={lead.id} checklistLabel={`${lead.retailer} · ${lead.checklistVersion}`} />
          ) : lead.state === "error" && lead.ingestError ? (
            <IngestError leadId={lead.id} ingestError={lead.ingestError} />
          ) : gate ? (
            <>
              <DecisionHeader lead={lead} gate={gate} />
              <EvaluationBar leadId={lead.id} evaluationId={gate.evaluationId} />
              {lead.override ? <OverrideBanner override={lead.override} /> : null}

              <SectionHeading title="Critical findings" trailing="evidence-backed · click to inspect" />
              {(() => {
                const findings = deriveFindings(lead);
                if (findings.length === 0) {
                  return (
                    <>
                      <EmptyFindings criticalChecks={gate.criticalChecks} />
                    </>
                  );
                }
                return (
                  <div className="grid grid-cols-[repeat(auto-fit,minmax(320px,1fr))] gap-4">
                    {findings.map((f) => (
                      <FindingCard key={f.result.checkCode} finding={f} pathname={pathname} searchParams={sp} />
                    ))}
                  </div>
                );
              })()}

              <SectionHeading
                title="Call timeline"
                trailing={`${Math.floor(lead.durationSec / 60)}:00 · speaker-separated · word-level timestamps`}
              />
              <CallTimeline durationSec={lead.durationSec} results={lead.results} transcript={lead.transcript} />

              <div className="mt-7 mb-3 flex flex-wrap items-baseline justify-between gap-3">
                <h2 className="text-[15px] font-medium tracking-[-0.3px]">Full checklist</h2>
                <ChecklistTabs counts={checklistCounts(lead.results)} />
              </div>
              <ChecklistTable
                rows={lead.results.filter((r) => tabMatches((sp.tab as ChecklistTab) ?? DEFAULT_CHECKLIST_TAB, r.type))}
                pathname={pathname}
                searchParams={sp}
                activeCheckCode={sp.check ?? null}
              />

              <div className="mt-7 grid grid-cols-[repeat(auto-fit,minmax(320px,1fr))] gap-4">
                <HumanReviewForm leadId={lead.id} decision={gate.decision} decisionLabel={decisionLabel(gate.decision)} />
                <Lineage leadId={lead.id} events={buildLineage(lead, gate)} />
              </div>

              <EvidenceDrawer results={lead.results} leadId={lead.id} hasAudio={!!lead.hasAudio} />
            </>
          ) : null}
        </div>
      </div>
    </ViewShell>
  );
}

function checklistCounts(results: { type: string }[]) {
  return Object.fromEntries(
    CHECKLIST_TABS.map((tab) => [tab, tab === "All" ? results.length : results.filter((r) => r.type === tab).length]),
  ) as Record<ChecklistTab, number>;
}

function SectionHeading({ title, trailing }: { title: string; trailing: string }) {
  return (
    <div className="mt-7 mb-3 flex flex-wrap items-baseline justify-between gap-3">
      <h2 className="text-[15px] font-medium tracking-[-0.3px]">{title}</h2>
      <span className="font-mono text-[11px] text-text-dim">{trailing}</span>
    </div>
  );
}
