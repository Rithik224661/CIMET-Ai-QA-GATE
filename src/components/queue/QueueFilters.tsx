"use client";

import clsx from "clsx";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { QUEUE_FILTERS, type QueueFilter } from "@/lib/data/queue";

export default function QueueFilters({ counts }: { counts: Record<QueueFilter, number> }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const active = (searchParams.get("filter") as QueueFilter | null) ?? "All";

  function select(filter: QueueFilter) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("filter", filter);
    router.push(`${pathname}?${params.toString()}`, { scroll: false });
  }

  return (
    <div className="mb-4 flex flex-wrap gap-2">
      {QUEUE_FILTERS.map((filter) => {
        const on = active === filter;
        return (
          <button
            key={filter}
            type="button"
            onClick={() => select(filter)}
            aria-pressed={on}
            className={clsx(
              "inline-flex items-center gap-2 border px-[11px] py-[7px] font-mono text-xs",
              on ? "border-accent bg-surface-2 text-text" : "border-ring bg-transparent text-text-2 hover:border-white/40",
            )}
          >
            {filter} <span className="text-text-dim">{counts[filter]}</span>
          </button>
        );
      })}
    </div>
  );
}
