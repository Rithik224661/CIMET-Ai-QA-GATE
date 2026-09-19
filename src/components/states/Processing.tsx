import clsx from "clsx";

type StepState = "done" | "running" | "queued";

const STEPS: Array<[label: string, state: StepState]> = [
  ["Recording received", "done"],
  ["Transcript generated", "done"],
  ["Transcript normalised", "done"],
  ["Rule set pinned", "done"],
  ["Checks executing", "running"],
  ["Gate decision", "queued"],
];

const DOT_CLASS: Record<StepState, string> = {
  done: "bg-pass",
  running: "bg-accent animate-qapulse",
  queued: "bg-[rgba(255,255,255,0.2)]",
};

const STATE_LABEL: Record<StepState, string> = { done: "complete", running: "14 of 20", queued: "pending" };

export default function Processing({ leadId, checklistLabel }: { leadId: string; checklistLabel: string }) {
  return (
    <div className="border border-ring bg-surface p-8">
      <div className="flex items-center gap-3">
        <span className="block size-3.5 animate-qaspin rounded-full border-2 border-ring border-t-accent" />
        <span className="font-mono text-xs uppercase tracking-[1px] text-accent">Processing</span>
      </div>
      <h2 className="mt-[18px] mb-1.5 text-2xl font-medium tracking-[-1px]">Scoring {leadId}</h2>
      <p className="mb-6 text-[13px] text-text-muted">
        Transcript received 34s ago. Checks are executing against {checklistLabel}.
      </p>
      <div className="flex flex-col gap-px border-y border-ring bg-ring">
        {STEPS.map(([label, state]) => (
          <div key={label} className="flex items-center gap-2.5 bg-surface px-0 py-[11px]">
            <span className={clsx("block size-1.5 flex-none rounded-full", DOT_CLASS[state])} />
            <span className={clsx("font-mono text-xs", state === "queued" ? "text-text-dim" : "text-text-2")}>{label}</span>
            <span className="ml-auto font-mono text-[11px] text-text-dim">{STATE_LABEL[state]}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
