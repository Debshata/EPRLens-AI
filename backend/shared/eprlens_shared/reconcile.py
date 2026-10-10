"""Deterministic invoice-vs-record comparison (mirror of frontend/src/lib/reconcile.ts, rules-v1).

Identity: a PDF carries no internal ids, so lines are linked to records through the company's invoice index
(invoice number + date + vendor -> internal invoice id and per-line transaction ids), like an ERP link.
Invoice number alone is never enough to match.  Output matches the frontend `Finding` contract.
"""
from __future__ import annotations

from .units import power_of_ten_ratio, round6, to_kg

RULES_VERSION = "rules-v1"
TOLERANCES = {"qty_tolerance_kg": 0.01, "qty_tolerance_rel": 0.0005}


def exceeds_tolerance(a_kg: float, b_kg: float, tol: dict = TOLERANCES) -> bool:
    return abs(a_kg - b_kg) > max(tol["qty_tolerance_kg"], tol["qty_tolerance_rel"] * max(a_kg, b_kg))


def find_index_entry(index: dict, invoice: dict) -> dict | None:
    """Composite identity: invoice number + date + vendor name. Several invoices may share a number."""
    cands = [e for e in index.get("invoices", []) if e["invoice_number"] == invoice["invoice_number"]]
    if len(cands) == 1 and not invoice.get("invoice_date"):
        return cands[0]
    exact = [e for e in cands if e.get("invoice_date") == invoice.get("invoice_date") and e.get("vendor") == invoice["vendor"]["name"]]
    if len(exact) == 1:
        return exact[0]
    if len(cands) == 1:  # unique number, date/vendor differ → still unambiguous
        return cands[0]
    return None


def record_kg(row: dict) -> float | None:
    v = row.get("normalized_quantity_kg")
    if v not in (None, ""):
        try:
            return float(v)
        except ValueError:
            pass
    try:
        qty = float(row.get("raw_quantity", ""))
    except ValueError:
        return None
    res = to_kg(qty, row.get("raw_unit", ""))
    return res["kg"] if res["ok"] else None


def reconcile_invoice(invoice: dict, entry: dict | None, rows: list[dict]) -> list[dict]:
    if entry is None:
        return []
    by_txn = {r.get("transaction_id"): r for r in rows}
    out = []
    for line in invoice["lines"]:
        link = next((l for l in entry.get("lines", []) if l["line_no"] == line["line_no"]), None)
        rec = by_txn.get(link["transaction_id"]) if link else None
        if rec is None or line["normalized_quantity_kg"] is None or line["quantity"] is None:
            continue
        rec_kg = record_kg(rec)
        if rec_kg is None or not exceeds_tolerance(line["normalized_quantity_kg"], rec_kg):
            continue
        ratio = power_of_ten_ratio(rec_kg, line["normalized_quantity_kg"])
        unit_slip = ratio in (1000.0, 0.001)
        rules = ["UNIT_MISMATCH", "QTY_MATCH_TOL", "QTY_RATIO_POW10"] if unit_slip else (["QTY_MATCH_TOL", "QTY_RATIO_POW10"] if ratio else ["QTY_MATCH_TOL"])
        qty_txt = f"{line['quantity']:g}"
        out.append(
            {
                "finding_id": f"live-{invoice['document_id']}-l{line['line_no']}",
                "type": "unit_conversion_error" if unit_slip else ("magnitude_error" if ratio else "quantity_mismatch"),
                "title": f"Invoice {qty_txt} {line['unit']} vs recorded {rec.get('raw_quantity')} {rec.get('raw_unit')}",
                "severity": "high" if (unit_slip or ratio) else "medium",
                "review_state": "open",
                "company_id": rec.get("company_id", ""),
                "invoice_id": entry.get("invoice_id"),
                "invoice_number": invoice["invoice_number"],
                "document_id": invoice["document_id"],
                "counterparty": invoice["vendor"]["name"],
                "material": line.get("material"),
                "component": line["description"],
                "expected": {"label": "Invoice (document)", "raw_value": line["quantity"], "raw_unit": line["unit"], "value_kg": line["normalized_quantity_kg"], "source_ref": line["line_reference"]},
                "observed": {"label": "Recorded (CSV/transaction)", "raw_value": float(rec["raw_quantity"]), "raw_unit": rec["raw_unit"], "value_kg": rec_kg, "source_ref": rec["transaction_id"]},
                "difference_kg": round6(abs(rec_kg - line["normalized_quantity_kg"])),
                "rule_ids": rules,
                "rule_version": RULES_VERSION,
                "detected_by": ["rule"],
                "model_score": None,
                "explanation": (
                    f"Invoice line {line['line_no']} and the linked record differ by a factor of {'1,000' if ratio == 1000.0 else '1/1,000'} — typical of a tonne/kg or decimal slip. A reviewer must confirm which value is right."
                    if unit_slip
                    else f"Invoice line {line['line_no']} and the linked record differ by more than the allowed tolerance."
                ),
                "legal_determination": False,
            }
        )
    return out
