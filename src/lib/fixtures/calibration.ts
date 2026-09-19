import type { CalibrationKpi } from "../types";

export const CALIBRATION_KPIS: CalibrationKpi[] = [
  { label: "AI / auditor agreement", value: "94.2", unit: "%", sub: "312 sampled calls", tone: "pass" },
  { label: "Critical false-pass", value: "0", unit: "", sub: "The release-blocking metric", tone: "pass" },
  { label: "Critical false-fail", value: "3", unit: "", sub: "Held sales a human then passed", tone: "review" },
  { label: "Auditor-to-auditor", value: "91.6", unit: "%", sub: "Humans disagree with each other too", tone: "default" },
];

export interface ConfidenceBucket {
  label: string;
  count: number;
  belowFloor: boolean;
}

const RAW_BUCKETS: Array<[label: string, count: number]> = [
  ["0.5", 4],
  ["0.6", 9],
  ["0.7", 18],
  ["0.8", 46],
  ["0.85", 97],
  ["0.9", 214],
  ["0.95", 381],
  ["1.0", 268],
];

export const CONFIDENCE_BUCKETS: ConfidenceBucket[] = RAW_BUCKETS.map(([label, count]) => ({
  label,
  count,
  belowFloor: Number(label) < 0.85,
}));

export const CONFIDENCE_BUCKET_MAX = Math.max(...CONFIDENCE_BUCKETS.map((b) => b.count));

export interface DisagreementCategory {
  name: string;
  count: number;
}

export const DISAGREEMENT_CATEGORIES: DisagreementCategory[] = [
  { name: "Behaviour · dead air threshold", count: 16 },
  { name: "Verbatim · crosstalk windows", count: 11 },
  { name: "Factual · address formatting", count: 9 },
  { name: "Verbatim · paraphrased DMO", count: 5 },
];

export const DISAGREEMENT_MAX = Math.max(...DISAGREEMENT_CATEGORIES.map((d) => d.count));

export const SAMPLED_CALLS_TOTAL = 312;
export const SAMPLED_DISAGREEMENTS_TOTAL = 41;
