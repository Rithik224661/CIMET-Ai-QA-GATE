import ViewShell from "@/components/layout/ViewShell";
import QueueFilters from "@/components/queue/QueueFilters";
import QueueTable from "@/components/queue/QueueTable";
import { DEMO_NOW } from "@/lib/fixtures/clock";
import { ALL_RETAILERS, DEFAULT_QUEUE_FILTER, QUEUE_FILTERS, getQueueCounts, getQueueRows, type QueueFilter } from "@/lib/data/queue";

export const metadata = { title: "QA Queue · VerityGate" };

function resolveFilter(value: string | undefined): QueueFilter {
  return (QUEUE_FILTERS as readonly string[]).includes(value ?? "") ? (value as QueueFilter) : DEFAULT_QUEUE_FILTER;
}

export default async function QueuePage({
  searchParams,
}: {
  searchParams: Promise<{ filter?: string; retailer?: string }>;
}) {
  const sp = await searchParams;
  const filter = resolveFilter(sp.filter);
  const retailer = sp.retailer ?? ALL_RETAILERS;

  const [rows, counts] = await Promise.all([
    getQueueRows({ retailer, filter, now: DEMO_NOW }),
    getQueueCounts(retailer),
  ]);

  return (
    <ViewShell crumb="Human attention" title="Work queue">
      <QueueFilters counts={counts} />
      <QueueTable rows={rows} />
      <p className="mt-3.5 font-mono text-[11px] text-text-dim">
        Ordered by severity, then age. Sampled clean calls are 5% of auto-submits, drawn for calibration.
      </p>
    </ViewShell>
  );
}
