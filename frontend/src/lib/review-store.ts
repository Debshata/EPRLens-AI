/**
 * Review workflow state. Rules (UX spec):
 *  - the original value is never overwritten; actions are appended to an immutable history
 *  - accept needs an explicit corrected value and a reason; reject needs a reason
 *  - the effective review state is derived from the latest action
 */
import type { Finding, ReviewAction, ReviewState } from "./contracts";

export interface ReviewInput {
  kind: ReviewAction["kind"];
  reason: string;
  proposed_value_kg?: number | null;
}

export type ReviewValidation = { ok: true } | { ok: false; message: string; next_step: string };

export function validateReviewInput(input: ReviewInput): ReviewValidation {
  if (input.kind === "accept_correction") {
    if (input.proposed_value_kg == null || !Number.isFinite(input.proposed_value_kg) || input.proposed_value_kg < 0) {
      return { ok: false, message: "Enter the corrected quantity in kg (zero or more).", next_step: "Type the value you believe is right — the original stays visible." };
    }
    if (input.reason.trim().length < 5) {
      return { ok: false, message: "A reason is required to accept a correction.", next_step: "Briefly say why (for example “Supplier confirmed 0.5 MT by email”)." };
    }
  }
  if (input.kind === "reject_suggestion" && input.reason.trim().length < 5) {
    return { ok: false, message: "A reason is required to reject a suggestion.", next_step: "Briefly say why the recorded value should stand." };
  }
  return { ok: true };
}

export function stateAfter(kind: ReviewAction["kind"]): ReviewState {
  switch (kind) {
    case "accept_correction":
      return "accepted";
    case "reject_suggestion":
      return "rejected";
    case "mark_needs_review":
      return "needs_review";
    case "reopen":
      return "open";
  }
}

export function effectiveState(finding: Finding, history: ReviewAction[]): ReviewState {
  const mine = history.filter((a) => a.finding_id === finding.finding_id);
  const last = mine[mine.length - 1];
  return last ? stateAfter(last.kind) : finding.review_state;
}

export function appendAction(
  history: readonly ReviewAction[],
  finding: Finding,
  input: ReviewInput,
  ctx: { actor: string; now: Date; idFactory?: () => string },
): ReviewAction[] {
  const v = validateReviewInput(input);
  if (!v.ok) throw new Error(v.message);
  const action: ReviewAction = {
    action_id: ctx.idFactory ? ctx.idFactory() : `act-${history.length + 1}-${finding.finding_id}`,
    finding_id: finding.finding_id,
    kind: input.kind,
    actor: ctx.actor,
    timestamp: ctx.now.toISOString(),
    original_value_kg: finding.observed.value_kg,
    proposed_value_kg: input.kind === "accept_correction" ? (input.proposed_value_kg ?? null) : null,
    reason: input.reason.trim(),
  };
  return [...history, action];
}

// ---- persistence (localStorage in the browser; every access is guarded) ----
const KEY = "eprlens.review.v1";

export function loadHistory(storage: Pick<Storage, "getItem"> | null | undefined): ReviewAction[] {
  try {
    const raw = storage?.getItem(KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as ReviewAction[]) : [];
  } catch {
    return [];
  }
}

export function saveHistory(storage: Pick<Storage, "setItem"> | null | undefined, history: readonly ReviewAction[]): boolean {
  try {
    storage?.setItem(KEY, JSON.stringify(history));
    return !!storage;
  } catch {
    return false;
  }
}

export function clearHistory(storage: Pick<Storage, "removeItem"> | null | undefined): void {
  try {
    storage?.removeItem(KEY);
  } catch {
    /* ignore */
  }
}
