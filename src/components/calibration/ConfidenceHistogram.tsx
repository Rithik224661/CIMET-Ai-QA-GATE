import type { ConfidenceBucket } from "@/lib/fixtures/calibration";

export default function ConfidenceHistogram({ buckets, max }: { buckets: ConfidenceBucket[]; max: number }) {
  return (
    <div className="border border-ring bg-surface p-5">
      <h2 className="mb-1 text-[15px] font-medium tracking-[-0.3px]">Confidence distribution</h2>
      <p className="mb-5 text-xs text-text-muted">Checks below 0.85 never auto-pass — they route to QA.</p>
      <div className="flex h-[140px] items-end gap-1.5">
        {buckets.map((b) => (
          <div key={b.label} className="flex h-full flex-1 flex-col items-center justify-end gap-2">
            <div
              className={b.belowFloor ? "w-full bg-review" : "w-full bg-bar-muted-2"}
              style={{ height: `${Math.max(4, (b.count / max) * 118)}px` }}
              title={`${b.count} checks`}
            />
            <span className="font-mono text-[10px] text-text-dim">{b.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
