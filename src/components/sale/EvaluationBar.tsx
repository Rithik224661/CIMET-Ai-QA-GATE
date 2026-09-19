"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import clsx from "clsx";
import { runEvaluation } from "@/lib/actions/evaluate";

/**
 * Developer/operator transparency strip (brief §9-10): a real "Re-score"
 * trigger that calls the backend's POST /api/evaluations, plus the
 * resulting evaluation id — proof this decision came from an actual
 * backend execution, not UI state. Kept visually secondary (small,
 * monospace, below the main decision) per the brief's explicit
 * instruction not to let this dominate the product UI.
 */
export default function EvaluationBar({ leadId, evaluationId }: { leadId: string; evaluationId: number }) {
  const router = useRouter();
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function rescore() {
    setRunning(true);
    setError(null);
    const result = await runEvaluation(leadId);
    setRunning(false);
    if (!result.ok) {
      setError(result.error);
      return;
    }
    router.refresh();
  }

  return (
    <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1.5 font-mono text-[11px] text-text-dim">
      <span>
        Evaluation <span className="text-text-muted">EVAL-{evaluationId}</span>
      </span>
      <button
        type="button"
        onClick={rescore}
        disabled={running}
        className={clsx(
          "border border-ring px-2 py-1 text-text-dim hover:border-text-muted hover:text-text-2 disabled:opacity-50",
        )}
      >
        {running ? "Re-scoring…" : "Re-score"}
      </button>
      {error ? <span className="text-fail">{error}</span> : null}
    </div>
  );
}
