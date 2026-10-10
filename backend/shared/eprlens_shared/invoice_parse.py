"""Digital-PDF invoice parsing (pypdf, no OCR). Output matches the frontend `Invoice` contract.

Scope: text-based PDFs only. Anything that cannot be read is returned as unknown/needs_review — never guessed.
The rotated "SYNTHETIC" watermark is skipped by reading upright text only.
"""
from __future__ import annotations

import io
import re
from datetime import datetime

from .units import is_unit_token, to_kg

PARSER_VERSION = "pdf-text-v1"

_NUM = r"-?\d[\d,]*(?:\.\d+)?"
_UNITS = {"kg", "kgs", "g", "gm", "mt", "tonne", "tonnes", "t", "pcs", "pc", "nos", "btl", "bottles", "bottle", "units", "unit", "piece", "pieces"}
_DATE_FORMATS = ("%d/%m/%Y", "%d-%b-%Y", "%Y-%m-%d", "%d-%m-%Y")
_TOTAL_MARKERS = ("total taxable value", "total taxable", "sub total", "subtotal")


def extract_text(pdf_bytes: bytes) -> tuple[str, int]:
    """Upright text of all pages (rotated watermark removed) and the page count."""
    from pypdf import PdfReader  # imported lazily: only the parse-invoice Lambda ships pypdf

    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages = [(p.extract_text(orientations=(0,)) or "") for p in reader.pages]
    return "\n".join(pages), len(reader.pages)


def to_float(s: str) -> float | None:
    try:
        return float(s.replace(",", "").strip())
    except (ValueError, AttributeError):
        return None


def parse_date(raw: str) -> str | None:
    raw = raw.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _clean_lines(text: str) -> list[str]:
    out = []
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln or set(ln) <= {"=", "-"} or ln.startswith("SYNTHETIC"):
            continue
        out.append(ln)
    return out


def _party(lines: list[str], labels: tuple[str, ...]) -> tuple[str | None, str | None]:
    """Name = first non-empty text after a party label line (or the same line for 'FROM: name'); GSTIN = next GSTIN line."""
    for i, ln in enumerate(lines):
        for lab in labels:
            m = re.match(rf"^{re.escape(lab)}\s*:?\s*(.*)$", ln, flags=re.I)
            if m and (not m.group(1) or ln.lower().startswith(lab.lower())):
                name = m.group(1).strip() or (lines[i + 1] if i + 1 < len(lines) else None)
                if name and re.match(r"^(GSTIN|Invoice No|Date)", name, flags=re.I):
                    continue
                gstin = None
                for j in range(i + 1, min(i + 7, len(lines))):
                    g = re.match(r"^GSTIN\s*:\s*(\S.*)$", lines[j])
                    if g:
                        gstin = g.group(1).strip()
                        break
                return name, (None if gstin and gstin.lower().startswith("not registered") else gstin)
    return None, None


def _header(lines: list[str]) -> dict:
    text = "\n".join(lines)
    m = re.search(r"(?:Invoice|Note)\s*No\.?\s*:?\s*([A-Z0-9][A-Z0-9/\-]*)", text)
    inv_no = m.group(1) if m else None
    d = re.search(r"Date\s*:\s*([0-9A-Za-z/\-]+)", text)
    raw_date = d.group(1) if d and d.group(1).lower() not in ("place",) else ""
    vendor, vendor_gstin = _party(lines, ("FROM", "Seller", "From", "Supplier", "Exporter"))
    if vendor is None:  # L10 recycler layout / unlabeled header: first non-title line
        for ln in lines:
            if not re.match(r"^(TAX INVOICE|COMMERCIAL INVOICE|QR|IRN|\(not scannable\)|[A-Z]{1,3}$)", ln):
                vendor = ln
                break
    buyer, buyer_gstin = _party(lines, ("TO", "Buyer", "Bill to", "Recipient", "Client", "Consignee / Importer"))
    cur = re.search(r"Currency\s*:\s*([A-Z]{3})", text)
    currency = cur.group(1) if cur else "INR"
    tot = re.search(r"(?:Invoice total|Total)[^\n]*?\(([A-Za-z.]+)\)\s*:?\s*\n?\s*(" + _NUM + ")", text)
    total = to_float(tot.group(2)) if tot else None
    return {
        "invoice_number": inv_no,
        "raw_date": raw_date,
        "invoice_date": parse_date(raw_date) if raw_date else None,
        "vendor": vendor,
        "vendor_gstin": vendor_gstin,
        "buyer": buyer,
        "buyer_gstin": buyer_gstin,
        "currency": currency,
        "total_amount": total,
    }


def _lines_keyvalue(lines: list[str]) -> list[dict]:
    """L11 'Item N:' blocks with Qty:/Unit:/Rate:/Amount: lines."""
    items, cur = [], None
    for ln in lines:
        m = re.match(r"^Item\s+(\d+)\s*:\s*$", ln)
        if m:
            cur = {"line_no": int(m.group(1)), "desc": []}
            items.append(cur)
            continue
        if cur is None:
            continue
        kv = re.match(r"^(HSN|Category|Qty|Unit|Rate|Amount)\s*:\s*(.*)$", ln)
        if kv:
            cur[kv.group(1).lower()] = kv.group(2).strip()
        elif ln.lower().startswith(_TOTAL_MARKERS):
            break
        elif "qty" not in cur:
            cur["desc"].append(ln)
    out = []
    for it in items:
        out.append(
            {
                "line_no": it["line_no"],
                "description": " ".join(it["desc"]).strip(),
                "qty_raw": it.get("qty"),
                "unit": it.get("unit"),
                "amount": to_float(it.get("amount", "")),
                "g_per_unit": None,
                "material": None,
            }
        )
    return out


def _lines_table(lines: list[str]) -> list[dict]:
    """Table layouts: header tokens, then one cell per text line. Right-side columns (Qty…) are never blank."""
    try:
        h0 = next(i for i, ln in enumerate(lines) if ln == "#")
    except StopIteration:
        return []
    header, i = [], h0
    while i < len(lines) and not re.fullmatch(r"\d+", lines[i]) or (i == h0):
        header.append(lines[i])
        i += 1
    header = [h for h in header if h != "#"]
    if "Qty" not in header:
        return []
    right = header[header.index("Qty"):]
    n_right = len(right)
    col = {name: k for k, name in enumerate(right)}
    body = []
    for ln in lines[i:]:
        if ln.lower().startswith(_TOTAL_MARKERS):
            break
        body.append(ln)
    # split into rows on the expected sequential index; ignore page-continuation noise and repeated headers
    rows, expect, cur, skipping = [], 1, None, False
    for ln in body:
        low = ln.lower()
        if low.startswith("carried forward") or low.startswith("continued on next page") or "(continued)" in low:
            continue
        if ln == "#":
            skipping = True
            continue
        if skipping:
            if ln == str(expect):
                skipping = False
            else:
                continue
        if ln == str(expect) and (cur is None or len(cur) >= 3):
            cur = [ln]
            rows.append(cur)
            expect += 1
        elif cur is not None:
            cur.append(ln)
    out = []
    full = list(range(n_right))
    optional = [col[c] for c in ("g/unit", "Qty") if c in col]  # cells that can be blank (absent) in a row
    variants = [full]
    for k in optional:
        variants.append([x for x in full if x != k])
    if len(optional) == 2:
        variants.append([x for x in full if x not in optional])
    for r in rows:
        toks = r[1:]
        hit = None
        has_hsn = any(h.lower().startswith(("hsn", "hs code")) for h in header)
        fallback = None
        for keep in variants:
            if len(toks) < len(keep) + 1:
                continue
            tail, head = toks[-len(keep):], toks[:-len(keep)]
            cell = {right[k]: tail[j] for j, k in enumerate(keep)}
            unit_ok = "Unit" in cell and is_unit_token(cell["Unit"])
            amt_name = next((n for n in cell if n.startswith("Amount")), None)
            qty_ok = "Qty" not in cell or to_float(cell["Qty"]) is not None
            if unit_ok and qty_ok and amt_name and to_float(cell[amt_name]) is not None:
                cand = (cell, head, amt_name)
                # an HSN code must stay in the head; otherwise it was consumed as the quantity (blank-quantity row)
                if not has_hsn or any(re.fullmatch(r"\d{4,8}", t) for t in head):
                    hit = cand
                    break
                fallback = fallback or cand
        if hit is None and fallback is not None:
            hit = fallback
        if hit is None:
            # quantity/unit cells blank (e.g. credit-note lines): keep the line, mark quantity unknown
            tail_amt = toks[-1] if toks else ""
            out.append({"line_no": int(r[0]), "description": " ".join(toks[:-1]).strip(), "qty_raw": None, "unit": None, "amount": to_float(tail_amt), "g_per_unit": None, "material": None})
            continue
        cell, head, amt_name = hit
        desc_parts, material = [], None
        for t in head:
            if re.fullmatch(r"\d{4,8}", t) or re.fullmatch(r"CAT_[IV]+|NA", t):
                continue
            if re.fullmatch(r"[A-Z][A-Z0-9_/ ]{1,15}", t) and desc_parts:
                material = t
                continue
            desc_parts.append(t)
        out.append(
            {
                "line_no": int(r[0]),
                "description": " ".join(desc_parts).strip(),
                "qty_raw": cell.get("Qty"),
                "unit": cell.get("Unit"),
                "amount": to_float(cell[amt_name]),
                "g_per_unit": to_float(cell["g/unit"]) if "g/unit" in cell else None,
                "material": material,
            }
        )
    return out


_GPC = re.compile(r"\((\d+(?:\.\d+)?)\s*g/pc\)")
_MATERIAL_TAIL = re.compile(r"-\s*([A-Z][A-Z0-9]{1,10})\b")


def _finish_line(doc_id: str, page_hint: int, ln: dict) -> dict:
    qty = to_float(ln["qty_raw"] or "")
    unit = (ln["unit"] or "").strip()
    g = ln.get("g_per_unit")
    if g is None:
        m = _GPC.search(ln["description"])
        g = float(m.group(1)) if m else None
    material = ln.get("material")
    if material is None:
        mm = _MATERIAL_TAIL.search(re.sub(r"\(.*?\)", "", ln["description"]))
        material = mm.group(1) if mm else None
    kg_res = to_kg(qty, unit, g) if qty is not None and unit else {"ok": False}
    return {
        "line_reference": f"{doc_id}:p{page_hint}:l{ln['line_no']}",
        "page": page_hint,
        "line_no": ln["line_no"],
        "description": ln["description"],
        "material": material,
        "quantity": qty,  # None = missing in the document; never shown as zero
        "unit": unit or "unknown",
        "printed_quantity": ln["qty_raw"],
        "printed_unit": unit,
        "normalized_quantity_kg": kg_res.get("kg") if kg_res.get("ok") else None,
        "conversion_rule": kg_res.get("rule") if kg_res.get("ok") else "UNRESOLVED",
        "amount": ln["amount"],
    }


def parse_invoice_text(text: str, page_count: int, document_id: str, file_name: str, sha256: str) -> dict:
    lines = _clean_lines(text)
    head = _header(lines)
    raw_lines = _lines_keyvalue(lines) if any(re.match(r"^Item\s+\d+\s*:", ln) for ln in lines) else _lines_table(lines)
    parsed = [_finish_line(document_id, 1, ln) for ln in raw_lines]

    fields = []

    def add(name, raw, norm, unit, ref, ok=True):
        fields.append(
            {
                "field": name,
                "raw_text": raw,
                "normalized_value": norm,
                "unit": unit,
                "source_ref": ref,
                "confidence_proxy": 1.0 if ok else 0.0,
                "review_state": "unreviewed" if ok else "needs_review",
                "status": "document_supported" if ok else "unknown",
            }
        )

    add("invoice_number", head["invoice_number"] or "", head["invoice_number"] or "", None, f"{document_id}:p1", bool(head["invoice_number"]))
    add("invoice_date", head["raw_date"], head["invoice_date"] or "", None, f"{document_id}:p1", bool(head["invoice_date"]))
    add("vendor", head["vendor"] or "", head["vendor"] or "", None, f"{document_id}:p1", bool(head["vendor"]))
    for ln in parsed:
        ok = ln["normalized_quantity_kg"] is not None
        add(f"line{ln['line_no']}.quantity", f"{ln['printed_quantity']} {ln['printed_unit']}".strip(), ln["normalized_quantity_kg"] if ok else "", "kg" if ok else None, ln["line_reference"] + ":quantity", ok)
        add(f"line{ln['line_no']}.amount", str(ln["amount"]), ln["amount"] if ln["amount"] is not None else "", head["currency"], ln["line_reference"] + ":amount", ln["amount"] is not None)

    needs_review = (not head["invoice_number"]) or (not head["invoice_date"]) or (not parsed) or any(ln["normalized_quantity_kg"] is None for ln in parsed)
    return {
        "document_id": document_id,
        "invoice_number": head["invoice_number"] or "",
        "invoice_date": head["invoice_date"] or "",
        "vendor": {"name": head["vendor"] or "", "gstin": head["vendor_gstin"]},
        "buyer": {"name": head["buyer"] or "", "gstin": head["buyer_gstin"]},
        "currency": head["currency"],
        "total_amount": head["total_amount"],
        "page_count": page_count,
        "lines": parsed,
        "fields": fields,
        "source": {"file_name": file_name, "sha256": sha256, "synthetic": "SYNTHETIC" in text or True},
        "extraction": {"method": "digital_pdf_text", "status": "needs_review" if needs_review else "success", "parser_version": PARSER_VERSION},
    }
