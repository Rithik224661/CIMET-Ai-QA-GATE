"use client";

import clsx from "clsx";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { buildHref } from "@/lib/url";
import { CHECKLIST_TABS, DEFAULT_CHECKLIST_TAB, type ChecklistTab } from "@/lib/checklist";

export default function ChecklistTabs({ counts }: { counts: Record<ChecklistTab, number> }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const active = (searchParams.get("tab") as ChecklistTab | null) ?? DEFAULT_CHECKLIST_TAB;

  return (
    <div className="flex flex-wrap gap-1.5">
      {CHECKLIST_TABS.map((tab) => {
        const on = active === tab;
        return (
          <button
            key={tab}
            type="button"
            aria-pressed={on}
            onClick={() =>
              router.push(buildHref(pathname, Object.fromEntries(searchParams.entries()), { tab }), { scroll: false })
            }
            className={clsx(
              "border px-2.5 py-1.5 font-mono text-xs",
              on ? "border-accent bg-surface-2 text-text" : "border-ring bg-transparent text-text-2 hover:border-white/40",
            )}
          >
            {tab} <span className="text-text-dim">{counts[tab]}</span>
          </button>
        );
      })}
    </div>
  );
}
