/**
 * Deterministic invoice-vs-record comparison (mirrors the `reconcile` Lambda contract so the mock adapter
 * can run the real logic against bundled sample files).
 *
 * Identity rule: lines are matched on transaction_id, else on invoice_id + component_id.
 * Invoice number alone is NEVER used to match or de-duplicate (the handbook allows several invoices
 * to share a number).
 */
import type { Finding, Invoice, InvoiceLine } from "./contracts";
import { powerOfTenRatio, round6, toKg } from "./units";

export interface RecordRow {
  transaction_id: string;
  invoice_id?: string | null;
  component_id?: string | null;
  raw_quantity: string;
  raw_unit: string;
  normalized_quantity_kg?: string | null;
  [key: string]: string | null | undefined;
}

export interface Tolerances {
  qty_tolerance_kg: number;
  qty_tolerance_rel: number;
}

export const DEFAULT_TOLERANCES: Tolerances = { qty_tolerance_kg: 0.01, qty_tolerance_rel: 0.0005 };
export const RULES_VERSION = "rules-v1";

export function matchRecord(line: InvoiceLine, invoiceId: string | undefined, records: RecordRow[]): RecordRow | null {
  if (line.transaction_id) {
    const byTxn = records.find((r) => r.transaction_id === line.transaction_id);
    if (byTxn) return byTxn;
  }
  if (invoiceId && line.component_id) {
    const byComposite = records.filter((r) => r.invoice_id === invoiceId && r.component_id === line.component_id);
    if (byComposite.length === 1) return byComposite[0];
  }
  return null;
}

export function recordKg(r: RecordRow, weightPerUnitG?: number | null): number | null {
  if (r.normalized_quantity_kg != null && r.normalized_quantity_kg !== "") {
    const n = Number(r.normalized_quantity_kg);
    if (Number.isFinite(n)) return n;
  }
  const res = toKg(Number(r.raw_quantity), r.raw_unit, { weightPerUnitG });
  return res.ok ? res.kg : null;
}

export function exceedsTolerance(aKg: number, bKg: number, tol: Tolerances = DEFAULT_TOLERANCES): boolean {
  const diff = Math.abs(aKg - bKg);
  return diff > Math.max(tol.qty_tolerance_kg, tol.qty_tolerance_rel * Math.max(aKg, bKg));
}

/** Compare every invoice line with its record; returns findings (empty = all lines agree). */
export function reconcileInvoice(invoice: Invoice, records: RecordRow[], tol: Tolerances = DEFAULT_TOLERANCES): Finding[] {
  const findings: Finding[] = [];
  for (const line of invoice.lines) {
    const rec = matchRecord(line, invoice.invoice_id, records);
    if (!rec || line.normalized_quantity_kg == null || line.quantity == null) continue;
    const recKg = recordKg(rec);
    if (recKg == null) continue;
    if (!exceedsTolerance(line.normalized_quantity_kg, recKg, tol)) continue;
    const ratio = powerOfTenRatio(recKg, line.normalized_quantity_kg);
    const unitSlip = ratio === 1000 || ratio === 0.001;
    const rules = unitSlip ? ["UNIT_MISMATCH", "QTY_MATCH_TOL", "QTY_RATIO_POW10"] : ratio ? ["QTY_MATCH_TOL", "QTY_RATIO_POW10"] : ["QTY_MATCH_TOL"];
    findings.push({
      finding_id: `local-${invoice.document_id}-l${line.line_no}`,
      type: unitSlip ? "unit_conversion_error" : ratio ? "magnitude_error" : "quantity_mismatch",
      title: `Invoice ${line.quantity} ${line.unit} vs recorded ${rec.raw_quantity} ${rec.raw_unit}`,
      severity: unitSlip || ratio ? "high" : "medium",
      review_state: "open",
      company_id: String(rec.company_id ?? ""),
      invoice_id: invoice.invoice_id ?? null,
      invoice_number: invoice.invoice_number,
      document_id: invoice.document_id,
      counterparty: invoice.vendor.name,
      material: line.material,
      component: line.description,
      expected: { label: "Invoice (document)", raw_value: line.quantity, raw_unit: line.unit, value_kg: line.normalized_quantity_kg, source_ref: line.line_reference },
      observed: { label: "Recorded (CSV/transaction)", raw_value: Number(rec.raw_quantity), raw_unit: rec.raw_unit, value_kg: recKg, source_ref: rec.transaction_id },
      difference_kg: round6(Math.abs(recKg - line.normalized_quantity_kg)),
      rule_ids: rules,
      rule_version: RULES_VERSION,
      detected_by: ["rule"],
      model_score: null,
      explanation: unitSlip
        ? `Invoice line ${line.line_no} and the linked record differ by a factor of ${ratio === 1000 ? "1,000" : "1/1,000"} — typical of a tonne/kg or decimal slip. A reviewer must confirm which value is right.`
        : `Invoice line ${line.line_no} and the linked record differ by more than the allowed tolerance.`,
      legal_determination: false,
    });
  }
  return findings;
}
