export default function EmptyFindings({ criticalChecks }: { criticalChecks: number }) {
  return (
    <div className="border border-ring bg-surface p-8 text-center">
      <div className="font-mono text-[28px] text-pass">✓</div>
      <div className="mt-3 text-[15px] text-text-2">No critical findings</div>
      <p className="mx-auto mt-2 max-w-[420px] text-[13px] leading-relaxed text-text-muted">
        All {criticalChecks} critical checks matched their source of truth. This sale was submitted without human
        touch; it remains eligible for the 5% calibration sample.
      </p>
    </div>
  );
}
