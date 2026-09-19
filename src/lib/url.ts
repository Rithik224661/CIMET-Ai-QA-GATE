export type SearchParamsRecord = Record<string, string | string[] | undefined>;

/** Builds an href that keeps existing query params (tab, filter, retailer…)
 * and only changes the given keys — `null` removes a key. Used so
 * navigating to open the evidence drawer, select a transcript turn, etc.
 * doesn't clobber unrelated URL state. */
export function buildHref(pathname: string, current: SearchParamsRecord, updates: Record<string, string | null>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(current)) {
    if (typeof value === "string") params.set(key, value);
  }
  for (const [key, value] of Object.entries(updates)) {
    if (value === null) params.delete(key);
    else params.set(key, value);
  }
  const qs = params.toString();
  return qs ? `${pathname}?${qs}` : pathname;
}
