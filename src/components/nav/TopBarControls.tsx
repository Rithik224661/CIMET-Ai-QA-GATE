"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { ALL_RETAILERS } from "@/lib/data/queue";

const RETAILERS = [ALL_RETAILERS, "Retailer 1", "Retailer 2", "Retailer 3"];
const RANGES = ["Today", "7 days", "30 days"];

const SELECT_CLASS =
  "border border-ring bg-surface px-2.5 py-[7px] font-mono text-xs text-text-2 focus-visible:outline-2 focus-visible:outline-accent";

/** URL-writing filter control — client per CLAUDE.md conventions. */
export default function TopBarControls() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  function setParam(key: string, value: string) {
    const params = new URLSearchParams(searchParams.toString());
    params.set(key, value);
    router.push(`${pathname}?${params.toString()}`, { scroll: false });
  }

  const retailer = searchParams.get("retailer") ?? ALL_RETAILERS;
  const range = searchParams.get("range") ?? "7 days";

  return (
    <div className="ml-auto flex flex-wrap items-center gap-2">
      <label htmlFor="qa-retailer" className="font-mono text-[11px] uppercase tracking-[0.5px] text-text-dim">
        Retailer
      </label>
      <select
        id="qa-retailer"
        value={retailer}
        onChange={(e) => setParam("retailer", e.target.value)}
        className={SELECT_CLASS}
      >
        {RETAILERS.map((r) => (
          <option key={r} value={r}>
            {r}
          </option>
        ))}
      </select>
      <label htmlFor="qa-range" className="font-mono text-[11px] uppercase tracking-[0.5px] text-text-dim">
        Range
      </label>
      <select id="qa-range" value={range} onChange={(e) => setParam("range", e.target.value)} className={SELECT_CLASS}>
        {RANGES.map((r) => (
          <option key={r} value={r}>
            {r}
          </option>
        ))}
      </select>
    </div>
  );
}
