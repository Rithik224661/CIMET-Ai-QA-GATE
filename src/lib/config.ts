/**
 * Tunables that the brief left unspecified. Change these, not the gate
 * logic in lib/gate.ts — see docs/DECISIONS.md for why each value was
 * chosen.
 */

/** Below this confidence on ANY check, the check routes to QA rather than auto-passing. */
export const CONFIDENCE_FLOOR = 0.85;

/** Fraction of clean (auto-submitted) calls sampled to a human for calibration. */
export const CLEAN_SAMPLE_RATE = 0.05;

/** Same critical check failing this many times... */
export const REPEAT_OFFENCE_THRESHOLD = 3;

/** ...within this rolling window flags the TL. */
export const REPEAT_OFFENCE_WINDOW_DAYS = 7;

/** Viewport width below which the rail collapses to a horizontal bar. */
export const RAIL_COLLAPSE_BREAKPOINT_PX = 1040;
