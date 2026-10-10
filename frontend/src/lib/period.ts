import type { DashboardSummary } from "./contracts";
import { round6 } from "./units";

/** Indian financial year string like "FY2025-26" → inclusive month range. */
export function fyMonths(fy: string): { from: string; to: string } {
  const m = /^FY(\d{4})-(\d{2})$/.exec(fy);
  if (!m) throw new Error(`Bad FY: ${fy}`);
  const y = Number(m[1]);
  return { from: `${y}-04`, to: `${y + 1}-03` };
}

export function sumFy(monthly: DashboardSummary["monthly_placed_on_market"], fy: string, key: "plastic_kg" | "total_packaging_kg"): number {
  const { from, to } = fyMonths(fy);
  return round6(monthly.filter((m) => m.month >= from && m.month <= to).reduce((s, m) => s + m[key], 0));
}
