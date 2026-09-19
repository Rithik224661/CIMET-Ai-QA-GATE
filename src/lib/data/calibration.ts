import { apiGet } from "../api/client";
import type { CalibrationKpi } from "../types";
import type { ConfidenceBucket, DisagreementCategory } from "../fixtures/calibration";

interface CalibrationMetrics {
  kpis: CalibrationKpi[];
  confidenceBuckets: ConfidenceBucket[];
  confidenceBucketMax: number;
  disagreements: DisagreementCategory[];
  disagreementMax: number;
  sampledCallsTotal: number;
  sampledDisagreementsTotal: number;
}

/** GET /api/calibration */
export async function getCalibrationMetrics(): Promise<CalibrationMetrics> {
  return apiGet<CalibrationMetrics>("/api/calibration");
}
