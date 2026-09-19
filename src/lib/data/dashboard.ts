import {
  DASHBOARD_KPIS,
  DECISION_DISTRIBUTION,
  FAILING_CHECKS,
  RECENT_FAILURES,
  RECENT_OVERRIDES,
} from "../fixtures/dashboard";

/** GET /api/metrics/dashboard — Phase 1 serves the fixture aggregate. */
export async function getDashboardMetrics() {
  return {
    kpis: DASHBOARD_KPIS,
    distribution: DECISION_DISTRIBUTION,
    failingChecks: FAILING_CHECKS,
    recentFailures: RECENT_FAILURES,
    recentOverrides: RECENT_OVERRIDES,
  };
}
