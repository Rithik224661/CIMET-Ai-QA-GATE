import type { DisagreementCategory } from "@/lib/fixtures/calibration";

export default function DisagreementBars({
  categories,
  max,
  sampledCallsTotal,
  disagreementsTotal,
}: {
  categories: DisagreementCategory[];
  max: number;
  sampledCallsTotal: number;
  disagreementsTotal: number;
}) {
  return (
    <div className="border border-ring bg-surface p-5">
      <h2 className="mb-1 text-[15px] font-medium tracking-[-0.3px]">Where AI and auditors disagree</h2>
      <p className="mb-5 text-xs text-text-muted">
        {sampledCallsTotal} sampled calls · {disagreementsTotal} disagreements
      </p>
      <div className="flex flex-col gap-3.5">
        {categories.map((d) => (
          <div key={d.name}>
            <div className="mb-1.5 flex justify-between gap-2.5">
              <span className="font-mono text-xs text-text-2">{d.name}</span>
              <span className="font-mono text-xs text-text-muted">{d.count}</span>
            </div>
            <div className="relative h-1.5 w-full bg-track">
              <div className="absolute inset-y-0 left-0 bg-accent" style={{ width: `${(d.count / max) * 100}%` }} />
            </div>
          </div>
        ))}
      </div>
      <p className="mt-5 font-mono text-[11px] leading-relaxed text-text-dim">
        Critical false-pass is the metric that gates release: it must stay at zero before the gate runs unattended
        on live traffic.
      </p>
    </div>
  );
}
