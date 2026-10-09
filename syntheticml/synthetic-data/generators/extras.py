"""Splits, what-if scenarios, business descriptions and the forecasting panel.
SYNTHETIC — EPRLens Demo."""
from .world import fy_label


# ================================================================ splits
def build_splits(w):
    sp = w.cfg["splits"]
    cids = [c["company_id"] for c in w.companies]
    by_hash = sorted(cids, key=lambda c: w.sub_seed("anomaly_split", c))
    n = len(cids)
    n_train = int(round(n * sp["anomaly"]["train"]))
    n_val = int(round(n * sp["anomaly"]["validation"]))
    anomaly = {}
    for i, c in enumerate(by_hash):
        anomaly[c] = "train" if i < n_train else ("validation" if i < n_train + n_val else "test")
    n_hold = int(round(sp["forecast"]["holdout_companies"] * n / 200.0))
    hold = set(sorted(cids, key=lambda c: w.sub_seed("forecast_holdout", c))[:n_hold])
    rows = [{"company_id": c, "anomaly_split": anomaly[c], "forecast_holdout": c in hold, "synthetic_flag": True}
            for c in cids]
    return anomaly, hold, rows


# ================================================================ scenarios
def build_scenarios(w, sales):
    sc = w.cfg["scenarios"]
    last_fy = fy_label(w.months[-1])
    fy_months = [i for i, m in enumerate(w.months) if fy_label(m) == last_fy]
    day = w.months[-1] + "-28"
    scenarios, results = [], []
    n = 0
    for c in w.companies:
        best = None
        for p in w.products_by_company[c["company_id"]]:
            units = sum(sales.get((p["product_id"], t), {}).get("domestic", 0) + sales.get((p["product_id"], t), {}).get("export", 0)
                        for t in fy_months)
            comps = w.components_on(p["product_id"], day)
            plastic_g = sum(x["weight_per_unit_g"] for x in comps if x["plastic_epr_relevant"])
            key = units * plastic_g
            if units > 0 and plastic_g > 0 and (best is None or key > best[0]):
                best = (key, p, units, comps)
        if not best:
            continue
        _, p, units, comps = best
        main = max((x for x in comps if x["plastic_epr_relevant"]), key=lambda x: (x["weight_per_unit_g"], x["component_id"]))
        total_g = sum(x["weight_per_unit_g"] for x in comps)
        plastic_g = sum(x["weight_per_unit_g"] for x in comps if x["plastic_epr_relevant"])
        for pct in sc["reduction_pct"]:
            n += 1
            sid = f"SCN_{n:06d}"
            bw = main["weight_per_unit_g"]
            pw = round(bw * (1 - pct / 100.0), 4)
            base_kg = round(units * bw / 1000.0, 3)
            prop_kg = round(units * pw / 1000.0, 3)
            red = round(base_kg - prop_kg, 3)
            assumptions = (f"Reduce {main['component_name']} ({main['material']}) of {p['product_name']} by {pct}% "
                           f"at unchanged {last_fy} units; assumes a feasible, safe redesign. Synthetic; not a compliance "
                           f"or cost claim.")
            scenarios.append({"scenario_id": sid, "company_id": c["company_id"], "product_id": p["product_id"],
                              "component_id": main["component_id"], "reduction_pct": pct,
                              "baseline_weight_g": bw, "proposed_weight_g": pw, "units": units, "baseline_kg": base_kg,
                              "proposed_kg": prop_kg, "projected_reduction_kg": red, "assumptions": assumptions,
                              "synthetic_flag": True})
            tb = round(units * total_g / 1000.0, 3)
            pb = round(units * plastic_g / 1000.0, 3)
            results.append({"scenario_id": sid, "company_id": c["company_id"], "product_id": p["product_id"],
                            "baseline_kg": tb, "proposed_kg": round(tb - red, 3), "projected_reduction_kg": red,
                            "reduction_pct_effective": round(red / tb * 100.0, 4) if tb else 0.0,
                            "plastic_baseline_kg": pb, "plastic_proposed_kg": round(pb - red, 3),
                            "plastic_reduction_kg": red, "units_basis": "historical", "period": last_fy,
                            "disclaimer": "Hypothetical; assumes unchanged sales and a feasible redesign; not a compliance or cost claim.",
                            "synthetic_flag": True})
    return scenarios, results


# ================================================================ business descriptions
SIZE_WORD = {"micro": "very small", "small": "small", "medium": "mid-sized", "large": "large"}


def build_descriptions(w):
    bd = w.cfg["business_descriptions"]
    cids = sorted((c["company_id"] for c in w.companies), key=lambda c: w.sub_seed("desc_pick", c))
    chosen = sorted(cids[: min(bd["count"], len(cids))])
    out = []
    for i, cid in enumerate(chosen, start=1):
        c = w.company[cid]
        r = w.r("description", cid)
        x = r.random()
        difficulty = "vague" if x < bd["vague_share"] else (
            "contradictory" if x < bd["vague_share"] + bd["contradictory_share"] else "plain")
        cats = sorted({p["product_category"].lower() for p in w.products_by_company[cid]})[:3]
        mats = sorted({w.versions[(p["product_id"], n)][0]["material"] for p in w.products_by_company[cid]
                       for n in w.groups_by_product.get(p["product_id"], [])})
        pack = ", ".join(m for m in mats if m not in ("CARDBOARD", "PAPER"))[:60] or "paper-based packs"
        n_states = len(c["states_operated"])
        if difficulty == "plain":
            roles = []
            if c["manufacturer"]:
                roles.append("we manufacture our products in our own plant")
            if c["importer"]:
                roles.append("we import part of our range and packaging")
            if c["brand_owner"]:
                roles.append("everything is sold under our own brands")
            text = (f"We are a {SIZE_WORD[c['company_size']]} {c['industry'].lower()} company headquartered in "
                    f"{c['headquarters_state']}. {'; '.join(roles).capitalize()}. Our main lines are {', '.join(cats)}, "
                    f"packed mainly in {pack}. We sell in {n_states} state{'s' if n_states > 1 else ''}.")
        elif difficulty == "vague":
            text = (f"Our {', '.join(cats)} reach customers across {n_states} Indian state{'s' if n_states > 1 else ''}. "
                    f"We work with packaging partners for {pack} packs and keep growing our presence.")
        else:
            bits = []
            bits.append("Our goods are made at partner facilities" if not c["manufacturer"] else "Production happens at our own unit")
            bits.append("and some finished stock arrives from overseas partners" if c["importer"] else "with no overseas sourcing")
            bits.append("but the labels carry another company's mark" if not c["brand_owner"] else "under labels we own")
            text = (f"{bits[0]} {bits[1]}, {bits[2]}. We operate in the {c['industry'].lower()} space with lines such as "
                    f"{', '.join(cats)}.")
        out.append({"description_id": f"DESC_{i:04d}", "company_id": cid, "description": text + " (SYNTHETIC — EPRLens Demo)",
                    "expected_manufacturer": c["manufacturer"], "expected_importer": c["importer"],
                    "expected_brand_owner": c["brand_owner"], "expected_industry": c["industry"],
                    "difficulty": difficulty, "synthetic_flag": True})
    return out


# ================================================================ forecasting panel (clean)
def build_forecast_panel(w, sales, hold):
    sp = w.cfg["splits"]["forecast"]
    nt = len(w.months)
    tr_end = sp["train_months"] - 1
    va_end = tr_end + sp["validation_months"]
    # industry × month-of-year seasonality index from TRAIN months only (no leakage)
    agg = {}
    series = {}
    for c in w.companies:
        for p in w.products_by_company[c["company_id"]]:
            pid = p["product_id"]
            ser = []
            for t, m in enumerate(w.months):
                s = sales.get((pid, t))
                units = (s["domestic"] + s["export"]) if s else 0
                comps = w.components_on(pid, f"{m}-15")
                wg = sum(x["weight_per_unit_g"] for x in comps)
                ser.append((units, wg, round(units * wg / 1000.0, 3)))
            series[pid] = (c, ser)
            if c["company_id"] in hold:
                continue
            for t in range(0, tr_end + 1):
                if ser[t][0] > 0:
                    key = (c["industry"], int(w.months[t][5:]))
                    a = agg.setdefault(key, [0.0, 0])
                    mean_p = sum(x[2] for x in ser[: tr_end + 1] if x[0] > 0) / max(1, sum(1 for x in ser[: tr_end + 1] if x[0] > 0))
                    if mean_p > 0:
                        a[0] += ser[t][2] / mean_p
                        a[1] += 1
    sidx = {k: round(v[0] / v[1], 4) for k, v in agg.items() if v[1]}
    rows = []
    for pid in sorted(series):
        c, ser = series[pid]
        for t in range(nt - 1):
            units, wg, kg = ser[t]
            if units == 0 or ser[t + 1][0] == 0:
                continue
            lag = lambda k: ser[t - k][2] if t - k >= 0 and ser[t - k][0] > 0 else None  # noqa: E731
            hist = [ser[t - k][2] for k in range(3) if t - k >= 0 and ser[t - k][0] > 0]
            hist6 = [ser[t - k][2] for k in range(6) if t - k >= 0 and ser[t - k][0] > 0]
            prev_units = ser[t - 1][0] if t >= 1 else 0
            target_t = t + 1
            split = "train" if target_t <= tr_end else ("validation" if target_t <= va_end else "test")
            rows.append({
                "company_id": c["company_id"], "product_id": pid, "industry": c["industry"], "month": w.months[t],
                "month_num": int(w.months[t][5:]), "t_index": t, "units_sold": units, "weight_per_unit_g": round(wg, 3),
                "packaging_kg": kg, "lag_1": lag(1), "lag_2": lag(2), "lag_3": lag(3), "lag_6": lag(6), "lag_12": lag(12),
                "rolling_mean_3": round(sum(hist) / len(hist), 3) if len(hist) == 3 else None,
                "rolling_mean_6": round(sum(hist6) / len(hist6), 3) if len(hist6) == 6 else None,
                "sales_growth": round(units / prev_units - 1, 6) if prev_units else None,
                "seasonality_index": sidx.get((c["industry"], int(w.months[t][5:]))),
                "target_month": w.months[target_t], "next_month_packaging_kg": ser[target_t][2],
                "time_split": split, "company_holdout": c["company_id"] in hold, "synthetic_flag": True,
            })
    return rows
