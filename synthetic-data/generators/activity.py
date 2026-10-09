"""Clean-world activity: monthly sales, transactions, packaging inventory,
material-flow events and the synthetic recycling proxy. SYNTHETIC — EPRLens Demo.

Everything here is the *clean* world (no anomalies). Equations follow
docs/generator-assumptions.md; every parameter is an illustrative assumption.
"""
import math

from .world import beta, business_day, dirichlet, split_integer, weighted_pick

UNIT_FOR_SELLING = {"bottle": "bottles", "bag": "bags"}
PLASTIC_CATS = ("CAT_I", "CAT_II", "CAT_III", "CAT_IV")


def clip(x, lo, hi):
    return max(lo, min(hi, x))


def season_vector(cfg, industry):
    v = cfg["seasonality"][industry]
    m = sum(v) / 12.0
    return [x / m for x in v]


# ======================================================================== sales
def build_sales(w):
    """Product-month units (domestic + export) for every product. Returns dict and per-product price."""
    cfg, sc = w.cfg, w.cfg["sales"]
    sales, price, growth = {}, {}, {}
    from .archetypes import UNIT_PRICE
    for c in w.companies:
        cid = c["company_id"]
        r = w.r("sales", cid)
        g = clip(r.gauss(sc["growth"]["mean"], sc["growth"]["sd"]), sc["growth"]["min"], sc["growth"]["max"])
        growth[cid] = g
        prods = w.products_by_company[cid]
        shares = dirichlet(r, [sc["product_share_alpha"]] * len(prods))
        season = season_vector(cfg, c["industry"])
        exporter = r.random() < sc["export_company_share"]
        exp_share = r.uniform(*sc["export_unit_share"]) if exporter else 0.0
        lo, hi = UNIT_PRICE[c["industry"]]
        for p, share in zip(prods, shares):
            pid = p["product_id"]
            pr = w.r("price", pid)
            price[pid] = round(math.exp(pr.uniform(math.log(lo), math.log(hi))), 2)
            first, last = w.active_months(p)
            in_window_launch = p["launch_date"][:7] >= w.months[0]
            ramp_len = r.randint(*sc["launch_ramp_months"])
            base = c["annual_units"] * share / 12.0
            for t, month in enumerate(w.months):
                eps = r.gauss(0, sc["noise_sd"])  # always drawn → stable stream
                if t < first or t > last:
                    continue
                ramp = min(1.0, (t - first + 1) / ramp_len) if in_window_launch else 1.0
                u = base * (1 + g) ** (t / 12.0) * season[int(month[5:]) - 1] * ramp * (1 + eps)
                units = max(0, int(round(u)))
                if units == 0:
                    continue
                exp_units = int(round(units * exp_share))
                sales[(pid, t)] = {"domestic": units - exp_units, "export": exp_units}
    return sales, price, growth


# ======================================================================== transactions
def _txn(w, **kw):
    row = {
        "transaction_id": w.ids.next("TXN"), "company_id": None, "product_id": None, "component_id": None,
        "date": None, "transaction_type": None, "units": None, "state": None, "buyer_id": None,
        "buyer_epr_registered": None, "supplier_id": None, "raw_quantity": None, "raw_unit": None,
        "normalized_quantity_kg": None, "plastic_kg": None, "invoice_id": None, "status": "posted",
        "synthetic_flag": True,
    }
    row.update(kw)
    return row


def packaging_kg(w, pid, units, day):
    comps = w.components_on(pid, day)
    parts = [(c, round(units * c["weight_per_unit_g"] / 1000.0, 3)) for c in comps]
    total = round(sum(kg for _, kg in parts), 3)
    plastic = round(sum(kg for c, kg in parts if c["plastic_epr_relevant"]), 3)
    return parts, total, plastic


def build_sales_transactions(w, sales):
    sc = w.cfg["sales"]
    txns = []
    rows_w = sc["rows_per_product_month"]
    for c in w.companies:
        cid = c["company_id"]
        buyers = sorted(w.buyers_of.get(cid, []))
        if not buyers:
            continue
        rb = w.r("buyer_weights", cid)
        bweights = dirichlet(rb, [1.5] * len(buyers))
        states = c["states_operated"]
        sweights = dirichlet(rb, [3.0 if s == c["headquarters_state"] else 1.0 for s in states])
        ship_state = {}
        for b in buyers:
            bs = w.buyer[b]["state"]
            ship_state[b] = bs if bs in states else weighted_pick(w.r("shipto", f"{cid}:{b}"), states, sweights)
        n_active = max(1, int(round(len(buyers) * sc["active_buyer_share"])))
        for t, month in enumerate(w.months):
            ra = w.r("active_buyers", f"{cid}:{month}")
            active = sorted(ra.sample(buyers, n_active))
            aw = [bweights[buyers.index(b)] for b in active]
            day_of = {b: business_day(w.r("saledate", f"{cid}:{b}:{month}"), month) for b in active}
            for p in w.products_by_company[cid]:
                pid = p["product_id"]
                s = sales.get((pid, t))
                if not s:
                    continue
                rr = w.r("sale_rows", f"{pid}:{month}")
                n = int(weighted_pick(rr, list(rows_w), list(rows_w.values())))
                n = min(n, len(active))
                chosen = []
                pool, pw = list(active), list(aw)
                for _ in range(n):
                    b = weighted_pick(rr, pool, pw)
                    i = pool.index(b)
                    pool.pop(i)
                    pw.pop(i)
                    chosen.append(b)
                chosen.sort()
                if s["domestic"] > 0:
                    parts = split_integer(s["domestic"], dirichlet(rr, [2.0] * len(chosen)))
                    for b, units in zip(chosen, parts):
                        if units <= 0:
                            continue
                        day = day_of[b]
                        comp_parts, total, plastic = packaging_kg(w, pid, units, day)
                        tx = _txn(w, company_id=cid, product_id=pid, date=day, transaction_type="sale", units=units,
                                  state=ship_state[b], buyer_id=b, buyer_epr_registered=w.buyer[b]["epr_registered"],
                                  raw_quantity=units, raw_unit=UNIT_FOR_SELLING.get(p["selling_unit"], "pcs"),
                                  normalized_quantity_kg=total, plastic_kg=plastic)
                        tx["_parts"] = comp_parts
                        txns.append(tx)
                if s["export"] > 0:
                    day = business_day(w.r("exportdate", f"{pid}:{month}"), month)
                    comp_parts, total, plastic = packaging_kg(w, pid, s["export"], day)
                    tx = _txn(w, company_id=cid, product_id=pid, date=day, transaction_type="export_sale",
                              units=s["export"], state="EXPORT", raw_quantity=s["export"],
                              raw_unit=UNIT_FOR_SELLING.get(p["selling_unit"], "pcs"),
                              normalized_quantity_kg=total, plastic_kg=plastic)
                    tx["_parts"] = comp_parts
                    txns.append(tx)
    return txns


def build_returns(w, sales_txns):
    ic = w.cfg["invoices"]
    out = []
    for tx in sales_txns:
        if tx["transaction_type"] != "sale":
            continue
        r = w.r("return", tx["transaction_id"])
        if r.random() >= ic["return_row_probability"]:
            continue
        t = w.month_index[tx["date"][:7]]
        if t + 1 >= len(w.months):
            continue
        units = max(1, int(round(tx["units"] * r.uniform(*ic["return_units_share"]))))
        day = business_day(r, w.months[t + 1])
        comp_parts, total, plastic = packaging_kg(w, tx["product_id"], units, tx["date"])
        rt = _txn(w, company_id=tx["company_id"], product_id=tx["product_id"], date=day, transaction_type="return",
                  units=units, state=tx["state"], buyer_id=tx["buyer_id"], buyer_epr_registered=tx["buyer_epr_registered"],
                  raw_quantity=units, raw_unit=tx["raw_unit"], normalized_quantity_kg=total, plastic_kg=plastic)
        rt["_parts"] = comp_parts
        rt["_original_txn"] = tx["transaction_id"]
        out.append(rt)
    return out


# ======================================================================== purchases + inventory
def _purchase_units(w, comp, kg, supplier, r):
    """Choose how the purchase is recorded/invoiced: pcs for count suppliers, kg or MT otherwise."""
    pc = w.cfg["purchases"]
    if supplier["typical_unit"] in ("pcs", "rolls"):
        pcs = int(math.ceil(kg * 1000.0 / comp["weight_per_unit_g"]))
        return pcs, "pcs", round(pcs * comp["weight_per_unit_g"] / 1000.0, 3)
    kg_whole = int(math.ceil(kg))
    if kg_whole >= pc["print_mt_if_kg_at_least"] and r.random() < pc["print_mt_probability"]:
        mt = math.ceil(kg_whole / 10.0) / 100.0  # 2-decimal tonnes, rounded up
        return mt, "MT", round(mt * 1000.0, 3)
    lo, hi = pc["small_mt_range_kg"]
    if lo <= kg_whole < hi and r.random() < pc["small_mt_probability"]:
        mt = math.ceil(kg_whole / 10.0) / 100.0
        return mt, "MT", round(mt * 1000.0, 3)
    return kg_whole, "kg", float(kg_whole)


def build_purchases_and_events(w, sale_like_txns):
    """Purchases (domestic / import), packaging inventory and every clean material event."""
    pc = w.cfg["purchases"]
    events, purchases = [], []
    nt = len(w.months)
    # consumption per (product, component_name, month) from sales + exports (produced = sold)
    cons = {}
    for tx in sale_like_txns:
        if tx["transaction_type"] not in ("sale", "export_sale"):
            continue
        t = w.month_index[tx["date"][:7]]
        for comp, kg in tx["_parts"]:
            key = (tx["product_id"], comp["component_name"])
            cons.setdefault(key, [0.0] * nt)[t] += kg
    # TS02 / demo top-ups from SUP_TEST_001 (COMP_0001 Cola PET bottle)
    topups = {}
    if "COMP_0001" in w.company and "SUP_TEST_001" in w.supplier:
        key = ("PROD_000001", "PET bottle")
        if key in cons:
            r = w.r("ts02_topups")
            active = [t for t in range(nt) if cons[key][t] > 0]
            months = sorted(r.sample(active, min(pc["sup_test_001_topup_months"], len(active))))
            demo_t = w.month_index.get(pc["demo_half_tonne_month"])
            for t in months:
                if t != demo_t:
                    topups[(key, t)] = ("share", r.uniform(*pc["sup_test_001_topup_share"]))
            if demo_t is not None:
                topups[(key, demo_t)] = ("demo_half_tonne", None)
    for c in w.companies:
        cid = c["company_id"]
        rc = w.r("purchase_policy", cid)
        cycle = pc["order_cycle_months"][c["company_size"]]
        offset = rc.randrange(cycle)
        safety = rc.uniform(*pc["safety_stock"])
        import_share = rc.uniform(*pc["import_share"]) if c["importer"] else 0.0
        for p in w.products_by_company[cid]:
            pid = p["product_id"]
            for name in w.groups_by_product.get(pid, []):
                key = (pid, name)
                series = cons.get(key)
                if not series or sum(series) <= 0:
                    continue
                first = next(t for t in range(nt) if series[t] > 0)
                rg = w.r("inventory", f"{pid}:{name}")
                supplier_id = w.versions[key][0]["supplier_id"]
                supplier = w.supplier[supplier_id]
                first_buy = next((t for t in range(first, nt) if (t - offset) % cycle == 0), nt)
                opening = sum(series[first:first_buy]) * (1 + safety) + 0.5 * series[first]
                opening = round(opening, 3)
                comp0 = w.version_on(pid, name, f"{w.months[first]}-01")
                events.append(_event(w, cid, pid, comp0, "OPENING_BALANCE", f"{w.months[first]}-01", opening, "memo",
                                     "estimated"))
                for t in range(first, nt):
                    month = w.months[t]
                    purchased = 0.0
                    extra = topups.get((key, t))
                    if extra:
                        tx = _topup_txn(w, cid, pid, name, t, series[t], extra)
                        purchases.append(tx)
                        purchased += tx["normalized_quantity_kg"]
                    if (t - offset) % cycle == 0:
                        need = sum(series[t:t + cycle]) * (1 + safety) - opening - purchased
                        if need > 0.0005:
                            day = business_day(w.r("buydate", f"{cid}:{supplier_id}:{month}"), month)
                            comp = w.version_on(pid, name, day)
                            rp = w.r("purchase", f"{pid}:{name}:{month}")
                            qty, unit, kg = _purchase_units(w, comp, need, supplier, rp)
                            ttype = "import" if rp.random() < import_share else "purchase"
                            tx = _txn(w, company_id=cid, product_id=pid, component_id=comp["component_id"], date=day,
                                      transaction_type=ttype, units=qty if unit == "pcs" else None,
                                      state=c["headquarters_state"], supplier_id=supplier_id, raw_quantity=qty,
                                      raw_unit=unit, normalized_quantity_kg=kg,
                                      plastic_kg=kg if comp["plastic_epr_relevant"] else 0.0)
                            tx["_comp"] = comp
                            for part in _split_lots(w, tx, rp, pc["lot_split_probability"]):
                                purchases.append(part)
                            purchased += kg
                    consumed = round(series[t], 3)
                    wo = 0.0
                    if consumed > 0 and rg.random() < pc["written_off_month_probability"]:
                        wo = round(consumed * rg.uniform(*pc["written_off_share"]), 3)
                    closing = round(opening + purchased - consumed - wo, 3)
                    assert closing >= -0.01, (key, month, closing)
                    mid = f"{month}-15"
                    comp_m = w.version_on(pid, name, mid)
                    if consumed > 0:
                        events.append(_event(w, cid, pid, comp_m, "CONSUMED", mid, consumed, "out", "estimated"))
                    if wo > 0:
                        events.append(_event(w, cid, pid, comp_m, "WRITTEN_OFF", mid, wo, "out", "declared"))
                    events.append(_event(w, cid, pid, comp_m, "CLOSING_BALANCE", f"{month}-28", max(closing, 0.0),
                                         "memo", "estimated"))
                    opening = closing
    return purchases, events


def _split_lots(w, tx, r, p):
    """Some deliveries arrive in two lots: two internal records, two invoice lines (same invoice)."""
    if tx["raw_unit"] not in ("pcs", "kg") or tx["raw_quantity"] < 2 or r.random() >= p:
        return [tx]
    share = r.uniform(0.4, 0.6)
    q1 = int(round(tx["raw_quantity"] * share))
    q1 = min(max(q1, 1), tx["raw_quantity"] - 1)
    q2 = tx["raw_quantity"] - q1
    comp = tx["_comp"]
    out = []
    for i, q in enumerate((q1, q2), start=1):
        kg = round(q * comp["weight_per_unit_g"] / 1000.0, 3) if tx["raw_unit"] == "pcs" else float(q)
        part = dict(tx) if i == 1 else _txn(w, **{k: v for k, v in tx.items() if not k.startswith("_") and k != "transaction_id"})
        part.update(raw_quantity=q, units=q if tx["raw_unit"] == "pcs" else None, normalized_quantity_kg=kg,
                    plastic_kg=kg if comp["plastic_epr_relevant"] else 0.0)
        part["_comp"], part["_lot"] = comp, (i, 2)
        out.append(part)
    return out


def _topup_txn(w, cid, pid, name, t, cons_kg, extra):
    month = w.months[t]
    day = business_day(w.r("ts02_date", month), month)
    comp = w.version_on(pid, name, day)
    kind, share = extra
    if kind == "demo_half_tonne":
        pcs = int(round(500.0 * 1000.0 / comp["weight_per_unit_g"]))
        kg = round(pcs * comp["weight_per_unit_g"] / 1000.0, 3)
        qty, unit = round(kg / 1000.0, 3), "MT"
    else:
        pcs = max(1, int(round(cons_kg * share * 1000.0 / comp["weight_per_unit_g"])))
        kg = round(pcs * comp["weight_per_unit_g"] / 1000.0, 3)
        qty, unit = pcs, "pcs"
    tx = _txn(w, company_id=cid, product_id=pid, component_id=comp["component_id"], date=day,
              transaction_type="purchase", units=pcs, state=w.company[cid]["headquarters_state"],
              supplier_id="SUP_TEST_001", raw_quantity=qty, raw_unit=unit, normalized_quantity_kg=kg, plastic_kg=kg)
    tx["_comp"] = comp
    tx["_topup"] = kind
    return tx


def _event(w, cid, pid, comp, etype, day, kg, direction, status, src=None, line=None, counterparty=None):
    return {
        "event_id": None, "company_id": cid, "product_id": pid,
        "component_id": comp["component_id"] if comp else None,
        "material": comp["material"] if comp else None,
        "synthetic_category": comp["synthetic_category"] if comp else None,
        "event_type": etype, "date": day, "period": day[:7], "kg": round(kg, 3), "direction": direction,
        "source_document_id": src, "source_line_id": line, "counterparty_id": counterparty, "status": status,
        "supersedes_event_id": None, "synthetic_flag": True,
    }


def market_events(w, txns):
    """PLACED_ON_MARKET / EXPORTED / RETURNED / PURCHASED events from transactions (source ids filled later)."""
    out = []
    for tx in txns:
        tt = tx["transaction_type"]
        if tt in ("sale", "export_sale", "return"):
            etype = {"sale": "PLACED_ON_MARKET", "export_sale": "EXPORTED", "return": "RETURNED"}[tt]
            direction = "memo"
            for comp, kg in tx["_parts"]:
                ev = _event(w, tx["company_id"], tx["product_id"], comp, etype, tx["date"], kg, direction,
                            "document_supported" if tt != "export_sale" else "declared",
                            counterparty=tx["buyer_id"])
                ev["_txn"] = tx["transaction_id"]
                out.append(ev)
        elif tt in ("purchase", "import"):
            ev = _event(w, tx["company_id"], tx["product_id"], tx["_comp"], "PURCHASED", tx["date"],
                        tx["normalized_quantity_kg"], "in", "document_supported", counterparty=tx["supplier_id"])
            ev["_txn"] = tx["transaction_id"]
            out.append(ev)
    return out


# ======================================================================== recycling proxy
def build_recycling(w, pom_events):
    rc = w.cfg["recycling"]
    lag = {int(k): v for k, v in rc["generation_lag_weights"].items()}
    nt = len(w.months)
    pom = {}
    mats = {}
    for ev in pom_events:
        if ev["event_type"] != "PLACED_ON_MARKET" or ev["synthetic_category"] not in PLASTIC_CATS:
            continue
        key = (ev["company_id"], ev["synthetic_category"])
        pom.setdefault(key, [0.0] * nt)[w.month_index[ev["period"]]] += ev["kg"]
        mats.setdefault(key, set()).add(ev["material"])
    rows, events = [], []
    for (cid, cat) in sorted(pom):
        series = pom[(cid, cat)]
        recs = [w.recycler[r] for r in w.recyclers_of.get(cid, [])]
        cands = [r for r in recs if r["registered"] and set(r["supported_materials"]) & mats[(cid, cat)]]
        if not cands:
            continue
        for t in range(max(lag), nt):
            gen = sum(series[t - k] * wgt for k, wgt in lag.items())
            if gen <= 0:
                continue
            month = w.months[t]
            r = w.r("recycling", f"{cid}:{cat}:{month}")
            collected = gen * beta(r, *rc["collection_beta"])
            recycled = collected * beta(r, *rc["recycling_beta"])
            rec = cands[r.randrange(len(cands))]
            credits = recycled * beta(r, *rc["documentation_beta"])
            row = {
                "recycling_record_id": w.ids.next("RCY"), "company_id": cid, "month": month,
                "synthetic_category": cat, "waste_generated_kg": round(gen, 3),
                "waste_collected_kg": round(collected, 3), "waste_recycled_kg": round(recycled, 3),
                "recycler_id": rec["recycler_id"], "recycler_registered": rec["registered"],
                "credits_documented_kg": round(credits, 3), "basis": "synthetic_proxy_v1", "synthetic_flag": True,
            }
            rows.append(row)
    return rows


def recycling_events(w, rows):
    out = []
    for row in rows:
        day = f"{row['month']}-28"
        for etype, field in (("WASTE_GENERATED_PROXY", "waste_generated_kg"), ("COLLECTED", "waste_collected_kg"),
                             ("RECYCLED", "waste_recycled_kg"), ("CREDITS_DOCUMENTED", "credits_documented_kg")):
            ev = _event(w, row["company_id"], None, None, etype, day, row[field], "memo",
                        "estimated" if etype == "WASTE_GENERATED_PROXY" else "declared",
                        src=row["recycling_record_id"], counterparty=row["recycler_id"])
            ev["synthetic_category"] = row["synthetic_category"]
            out.append(ev)
    return out
