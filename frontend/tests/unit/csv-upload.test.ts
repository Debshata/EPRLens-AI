import { describe, expect, it } from "vitest";
import { parseCsvText, summarizeTransactionCsv } from "@/lib/csv";
import { validateFileMeta } from "@/lib/upload-validation";

describe("csv", () => {
  it("handles quotes, escaped quotes and CRLF", () => {
    expect(parseCsvText('a,b\r\n"x, y","he said ""hi"""\r\n')).toEqual([["a", "b"], ["x, y", 'he said "hi"']]);
  });
  it("reports missing required columns", () => {
    const s = summarizeTransactionCsv("t.csv", "transaction_id,date\nT1,2026-03-01\n");
    expect(s.row_count).toBe(1);
    expect(s.missing_required_columns).toEqual(["company_id", "raw_quantity", "raw_unit"]);
  });
  it("strips a UTF-8 BOM", () => {
    expect(summarizeTransactionCsv("t.csv", "﻿transaction_id\nT1\n").columns).toEqual(["transaction_id"]);
  });
});

describe("upload validation", () => {
  it("rejects empty, wrong type and oversize with a next step", () => {
    const bad = [
      validateFileMeta("csv", { name: "a.csv", size: 0, type: "text/csv" }),
      validateFileMeta("invoice", { name: "a.docx", size: 10, type: "application/msword" }),
      validateFileMeta("image", { name: "a.png", size: 9 * 1024 * 1024, type: "image/png" }),
    ];
    for (const r of bad) {
      expect(r.ok).toBe(false);
      if (!r.ok) expect(r.next_step.length).toBeGreaterThan(5);
    }
  });
  it("accepts valid files", () => {
    expect(validateFileMeta("csv", { name: "a.csv", size: 10, type: "text/csv" }).ok).toBe(true);
    expect(validateFileMeta("invoice", { name: "a.pdf", size: 10, type: "application/pdf" }).ok).toBe(true);
    expect(validateFileMeta("image", { name: "a.JPG", size: 10, type: "image/jpeg" }).ok).toBe(true);
  });
});
