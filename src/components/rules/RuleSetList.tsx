import clsx from "clsx";
import Link from "next/link";
import Chip from "@/components/ui/Chip";
import type { RuleSetVersion } from "@/lib/types";

export default function RuleSetList({ ruleSets, activeIndex }: { ruleSets: RuleSetVersion[]; activeIndex: number }) {
  return (
    <div className="border border-ring bg-surface">
      <div className="px-4 pb-2 pt-3.5 font-mono text-[11px] uppercase tracking-[1px] text-text-dim">
        Retailer → checklist → version
      </div>
      {ruleSets.map((rs, i) => {
        const active = i === activeIndex;
        return (
          <Link
            key={`${rs.retailer}-${rs.version}`}
            href={`/rules?set=${i}`}
            aria-current={active ? "true" : undefined}
            className={clsx(
              "block w-full border-b border-hairline border-l-2 px-4 py-3.5 text-left hover:bg-surface-2",
              active ? "border-l-accent bg-surface-2" : "border-l-transparent",
            )}
          >
            <div className="font-mono text-[13px] text-text-2">{rs.retailer}</div>
            <div className="mt-1.5 font-mono text-[11px] text-text-muted">{rs.checklist}</div>
            <div className="mt-2 flex items-center gap-2">
              <Chip tone={rs.live ? "pass" : "muted"}>{rs.version}</Chip>
              <span className="font-mono text-[11px] text-text-dim">eff. {rs.effectiveFrom}</span>
            </div>
          </Link>
        );
      })}
      <p className="border-t border-ring px-4 py-3.5 font-mono text-[11px] leading-relaxed text-text-dim">
        Every score resolves to the version live on the call date, not today&apos;s version.
      </p>
    </div>
  );
}
