import { describe, expect, it } from "vitest";
import { formatDate, formatKg, formatMass, formatMonth, formatSigned, formatTonnes } from "@/lib/formatters";

describe("formatters", () => {
  it("shows kg, and tonnes from 1,000 kg", () => {
    expect(formatMass(500)).toBe("500 kg");
    expect(formatMass(499500)).toBe("499,500 kg (499.5 t)");
    expect(formatMass(-2500)).toBe("-2,500 kg (-2.5 t)");
  });
  it("trims trailing decimals and keeps 3 dp max", () => {
    expect(formatKg(1008)).toBe("1,008 kg");
    expect(formatKg(0.1 + 0.2)).toBe("0.3 kg");
    expect(formatKg(19183.5591)).toBe("19,183.559 kg");
  });
  it("tonnes", () => expect(formatTonnes(52800)).toBe("52.8 t"));
  it("signed", () => expect(formatSigned(-500)).toBe("−500 kg"));
  it("dates are timezone safe", () => {
    expect(formatDate("2025-11-17")).toBe("17 Nov 2025");
    expect(formatMonth("2026-04")).toBe("Apr 2026");
    expect(formatMonth("bad")).toBe("bad");
  });
});
