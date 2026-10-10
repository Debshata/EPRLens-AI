/** Display helpers. Quantities are stored in kg; show kg always and tonnes once ≥ 1,000 kg. */

const kgFmt = new Intl.NumberFormat("en-US", { maximumFractionDigits: 3 });
const tFmt = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 });
const pctFmt = new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 });

/** "499,500 kg" — up to 3 decimals, trailing zeros trimmed. */
export function formatKg(kg: number): string {
  return `${kgFmt.format(kg)} kg`;
}

export function formatTonnes(kg: number): string {
  return `${tFmt.format(kg / 1000)} t`;
}

/** "499,500 kg (499.5 t)" — tonnes appear only when |kg| ≥ 1,000. */
export function formatMass(kg: number): string {
  return Math.abs(kg) >= 1000 ? `${formatKg(kg)} (${formatTonnes(kg)})` : formatKg(kg);
}

export function formatPct(n: number): string {
  return `${pctFmt.format(n)}%`;
}

export function formatSigned(n: number, unit = "kg"): string {
  const sign = n > 0 ? "+" : n < 0 ? "−" : "";
  return `${sign}${kgFmt.format(Math.abs(n))} ${unit}`;
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** "2026-04" → "Apr 2026" */
export function formatMonth(ym: string): string {
  const [y, m] = ym.split("-");
  const idx = Number(m) - 1;
  return idx >= 0 && idx < 12 ? `${MONTHS[idx]} ${y}` : ym;
}

/** "2025-11-17" → "17 Nov 2025" (timezone-safe; no Date parsing). */
export function formatDate(iso: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!m) return iso;
  return `${Number(m[3])} ${MONTHS[Number(m[2]) - 1]} ${m[1]}`;
}

export function formatInr(n: number): string {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(n);
}

export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

export function shortHash(sha: string): string {
  return sha.slice(0, 10);
}
