"use client";

import { useState } from "react";
import clsx from "clsx";
import { buttonClass } from "@/components/ui/Button";
import type { Decision } from "@/lib/types";

interface SavedReview {
  choice: string;
  reason: string;
}

/**
 * Local, transient form state (CLAUDE.md: "only form and playback state is
 * local"). Confirming shows the audit-event confirmation panel below —
 * Phase 3 wires this to a server action that actually appends a
 * HumanReview + AuditEvent row; today it demonstrates the shape without
 * persistence. It never replaces the AI decision shown above it.
 */
export default function HumanReviewForm({ decision, decisionLabel }: { decision: Decision; decisionLabel: string }) {
  const [choice, setChoice] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [saved, setSaved] = useState<SavedReview | null>(null);

  const overrideValue = decision === "AUTO_SUBMIT" ? "HOLD" : "PASS";
  const overrideLabel = decision === "AUTO_SUBMIT" ? "Override → HOLD" : "Override → PASS";
  const options = [
    { label: "Agree with AI", value: decisionLabel },
    { label: overrideLabel, value: overrideValue },
  ];

  const canConfirm = !!choice && reason.trim().length > 3;

  function confirm() {
    if (!canConfirm || !choice) return;
    setSaved({ choice, reason });
  }

  return (
    <div className="border border-ring bg-surface p-5">
      <h2 className="mb-1 text-[15px] font-medium tracking-[-0.3px]">Human review</h2>
      <p className="mb-[18px] text-[13px] leading-relaxed text-text-muted">
        The AI decision is never replaced. Your decision is recorded alongside it.
      </p>

      <div className="flex items-center gap-2.5 border border-ring bg-bg px-3.5 py-3">
        <span className="font-mono text-[10px] uppercase tracking-[0.5px] text-text-dim">AI decision</span>
        <span className="ml-auto font-mono text-sm text-text-2">{decisionLabel}</span>
      </div>

      <div className="mt-3 flex gap-2">
        {options.map((o) => {
          const on = choice === o.value;
          return (
            <button
              key={o.label}
              type="button"
              aria-pressed={on}
              onClick={() => setChoice(o.value)}
              className={clsx(
                "flex-1 border px-2.5 py-2.5 font-mono text-xs",
                on ? "border-text bg-text text-cta-ink" : "border-ring bg-transparent text-text-2",
              )}
            >
              {o.label}
            </button>
          );
        })}
      </div>

      <label htmlFor="qa-reason" className="mt-4 mb-1.5 block font-mono text-[10px] uppercase tracking-[0.5px] text-text-dim">
        Override reason (required)
      </label>
      <textarea
        id="qa-reason"
        rows={3}
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        placeholder="e.g. Customer corrected the rate at 27:40; agent re-confirmed."
        className="w-full resize-y border border-ring bg-bg p-2.5 font-mono text-xs text-text-2 focus-visible:outline-2 focus-visible:outline-accent"
      />

      <button type="button" onClick={confirm} disabled={!canConfirm} className={buttonClass(canConfirm ? "primary" : "secondary", "mt-3 w-full justify-center disabled:border-0 disabled:bg-chip-bg disabled:text-text-dim")}>
        Confirm decision
      </button>

      {saved ? (
        <div className="mt-3.5 animate-qaslide border border-accent bg-bg px-3.5 py-3">
          <div className="font-mono text-[11px] uppercase tracking-[0.5px] text-accent">Audit event written</div>
          <div className="mt-2 font-mono text-xs leading-loose text-text-2">
            AI: {decisionLabel}
            <br />
            Human: {saved.choice}
            <br />
            Reviewer: QA Analyst · S. Bhandari
            <br />
            Reason: {saved.reason}
            <br />
            Time: 14:37:02
          </div>
        </div>
      ) : null}
    </div>
  );
}
