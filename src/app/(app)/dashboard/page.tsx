import ViewShell from "@/components/layout/ViewShell";
import KpiGrid from "@/components/dashboard/KpiGrid";
import DecisionDistribution from "@/components/dashboard/DecisionDistribution";
import FailingChecks from "@/components/dashboard/FailingChecks";
import RecentFailures from "@/components/dashboard/RecentFailures";
import RecentOverrides from "@/components/dashboard/RecentOverrides";
import { getDashboardMetrics } from "@/lib/data/dashboard";

export const metadata = { title: "Dashboard · CIMET QA Gate" };

export default async function DashboardPage() {
  const { kpis, distribution, failingChecks, recentFailures, recentOverrides } = await getDashboardMetrics();

  return (
    <ViewShell crumb="Operations" title="Executive QA overview">
      <KpiGrid kpis={kpis} />

      <div className="mt-4 grid grid-cols-[repeat(auto-fit,minmax(320px,1fr))] gap-4">
        <DecisionDistribution rows={distribution} totalLabel="1,284 sales scored" />
        <FailingChecks rows={failingChecks} />
      </div>

      <div className="mt-4 grid grid-cols-[repeat(auto-fit,minmax(320px,1fr))] gap-4">
        <RecentFailures rows={recentFailures} />
        <RecentOverrides rows={recentOverrides} />
      </div>
    </ViewShell>
  );
}
