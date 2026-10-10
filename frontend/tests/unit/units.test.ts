import { describe, expect, it } from "vitest";
import { normalizeUnit, powerOfTenRatio, toKg } from "@/lib/units";

describe("toKg", () => {
  it("keeps kg", () => expect(toKg(500, "kg")).toEqual({ ok: true, kg: 500, rule: "KG" }));
  it("converts grams", () => expect(toKg(2500, "g")).toMatchObject({ ok: true, kg: 2.5 }));
  it("converts MT/tonne", () => {
    expect(toKg(0.5, "MT")).toMatchObject({ ok: true, kg: 500 });
    expect(toKg(500, "Tonne")).toMatchObject({ ok: true, kg: 500000 });
  });
  it("converts pieces only with a weight per piece", () => {
    expect(toKg(48000, "pcs", { weightPerUnitG: 21 })).toMatchObject({ ok: true, kg: 1008 });
    const r = toKg(48000, "pcs");
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.next_step).toMatch(/weight/i);
  });
  it("rejects negative, NaN and unknown units with a next step", () => {
    for (const r of [toKg(-1, "kg"), toKg(NaN, "kg"), toKg(1, "barrels")]) {
      expect(r.ok).toBe(false);
      if (!r.ok) expect(r.next_step.length).toBeGreaterThan(5);
    }
  });
  it("normalises unit spellings", () => {
    expect(normalizeUnit(" KGS ")).toBe("kg");
    expect(normalizeUnit("tonnes")).toBe("mt");
    expect(normalizeUnit("bottles")).toBe("pcs");
    expect(normalizeUnit("furlong")).toBeNull();
  });
});

describe("powerOfTenRatio", () => {
  it("detects the 0.5 MT vs 500 MT slip (×1000)", () => expect(powerOfTenRatio(500000, 500)).toBe(1000));
  it("detects the inverse", () => expect(powerOfTenRatio(500, 500000)).toBe(0.001));
  it("ignores ordinary differences", () => {
    expect(powerOfTenRatio(19183.559, 10391.394)).toBeNull();
    expect(powerOfTenRatio(100, 100)).toBeNull();
  });
});
