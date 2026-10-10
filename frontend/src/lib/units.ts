/**
 * Unit normalisation. Everything is converted to kg for comparison, but callers must keep the
 * original value + unit next to the result (UX rule: never hide the original).
 */

export type ConversionRule = "KG" | "G_TO_KG_1000" | "MT_TO_KG_1000" | "PCS_X_WEIGHT_G_1000";

export type NormalizeResult =
  | { ok: true; kg: number; rule: ConversionRule }
  | { ok: false; reason: string; next_step: string };

const KG = new Set(["kg", "kgs", "kilogram", "kilograms"]);
const GRAM = new Set(["g", "gm", "gms", "gram", "grams"]);
const TONNE = new Set(["mt", "t", "tonne", "tonnes", "ton", "tons", "metric ton", "metric tons"]);
const PIECE = new Set(["pcs", "pc", "piece", "pieces", "nos", "bottles", "bottle", "units", "unit"]);

export function normalizeUnit(unit: string): "kg" | "g" | "mt" | "pcs" | null {
  const u = unit.trim().toLowerCase();
  if (KG.has(u)) return "kg";
  if (GRAM.has(u)) return "g";
  if (TONNE.has(u)) return "mt";
  if (PIECE.has(u)) return "pcs";
  return null;
}

/** Round away binary float noise without hiding real precision (6 dp). */
export function round6(n: number): number {
  return Math.round((n + Number.EPSILON) * 1e6) / 1e6;
}

export function toKg(value: number, unit: string, opts: { weightPerUnitG?: number | null } = {}): NormalizeResult {
  if (!Number.isFinite(value)) {
    return { ok: false, reason: "The quantity is not a number.", next_step: "Correct the quantity in the source file and upload it again." };
  }
  if (value < 0) {
    return { ok: false, reason: "The quantity is negative.", next_step: "Check whether this is a credit note; otherwise correct the sign." };
  }
  const u = normalizeUnit(unit);
  switch (u) {
    case "kg":
      return { ok: true, kg: round6(value), rule: "KG" };
    case "g":
      return { ok: true, kg: round6(value / 1000), rule: "G_TO_KG_1000" };
    case "mt":
      return { ok: true, kg: round6(value * 1000), rule: "MT_TO_KG_1000" };
    case "pcs": {
      const w = opts.weightPerUnitG;
      if (w == null || !Number.isFinite(w) || w <= 0) {
        return {
          ok: false,
          reason: `Quantity is in "${unit}" and no per-unit weight is available, so kg cannot be derived.`,
          next_step: "Add the packaging weight (g per unit) for this item, or mark the quantity as unknown.",
        };
      }
      return { ok: true, kg: round6((value * w) / 1000), rule: "PCS_X_WEIGHT_G_1000" };
    }
    default:
      return {
        ok: false,
        reason: `Unit "${unit}" is not recognised.`,
        next_step: "Use kg, g, MT (tonnes) or pieces with a known weight per unit.",
      };
  }
}

/** True when a/b is (within `tolPct`) an exact power of ten (including 1). Used to spot unit/decimal slips. */
export function powerOfTenRatio(a: number, b: number, tolPct = 1): number | null {
  if (!(a > 0) || !(b > 0)) return null;
  const ratio = a / b;
  const exp = Math.round(Math.log10(ratio));
  if (exp === 0) return null;
  const target = Math.pow(10, exp);
  return Math.abs(ratio - target) / target <= tolPct / 100 ? target : null;
}
