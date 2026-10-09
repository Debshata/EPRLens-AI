"""Fixtures derived from the entity masters — one source of truth for the demo
company, DB seed samples, frontend mocks, Lambda test events and the illustrative
example invoice. SYNTHETIC — EPRLens Demo.

Only entity-level fixtures are produced here. Fixtures that need transactions,
invoices, recycling, forecasts or anomalies wait for full-dataset approval.

Illustrative fixtures use the reserved 99-range IDs (INV_99xxxxxx, DOC_99xxxx,
TXN_99xxxxxx) so they can never collide with generated records.
"""
from datetime import date

from . import geo
from . import identifiers as ids
from .formatting import date_dmy, inr

WATERMARK = "SYNTHETIC — EPRLens Demo"
PENDING = [
    "36 months of sales", "purchase records", "sales records", "recycling records", "invoices",
    "anomalies", "forecast history", "what-if scenario results",
]
# Illustrative only (docs/generator-assumptions.md §7) — not market prices.
ILLUSTRATIVE_RATE_PER_KG = {"PET": 140.0, "PP": 130.0, "HDPE": 125.0, "CARDBOARD": 60.0, "GLASS": 25.0, "PAPER": 80.0}


def meta(cfg, pack, note=None):
    m = {"synthetic": True, "watermark": WATERMARK, "seed": cfg["seed"],
         "generator_version": cfg["generator_version"], "entity_pack": pack,
         "source_of_truth": "synthetic-data/masters/*.csv"}
    if note:
        m["note"] = note
    return m


def index(ctx):
    return {
        "company": {c["company_id"]: c for c in ctx.companies},
        "product": {p["product_id"]: p for p in ctx.products},
        "supplier": {s["supplier_id"]: s for s in ctx.suppliers},
        "buyer": {b["buyer_id"]: b for b in ctx.buyers},
        "recycler": {r["recycler_id"]: r for r in ctx.recyclers},
        "address": {a["address_id"]: a for a in ctx.addresses},
    }


def rel_targets(ctx, source_id, rtype):
    return [r["target_entity_id"] for r in ctx.relationships
            if r["source_entity_id"] == source_id and r["relationship_type"] == rtype]


def components_in_force(ctx, product_id, on):
    on = on.isoformat()
    return [c for c in ctx.components if c["product_id"] == product_id and c["effective_from"] <= on
            and (c["effective_to"] is None or c["effective_to"] >= on)]


def product_view(ctx, p, on):
    comps = [c for c in ctx.components if c["product_id"] == p["product_id"]]
    cur = components_in_force(ctx, p["product_id"], on)
    return {**p, "components": comps,
            "current_total_packaging_g": round(sum(c["weight_per_unit_g"] for c in cur), 2),
            "current_plastic_packaging_g": round(sum(c["weight_per_unit_g"] for c in cur if c["plastic_epr_relevant"]), 2),
            "weights_as_of": on.isoformat()}


def address_text(a):
    return f"{a['address_line_1']}, {a['address_line_2']}, {a['city']}, {a['state']} {a['postal_code']}, India"


# ----------------------------------------------------------------- example invoice
def example_invoice(ctx, cfg):
    """Hand-composed IT01 packaging purchase invoice for the demo company (illustrative)."""
    ix = index(ctx)
    inv_date = date(2025, 10, 14)
    buyer = ix["company"]["COMP_0001"]
    demo_pids = [p["product_id"] for p in ctx.products if p["company_id"] == "COMP_0001"]
    counts = {}
    for pid in demo_pids:
        for c in components_in_force(ctx, pid, inv_date):
            if c["plastic_epr_relevant"]:
                counts[c["supplier_id"]] = counts.get(c["supplier_id"], 0) + c["weight_per_unit_g"]
    supplier = ix["supplier"][sorted(counts, key=lambda k: (-counts[k], k))[0]]
    lines_src = []
    for pid in demo_pids:
        for c in components_in_force(ctx, pid, inv_date):
            if c["supplier_id"] == supplier["supplier_id"] and c["plastic_epr_relevant"]:
                lines_src.append((ix["product"][pid], c))
    qty_plan = [48000, 36000, 24000, 30000, 12000]
    s_addr, b_addr = ix["address"][supplier["hq_address_id"]], ix["address"][buyer["hq_address_id"]]
    intra = supplier["state"] == buyer["headquarters_state"]
    lines, total_taxable, gst_total = [], 0.0, 0.0
    for n, ((prod, c), qty) in enumerate(zip(lines_src, qty_plan), start=1):
        rate = round(ILLUSTRATIVE_RATE_PER_KG[c["material"]] * c["weight_per_unit_g"] / 1000 * 1.35, 2)
        taxable = round(qty * rate, 2)
        gst = round(taxable * 0.18, 2)
        kg = round(qty * c["weight_per_unit_g"] / 1000, 3)
        size = " ".join(prod["product_name"].split()[-2:])
        lines.append({
            "line_reference": f"DOC_990001:p1:l{n}", "page_number": 1, "line_no": n,
            "item_description": f"{c['component_name']} {size} — {c['material']} ({c['weight_per_unit_g']} g/pc)",
            "product_id": prod["product_id"], "component_id": c["component_id"], "material": c["material"],
            "synthetic_category": c["synthetic_category"], "hsn_code": c["hsn_code"], "quantity": qty, "unit": "pcs",
            "weight_per_unit_g": c["weight_per_unit_g"], "normalized_quantity_kg": kg,
            "conversion_rule": "U_PCS", "rate": rate, "amount": taxable, "gst_rate": 18,
            "cgst": round(gst / 2, 2) if intra else 0.0, "sgst": round(gst / 2, 2) if intra else 0.0,
            "igst": 0.0 if intra else gst, "transaction_id": ids.make_id("TXN", 99000000 + n),
        })
        total_taxable += taxable
        gst_total += gst
    total = round(total_taxable + gst_total, 2)
    series = ids.invoice_series(supplier["supplier_name"])
    number = ids.invoice_number(series, ids.fy_code(2025), 123)
    expected = {
        "invoice_number": number, "invoice_date": inv_date.isoformat(), "invoice_type": "PKG_PURCHASE",
        "vendor": supplier["supplier_name"], "vendor_gstin": supplier["fake_gstin"],
        "vendor_address": address_text(s_addr), "buyer": buyer["company_name"],
        "buyer_gstin": None, "buyer_address": address_text(b_addr),
        "place_of_supply": f"{buyer['headquarters_state']} ({geo.state_code(buyer['headquarters_state'])})",
        "tax_mode": "intra" if intra else "inter", "currency": "INR", "lines": lines,
        "total_taxable_value": round(total_taxable, 2),
        "cgst": round(gst_total / 2, 2) if intra else 0.0, "sgst": round(gst_total / 2, 2) if intra else 0.0,
        "igst": 0.0 if intra else round(gst_total, 2), "gst": round(gst_total, 2), "invoice_total": total,
        "total_normalized_kg": round(sum(line["normalized_quantity_kg"] for line in lines), 3),
    }
    doc = {
        "document_id": "DOC_990001", "invoice_id": "INV_99000001", "invoice_number": number,
        "invoice_type": "PKG_PURCHASE", "company_id": "COMP_0001", "supplier_id": supplier["supplier_id"],
        "buyer_id": "COMP_0001", "expected_fields": expected,
        "linked_transaction_ids": [line["transaction_id"] for line in lines], "is_anomaly": False,
        "anomaly_types": [], "test_case_type": "illustrative", "template_id": "L01", "seed": cfg["seed"],
        "watermark": WATERMARK, "synthetic_flag": True,
        "illustrative_note": ("Hand-composed from the entity masters to show field shapes. NOT output of the "
                              "approved invoice generator; rates are illustrative, not market prices; the "
                              "buyer GSTIN is omitted because company masters carry no GSTIN yet (TBD)."),
    }
    return doc, render_text(doc, supplier, buyer, inv_date)


def render_text(doc, supplier, buyer, inv_date):
    e = doc["expected_fields"]
    w = 96
    out = [WATERMARK.center(w, "="), "TAX INVOICE".center(w), ""]
    out += [f"{e['vendor']}", f"{e['vendor_address']}", f"GSTIN: {e['vendor_gstin']}    Tel: {ids.fake_phone(4401)}", ""]
    out += [f"Invoice No.: {e['invoice_number']:<24} Invoice Date: {date_dmy(inv_date, 'slash')}",
            f"Place of Supply: {e['place_of_supply']}", ""]
    out += ["Bill To:", f"  {e['buyer']}", f"  {e['buyer_address']}", ""]
    out.append(f"{'#':<3}{'Description':<44}{'HSN':<6}{'Qty':>9} {'Unit':<5}{'Rate':>8}{'Taxable':>14}")
    out.append("-" * w)
    for line in e["lines"]:
        out.append(f"{line['line_no']:<3}{line['item_description'][:43]:<44}{line['hsn_code']:<6}"
                   f"{inr(line['quantity'], 0):>9} {line['unit']:<5}{inr(line['rate']):>8}{inr(line['amount']):>14}")
    out.append("-" * w)
    out.append(f"{'Total taxable value':>80}{inr(e['total_taxable_value']):>16}")
    if e["tax_mode"] == "intra":
        out.append(f"{'CGST @ 9%':>80}{inr(e['cgst']):>16}")
        out.append(f"{'SGST @ 9%':>80}{inr(e['sgst']):>16}")
    else:
        out.append(f"{'IGST @ 18%':>80}{inr(e['igst']):>16}")
    out.append(f"{'Invoice total (Rs.)':>80}{inr(e['invoice_total']):>16}")
    out += ["", f"Bank: {ids.fake_bank_account(1234)}  IFSC: {ids.FAKE_IFSC}",
            f"for {e['vendor']} — Authorised Signatory", "", f"{WATERMARK} · {doc['document_id']} · page 1/1".center(w, "=")]
    return "\n".join(out) + "\n"


# ----------------------------------------------------------------- bundles
def demo_bundle(ctx, cfg, pack, today):
    ix = index(ctx)
    cid = "COMP_0001"
    company = ix["company"][cid]
    products = [product_view(ctx, p, today) for p in ctx.products if p["company_id"] == cid]
    sup_ids = rel_targets(ctx, cid, "BUYS_FROM")
    rec_ids = rel_targets(ctx, cid, "USES_RECYCLER")
    buy_ids = rel_targets(ctx, cid, "SELLS_TO")
    related = {cid} | {p["product_id"] for p in products} | {c["component_id"] for p in products for c in p["components"]}
    cola_v2 = next(c for c in products[0]["components"] if c["material"] == "PET" and c["spec_version"] == 2)
    return {
        "_meta": meta(cfg, pack, "FICTIONAL / SYNTHETIC demo company. Activity data pending approval."),
        "company": company,
        "addresses": [a for a in ctx.addresses if a["entity_id"] == cid],
        "products": products,
        "suppliers": [ix["supplier"][s] for s in sup_ids],
        "buyers": [ix["buyer"][b] for b in buy_ids],
        "recyclers": [ix["recycler"][r] for r in rec_ids],
        "relationships": [r for r in ctx.relationships if r["source_entity_id"] in related],
        "test_users": [u for u in ctx.users if cid in u["company_scope"]],
        "demo_story_proposal": [
            "Onboard EcoFizz (manufacturer + brand owner, Beverages, Delhi HQ, 5 states).",
            f"Packaging bill of materials: PET bottle, PP/HDPE cap, PP label (plastic) + carton (not plastic EPR per handbook).",
            f"Light-weighting: Cola 750 ml bottle {products[0]['components'][0]['weight_per_unit_g']} g → "
            f"{cola_v2['weight_per_unit_g']} g from {cola_v2['effective_from']} (spec v2).",
            "Anomaly to demonstrate (handbook p.15 pattern): a PET bottle purchase printed as 0.5 MT "
            "(= 500 kg ≈ 20,000 bottles at 25 g) but recorded internally as 500 MT → AN08/AN01.",
            "Second anomaly: purchases from SUP_TEST_001 with irregular x5 spikes (AN09).",
            "Buyer BUY_TEST_001 has a truncated GSTIN (AN06).",
            "What-if: reduce bottle weight 15 % on forecast volume (docs/scenario-formulas.md).",
        ],
        "pending_until_approval": PENDING,
    }


def seed_samples(ctx, cfg, pack):
    core = {"COMP_0001", "COMP_0002", "COMP_0003", "COMP_0004", "COMP_0005"}
    m = meta(cfg, pack, "Small DB seed (core pack).")
    prods = [p for p in ctx.products if p["company_id"] in core]
    pids = {p["product_id"] for p in prods}
    return {
        "companies.sample.json": {"_meta": m, "records": [c for c in ctx.companies if c["company_id"] in core]},
        "products.sample.json": {"_meta": m, "records": prods,
                                 "packaging_components": [c for c in ctx.components if c["product_id"] in pids]},
        "suppliers.sample.json": {"_meta": m, "records": [s for s in ctx.suppliers
                                                          if s["supplier_id"].startswith("SUP_TEST") or int(s["supplier_id"][4:]) <= 10]},
        "buyers.sample.json": {"_meta": m, "records": [b for b in ctx.buyers
                                                       if b["buyer_id"].startswith("BUY_TEST") or int(b["buyer_id"][4:]) <= 10]},
        "recyclers.sample.json": {"_meta": m, "records": [r for r in ctx.recyclers
                                                          if r["recycler_id"].startswith("REC_TEST") or int(r["recycler_id"][4:]) <= 5]},
    }


def frontend_mocks(ctx, cfg, pack, demo, invoice_doc):
    m = meta(cfg, pack, "Same IDs as synthetic-data/masters. Do not invent frontend-only entities.")
    return {
        "company.json": {"_meta": m, "company": demo["company"], "addresses": demo["addresses"]},
        "products.json": {"_meta": m, "products": demo["products"]},
        "suppliers.json": {"_meta": m, "suppliers": demo["suppliers"]},
        "recyclers.json": {"_meta": m, "recyclers": demo["recyclers"]},
        "invoice.json": {"_meta": {**m, "note": "ILLUSTRATIVE example invoice (99-range IDs)."}, "invoice": invoice_doc},
    }


def lambda_events(ctx, cfg, pack, demo, invoice_doc):
    m = meta(cfg, pack, "Invocation envelope TBD (D056). Payload shape is a proposal.")
    pet = next(c for c in demo["products"][0]["components"] if c["material"] == "PET" and c["effective_to"] is None)
    units, reduction = 100000, 15
    base_kg = units * pet["weight_per_unit_g"] / 1000
    prop_g = round(pet["weight_per_unit_g"] * (1 - reduction / 100), 4)
    prop_kg = units * prop_g / 1000
    return {
        "company.json": {"_meta": m, "action": "get_company_profile", "company_id": "COMP_0001"},
        "invoice-upload.json": {
            "_meta": m, "action": "parse_invoice", "company_id": "COMP_0001", "document_id": invoice_doc["document_id"],
            "s3": {"bucket": "<uploads-bucket-placeholder>", "key": f"uploads/COMP_0001/invoices/{invoice_doc['document_id']}.pdf"},
            "expected": {"invoice_number": invoice_doc["invoice_number"], "supplier_id": invoice_doc["supplier_id"],
                         "total_normalized_kg": invoice_doc["expected_fields"]["total_normalized_kg"]},
        },
        "classify-image.json": {
            "_meta": m, "action": "classify_image", "company_id": "COMP_0001", "product_id": demo["products"][0]["product_id"],
            "component_id": pet["component_id"],
            "s3": {"bucket": "<uploads-bucket-placeholder>", "key": "uploads/COMP_0001/images/<image-placeholder>.jpg"},
            "declared_material": "PET", "note": "Image not included; prediction is a probable material only, never a legal category.",
        },
        "scenario.json": {
            "_meta": m, "action": "what_if", "company_id": "COMP_0001", "product_id": demo["products"][0]["product_id"],
            "input": {"baseline_weight_g": pet["weight_per_unit_g"], "reduction_pct": reduction, "units": units,
                      "units_note": "Illustrative input, not generated sales."},
            "expected_output": {"proposed_weight_g": prop_g, "baseline_kg": round(base_kg, 3), "proposed_kg": round(prop_kg, 3),
                                "projected_reduction_kg": round(base_kg - prop_kg, 3)},
        },
    }
