"use server";

import { revalidatePath } from "next/cache";
import { apiPost, ApiError } from "@/lib/api/client";
import type { GateOutcome } from "@/lib/gate";

export type RunEvaluationResult =
  | { ok: true; leadId: string; decision: GateOutcome; checksRun: number }
  | { ok: false; error: string };

/**
 * Real evaluation trigger (brief §9): calls POST /api/evaluations on the
 * FastAPI backend, which runs the actual deterministic pipeline (checks ->
 * evidence -> gate -> persistence -> submission-if-eligible) and returns
 * the persisted decision, including its evaluationId. This is not a mock
 * UI-state toggle — a failed call surfaces a real error, and success
 * revalidates the pages that read the lead so the refreshed decision is
 * what the backend actually persisted, not optimistic client state.
 */
export async function runEvaluation(leadId: string): Promise<RunEvaluationResult> {
  try {
    const result = await apiPost<{ leadId: string; decision: GateOutcome; checksRun: number }>("/api/evaluations", {
      leadId,
    });
    revalidatePath(`/sales/${leadId}`);
    revalidatePath(`/audit/${leadId}`);
    revalidatePath("/dashboard");
    revalidatePath("/queue");
    return { ok: true, ...result };
  } catch (err) {
    const message = err instanceof ApiError ? err.message : "Could not run evaluation. Try again.";
    return { ok: false, error: message };
  }
}
