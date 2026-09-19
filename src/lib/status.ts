/**
 * Single source of truth for status → color/glyph mapping. Nothing else
 * in the app should write a status ternary — import from here instead.
 * See CLAUDE.md conventions.
 */
import { CONFIDENCE_FLOOR } from "./config";
import type { Decision, ResultStatus } from "./types";

export type StatusTone = "pass" | "fail" | "review";

const RESULT_TONE: Record<ResultStatus, StatusTone> = {
  PASS: "pass",
  FAIL: "fail",
  REVIEW: "review",
};

const RESULT_GLYPH: Record<ResultStatus, string> = {
  PASS: "✓",
  FAIL: "✕",
  REVIEW: "⚠",
};

const DECISION_TONE: Record<Decision, StatusTone> = {
  AUTO_SUBMIT: "pass",
  HOLD: "fail",
  QA_REVIEW: "review",
};

const DECISION_LABEL: Record<Decision, string> = {
  AUTO_SUBMIT: "AUTO-SUBMIT",
  HOLD: "HOLD",
  QA_REVIEW: "QA REVIEW",
};

/** Tailwind color token name for a given tone — use as `text-${tone}`, `bg-${tone}`, `border-${tone}`. */
export function toneToken(tone: StatusTone): "pass" | "fail" | "review" {
  return tone;
}

export function resultTone(status: ResultStatus): StatusTone {
  return RESULT_TONE[status];
}

export function resultGlyph(status: ResultStatus): string {
  return RESULT_GLYPH[status];
}

export function decisionTone(decision: Decision): StatusTone {
  return DECISION_TONE[decision];
}

export function decisionLabel(decision: Decision): string {
  return DECISION_LABEL[decision];
}

/** 3-tier confidence text tone: strong (>=0.9), adequate (>=floor), low (<floor, never auto-passes). */
export function confidenceTone(confidence: number): "strong" | "adequate" | "low" {
  if (confidence >= 0.9) return "strong";
  if (confidence >= CONFIDENCE_FLOOR) return "adequate";
  return "low";
}

export function confidenceTextClass(confidence: number): string {
  const tone = confidenceTone(confidence);
  if (tone === "strong") return "text-text-2";
  if (tone === "adequate") return "text-text-muted";
  return "text-review";
}

export function formatConfidence(confidence: number): string {
  return `${Math.round(confidence * 100)}%`;
}
