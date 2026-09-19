import { notFound } from "next/navigation";
import Link from "next/link";
import ViewShell from "@/components/layout/ViewShell";
import LedgerTable from "@/components/audit/LedgerTable";
import { buttonClass } from "@/components/ui/Button";
import { getLedger } from "@/lib/data/audit";

export async function generateMetadata({ params }: { params: Promise<{ leadId: string }> }) {
  const { leadId } = await params;
  return { title: `Audit · ${leadId} · CIMET QA Gate` };
}

export default async function AuditPage({ params }: { params: Promise<{ leadId: string }> }) {
  const { leadId } = await params;
  const events = await getLedger(leadId);
  if (!events) notFound();

  return (
    <ViewShell crumb="Traceability" title="Decision ledger">
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <span className="font-mono text-xs text-text-muted">Decision ledger for</span>
        <span className="font-mono text-sm text-text-2">{leadId}</span>
        <Link href={`/sales/${leadId}`} className={buttonClass("secondary", "px-2.5 py-1.5 text-[11px] uppercase tracking-[0.5px]")}>
          Back to sale
        </Link>
      </div>
      <LedgerTable events={events} />
      <p className="mt-3.5 font-mono text-[11px] text-text-dim">
        Ledger is append-only. Overrides add an event; they never rewrite the AI decision.
      </p>
    </ViewShell>
  );
}
