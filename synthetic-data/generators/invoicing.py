"""Clean-world invoice register (headers + lines) built from transactions and the
recycling proxy. SYNTHETIC — EPRLens Demo.

Rates, GST rates, HSN headings and FX are ILLUSTRATIVE configurable test values
(DS-13), not verified market prices or tax treatment.
"""
from datetime import date, timedelta

from . import identifiers as ids
from .world import business_day, fy_label, fy_start_year

COMPONENT_SUPPLIER_TYPES = {"cap supplier", "closure supplier", "label supplier", "carton supplier", "component supplier"}
PLASTIC_CATS = {"CAT_I", "CAT_II", "CAT_III", "CAT_IV"}


def size_label(product_name):
    return " ".join(product_name.split()[-2:])


class Register:
    def __init__(self, w):
        self.w = w
        self.invoices = {}   # invoice_id -> header
        self.lines = {}      # invoice_id -> [lines]
        self.txn_line = {}   # transaction_id -> line

    # ------------------------------------------------------------ primitives
    def new_invoice(self, itype, company_id, supplier_id, buyer_id, day, pos_state, currency="INR", fx=None, **kw):
        w = self.w
        inv = {
            "invoice_id": w.ids.next("INV"), "invoice_number": None, "invoice_type": itype, "company_id": company_id,
            "supplier_id": supplier_id, "buyer_id": buyer_id, "invoice_date": day, "place_of_supply_state": pos_state,
            "tax_mode": "import" if itype == "IMPORT_COMMERCIAL" else (
                "intra" if w.party_state(supplier_id) == pos_state else "inter"),
            "currency": currency, "fx_rate": fx,
            "supplier_gstin": w.party(supplier_id).get("fake_gstin") if itype != "IMPORT_COMMERCIAL" else None,
            "buyer_gstin": w.party(buyer_id).get("fake_gstin"),
            "total_taxable_value": 0.0, "cgst": 0.0, "sgst": 0.0, "igst": 0.0, "gst": 0.0, "total": 0.0,
            "line_count": 0, "status": "issued", "original_invoice_id": None, "document_id": None,
            "is_anomaly": False, "anomaly_type": None, "synthetic_flag": True,
        }
        inv.update(kw)
        self.invoices[inv["invoice_id"]] = inv
        self.lines[inv["invoice_id"]] = []
        return inv

    def add_line(self, inv, desc, qty, unit, rate, gst_rate, product_id=None, component_id=None, material=None,
                 category=None, hsn=None, wpu=None, norm=None, recorded=None, txn=None, source=None):
        w = self.w
        lines = self.lines[inv["invoice_id"]]
        taxable = round((qty if qty is not None else 1) * rate, 2)
        gst = 0.0 if inv["tax_mode"] == "import" else round(taxable * gst_rate / 100.0, 2)
        line = {
            "invoice_line_id": w.ids.next("INVL"), "invoice_id": inv["invoice_id"], "line_no": len(lines) + 1,
            "item_description": desc, "product_id": product_id, "component_id": component_id, "material": material,
            "plastic_category": category, "hsn_code": hsn, "raw_quantity": qty, "raw_unit": unit,
            "weight_per_unit_g": wpu, "normalized_quantity_kg": norm, "recorded_quantity_kg": recorded,
            "rate": rate, "taxable_value": taxable, "gst_rate": 0 if inv["tax_mode"] == "import" else gst_rate,
            "gst_amount": gst, "transaction_id": txn, "source_record_id": source, "synthetic_flag": True,
        }
        lines.append(line)
        if txn:
            self.txn_line[txn] = line
        return line

    def recompute(self, inv):
        lines = self.lines[inv["invoice_id"]]
        taxable = round(sum(l["taxable_value"] for l in lines), 2)
        gst = round(sum(l["gst_amount"] for l in lines), 2)
        inv["total_taxable_value"] = taxable
        inv["gst"] = gst
        if inv["tax_mode"] == "intra":
            inv["cgst"] = round(gst / 2.0, 2)
            inv["sgst"] = round(gst - inv["cgst"], 2)
            inv["igst"] = 0.0
        else:
            inv["cgst"] = inv["sgst"] = 0.0
            inv["igst"] = gst
        inv["total"] = round(taxable + gst, 2)
        inv["line_count"] = len(lines)
        for i, l in enumerate(lines, start=1):
            l["line_no"] = i


# ================================================================ helpers
def _chunks(items, n):
    for i in range(0, len(items), n):
        yield items[i:i + n]


def _per_kg_price(w, supplier_id, material):
    lo, hi = w.cfg["invoices"]["price_per_kg_inr"][material]
    r = w.r("price_per_kg", f"{supplier_id}:{material}")
    base = r.uniform(lo, hi)
    margin = r.uniform(*w.cfg["invoices"]["conversion_margin"])
    gst = 12 if r.random() < w.cfg["invoices"]["purchase_gst_12_share"] else 18
    return base * (1 + margin), gst


def purchase_line_fields(w, tx):
    comp = tx["_comp"]
    prod = w.product[tx["product_id"]]
    per_kg, gst = _per_kg_price(w, tx["supplier_id"], comp["material"])
    unit = tx["raw_unit"]
    if unit == "pcs":
        rate = max(0.01, round(per_kg * comp["weight_per_unit_g"] / 1000.0, 2))
        desc = f"{comp['component_name']} {size_label(prod['product_name'])} - {comp['material']} ({comp['weight_per_unit_g']} g/pc)"
        wpu = comp["weight_per_unit_g"]
    elif unit == "MT":
        rate = round(per_kg * 1000.0, 2)
        desc = f"{comp['component_name']} for {size_label(prod['product_name'])} - {comp['material']}"
        wpu = None
    else:
        rate = round(per_kg, 2)
        desc = f"{comp['component_name']} for {size_label(prod['product_name'])} - {comp['material']}"
        wpu = None
    if tx.get("_lot"):
        desc += f" (lot {tx['_lot'][0]}/{tx['_lot'][1]})"
    return dict(desc=desc, rate=rate, gst=gst, wpu=wpu, material=comp["material"], category=comp["synthetic_category"],
                hsn=comp["hsn_code"], component_id=comp["component_id"])


# ================================================================ builders
def build_trade_invoices(w, reg, sales_txns, returns, purchases, price):
    lines_max = w.cfg["invoices"]["lines_max"]
    ic = w.cfg["invoices"]
    # ---------------------------------------------------------- sales
    groups = {}
    for tx in sales_txns:
        if tx["transaction_type"] != "sale":
            continue
        groups.setdefault((tx["company_id"], tx["buyer_id"], tx["date"][:7]), []).append(tx)
    for (cid, bid, month) in sorted(groups):
        txs = sorted(groups[(cid, bid, month)], key=lambda t: (t["product_id"], t["transaction_id"]))
        c = w.company[cid]
        for chunk in _chunks(txs, lines_max):
            inv = reg.new_invoice("FG_SALES", cid, cid, bid, chunk[0]["date"], chunk[0]["state"])
            for tx in chunk:
                p = w.product[tx["product_id"]]
                l = reg.add_line(inv, p["product_name"], tx["units"], tx["raw_unit"], price[p["product_id"]],
                                 ic["sales_gst_by_industry"][c["industry"]], product_id=p["product_id"],
                                 hsn=ic["sales_hsn_by_industry"][c["industry"]], norm=tx["normalized_quantity_kg"],
                                 recorded=tx["normalized_quantity_kg"], txn=tx["transaction_id"])
                tx["invoice_id"] = inv["invoice_id"]
            reg.recompute(inv)
    # ---------------------------------------------------------- purchases / imports
    groups = {}
    for tx in purchases:
        groups.setdefault((tx["company_id"], tx["supplier_id"], tx["date"][:7], tx["transaction_type"]), []).append(tx)
    fx = ic["usd_inr_rate"]
    for key in sorted(groups):
        cid, sid, month, ttype = key
        txs = sorted(groups[key], key=lambda t: (t["date"], t["transaction_id"]))
        supplier = w.supplier[sid]
        for chunk in _chunks(txs, lines_max):
            fields = [purchase_line_fields(w, tx) for tx in chunk]
            cats = {f["category"] for f in fields if f["category"] in PLASTIC_CATS}
            if ttype == "import":
                itype = "IMPORT_COMMERCIAL"
            elif len(cats) >= 2:
                itype = "MULTI_MATERIAL"
            elif supplier["supplier_type"] in COMPONENT_SUPPLIER_TYPES:
                itype = "PKG_COMPONENT"
            else:
                itype = "PKG_PURCHASE"
            c = w.company[cid]
            inv = reg.new_invoice(itype, cid, sid, cid, chunk[0]["date"], c["headquarters_state"],
                                  currency="USD" if ttype == "import" else "INR", fx=fx if ttype == "import" else None)
            for tx, f in zip(chunk, fields):
                rate = round(f["rate"] / fx, 2) if ttype == "import" else f["rate"]
                rate = max(rate, 0.01)
                reg.add_line(inv, f["desc"], tx["raw_quantity"], tx["raw_unit"], rate, f["gst"],
                             product_id=tx["product_id"], component_id=f["component_id"], material=f["material"],
                             category=f["category"], hsn=f["hsn"], wpu=f["wpu"], norm=tx["normalized_quantity_kg"],
                             recorded=tx["normalized_quantity_kg"], txn=tx["transaction_id"])
                tx["invoice_id"] = inv["invoice_id"]
            reg.recompute(inv)
    # ---------------------------------------------------------- returns (debit notes from buyers)
    for tx in sorted(returns, key=lambda t: t["transaction_id"]):
        orig_line = reg.txn_line[tx["_original_txn"]]
        orig = reg.invoices[orig_line["invoice_id"]]
        c = w.company[tx["company_id"]]
        p = w.product[tx["product_id"]]
        inv = reg.new_invoice("RETURN", tx["company_id"], tx["buyer_id"], tx["company_id"], tx["date"],
                              c["headquarters_state"], original_invoice_id=orig["invoice_id"])
        reg.add_line(inv, f"Goods returned: {p['product_name']}", tx["units"], tx["raw_unit"], orig_line["rate"],
                     orig_line["gst_rate"], product_id=p["product_id"], hsn=orig_line["hsn_code"],
                     norm=tx["normalized_quantity_kg"], recorded=tx["normalized_quantity_kg"], txn=tx["transaction_id"])
        tx["invoice_id"] = inv["invoice_id"]
        reg.recompute(inv)


def build_credit_notes(w, reg, txns_out):
    ic = w.cfg["invoices"]
    end = w.months[-1] + "-28"
    base = sorted(i for i, inv in reg.invoices.items()
                  if inv["invoice_type"] in ("PKG_PURCHASE", "PKG_COMPONENT", "MULTI_MATERIAL"))
    r = w.r("credit_notes")
    chosen = sorted(r.sample(base, int(round(len(base) * ic["credit_note_share"]))))
    from .activity import _txn
    for iid in chosen:
        orig = reg.invoices[iid]
        rr = w.r("credit_note", iid)
        d = date.fromisoformat(orig["invoice_date"]) + timedelta(days=rr.randint(5, 20))
        day = min(d.isoformat(), end)
        amount = round(orig["total_taxable_value"] * rr.uniform(0.02, 0.08), 2)
        gst_rate = reg.lines[iid][0]["gst_rate"]
        inv = reg.new_invoice("CREDIT_NOTE", orig["company_id"], orig["supplier_id"], orig["company_id"], day,
                              orig["place_of_supply_state"], original_invoice_id=iid)
        tx = _txn(w, company_id=orig["company_id"], date=day, transaction_type="credit_adjustment",
                  state=orig["place_of_supply_state"], supplier_id=orig["supplier_id"], raw_quantity=0.0, raw_unit="kg",
                  normalized_quantity_kg=0.0, plastic_kg=0.0, invoice_id=inv["invoice_id"])
        txns_out.append(tx)
        reg.add_line(inv, f"Rate difference credit against invoice dated {orig['invoice_date']}", None, None, amount,
                     gst_rate, hsn=reg.lines[iid][0]["hsn_code"], txn=tx["transaction_id"])
        reg.recompute(inv)


def build_cancelled_twins(w, reg, txn_by_id, txns_out):
    """A cancelled erroneous duplicate issued just before the real invoice (clean-world, correctly cancelled)."""
    ic = w.cfg["invoices"]
    base = sorted(i for i, inv in reg.invoices.items() if inv["invoice_type"] in ("FG_SALES", "PKG_PURCHASE"))
    r = w.r("cancelled_twins")
    chosen = sorted(r.sample(base, int(round(len(base) * ic["cancelled_twin_share"]))))
    from .activity import _txn
    twins = []
    for iid in chosen:
        orig = reg.invoices[iid]
        rr = w.r("twin", iid)
        d = date.fromisoformat(orig["invoice_date"])
        day = max(d - timedelta(days=rr.randint(1, 3)), d.replace(day=1)).isoformat()
        twin = reg.new_invoice(orig["invoice_type"], orig["company_id"], orig["supplier_id"], orig["buyer_id"], day,
                               orig["place_of_supply_state"], status="cancelled")
        for l in reg.lines[iid]:
            src = txn_by_id[l["transaction_id"]]
            tx = _txn(w, **{k: v for k, v in src.items() if not k.startswith("_") and k != "transaction_id"})
            tx["date"], tx["status"], tx["invoice_id"] = day, "cancelled", twin["invoice_id"]
            txns_out.append(tx)
            nl = reg.add_line(twin, l["item_description"], l["raw_quantity"], l["raw_unit"], l["rate"], l["gst_rate"],
                              product_id=l["product_id"], component_id=l["component_id"], material=l["material"],
                              category=l["plastic_category"], hsn=l["hsn_code"], wpu=l["weight_per_unit_g"],
                              norm=l["normalized_quantity_kg"], recorded=tx["normalized_quantity_kg"],
                              txn=tx["transaction_id"])
        reg.recompute(twin)
        twin["_twin_of"] = iid
        twins.append(twin["invoice_id"])
    return twins


def _half(month):
    y = fy_start_year(month)
    m = int(month[5:])
    return f"{y}-H1" if 4 <= m <= 9 else f"{y}-H2"


def _year(month):
    return f"{fy_start_year(month)}-FY"


def _half_end_month(half):
    y, h = half.split("-")
    if h == "FY":
        return f"{int(y) + 1:04d}-03"
    return f"{int(y):04d}-09" if h == "H1" else f"{int(y) + 1:04d}-03"


def build_waste_procurement(w, reg, events):
    """Company sells pre-consumer plastic scrap (WRITTEN_OFF) to a registered recycler, once per FY."""
    ic = w.cfg["invoices"]
    agg = {}
    for ev in events:
        if ev["event_type"] != "WRITTEN_OFF" or ev["synthetic_category"] == "NA":
            continue
        key = (ev["company_id"], _year(ev["period"]))
        d = agg.setdefault(key, {})
        k2 = (ev["material"], ev["synthetic_category"])
        d[k2] = d.get(k2, 0.0) + ev["kg"]
    for (cid, half) in sorted(agg):
        recs = [w.recycler[r] for r in w.recyclers_of.get(cid, []) if w.recycler[r]["registered"]]
        items = sorted(agg[(cid, half)].items())
        by_rec = {}
        for (mat, cat), kg in items:
            if round(kg, 2) <= 0:
                continue
            rec = next((r for r in recs if mat in r["supported_materials"]), None)
            if rec:
                by_rec.setdefault(rec["recycler_id"], []).append((mat, cat, round(kg, 2)))
        month = _half_end_month(half)
        if month not in w.month_index:
            continue
        rate = round(w.r("scrap_rate", cid).uniform(*ic["waste_procurement_rate_inr_per_kg"]), 2)
        for rid, rows in sorted(by_rec.items()):
            day = business_day(w.r("scrapdate", f"{cid}:{rid}:{half}"), month, 20, 28)
            inv = reg.new_invoice("WASTE_PROCUREMENT", cid, cid, rid, day, w.recycler[rid]["state"])
            for mat, cat, kg in rows[:ic["lines_max"]]:
                reg.add_line(inv, f"Pre-consumer {mat} packaging scrap ({cat})", kg, "kg", rate, 18, material=mat,
                             category=cat, hsn="3915", norm=kg, recorded=None)
            reg.recompute(inv)


def build_recycler_invoices(w, reg, recycling_rows):
    """IT03 processing invoices (half-yearly per company × recycler) and IT10 service invoices (per FY)."""
    ic = w.cfg["invoices"]
    groups = {}
    for row in recycling_rows:
        groups.setdefault((row["company_id"], row["recycler_id"], _year(row["month"])), []).append(row)
    for key in sorted(groups):
        cid, rid, half = key
        rows = sorted(groups[key], key=lambda r: (r["month"], r["synthetic_category"]))
        month = _half_end_month(half)
        if month not in w.month_index:
            month = rows[-1]["month"]
        rate = round(w.r("processing_rate", rid).uniform(*ic["recycler_processing_rate_inr_per_kg"]), 2)
        c = w.company[cid]
        for chunk in _chunks(rows, ic["lines_max"]):
            day = business_day(w.r("recdate", f"{cid}:{rid}:{half}:{chunk[0]['recycling_record_id']}"), month, 20, 28)
            inv = reg.new_invoice("RECYCLER_PROCESSING", cid, rid, cid, day, c["headquarters_state"])
            for row in chunk:
                add_recycling_line(reg, inv, row, rate)
            reg.recompute(inv)
    # IT10 service invoices
    pairs = sorted({(r["company_id"], r["recycler_id"], fy_label(r["month"])) for r in recycling_rows})
    for cid, rid, fy in pairs:
        r = w.r("service", f"{cid}:{rid}:{fy}")
        if r.random() >= ic["recycling_service_pair_share"]:
            continue
        y = int(fy[2:6])
        month = f"{y + 1:04d}-03"
        if month not in w.month_index:
            continue
        day = business_day(r, month, 10, 28)
        c = w.company[cid]
        inv = reg.new_invoice("RECYCLING_SERVICE", cid, rid, cid, day, c["headquarters_state"])
        lo, hi = ic["recycling_service_fee_inr"]
        reg.add_line(inv, f"Collection & logistics services {fy}", 1, None, round(r.uniform(lo, hi), 2), 18, hsn="9985")
        reg.add_line(inv, f"Documentation & reporting support {fy}", 1, None, round(r.uniform(lo, hi) / 3, 2), 18,
                     hsn="9983")
        reg.recompute(inv)


def add_recycling_line(reg, inv, row, rate):
    qty = round(row["waste_recycled_kg"], 2)
    desc = (f"Processing of post-consumer {row['synthetic_category']} plastic waste {row['month']} "
            f"(received {row['waste_collected_kg']:.2f} kg)")
    return reg.add_line(inv, desc, qty, "kg", rate, 18, category=row["synthetic_category"], hsn="9994", norm=qty,
                        recorded=round(row["waste_recycled_kg"], 3), source=row["recycling_record_id"])


# ================================================================ numbering
def _kind(inv):
    return {"CREDIT_NOTE": "CN", "RETURN": "RN", "IMPORT_COMMERCIAL": "EXP"}.get(inv["invoice_type"], "TAX")


def assign_numbers(w, reg):
    order = sorted(reg.invoices.values(), key=lambda i: (i["supplier_id"], _kind(i), i["invoice_date"], i["invoice_id"]))
    seq = {}
    for inv in order:
        kind = _kind(inv)
        fy = ids.fy_code(fy_start_year(inv["invoice_date"]))
        key = (inv["supplier_id"], kind, fy if kind != "EXP" else "")
        seq[key] = seq.get(key, 0) + 1
        n = seq[key]
        if kind == "TAX":
            inv["invoice_number"] = ids.invoice_number(ids.invoice_series(w.party_name(inv["supplier_id"])), fy, n)
        elif kind == "EXP":
            inv["invoice_number"] = f"SYEXP-{n:05d}"
        else:
            inv["invoice_number"] = ids.invoice_number(f"SY{kind}", fy, n)


def assign_shared_numbers(w, reg, n_groups):
    """AN17 hard negatives: 2–5 legitimate invoices of one issuer share a number (handbook p.41)."""
    by_cm = {}
    for inv in reg.invoices.values():
        if inv["invoice_type"] == "FG_SALES" and inv["status"] == "issued":
            by_cm.setdefault((inv["company_id"], inv["invoice_date"][:7]), []).append(inv)
    cands = sorted(k for k, v in by_cm.items() if len({i["buyer_id"] for i in v}) >= 2)
    r = w.r("shared_numbers")
    chosen = sorted(r.sample(cands, min(n_groups, len(cands))))
    groups = []
    for key in chosen:
        invs = sorted(by_cm[key], key=lambda i: (i["invoice_date"], i["invoice_id"]))
        seen, uniq = set(), []
        for i in invs:
            if i["buyer_id"] not in seen:
                seen.add(i["buyer_id"])
                uniq.append(i)
        rr = w.r("shared_group", f"{key[0]}:{key[1]}")
        k = min(len(uniq), rr.choice([2, 2, 3, 3, 3, 4, 5]))
        members = uniq[:k]
        for m in members[1:]:
            m["invoice_number"] = members[0]["invoice_number"]
        groups.append([m["invoice_id"] for m in members])
    return groups
