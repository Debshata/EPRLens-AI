import type { CsvSummary } from "./contracts";

export const REQUIRED_TRANSACTION_COLUMNS = ["transaction_id", "company_id", "date", "raw_quantity", "raw_unit"] as const;

/** Minimal RFC-4180 style parser (quotes, escaped quotes, CRLF). Enough for transaction CSVs. */
export function parseCsvText(text: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let cell = "";
  let inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (inQuotes) {
      if (ch === '"') {
        if (text[i + 1] === '"') {
          cell += '"';
          i++;
        } else inQuotes = false;
      } else cell += ch;
    } else if (ch === '"') inQuotes = true;
    else if (ch === ",") {
      row.push(cell);
      cell = "";
    } else if (ch === "\n" || ch === "\r") {
      if (ch === "\r" && text[i + 1] === "\n") i++;
      row.push(cell);
      cell = "";
      if (row.some((c) => c !== "")) rows.push(row);
      row = [];
    } else cell += ch;
  }
  row.push(cell);
  if (row.some((c) => c !== "")) rows.push(row);
  return rows;
}

export function summarizeTransactionCsv(fileName: string, text: string): CsvSummary {
  const table = parseCsvText(text.replace(/^﻿/, ""));
  const header = (table[0] ?? []).map((h) => h.trim());
  const rows = table.slice(1).map((cells) => {
    const rec: Record<string, string> = {};
    header.forEach((h, i) => (rec[h] = (cells[i] ?? "").trim()));
    return rec;
  });
  return {
    file_name: fileName,
    row_count: rows.length,
    columns: header,
    missing_required_columns: REQUIRED_TRANSACTION_COLUMNS.filter((c) => !header.includes(c)),
    rows,
  };
}
