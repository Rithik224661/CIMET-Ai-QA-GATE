"use server";

import { revalidatePath } from "next/cache";
import { apiPost, ApiError } from "@/lib/api/client";
import type { HumanOverride } from "@/lib/types";

export interface SubmitOverrideInput {
  leadId: string;
  humanDecision: "PASS" | "HOLD";
  reason: string;
  reviewerName?: string;
  reviewerRole?: string;
}

export type SubmitOverrideResult =
  | { ok: true; review: HumanOverride }
  | { ok: false; error: string };

/**
 * The ONLY write path in the app (CLAUDE.md #7: a human override appends a
 * record, it never mutates or hides the AI decision). Wraps the API call
 * so the client component can show a friendly inline error instead of
 * crashing on a failed submit.
 */
export async function submitOverride(input: SubmitOverrideInput): Promise<SubmitOverrideResult> {
  try {
    const result = await apiPost<{ ok: true; review: HumanOverride }>("/api/reviews", input);
    revalidatePath(`/sales/${input.leadId}`);
    revalidatePath(`/audit/${input.leadId}`);
    revalidatePath("/dashboard");
    revalidatePath("/queue");
    return result;
  } catch (err) {
    const message = err instanceof ApiError ? err.message : "Could not submit review. Try again.";
    return { ok: false, error: message };
  }
}
