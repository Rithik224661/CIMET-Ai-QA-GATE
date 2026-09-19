/** Formatting helpers. Pure — take `now` as a parameter rather than reading
 * the clock, so callers can pin it (the demo fixtures are dated relative to
 * a fixed reference instant; see lib/fixtures/clock.ts). */

export function relativeAge(dateStr: string, now: Date): string {
  const then = new Date(dateStr.replace(" ", "T"));
  const mins = Math.max(1, Math.round((now.getTime() - then.getTime()) / 60000));
  if (mins < 60) return `${mins}m`;
  if (mins < 1440) return `${Math.round(mins / 60)}h`;
  return `${Math.round(mins / 1440)}d`;
}

/** Parses "mm:ss" into whole seconds, or null for a non-timestamped check ("—"). */
export function timestampToSeconds(ts: string | null): number | null {
  if (!ts) return null;
  const m = /^(\d+):(\d+)$/.exec(ts);
  if (!m) return null;
  return Number(m[1]) * 60 + Number(m[2]);
}

export function formatDurationLabel(durationSec: number): string {
  const mm = Math.floor(durationSec / 60);
  return `${mm}:00`;
}

export function formatDurationMinutes(durationSec: number): string {
  return `${Math.floor(durationSec / 60)}m`;
}
