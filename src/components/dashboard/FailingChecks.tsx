interface FailingCheckRow {
  name: string;
  type: string;
  count: number;
}

export default function FailingChecks({ rows }: { rows: FailingCheckRow[] }) {
  const max = Math.max(...rows.map((r) => r.count));

  return (
    <div className="border border-ring bg-surface p-5">
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="text-[15px] font-medium tracking-[-0.3px]">Which check is failing</h2>
        <span className="font-mono text-[11px] text-text-dim">rolling 7 days</span>
      </div>
      <div className="mt-5 flex flex-col gap-3.5">
        {rows.map((r) => (
          <div key={r.name}>
            <div className="mb-1.5 flex justify-between gap-2.5">
              <span className="overflow-hidden text-ellipsis whitespace-nowrap font-mono text-xs text-text-2">{r.name}</span>
              <span className="flex-none font-mono text-xs text-text-muted">
                {r.count} fails · {r.type}
              </span>
            </div>
            <div className="relative h-1.5 w-full bg-track">
              <div
                className={r.count > 40 ? "absolute inset-y-0 left-0 bg-fail" : "absolute inset-y-0 left-0 bg-bar-muted-2"}
                style={{ width: `${(r.count / max) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
