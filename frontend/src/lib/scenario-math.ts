import type { ScenarioRequest, ScenarioResult } from "./contracts";
import { round6 } from "./units";

export const SCENARIO_DISCLAIMER =
  "Hypothetical: assumes unchanged sales and a feasible, safe redesign. Not measured waste reduction, verified cost saving or a change in legal EPR liability.";

export const SCENARIO_FORMULA = "kg = units × grams per unit ÷ 1000; scenario weight = baseline weight × (1 − reduction % ÷ 100)";

export interface FieldError {
  field: keyof ScenarioRequest | "reduction_pct";
  message: string;
  next_step: string;
}

/** kg = units × g/unit / 1000 */
export function packagingKg(units: number, gramsPerUnit: number): number {
  return round6((units * gramsPerUnit) / 1000);
}

export function weightFromReduction(baselineG: number, reductionPct: number): number {
  return round6(baselineG * (1 - reductionPct / 100));
}

export function reductionPctFromWeights(baselineG: number, proposedG: number): number {
  if (baselineG <= 0) return 0;
  return round6(((baselineG - proposedG) / baselineG) * 100);
}

export function validateScenarioInput(input: Partial<Record<keyof ScenarioRequest, unknown>>): FieldError[] {
  const errors: FieldError[] = [];
  const num = (v: unknown) => (typeof v === "number" ? v : typeof v === "string" && v.trim() !== "" ? Number(v) : NaN);
  const units = num(input.units);
  const base = num(input.baseline_g_per_unit);
  const prop = num(input.proposed_g_per_unit);
  if (!Number.isFinite(units) || units < 0) {
    errors.push({ field: "units", message: "Units must be zero or more.", next_step: "Enter the number of units sold in the period (for example 100000)." });
  }
  if (!Number.isFinite(base) || base <= 0) {
    errors.push({ field: "baseline_g_per_unit", message: "Current weight must be greater than 0 g.", next_step: "Use the declared packaging weight from the product master, or enter an estimate (it will be tagged estimated)." });
  }
  if (!Number.isFinite(prop) || prop <= 0) {
    errors.push({ field: "proposed_g_per_unit", message: "Proposed weight must be greater than 0 g.", next_step: "Enter the target grams per unit, or use the reduction slider." });
  }
  return errors;
}

/** Deterministic what-if. Throws on invalid input so callers must validate first (UI shows the errors). */
export function computeScenario(input: Pick<ScenarioRequest, "units" | "baseline_g_per_unit" | "proposed_g_per_unit">): ScenarioResult {
  const errs = validateScenarioInput(input);
  if (errs.length) throw new Error(errs.map((e) => e.message).join(" "));
  const baseline_kg = packagingKg(input.units, input.baseline_g_per_unit);
  const proposed_kg = packagingKg(input.units, input.proposed_g_per_unit);
  const reduction_kg = round6(baseline_kg - proposed_kg);
  return {
    baseline_kg,
    proposed_kg,
    reduction_kg,
    reduction_pct: reductionPctFromWeights(input.baseline_g_per_unit, input.proposed_g_per_unit),
    formula: SCENARIO_FORMULA,
    hypothetical: true,
    disclaimer: SCENARIO_DISCLAIMER,
  };
}
