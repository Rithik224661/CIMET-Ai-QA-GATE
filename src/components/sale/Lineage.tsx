import clsx from "clsx";
import Link from "next/link";
import { buttonClass } from "@/components/ui/Button";
import { auditStateTone } from "@/lib/audit";
import type { AuditEvent } from "@/lib/types";

const TONE_TEXT = { pass: "text-pass", fail: "text-fail", review: "text-review", muted: "text-text-2" } as const;
const TONE_DOT = { pass: "bg-pass", fail: "bg-fail", review: "bg-review", muted: "bg-[rgba(255,255,255,0.3)]" } as const;

export default function Lineage({ leadId, events }: { leadId: string; events: AuditEvent[] }) {
  return (
    <div className="border border-ring bg-surface p-5">
      <div className="flex items-baseline justify-between gap-2.5">
        <h2 className="text-[15px] font-medium tracking-[-0.3px]">Decision lineage</h2>
        <Link href={`/audit/${leadId}`} className={buttonClass("secondary", "px-2.5 py-1.5 text-[11px] uppercase tracking-[0.5px]")}>
          Full ledger
        </Link>
      </div>
      <div className="mt-[18px]">
        {events.map((e, i) => {
          const isLast = i === events.length - 1;
          const tone = isLast ? auditStateTone(e.resultingState) : "muted";
          return (
            <div key={`${e.time}-${e.event}`} className="grid grid-cols-[56px_10px_1fr] items-start gap-3">
              <span className="pt-0.5 font-mono text-[11px] text-text-dim">{e.time}</span>
              <span className={clsx("mt-1.5 block size-2 flex-none", isLast ? TONE_DOT[tone] : "bg-[rgba(255,255,255,0.3)]")} />
              <span className="pb-3.5">
                <span className={clsx("block font-mono text-xs", isLast ? TONE_TEXT[tone] : "text-text-2")}>{e.event}</span>
                <span className="mt-0.5 block font-mono text-[11px] text-text-dim">
                  {e.version ? `${e.actor} · ${e.version}` : e.actor}
                </span>
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
