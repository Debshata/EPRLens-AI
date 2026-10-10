"""CSV parsing/validation (mirror of frontend/src/lib/csv.ts)."""
from __future__ import annotations

REQUIRED_TRANSACTION_COLUMNS = ["transaction_id", "company_id", "date", "raw_quantity", "raw_unit"]


def parse_csv_text(text: str) -> list[list[str]]:
    rows, row, cell, in_q, i = [], [], "", False, 0
    while i < len(text):
        ch = text[i]
        if in_q:
            if ch == '"':
                if i + 1 < len(text) and text[i + 1] == '"':
                    cell += '"'
                    i += 1
                else:
                    in_q = False
            else:
                cell += ch
        elif ch == '"':
            in_q = True
        elif ch == ",":
            row.append(cell)
            cell = ""
        elif ch in "\r\n":
            if ch == "\r" and i + 1 < len(text) and text[i + 1] == "\n":
                i += 1
            row.append(cell)
            cell = ""
            if any(c != "" for c in row):
                rows.append(row)
            row = []
        else:
            cell += ch
        i += 1
    row.append(cell)
    if any(c != "" for c in row):
        rows.append(row)
    return rows


def summarize_transaction_csv(file_name: str, text: str, max_rows: int = 2000) -> dict:
    table = parse_csv_text(text.lstrip("﻿"))
    header = [h.strip() for h in (table[0] if table else [])]
    rows = []
    for cells in table[1:]:
        rows.append({h: (cells[i].strip() if i < len(cells) else "") for i, h in enumerate(header)})
    return {
        "file_name": file_name,
        "row_count": len(rows),
        "columns": header,
        "missing_required_columns": [c for c in REQUIRED_TRANSACTION_COLUMNS if c not in header],
        "rows": rows[:max_rows],
    }
