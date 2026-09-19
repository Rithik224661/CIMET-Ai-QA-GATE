import type { CheckType } from "./types";

/**
 * Plain shared constants — deliberately NOT in ChecklistTabs.tsx. Every
 * export of a "use client" module becomes an opaque client reference when
 * imported from a Server Component, so a server page can't call `.map()`
 * on an array re-exported from a client file. Both the client tabs control
 * and the server table/page import from here instead.
 */
export const CHECKLIST_TABS = ["All", "Verbatim", "Factual", "Behaviour"] as const;
export type ChecklistTab = (typeof CHECKLIST_TABS)[number];
export const DEFAULT_CHECKLIST_TAB: ChecklistTab = "All";

export function tabMatches(tab: ChecklistTab, type: CheckType): boolean {
  return tab === "All" || tab === type;
}
