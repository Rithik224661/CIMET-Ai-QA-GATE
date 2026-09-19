import type { RecentOverrideRow } from "@/lib/fixtures/dashboard";

export default function RecentOverrides({ rows }: { rows: RecentOverrideRow[] }) {
  return (
    <div className="border border-ring bg-surface">
      <div className="border-b border-ring px-5 py-4">
        <h2 className="text-[15px] font-medium tracking-[-0.3px]">Recent human overrides</h2>
      </div>
      {rows.map((r) => (
        <div key={r.leadId} className="border-b border-hairline px-5 py-3.5 last:border-b-0">
          <div className="flex flex-wrap items-center gap-2.5">
            <span className="font-mono text-[13px] text-text-2">{r.leadId}</span>
            <span className="font-mono text-xs text-fail">AI {r.ai}</span>
            <span className="font-mono text-xs text-text-dim">→</span>
            <span className="font-mono text-xs text-pass">Human {r.human}</span>
          </div>
          <div className="mt-1.5 text-xs leading-relaxed text-text-muted">{r.reason}</div>
          <div className="mt-1.5 font-mono text-[11px] text-text-dim">
            {r.who} · {r.time}
          </div>
        </div>
      ))}
    </div>
  );
}
