import type { DashboardKpi } from "../types";

/** Aggregate operational figures — in production these come from
 * GET /api/metrics/dashboard, computed across the full sales volume, not
 * just the 9 scenario leads in this fixture bundle. */

export const DASHBOARD_KPIS: DashboardKpi[] = [
  { label: "Sales scored", value: "1,284", unit: "", sub: "Automatically, before submission", tone: "default" },
  { label: "Auto-submitted", value: "1,019", unit: "79.4%", sub: "First-pass yield, no rework", tone: "pass" },
  { label: "Held", value: "168", unit: "13.1%", sub: "Critical fail → TL queue", tone: "fail" },
  { label: "QA review", value: "97", unit: "7.5%", sub: "Low confidence, never auto-passed", tone: "review" },
  { label: "Critical fail rate", value: "13.1", unit: "%", sub: "Rates and email lead the failures", tone: "default" },
  { label: "Low-confidence checks", value: "2.1", unit: "%", sub: "Of 24,196 checks executed", tone: "default" },
  { label: "Repeat offences", value: "6", unit: "agents", sub: "Same critical failing 3+ times in 7 days", tone: "fail" },
  { label: "Sampled clean calls", value: "51", unit: "5%", sub: "Human-audited for calibration", tone: "accent" },
];

export const DECISION_DISTRIBUTION = [
  { label: "AUTO-SUBMIT", count: "1,019", pct: "79.4%", pctValue: 79.4, tone: "pass" as const },
  { label: "HOLD", count: "168", pct: "13.1%", pctValue: 13.1, tone: "fail" as const },
  { label: "QA REVIEW", count: "97", pct: "7.5%", pctValue: 7.5, tone: "review" as const },
];

export const FAILING_CHECKS = [
  { name: "Rates and charges", type: "Factual", count: 62 },
  { name: "Email captured", type: "Factual", count: 41 },
  { name: "Recording disclaimer", type: "Verbatim", count: 28 },
  { name: "DMO read verbatim", type: "Verbatim", count: 19 },
  { name: "NMI / MIRN verified", type: "Factual", count: 12 },
];

export interface RecentFailureRow {
  leadId: string;
  check: string;
  meta: string;
  age: string;
}

export const RECENT_FAILURES: RecentFailureRow[] = [
  { leadId: "3613790", check: "Rates and charges", meta: "Retailer 1 · Agent A", age: "12m" },
  { leadId: "3613778", check: "Recording disclaimer", meta: "Retailer 1 · Agent B · repeat ×3", age: "48m" },
  { leadId: "3613803", check: "Address match", meta: "Retailer 2 · Agent C", age: "2h" },
  { leadId: "3613766", check: "Rates and charges", meta: "Retailer 1 · Agent A · overridden", age: "1d" },
];

export interface RecentOverrideRow {
  leadId: string;
  ai: string;
  human: string;
  reason: string;
  who: string;
  time: string;
}

export const RECENT_OVERRIDES: RecentOverrideRow[] = [
  {
    leadId: "3613766",
    ai: "HOLD",
    human: "PASS",
    reason: "Customer corrected the rate at 27:40; agent re-confirmed 31.9c.",
    who: "S. Bhandari",
    time: "17:31",
  },
  {
    leadId: "3613701",
    ai: "AUTO-SUBMIT",
    human: "HOLD",
    reason: "Sampled clean call — auditor found an unread cooling-off clause the check scored as present.",
    who: "A. Fernandes",
    time: "11:02",
  },
  {
    leadId: "3613688",
    ai: "QA REVIEW",
    human: "PASS",
    reason: "Crosstalk resolved on listen-back; DMO was read verbatim.",
    who: "S. Bhandari",
    time: "09:47",
  },
];
