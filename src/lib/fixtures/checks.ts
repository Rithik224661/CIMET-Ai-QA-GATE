import type { CheckDefinition, CheckType } from "../types";

/** Weight per check type — uniform within a type in this checklist export. */
const WEIGHT_BY_TYPE: Record<CheckType, number> = {
  Verbatim: 8,
  Factual: 10,
  Behaviour: 3,
};

interface CatalogueRow {
  name: string;
  type: CheckType;
  critical: boolean;
  defaultTimestamp: string | null;
  defaultConfidence: number;
  code: string;
  sourceOfTruth: string;
}

/**
 * Retailer 1 · Energy QA checklist · v1.4 — 20 checks, the check-library
 * export handed off with the brief. A check's default result (timestamp,
 * confidence) is what a clean call produces; lib/fixtures/leads.ts patches
 * individual checks per scenario.
 */
const CATALOGUE: CatalogueRow[] = [
  { name: "Recording disclaimer", type: "Verbatim", critical: true, defaultTimestamp: "00:12", defaultConfidence: 0.99, code: "RET1-VB-001", sourceOfTruth: "Approved script v1.4 §1" },
  { name: "Account holder confirmed", type: "Factual", critical: true, defaultTimestamp: "02:41", defaultConfidence: 0.99, code: "RET1-FM-002", sourceOfTruth: "CRM · account_holder" },
  { name: "Address match", type: "Factual", critical: true, defaultTimestamp: "03:20", defaultConfidence: 0.98, code: "RET1-FM-003", sourceOfTruth: "CRM · service_address" },
  { name: "DOB match", type: "Factual", critical: true, defaultTimestamp: "04:05", defaultConfidence: 0.97, code: "RET1-FM-004", sourceOfTruth: "CRM · date_of_birth" },
  { name: "Fuel type", type: "Factual", critical: true, defaultTimestamp: "05:02", defaultConfidence: 0.99, code: "RET1-FM-005", sourceOfTruth: "CRM · fuel_type" },
  { name: "NMI / MIRN verified", type: "Factual", critical: true, defaultTimestamp: "06:12", defaultConfidence: 0.93, code: "RET1-FM-006", sourceOfTruth: "CRM · nmi" },
  { name: "DMO read verbatim", type: "Verbatim", critical: true, defaultTimestamp: "09:55", defaultConfidence: 0.97, code: "RET1-VB-007", sourceOfTruth: "Approved script v1.4 §4" },
  { name: "Rates and charges", type: "Factual", critical: true, defaultTimestamp: "14:02", defaultConfidence: 0.98, code: "RET1-FM-008", sourceOfTruth: "Retailer 1 rate card · plan EN-A2" },
  { name: "Concession applied", type: "Factual", critical: false, defaultTimestamp: "16:20", defaultConfidence: 0.91, code: "RET1-FM-009", sourceOfTruth: "CRM · concession_flag" },
  { name: "Life support declared", type: "Factual", critical: true, defaultTimestamp: "17:05", defaultConfidence: 0.99, code: "RET1-FM-010", sourceOfTruth: "CRM · life_support" },
  { name: "Dead air", type: "Behaviour", critical: false, defaultTimestamp: "18:30", defaultConfidence: 0.94, code: "RET1-BH-011", sourceOfTruth: "Transcript only" },
  { name: "Move-in date", type: "Factual", critical: false, defaultTimestamp: "20:15", defaultConfidence: 0.95, code: "RET1-FM-012", sourceOfTruth: "CRM · move_in_date" },
  { name: "Email captured", type: "Factual", critical: true, defaultTimestamp: "22:10", defaultConfidence: 0.96, code: "RET1-FM-013", sourceOfTruth: "CRM · email" },
  { name: "Gift card value", type: "Factual", critical: false, defaultTimestamp: "24:00", defaultConfidence: 0.92, code: "RET1-FM-014", sourceOfTruth: "Retailer 1 promo table" },
  { name: "T&Cs read", type: "Verbatim", critical: true, defaultTimestamp: "25:40", defaultConfidence: 0.96, code: "RET1-VB-015", sourceOfTruth: "Approved script v1.4 §9" },
  { name: "EIC provided", type: "Verbatim", critical: false, defaultTimestamp: "26:30", defaultConfidence: 0.94, code: "RET1-VB-016", sourceOfTruth: "Approved script v1.4 §10" },
  { name: "Cooling-off rights", type: "Verbatim", critical: true, defaultTimestamp: "26:58", defaultConfidence: 0.95, code: "RET1-VB-017", sourceOfTruth: "Approved script v1.4 §11" },
  { name: "Rapport", type: "Behaviour", critical: false, defaultTimestamp: null, defaultConfidence: 0.88, code: "RET1-BH-018", sourceOfTruth: "Transcript only" },
  { name: "Interruptions", type: "Behaviour", critical: false, defaultTimestamp: null, defaultConfidence: 0.9, code: "RET1-BH-019", sourceOfTruth: "Transcript only" },
  { name: "Objection handling", type: "Behaviour", critical: false, defaultTimestamp: null, defaultConfidence: 0.86, code: "RET1-BH-020", sourceOfTruth: "Transcript only" },
];

export const RETAILER_1_CHECKLIST_VERSION = "v1.4";

export function retailer1Catalogue(): CatalogueRow[] {
  return CATALOGUE;
}

export function retailer1CheckDefinitions(): CheckDefinition[] {
  return CATALOGUE.map((row) => ({
    code: row.code,
    name: row.name,
    type: row.type,
    critical: row.critical,
    weight: WEIGHT_BY_TYPE[row.type],
    sourceOfTruth: row.sourceOfTruth,
  }));
}

export type { CatalogueRow };
