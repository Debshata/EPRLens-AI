import { describe, expect, it } from "vitest";
import { computeScenario, packagingKg, reductionPctFromWeights, validateScenarioInput, weightFromReduction } from "@/lib/scenario-math";

describe("scenario math", () => {
  it("100,000 units × 25 g = 2,500 kg", () => expect(packagingKg(100000, 25)).toBe(2500));

  it("25 → 20 g/unit reduces 500 kg (UX spec acceptance case)", () => {
    const r = computeScenario({ units: 100000, baseline_g_per_unit: 25, proposed_g_per_unit: 20 });
    expect(r).toMatchObject({ baseline_kg: 2500, proposed_kg: 2000, reduction_kg: 500, reduction_pct: 20, hypothetical: true });
  });

  it("20% less weight from the slider gives the same answer", () => {
    expect(weightFromReduction(25, 20)).toBe(20);
    expect(reductionPctFromWeights(25, 20)).toBe(20);
  });

  it("0% change yields exactly 0 kg reduction", () => {
    expect(computeScenario({ units: 123456, baseline_g_per_unit: 22, proposed_g_per_unit: 22 }).reduction_kg).toBe(0);
  });

  it("reduction is monotonic in the reduction % for fixed units", () => {
    let prev = -1;
    for (let pct = 0; pct <= 50; pct += 5) {
      const kg = computeScenario({ units: 40000, baseline_g_per_unit: 30, proposed_g_per_unit: weightFromReduction(30, pct) }).reduction_kg;
      expect(kg).toBeGreaterThanOrEqual(prev);
      prev = kg;
    }
  });

  it("matches the repo test event (100,000 × 25 g → 15% = 375 kg)", () => {
    const r = computeScenario({ units: 100000, baseline_g_per_unit: 25, proposed_g_per_unit: 21.25 });
    expect(r.reduction_kg).toBe(375);
  });

  it("matches the repo scenario SCN_000001 (5% of 22 g over 39,220,030 units)", () => {
    const r = computeScenario({ units: 39220030, baseline_g_per_unit: 22, proposed_g_per_unit: 20.9 });
    expect(r.baseline_kg).toBeCloseTo(862840.66, 2);
    expect(r.reduction_kg).toBeCloseTo(43142.033, 2);
  });

  it("rejects negative, zero and missing weights with next steps", () => {
    const errs = validateScenarioInput({ units: -5, baseline_g_per_unit: 0, proposed_g_per_unit: "" });
    expect(errs.map((e) => e.field).sort()).toEqual(["baseline_g_per_unit", "proposed_g_per_unit", "units"]);
    errs.forEach((e) => expect(e.next_step.length).toBeGreaterThan(5));
    expect(() => computeScenario({ units: 1, baseline_g_per_unit: -1, proposed_g_per_unit: 1 })).toThrow();
  });
});
