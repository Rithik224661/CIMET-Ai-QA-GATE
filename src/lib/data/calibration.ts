import {
  CALIBRATION_KPIS,
  CONFIDENCE_BUCKETS,
  CONFIDENCE_BUCKET_MAX,
  DISAGREEMENT_CATEGORIES,
  DISAGREEMENT_MAX,
  SAMPLED_CALLS_TOTAL,
  SAMPLED_DISAGREEMENTS_TOTAL,
} from "../fixtures/calibration";

/** GET /api/metrics/calibration */
export async function getCalibrationMetrics() {
  return {
    kpis: CALIBRATION_KPIS,
    confidenceBuckets: CONFIDENCE_BUCKETS,
    confidenceBucketMax: CONFIDENCE_BUCKET_MAX,
    disagreements: DISAGREEMENT_CATEGORIES,
    disagreementMax: DISAGREEMENT_MAX,
    sampledCallsTotal: SAMPLED_CALLS_TOTAL,
    sampledDisagreementsTotal: SAMPLED_DISAGREEMENTS_TOTAL,
  };
}
