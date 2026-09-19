import { apiGet } from "../api/client";
import type { DashboardKpi } from "../types";
import type { RecentFailureRow, RecentOverrideRow } from "../fixtures/dashboard";

interface DistributionRow {
  label: string;
  count: string;
  pct: string;
  pctValue: number;
  tone: "pass" | "fail" | "review";
}

interface FailingCheckRow {
  name: string;
  type: string;
  count: number;
}

interface DashboardMetrics {
  kpis: DashboardKpi[];
  distribution: DistributionRow[];
  failingChecks: FailingCheckRow[];
  recentFailures: RecentFailureRow[];
  recentOverrides: RecentOverrideRow[];
}

/** GET /api/dashboard */
export async function getDashboardMetrics(): Promise<DashboardMetrics> {
  return apiGet<DashboardMetrics>("/api/dashboard");
}
