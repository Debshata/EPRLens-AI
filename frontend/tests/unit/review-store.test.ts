import { describe, expect, it } from "vitest";
import reconciliation from "@/lib/mocks/reconciliation.json";
import { ReconciliationResponse } from "@/lib/contracts";
import { appendAction, effectiveState, loadHistory, saveHistory, validateReviewInput } from "@/lib/review-store";

const finding = ReconciliationResponse.parse(reconciliation).findings[0];
const ctx = { actor: "demo.admin01@example.com", now: new Date("2026-10-09T10:00:00Z") };

describe("review workflow", () => {
  it("accepting a correction needs a value and a reason", () => {
    expect(validateReviewInput({ kind: "accept_correction", reason: "ok" }).ok).toBe(false);
    expect(validateReviewInput({ kind: "accept_correction", reason: "Supplier confirmed 0.5 MT", proposed_value_kg: 500 }).ok).toBe(true);
    expect(validateReviewInput({ kind: "reject_suggestion", reason: "" }).ok).toBe(false);
    expect(validateReviewInput({ kind: "mark_needs_review", reason: "" }).ok).toBe(true);
  });

  it("preserves the original value and never mutates earlier history", () => {
    const h0: never[] = [];
    const h1 = appendAction(h0, finding, { kind: "accept_correction", reason: "Supplier confirmed 0.5 MT", proposed_value_kg: 500 }, ctx);
    expect(h0).toHaveLength(0);
    expect(h1[0]).toMatchObject({ original_value_kg: 500000, proposed_value_kg: 500, kind: "accept_correction" });
    expect(finding.observed.value_kg).toBe(500000); // finding itself untouched
    const h2 = appendAction(h1, finding, { kind: "reopen", reason: "" }, ctx);
    expect(h2).toHaveLength(2);
    expect(h2[0]).toBe(h1[0]);
    expect(effectiveState(finding, h1)).toBe("accepted");
    expect(effectiveState(finding, h2)).toBe("open");
  });

  it("only considers actions for the same finding", () => {
    const other = { ...finding, finding_id: "other" };
    const h = appendAction([], other, { kind: "mark_needs_review", reason: "" }, ctx);
    expect(effectiveState(finding, h)).toBe(finding.review_state);
  });

  it("persists safely and survives a broken or missing storage", () => {
    const mem = new Map<string, string>();
    const storage = { getItem: (k: string) => mem.get(k) ?? null, setItem: (k: string, v: string) => void mem.set(k, v) };
    const h = appendAction([], finding, { kind: "mark_needs_review", reason: "" }, ctx);
    expect(saveHistory(storage, h)).toBe(true);
    expect(loadHistory(storage)).toEqual(h);
    expect(loadHistory({ getItem: () => "{not json" })).toEqual([]);
    expect(loadHistory(null)).toEqual([]);
    expect(saveHistory({ setItem: () => { throw new Error("quota"); } }, h)).toBe(false);
  });
});
