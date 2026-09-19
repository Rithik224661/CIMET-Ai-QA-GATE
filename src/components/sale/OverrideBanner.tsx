import { decisionLabel } from "@/lib/status";
import type { HumanOverride } from "@/lib/types";

/** A human override never replaces the AI decision — both are shown side
 * by side, and this banner is additive: it never appears instead of the
 * DecisionHeader above it. CLAUDE.md non-negotiable #7. */
export default function OverrideBanner({ override }: { override: HumanOverride }) {
  return (
    <div className="mt-4 border border-ring border-l-2 border-l-accent bg-surface px-5 py-[18px]">
      <div className="font-mono text-[11px] uppercase tracking-[1px] text-accent">Human override recorded</div>
      <div className="mt-3.5 flex flex-wrap gap-6">
        <div>
          <div className="font-mono text-[10px] uppercase tracking-[0.5px] text-text-dim">AI decision</div>
          <div className="mt-1.5 font-mono text-base text-fail">{decisionLabel(override.aiDecision)}</div>
        </div>
        <div>
          <div className="font-mono text-[10px] uppercase tracking-[0.5px] text-text-dim">Human decision</div>
          <div className="mt-1.5 font-mono text-base text-pass">{override.humanDecision}</div>
        </div>
        <div className="min-w-[200px] flex-1">
          <div className="font-mono text-[10px] uppercase tracking-[0.5px] text-text-dim">Reason</div>
          <div className="mt-1.5 text-[13px] leading-relaxed text-text-2">{override.reason}</div>
        </div>
      </div>
      <div className="mt-3.5 font-mono text-[11px] text-text-dim">
        {override.reviewerRole} · {override.reviewerName} · {override.at} · both decisions retained in the ledger
      </div>
    </div>
  );
}
