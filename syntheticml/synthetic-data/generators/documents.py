"""Select exactly 1,000 invoices, build one document model per invoice, render the
PDF and write the matching ground-truth JSON from the SAME model.
SYNTHETIC — EPRLens Demo."""
import hashlib
import json
from datetime import date
from pathlib import Path

from . import geo
from . import identifiers as ids
from .pdf_render import (LAYOUTS, PRINTS_CATEGORY, PRINTS_HSN, Pdf, capacity)

TYPE_CODE = {"PKG_PURCHASE": "IT01", "FG_SALES": "IT02", "RECYCLER_PROCESSING": "IT03", "WASTE_PROCUREMENT": "IT04",
             "CREDIT_NOTE": "IT05", "RETURN": "IT06", "IMPORT_COMMERCIAL": "IT07", "PKG_COMPONENT": "IT08",
             "MULTI_MATERIAL": "IT09", "RECYCLING_SERVICE": "IT10"}
CODE_TYPE = {v: k for k, v in TYPE_CODE.items()}
TYPE_LAYOUTS = {
    "PKG_PURCHASE": ["L01", "L02", "L04", "L06", "L07", "L09", "L11"],
    "FG_SALES": ["L01", "L02", "L05", "L06", "L08"],
    "PKG_COMPONENT": ["L01", "L03", "L07", "L09"],
    "MULTI_MATERIAL": ["L02", "L03", "L05", "L09"],
    "RECYCLER_PROCESSING": ["L10"],
    "RECYCLING_SERVICE": ["L07", "L10", "L11"],
    "WASTE_PROCUREMENT": ["L10", "L11", "L04"],
    "CREDIT_NOTE": ["L09", "L11", "L04"],
    "RETURN": ["L04", "L08", "L11"],
    "IMPORT_COMMERCIAL": ["L12"],
}
TITLES = {"PKG_PURCHASE": "TAX INVOICE", "FG_SALES": "TAX INVOICE", "PKG_COMPONENT": "TAX INVOICE",
          "MULTI_MATERIAL": "TAX INVOICE", "RECYCLER_PROCESSING": "TAX INVOICE - PROCESSING SERVICES",
          "RECYCLING_SERVICE": "TAX INVOICE - RECYCLING SERVICES", "WASTE_PROCUREMENT": "TAX INVOICE - SCRAP SALE",
          "CREDIT_NOTE": "CREDIT NOTE", "RETURN": "DEBIT NOTE - GOODS RETURNED", "IMPORT_COMMERCIAL": "COMMERCIAL INVOICE"}
UNIT_SPELL = {"kg": ["kg", "Kg", "KGS"], "MT": ["MT", "M.T.", "Tonne"], "pcs": ["pcs", "Nos", "PCS"],
              "bottles": ["bottles", "Btl"], "bags": ["bags", "Bags"], "g": ["g", "gm"], None: ["Job"]}
UNIT_DP = {"kg": 2, "MT": 3, "g": 0, "pcs": 0, "bottles": 0, "bags": 0, None: 0}


# ================================================================ formatting
def group_digits(intpart: str, style: str):
    if style == "plain" or len(intpart) <= 3:
        return intpart
    if style == "western":
        out = []
        while len(intpart) > 3:
            out.insert(0, intpart[-3:])
            intpart = intpart[:-3]
        return ",".join([intpart] + out)
    head, tail = intpart[:-3], intpart[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return ",".join(groups + [tail])


def fmt(x, dp, style):
    if x is None:
        return ""
    neg = x < 0
    s = f"{abs(x):.{dp}f}"
    whole, _, frac = s.partition(".")
    out = group_digits(whole, style) + (("." + frac) if dp else "")
    return ("-" if neg else "") + out


def fmt_date(iso, style):
    if not iso:
        return ""
    d = date.fromisoformat(iso)
    return {"slash": d.strftime("%d/%m/%Y"), "dash": d.strftime("%d-%m-%Y"), "mon": d.strftime("%d-%b-%Y"),
            "iso": iso}[style]


ONES = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve",
        "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _words_99(n):
    return ONES[n] if n < 20 else (TENS[n // 10] + ("-" + ONES[n % 10] if n % 10 else ""))


def _words_999(n):
    h, r = divmod(n, 100)
    parts = []
    if h:
        parts.append(ONES[h] + " Hundred")
    if r:
        parts.append(_words_99(r))
    return " ".join(parts)


def indian_words(amount):
    rupees = int(amount)
    paise = int(round((amount - rupees) * 100))
    if paise == 100:
        rupees, paise = rupees + 1, 0
    parts = []
    crore, rest = divmod(rupees, 10_000_000)
    lakh, rest = divmod(rest, 100_000)
    thousand, rest = divmod(rest, 1000)
    if crore:
        parts.append(_words_999(crore) if crore < 1000 else indian_words(crore).replace("Rupees ", "").replace(" Only", ""))
        parts[-1] += " Crore"
    if lakh:
        parts.append(_words_99(lakh) + " Lakh")
    if thousand:
        parts.append(_words_99(thousand) + " Thousand")
    if rest:
        parts.append(_words_999(rest))
    text = "Rupees " + (" ".join(parts) if parts else "Zero")
    if paise:
        text += f" and {_words_99(paise)} Paise"
    return text + " Only"


# ================================================================ selection
class Selector:
    def __init__(self, w, reg, inj):
        self.w, self.reg, self.inj = w, reg, inj
        self.chosen = {}  # invoice_id -> dict(stratum, case, constraint)
        self.anoms = {}
        for g in inj.gt:
            if g["invoice_id"] and g["is_anomaly"]:
                self.anoms.setdefault(g["invoice_id"], []).append(g)

    def clean_ok(self, iid):
        inv = self.reg.invoices.get(iid)
        return (inv is not None and inv["status"] == "issued" and not inv["is_anomaly"] and iid not in self.inj.used_inv
                and iid not in self.inj.touched and iid not in self.inj.shared and iid not in self.inj.twins
                and self.reg.lines.get(iid) and iid not in self.chosen)

    def pick(self, key, cands, k):
        cands = sorted(set(c for c in cands if c not in self.chosen))
        r = self.w.r("pdf_pick", key)
        return r.sample(cands, max(0, min(k, len(cands))))

    def add(self, iids, stratum, case, constraint=None, extra=None):
        for i in iids:
            self.chosen[i] = {"stratum": stratum, "case": case, "constraint": constraint, **(extra or {})}

    def run(self):
        pc = self.w.cfg["pdfs"]
        reg = self.reg
        # ---------------- targeted anomaly
        by_type = {}
        for iid, gs in self.anoms.items():
            if reg.lines.get(iid):
                by_type.setdefault(gs[0]["anomaly_type"], []).append(iid)
        for atype, k in pc["targeted_anomaly_by_type"].items():
            cands = by_type.get(atype, [])
            if atype == "AN05":
                dups = self.pick("AN05", cands, k // 2)
                self.add(dups, "targeted_anomaly", "AN05")
                origs = [reg.invoices[d]["_duplicate_of"] for d in dups]
                for o, dpl in zip(origs, dups):
                    self.chosen[o] = {"stratum": "targeted_anomaly", "case": "AN05_original", "constraint": None,
                                      "paired": dpl}
                    self.chosen[dpl]["paired"] = o
                continue
            if atype == "AN08":
                demo = [i for i in cands if any((g.get("note") or "").startswith("DEMO") for g in self.anoms[i])]
                mt = [i for i in cands if any(g.get("note") == "mt_magnitude" for g in self.anoms[i])]
                imp = [i for i in cands if reg.invoices[i]["invoice_type"] == "IMPORT_COMMERCIAL"]
                self.add(demo, "targeted_anomaly", "AN08")
                n_mt = int(round(k / 3))  # 10 of 30 in the full run: "0.5 MT printed vs 500 MT recorded"
                self.add(self.pick("AN08mt", mt, n_mt - len(demo)), "targeted_anomaly", "AN08")
                self.add(self.pick("AN08imp", imp, (k - n_mt) // 2), "targeted_anomaly", "AN08")
                self.add(self.pick("AN08rest", cands, k - sum(1 for v in self.chosen.values() if v["case"] == "AN08")),
                         "targeted_anomaly", "AN08")
                continue
            if atype in ("AN04",):
                cands = [i for i in cands if reg.invoices[i]["invoice_type"] != "IMPORT_COMMERCIAL"]
                self.add(self.pick(atype, cands, k), "targeted_anomaly", atype, constraint="category")
                continue
            if atype == "AN06":
                ok = [i for i in cands if self.anoms[i][0]["field"] != "plastic_category"]
                cat = [i for i in cands if self.anoms[i][0]["field"] == "plastic_category"
                       and reg.invoices[i]["invoice_type"] != "IMPORT_COMMERCIAL"]
                n_cat = min(len(cat), k // 5)
                self.add(self.pick("AN06cat", cat, n_cat), "targeted_anomaly", atype, constraint="category")
                self.add(self.pick("AN06", ok, k - n_cat), "targeted_anomaly", atype)
                continue
            imports_first = atype in ("AN01", "AN02", "AN07")
            if imports_first:
                imp = [i for i in cands if reg.invoices[i]["invoice_type"] == "IMPORT_COMMERCIAL"]
                self.add(self.pick(atype + "imp", imp, k // 3), "targeted_anomaly", atype)
                k -= sum(1 for v in self.chosen.values() if v["case"] == atype)
            self.add(self.pick(atype, cands, k), "targeted_anomaly", atype)
        # ---------------- legitimate but difficult
        hard = pc["targeted_legit_hard"]
        groups = [g for g in self.inj.shared_groups if len(g) >= 3]
        r = self.w.r("pdf_pick", "AN17")
        for g in r.sample(sorted(groups), min(hard["shared_invoice_number"] // 3, len(groups))):
            self.add(g[:3], "targeted_legit_hard", "AN17_shared_number")
        clean = [i for i in reg.invoices if self.clean_ok(i)]
        T = lambda i: reg.invoices[i]["invoice_type"]  # noqa: E731
        L = lambda i: reg.lines[i]  # noqa: E731
        self.add(self.pick("multipage", [i for i in clean if T(i) in ("FG_SALES", "MULTI_MATERIAL") and len(L(i)) >= 7],
                           hard["multi_page"]), "targeted_legit_hard", "multi_page", constraint="L05")
        peak = {("Beverages", "04"), ("Beverages", "05"), ("Electronics", "10"), ("Electronics", "11"),
                ("E-commerce", "10"), ("Appliances", "04")}
        seas = [i for i in clean if T(i) == "FG_SALES"
                and (self.w.company[reg.invoices[i]["company_id"]]["industry"], reg.invoices[i]["invoice_date"][5:7]) in peak]
        seas = sorted(seas, key=lambda i: -max(l["raw_quantity"] for l in L(i)))[: hard["large_seasonal"] * 4]
        self.add(self.pick("seasonal", seas, hard["large_seasonal"]), "targeted_legit_hard", "large_seasonal")
        clean = [i for i in clean if i not in self.chosen]
        self.add(self.pick("gpcs", [i for i in clean if T(i) in ("PKG_PURCHASE", "PKG_COMPONENT")
                                    and any(l["raw_unit"] == "pcs" for l in L(i))], hard["g_and_pcs_units"]),
                 "targeted_legit_hard", "g_and_pcs_units", constraint="wpu")
        self.add(self.pick("smallmt", [i for i in clean if T(i) != "IMPORT_COMMERCIAL"
                                       and any(l["raw_unit"] == "MT" and l["raw_quantity"] < 1 for l in L(i))],
                           hard["small_mt"]), "targeted_legit_hard", "small_mt")
        self.add(self.pick("credit", [i for i in clean if T(i) == "CREDIT_NOTE"], hard["credit_note_applied"]),
                 "targeted_legit_hard", "credit_note_applied")
        self.add(self.pick("ret", [i for i in clean if T(i) == "RETURN"], hard["return_applied"]),
                 "targeted_legit_hard", "return_applied")
        ship = [i for i in clean if T(i) == "FG_SALES" and reg.invoices[i]["tax_mode"] == "inter"
                and self.w.buyer[reg.invoices[i]["buyer_id"]]["state"] != reg.invoices[i]["place_of_supply_state"]]
        self.add(self.pick("ship", ship, hard["igst_ship_to_other_state"]), "targeted_legit_hard", "igst_ship_to",
                 constraint="L08")
        unreg = [i for i in clean if T(i) == "FG_SALES" and not self.w.buyer[reg.invoices[i]["buyer_id"]]["fake_gstin"]]
        self.add(self.pick("unreg", unreg, hard["unregistered_buyer"]), "targeted_legit_hard", "unregistered_buyer")
        # ---------------- routine
        for code, k in pc["routine_by_type"].items():
            itype = CODE_TYPE[code]
            cands = [i for i in reg.invoices if T(i) == itype and self.clean_ok(i)]
            self.add(self.pick("routine" + code, cands, k), "routine", "routine")
        return self.chosen


def assign_layouts(w, reg, chosen):
    counts = {k: 0 for k in LAYOUTS}
    options = {}
    for iid, meta in chosen.items():
        itype = reg.invoices[iid]["invoice_type"]
        opts = list(TYPE_LAYOUTS[itype])
        n_lines = len(reg.lines[iid])
        if meta["constraint"] == "L05":
            opts = ["L05"]
        elif meta["constraint"] == "L08":
            opts = ["L08"]
        else:
            opts = [o for o in opts if o != "L05" or n_lines >= 6] or opts
            if meta["constraint"] == "category":
                opts = [o for o in opts if o in PRINTS_CATEGORY] or opts
            if meta["constraint"] == "wpu":
                opts = [o for o in opts if o in ("L03", "L07")] or opts
        options[iid] = opts
    r = w.r("layouts")
    order = sorted(chosen, key=lambda i: (len(options[i]), i))
    out = {}
    for iid in order:
        opts = options[iid]
        low = min(counts[o] for o in opts)
        best = sorted(o for o in opts if counts[o] == low)
        pick = best[r.randrange(len(best))]
        out[iid] = pick
        counts[pick] += 1
    return out, counts


# ================================================================ document model
def party(w, pid, gstin, role):
    row = w.party(pid)
    name = row.get("company_name") or row.get("supplier_name") or row.get("buyer_name") or row.get("recycler_name")
    a = w.address[row["hq_address_id"]]
    lines = [f"{a['address_line_1']}, {a['address_line_2']}", f"{a['city']}, {a['state']} {a['postal_code']}, India"]
    p = {"name": name, "address_lines": lines, "state": a["state"],
         "initials": "".join(x[0] for x in name.split()[:2]).upper(), "extra_lines": []}
    if role == "import_exporter":
        p["address_lines"] = ["Overseas dispatch unit of the supplier (location not modelled)", "SYNTHETIC - EPRLens Demo"]
        p["state"] = None
    elif gstin is not None:
        p["gstin_line"] = f"GSTIN: {gstin}"
    else:
        p["gstin_line"] = "GSTIN: " if role == "missing" else "GSTIN: Not registered"
    return p


def build_doc(w, reg, iid, doc_id, layout, meta, gt_for_invoice, gen_version):
    inv = reg.invoices[iid]
    lines = reg.lines[iid]
    style_seed = w.sub_seed("doc_style", doc_id)
    r = w.r("doc_style", doc_id)
    date_style = r.choices(["slash", "dash", "mon", "iso"], weights=[0.4, 0.2, 0.3, 0.1])[0]
    nf = r.choices(["indian", "western", "plain"], weights=[0.75, 0.15, 0.10])[0]
    cur_mark = "USD" if inv["currency"] == "USD" else r.choice(["Rs.", "INR"])
    spell = {u: r.choice(v) for u, v in UNIT_SPELL.items()}
    itype = inv["invoice_type"]
    issuer_role = "import_exporter" if itype == "IMPORT_COMMERCIAL" else ("issuer" if inv["supplier_gstin"] or
                                                                          not _gst_expected(w, inv["supplier_id"]) else "missing")
    issuer = party(w, inv["supplier_id"], inv["supplier_gstin"], issuer_role)
    recipient = party(w, inv["buyer_id"], inv["buyer_gstin"], "recipient")
    if itype in ("RECYCLER_PROCESSING", "RECYCLING_SERVICE"):
        rec = w.recycler[inv["supplier_id"]]
        issuer["extra_lines"] = [f"EPR Reg. (claimed): {rec['fake_registration_number'] or 'not provided'}",
                                 "Fictional number - does not represent a CPCB authorization"]
    date_str = fmt_date(inv["invoice_date"], date_style)
    pos = inv["place_of_supply_state"]
    pos_str = f"{pos} ({geo.state_code(pos)})" if pos in geo.STATES else (pos or "")
    meta_rows = [("Invoice No." if itype not in ("CREDIT_NOTE", "RETURN") else "Note No.", inv["invoice_number"]),
                 ("Date", date_str)]
    if itype != "IMPORT_COMMERCIAL":
        meta_rows.append(("Place of Supply", pos_str))
    else:
        meta_rows += [("Currency", "USD"), ("Incoterm", "CIF (synthetic)"),
                      ("Bill of Entry", f"SYN-BE-{int(iid[4:]) % 100000:05d}")]
    orig_no = None
    if inv["original_invoice_id"]:
        orig_no = reg.invoices[inv["original_invoice_id"]]["invoice_number"]
        meta_rows.append(("Against invoice", orig_no))
    ship_to = None
    if layout == "L08":
        st = inv["place_of_supply_state"]
        ship_to = dict(recipient)
        if st in geo.STATES and st != recipient["state"]:
            ship_to = {"name": recipient["name"] + " - delivery point", "address_lines": [f"Delivery depot, {st}",
                                                                                          "(synthetic ship-to)"],
                       "state": st, "extra_lines": []}
    cats_printed = layout in PRINTS_CATEGORY
    hsn_printed = layout in PRINTS_HSN
    model_lines = []
    for l in lines:
        unit = l["raw_unit"]
        qty = l["raw_quantity"]
        printed_qty = fmt(qty, UNIT_DP.get(unit, 2), nf) if qty is not None else ""
        if unit is None:
            printed_unit = spell[None] if (itype == "RECYCLING_SERVICE" and qty is not None) else ""
        else:
            printed_unit = spell.get(unit, unit)
        cat = l["plastic_category"]
        cells = {"no": str(l["line_no"]), "hsn": l["hsn_code"] or "", "mat": l["material"] or "",
                 "cat": (cat or ""), "qty": printed_qty, "unit": printed_unit or "",
                 "wpu": f"{l['weight_per_unit_g']:.1f}" if l["weight_per_unit_g"] else "",
                 "rate": fmt(l["rate"], 2, nf), "amt": fmt(l["taxable_value"], 2, nf),
                 "gst": f"{l['gst_rate']}%", "tax": fmt(l["gst_amount"], 2, nf)}
        model_lines.append({
            "line_no": l["line_no"], "invoice_line_id": l["invoice_line_id"], "item_description": l["item_description"],
            "cells": cells, "material": l["material"], "plastic_category": cat if cats_printed else None,
            "plastic_category_printed": cats_printed and bool(cat), "hsn_code": l["hsn_code"] if hsn_printed else None,
            "quantity": qty, "unit": unit if qty is not None else unit, "printed_quantity": printed_qty,
            "printed_unit": printed_unit, "weight_per_unit_g": l["weight_per_unit_g"],
            "normalized_quantity_kg": l["normalized_quantity_kg"],
            "normalization_requires_master": itype in ("FG_SALES", "RETURN"),
            "rate": l["rate"], "printed_rate": cells["rate"], "amount": l["taxable_value"], "printed_amount": cells["amt"],
            "gst_rate": l["gst_rate"], "gst_amount": l["gst_amount"], "recorded_quantity_kg": l["recorded_quantity_kg"],
            "transaction_id": l["transaction_id"], "source_record_id": l["source_record_id"],
        })
    cap = capacity(layout)
    pages = [model_lines[i:i + cap] for i in range(0, len(model_lines), cap)] or [[]]
    carried, running = [], 0.0
    for n, pg in enumerate(pages, start=1):
        for ml in pg:
            ml["page_number"] = n
            ml["line_reference"] = f"{doc_id}:p{n}:l{ml['line_no']}"
            running += ml["amount"]
        carried.append(fmt(round(running, 2), 2, nf))
    cl = cur_mark
    totals = [("Total taxable value", fmt(inv["total_taxable_value"], 2, nf))]
    if inv["tax_mode"] == "intra":
        rates = sorted({l["gst_rate"] for l in lines})
        rlabel = "/".join(f"{x / 2:g}%" for x in rates)
        totals += [(f"CGST @ {rlabel}", fmt(inv["cgst"], 2, nf)), (f"SGST @ {rlabel}", fmt(inv["sgst"], 2, nf))]
    elif inv["tax_mode"] == "inter":
        rates = sorted({l["gst_rate"] for l in lines})
        totals += [("IGST @ " + "/".join(f"{x:g}%" for x in rates), fmt(inv["igst"], 2, nf))]
    else:
        totals += [("IGST on import", "per Bill of Entry (not modelled)")]
    printed_total = fmt(inv["total"], 2, nf)
    totals.append((f"Invoice total ({cl})", printed_total))
    if itype == "IMPORT_COMMERCIAL":
        totals.append((f"INR equivalent @ {inv['fx_rate']:.2f}", fmt(round(inv["total"] * inv["fx_rate"], 2), 2, nf)))
    tax_summary = []
    if LAYOUTS[layout].get("tax_summary"):
        agg = {}
        for l in lines:
            k = (l["hsn_code"] or "", l["gst_rate"])
            a = agg.setdefault(k, [0.0, 0.0])
            a[0] += l["taxable_value"]
            a[1] += l["gst_amount"]
        tax_summary = [[h, fmt(round(a[0], 2), 2, nf), f"{g}%", fmt(round(a[1], 2), 2, nf)] for (h, g), a in sorted(agg.items())]
    notes = []
    if itype == "IMPORT_COMMERCIAL":
        notes.append("Customs duty and IGST on import are not modelled in this synthetic document.")
    if itype in ("RECYCLER_PROCESSING", "RECYCLING_SERVICE"):
        notes.append("Quantities are synthetic test values; this document is not an EPR certificate.")
    notes.append(f"{('SYNTHETIC - EPRLens Demo. All parties, identifiers, addresses and amounts are fictional.')}")
    doc = {
        "document_id": doc_id, "invoice_id": iid, "template_id": layout, "title": TITLES[itype],
        "invoice_number_printed": inv["invoice_number"], "status": inv["status"], "issuer": issuer,
        "recipient": recipient, "ship_to": ship_to, "meta": meta_rows, "pages": pages, "carried_forward": carried,
        "totals": totals, "tax_summary": tax_summary, "currency_label": cl,
        "amount_in_words": indian_words(inv["total"]) if inv["currency"] == "INR" else None,
        "bank_lines": [f"Bank: Synthetic Demo Bank   A/C: {ids.fake_bank_account(int(iid[4:]) % 1000000)}",
                       f"IFSC: {ids.FAKE_IFSC}   (non-routable, SYNTHETIC)"],
        "notes": notes,
    }
    anomaly_rows = gt_for_invoice
    is_anom = any(g["is_anomaly"] for g in anomaly_rows)
    gt = {
        "document_id": doc_id, "invoice_id": iid, "invoice_number": inv["invoice_number"], "invoice_type": itype,
        "invoice_type_code": TYPE_CODE[itype], "company_id": inv["company_id"], "supplier_id": inv["supplier_id"],
        "buyer_id": inv["buyer_id"],
        "expected_fields": {
            "invoice_number": inv["invoice_number"], "invoice_date": inv["invoice_date"], "printed_date": date_str,
            "invoice_type": itype, "title": TITLES[itype], "status": inv["status"], "vendor": issuer["name"],
            "vendor_gstin": inv["supplier_gstin"], "buyer": recipient["name"], "buyer_gstin": inv["buyer_gstin"],
            "place_of_supply": pos_str if itype != "IMPORT_COMMERCIAL" else None, "tax_mode": inv["tax_mode"],
            "currency": inv["currency"], "fx_rate": inv["fx_rate"], "original_invoice_number": orig_no,
            "lines": [{k: ml[k] for k in ("line_reference", "page_number", "line_no", "item_description", "material",
                                          "plastic_category", "plastic_category_printed", "hsn_code", "quantity", "unit",
                                          "printed_quantity", "printed_unit", "weight_per_unit_g",
                                          "normalized_quantity_kg", "normalization_requires_master", "rate",
                                          "printed_rate", "amount", "printed_amount", "gst_rate", "gst_amount")}
                      for ml in model_lines],
            "total_taxable_value": inv["total_taxable_value"], "cgst": inv["cgst"], "sgst": inv["sgst"],
            "igst": inv["igst"], "gst": inv["gst"], "invoice_total": inv["total"], "printed_total": printed_total,
            "page_count": len(pages),
        },
        "recorded_quantities_kg": [ml["recorded_quantity_kg"] for ml in model_lines],
        "linked_transaction_ids": [ml["transaction_id"] for ml in model_lines if ml["transaction_id"]],
        "linked_recycling_record_ids": [ml["source_record_id"] for ml in model_lines if ml["source_record_id"]],
        "is_anomaly": is_anom,
        "anomaly_types": sorted({g["anomaly_type"] for g in anomaly_rows if g["is_anomaly"]}),
        "anomaly_instance_ids": [g["anomaly_instance_id"] for g in anomaly_rows],
        "test_case_type": meta["stratum"], "test_case": meta["case"], "paired_document_id": None,
        "template_id": layout, "template_name": LAYOUTS[layout]["name"],
        "layout_variant": {"date_style": date_style, "number_format": nf, "currency_mark": cur_mark},
        "seed": style_seed, "generator_version": gen_version, "watermark": "SYNTHETIC — EPRLens Demo",
        "synthetic_flag": True,
    }
    return doc, gt


def _gst_expected(w, pid):
    row = w.party(pid)
    return bool(row.get("fake_gstin"))


def render_all(w, reg, inj, chosen, layouts, out_pdf, out_json, gen_version):
    out_pdf, out_json = Path(out_pdf), Path(out_json)
    out_pdf.mkdir(parents=True, exist_ok=True)
    out_json.mkdir(parents=True, exist_ok=True)
    gt_by_inv = {}
    for g in inj.gt:
        if g["invoice_id"]:
            gt_by_inv.setdefault(g["invoice_id"], []).append(g)
    strata_order = {"targeted_anomaly": 0, "targeted_legit_hard": 1, "routine": 2}
    order = sorted(chosen, key=lambda i: (reg.invoices[i]["invoice_date"] or "0000", i))
    doc_ids = {iid: f"DOC_{n:06d}" for n, iid in enumerate(order, start=1)}
    results = []
    for iid in order:
        meta = chosen[iid]
        doc_id = doc_ids[iid]
        doc, gt = build_doc(w, reg, iid, doc_id, layouts[iid], meta, gt_by_inv.get(iid, []), gen_version)
        if meta.get("paired"):
            gt["paired_document_id"] = doc_ids[meta["paired"]]
        pdf_path = out_pdf / f"{doc_id}.pdf"
        Pdf(pdf_path, doc).render()
        for ml, gl in zip([x for p in doc["pages"] for x in p], gt["expected_fields"]["lines"]):
            gl["printed_description_lines"] = ml.get("printed_description_lines", [ml["item_description"]])
        gt["render_sha256"] = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
        (out_json / f"{doc_id}.json").write_text(json.dumps(gt, indent=2, ensure_ascii=False) + "\n",
                                                  encoding="utf-8", newline="\n")
        reg.invoices[iid]["document_id"] = doc_id
        results.append(gt)
    del strata_order
    return results
