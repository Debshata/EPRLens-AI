import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import invoiceFixture from "@/lib/mocks/invoice.json";
import reconciliation from "@/lib/mocks/reconciliation.json";
import { InvoiceFixture, ReconciliationResponse } from "@/lib/contracts";
import { summarizeTransactionCsv } from "@/lib/csv";
import { exceedsTolerance, matchRecord, reconcileInvoice, type RecordRow } from "@/lib/reconcile";

const invoice = InvoiceFixture.parse(invoiceFixture).invoice;
const csv = summarizeTransactionCsv("transactions_demo.csv", readFileSync(join(__dirname, "../../public/samples/transactions_demo.csv"), "utf8"));
const records = csv.rows as unknown as RecordRow[];

describe("reconcileInvoice — demo mismatch", () => {
  it("finds the 0.5 MT vs 500 MT mismatch: 500 kg vs 500,000 kg, difference 499,500 kg", () => {
    const f = reconcileInvoice(invoice, records);
    expect(f).toHaveLength(1);
    expect(f[0].expected).toMatchObject({ raw_value: 0.5, raw_unit: "MT", value_kg: 500 });
    expect(f[0].observed).toMatchObject({ raw_value: 500, raw_unit: "MT", value_kg: 500000, source_ref: "TXN_00121740" });
    expect(f[0].difference_kg).toBe(499500);
    expect(f[0].type).toBe("unit_conversion_error");
    expect(f[0].rule_ids).toContain("UNIT_MISMATCH");
    expect(f[0].legal_determination).toBe(false);
  });

  it("agrees with the bundled reconciliation fixture for the demo finding", () => {
    const fixture = ReconciliationResponse.parse(reconciliation).findings.find((x) => x.invoice_id === "INV_00017685")!;
    const local = reconcileInvoice(invoice, records)[0];
    expect(local.difference_kg).toBe(fixture.difference_kg);
    expect(local.expected.value_kg).toBe(fixture.expected.value_kg);
    expect(local.observed.value_kg).toBe(fixture.observed.value_kg);
  });

  it("raises nothing when the record agrees within tolerance", () => {
    const ok = records.map((r) => (r.transaction_id === "TXN_00121740" ? { ...r, raw_quantity: "0.5", normalized_quantity_kg: "500" } : r));
    expect(reconcileInvoice(invoice, ok)).toEqual([]);
  });
});

describe("matching identity", () => {
  it("never matches on invoice number alone", () => {
    const line = { ...invoice.lines[0], transaction_id: null, component_id: null };
    const sameNumberOtherInvoice: RecordRow[] = [{ transaction_id: "T1", invoice_id: "INV_OTHER", component_id: "X", raw_quantity: "1", raw_unit: "kg", invoice_number: invoice.invoice_number }];
    expect(matchRecord(line, invoice.invoice_id, sameNumberOtherInvoice)).toBeNull();
  });
  it("falls back to invoice id + component only when unambiguous", () => {
    const line = { ...invoice.lines[0], transaction_id: null };
    const a: RecordRow = { transaction_id: "A", invoice_id: invoice.invoice_id, component_id: line.component_id, raw_quantity: "1", raw_unit: "kg" };
    expect(matchRecord(line, invoice.invoice_id, [a])).toBe(a);
    expect(matchRecord(line, invoice.invoice_id, [a, { ...a, transaction_id: "B" }])).toBeNull();
  });
});

describe("tolerance", () => {
  it("0.05% or 0.01 kg", () => {
    expect(exceedsTolerance(1000, 1000.4)).toBe(false);
    expect(exceedsTolerance(1000, 1001)).toBe(true);
    expect(exceedsTolerance(0.005, 0.0)).toBe(false);
  });
});
