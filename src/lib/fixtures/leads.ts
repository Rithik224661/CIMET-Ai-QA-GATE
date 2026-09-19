import type { CheckResult, HumanOverride, Lead, ResultStatus } from "../types";
import { RETAILER_1_CHECKLIST_VERSION, retailer1Catalogue } from "./checks";
import { TRANSCRIPTS } from "./transcripts";

interface CheckPatch {
  status?: ResultStatus;
  confidence?: number;
  timestamp?: string;
  observed?: string;
  expected?: string;
  evidenceQuote?: string;
  rationale?: string;
}

interface LeadFixture {
  id: string;
  scenarioTag: string;
  scenarioSummary: string;
  retailer: Lead["retailer"];
  product: Lead["product"];
  agent: string;
  teamLead: string;
  callDate: string;
  durationSec: number;
  state: Lead["state"];
  repeatOffence?: boolean;
  patch?: Record<string, CheckPatch>;
  override?: HumanOverride;
  ingestError?: Lead["ingestError"];
}

/**
 * Every scored lead is graded against the same Retailer 1 energy checklist
 * (the one full checklist export handed off with the brief — see
 * docs/DECISIONS.md). A patch overrides the clean-call default for named
 * checks; everything else on the catalogue passes at its default
 * confidence and timestamp.
 */
function buildResults(patch: Record<string, CheckPatch> = {}): CheckResult[] {
  return retailer1Catalogue().map((def) => {
    const p = patch[def.name] ?? {};
    return {
      checkCode: def.code,
      name: def.name,
      type: def.type,
      critical: def.critical,
      status: p.status ?? "PASS",
      confidence: p.confidence ?? def.defaultConfidence,
      timestamp: p.timestamp ?? def.defaultTimestamp,
      ruleVersion: `${def.code} · ${RETAILER_1_CHECKLIST_VERSION}`,
      sourceOfTruth: def.sourceOfTruth,
      observed: p.observed ?? null,
      expected: p.expected ?? null,
      evidenceQuote: p.evidenceQuote ?? null,
      rationale: p.rationale ?? null,
    };
  });
}

const FIXTURES: LeadFixture[] = [
  {
    id: "3613742",
    scenarioTag: "Lead A",
    scenarioSummary: "Clean call · auto-submit",
    retailer: "Retailer 1",
    product: "Energy",
    agent: "Agent A · R. Kaul",
    teamLead: "TL · M. Sethi",
    callDate: "2026-09-18 09:12",
    durationSec: 1620,
    state: "scored",
  },
  {
    id: "3613790",
    scenarioTag: "Lead B",
    scenarioSummary: "Rate + email mismatch · hold",
    retailer: "Retailer 1",
    product: "Energy",
    agent: "Agent A · R. Kaul",
    teamLead: "TL · M. Sethi",
    callDate: "2026-09-18 14:02",
    durationSec: 1800,
    state: "scored",
    patch: {
      "Rates and charges": {
        status: "FAIL",
        confidence: 0.98,
        observed: "28.6c / kWh peak",
        expected: "31.9c / kWh peak",
        evidenceQuote:
          '"…so your peak usage will be charged at twenty-eight point six cents per kilowatt hour, and off-peak sits lower than that."',
        rationale:
          "The quoted peak rate was extracted from the agent turn at 14:02 and compared with the rate card for plan EN-A2 attached to this lead. Numeric mismatch of 3.3c; outside the 0c tolerance for rate checks.",
      },
      "Email captured": {
        status: "FAIL",
        confidence: 0.96,
        observed: "j.smith@gmial.com",
        expected: "j.smith@gmail.com",
        evidenceQuote: '"Let me read that back — j dot smith at g-m-i-a-l dot com, is that right?"',
        rationale:
          "Read-back string normalised and compared character-by-character with the CRM email field. Domain transposition detected. Flagged rather than corrected — the system does not edit CRM data.",
      },
      "Dead air": {
        status: "FAIL",
        confidence: 0.94,
        observed: "47s continuous silence at 18:30",
        expected: "< 30s",
        evidenceQuote: "[silence 18:30 → 19:17]",
        rationale: "Non-critical behaviour check. Logged as a coaching note; does not block submission on its own.",
      },
    },
  },
  {
    id: "3613803",
    scenarioTag: "Lead C",
    scenarioSummary: "Address mismatch · hold",
    retailer: "Retailer 2",
    product: "Energy",
    agent: "Agent C · P. Nair",
    teamLead: "TL · M. Sethi",
    callDate: "2026-09-18 11:48",
    durationSec: 1440,
    state: "scored",
    patch: {
      "Address match": {
        status: "FAIL",
        confidence: 0.95,
        observed: "Unit 4, 12 Barker Street",
        expected: "Unit 7, 12 Barker Street",
        evidenceQuote: '"That\'s unit four, twelve Barker Street — correct?"',
        rationale:
          "Address components parsed from the confirmation turn and compared with the CRM service address. Unit number mismatch; street and suburb agree.",
      },
    },
  },
  {
    id: "3613811",
    scenarioTag: "Lead D",
    scenarioSummary: "Low confidence · QA review",
    retailer: "Retailer 1",
    product: "Energy",
    agent: "Agent B · D. Aurora",
    teamLead: "TL · K. Rao",
    callDate: "2026-09-18 13:20",
    durationSec: 1680,
    state: "scored",
    patch: {
      "DMO read verbatim": {
        status: "REVIEW",
        confidence: 0.61,
        observed: "Partially audible — crosstalk 09:48–10:06",
        expected: "DMO paragraph read verbatim",
        evidenceQuote: '"…the Default Market Offer for your [crosstalk] compared to…"',
        rationale:
          "Word-error rate in this window exceeded the verbatim threshold because the customer spoke over the agent. The system will not assert a pass or a fail on degraded audio; it routes to a human.",
      },
    },
  },
  {
    id: "3613824",
    scenarioTag: "Lead E",
    scenarioSummary: "Behaviour note only · auto-submit",
    retailer: "Retailer 3",
    product: "Broadband",
    agent: "Agent D · S. Iyer",
    teamLead: "TL · K. Rao",
    callDate: "2026-09-18 10:05",
    durationSec: 1260,
    state: "scored",
    patch: {
      "Dead air": {
        status: "FAIL",
        confidence: 0.92,
        timestamp: "12:14",
        observed: "38s continuous silence at 12:14",
        expected: "< 30s",
        evidenceQuote: "[silence 12:14 → 12:52]",
        rationale: "Behaviour checks never block a sale. Routed to the agent scorecard as a coaching note.",
      },
    },
  },
  {
    id: "3613766",
    scenarioTag: "Lead F",
    scenarioSummary: "Human override · audit trail",
    retailer: "Retailer 1",
    product: "Energy",
    agent: "Agent A · R. Kaul",
    teamLead: "TL · M. Sethi",
    callDate: "2026-09-17 16:44",
    durationSec: 1560,
    state: "scored",
    override: {
      aiDecision: "HOLD",
      humanDecision: "PASS",
      reason:
        "Customer corrected the rate at 27:40 and the agent re-confirmed 31.9c. The failing line predates the correction.",
      reviewerRole: "QA Analyst",
      reviewerName: "S. Bhandari",
      at: "2026-09-17 17:31",
    },
    patch: {
      "Rates and charges": {
        status: "FAIL",
        confidence: 0.88,
        observed: "30.9c / kWh peak",
        expected: "31.9c / kWh peak",
        evidenceQuote: '"peak is thirty point nine cents" … later "sorry, that\'s thirty-one point nine"',
        rationale:
          "First quoted rate mismatched the rate card. A later correction exists in the transcript but the check evaluates the read-back turn, which is why a human reviewed it.",
      },
    },
  },
  {
    id: "3613778",
    scenarioTag: "Lead G",
    scenarioSummary: "Repeat critical failure ×3",
    retailer: "Retailer 1",
    product: "Energy",
    agent: "Agent B · D. Aurora",
    teamLead: "TL · K. Rao",
    callDate: "2026-09-18 15:10",
    durationSec: 1740,
    state: "scored",
    repeatOffence: true,
    patch: {
      "Recording disclaimer": {
        status: "FAIL",
        confidence: 0.97,
        observed: "Disclaimer not detected in first 120s",
        expected: "Verbatim disclaimer before any capture",
        evidenceQuote: '"Hi, am I speaking with the account holder? Great, let\'s look at your bill…"',
        rationale:
          "Consent is verified, not assumed. No disclaimer utterance matched the approved script inside the required window, so the call is treated as non-compliant regardless of the recording existing.",
      },
    },
  },
  {
    id: "3613830",
    scenarioTag: "Lead H",
    scenarioSummary: "Scoring in progress",
    retailer: "Retailer 2",
    product: "Energy",
    agent: "Agent C · P. Nair",
    teamLead: "TL · M. Sethi",
    callDate: "2026-09-18 15:38",
    durationSec: 1500,
    state: "processing",
  },
  {
    id: "3613834",
    scenarioTag: "Lead I",
    scenarioSummary: "Ingest error · partial data",
    retailer: "Retailer 3",
    product: "Broadband",
    agent: "Agent D · S. Iyer",
    teamLead: "TL · K. Rao",
    callDate: "2026-09-18 09:41",
    durationSec: 0,
    state: "error",
    ingestError: {
      code: "E_EMPTY_MEDIA",
      message:
        "The dialler returned a 0-byte recording on the ingest callback. Nothing was scored, and the sale has not been submitted — it is held pending a usable artifact rather than passed by default.",
      retry: "2 of 3",
      at: "09:41:06",
    },
  },
];

const LEADS: Lead[] = FIXTURES.map((f) => ({
  id: f.id,
  scenarioTag: f.scenarioTag,
  scenarioSummary: f.scenarioSummary,
  retailer: f.retailer,
  product: f.product,
  agent: f.agent,
  teamLead: f.teamLead,
  callDate: f.callDate,
  durationSec: f.durationSec,
  checklistVersion: RETAILER_1_CHECKLIST_VERSION,
  state: f.state,
  repeatOffence: f.repeatOffence ?? false,
  results: f.state === "scored" ? buildResults(f.patch) : [],
  transcript: TRANSCRIPTS[f.id] ?? [],
  override: f.override ?? null,
  ingestError: f.ingestError ?? null,
}));

/** Default lead shown when opening the Sales view with no lead selected —
 * the brief's worked example (lead 3613790). */
export const DEFAULT_LEAD_ID = "3613790";

export function allLeads(): Lead[] {
  return LEADS;
}

export function findLead(id: string): Lead | undefined {
  return LEADS.find((l) => l.id === id);
}
