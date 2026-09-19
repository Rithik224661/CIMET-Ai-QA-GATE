import Link from "next/link";
import { buttonClass } from "@/components/ui/Button";
import type { RecentFailureRow } from "@/lib/fixtures/dashboard";

export default function RecentFailures({ rows }: { rows: RecentFailureRow[] }) {
  return (
    <div className="border border-ring bg-surface">
      <div className="flex items-center justify-between gap-3 border-b border-ring px-5 py-4">
        <h2 className="text-[15px] font-medium tracking-[-0.3px]">Recent critical failures</h2>
        <Link href="/queue" className={buttonClass("secondary", "px-2.5 py-1.5 text-[11px] uppercase tracking-[0.5px]")}>
          Open queue
        </Link>
      </div>
      {rows.map((r) => (
        <Link
          key={r.leadId}
          href={`/sales/${r.leadId}`}
          className="grid w-full grid-cols-[1fr_auto] gap-x-3 gap-y-1 border-b border-hairline px-5 py-3 text-left hover:bg-surface-2"
        >
          <span className="font-mono text-[13px] text-text-2">{r.leadId}</span>
          <span className="font-mono text-xs text-fail">✕ {r.check}</span>
          <span className="font-mono text-[11px] text-text-dim">{r.meta}</span>
          <span className="text-right font-mono text-[11px] text-text-dim">{r.age}</span>
        </Link>
      ))}
    </div>
  );
}
