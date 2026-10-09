"""Data loading, dataset validation, leakage-safe feature tables and labels.
SYNTHETIC — EPRLens Demo."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import anomaly_features as af
from . import forecast_features as ff
from .common import ROOT, sha256_file

LABEL_COLUMNS = {"is_anomaly", "anomaly_type"}  # present in invoices.csv as ground-truth summaries — dropped at load


# ================================================================ validation
def validate_dataset(cfg, log):
    data = ROOT / cfg["data_dir"]
    man = json.loads((data / "manifests" / "MANIFEST.json").read_text(encoding="utf-8"))
    if man["dataset_sha256"] != cfg["expected_dataset_sha256"]:
        raise SystemExit(f"dataset_sha256 {man['dataset_sha256']} != expected {cfg['expected_dataset_sha256']}")
    bad = [k for k, v in {**man["file_hashes"], **man["document_hashes"]}.items() if sha256_file(data / k) != v]
    if bad:
        raise SystemExit(f"{len(bad)} dataset files do not match MANIFEST hashes, e.g. {bad[:3]}")
    splits = pd.read_csv(data / "csv" / "splits.csv")
    counts = splits["anomaly_split"].value_counts().to_dict()
    panel = pd.read_csv(data / "csv" / "forecast_panel.csv")
    checks = {
        "dataset_sha256": man["dataset_sha256"], "files_verified": len(man["file_hashes"]) + len(man["document_hashes"]),
        "anomaly_company_split": counts, "forecast_holdout_companies": int(splits["forecast_holdout"].sum()),
        "forecast_rows": int(len(panel)), "forecast_time_split": panel["time_split"].value_counts().to_dict(),
        "counts": man["counts"], "generator_version": man["generator_version"], "seed": man["seed"],
    }
    assert counts == {"train": 120, "validation": 40, "test": 40}, counts
    log.info(f"dataset verified: {checks['files_verified']} files, sha {man['dataset_sha256'][:16]}")
    return checks


# ================================================================ forecasting
def season_table_from_train(panel_train):
    """Industry x month-of-year seasonality index from TRAIN rows only (no leakage)."""
    p = panel_train.copy()
    p["rel"] = p["packaging_kg"] / p.groupby("product_id")["packaging_kg"].transform("mean")
    t = p.groupby(["industry", "month_num"])["rel"].mean().unstack()
    out = {}
    for ind in ff.INDUSTRIES:
        if ind in t.index:
            row = [float(t.loc[ind].get(m, np.nan)) for m in range(1, 13)]
            mean = np.nanmean(row)
            out[ind] = [round(x / mean, 6) if x == x else 1.0 for x in row]
        else:
            out[ind] = [1.0] * 12
    return out


def forecast_split(row):
    if row["time_split"] == "test":
        return "test"
    if row["company_holdout"]:
        return "unused_holdout_window"   # held-out companies are never seen before the final test
    return row["time_split"]


def build_forecast_frame(cfg):
    data = ROOT / cfg["data_dir"]
    panel = pd.read_csv(data / "csv" / "forecast_panel.csv")
    companies = pd.read_csv(ROOT / cfg["masters_dir"] / "companies.csv")[["company_id", "company_size"]]
    panel["fsplit"] = panel.apply(forecast_split, axis=1)
    train = panel[panel["fsplit"] == "train"]
    season = season_table_from_train(train)
    series = {}
    for r in panel.itertuples(index=False):
        series.setdefault(r.product_id, {})[r.month] = {"month": r.month, "packaging_kg": r.packaging_kg,
                                                         "units_sold": r.units_sold,
                                                         "weight_per_unit_g": r.weight_per_unit_g}
    feats, raws = [], []
    for r in panel.itertuples(index=False):
        s = series[r.product_id]
        hist = [s[m] for m in (ff.month_add(r.month, -k) for k in range(12, -1, -1)) if m in s]
        f, raw, origin, target = ff.build_features(hist, r.industry, season, validate=False)
        assert target == r.target_month
        feats.append(f)
        raws.append(raw)
    X = pd.DataFrame(feats, columns=ff.FEATURES)
    R = pd.DataFrame(raws)
    meta = panel[["company_id", "product_id", "industry", "month", "target_month", "t_index", "time_split",
                  "company_holdout", "fsplit", "packaging_kg", "next_month_packaging_kg", "lag_1", "lag_12",
                  "rolling_mean_3"]].reset_index(drop=True)
    meta = meta.merge(companies, on="company_id", how="left")
    df = pd.concat([meta, X, R.add_prefix("raw_")], axis=1)
    return df, season


# ================================================================ anomaly records
def _none(v):
    if v is None:
        return None
    if isinstance(v, float) and v != v:
        return None
    return v


def load_observed(cfg):
    data = ROOT / cfg["data_dir"] / "csv"
    inv = pd.read_csv(data / "invoices.csv", low_memory=False)
    labels = inv[["invoice_id", "invoice_type", "company_id", "is_anomaly", "anomaly_type", "status"]].copy()
    inv = inv.drop(columns=list(LABEL_COLUMNS))          # ground truth never enters records / features
    lines = pd.read_csv(data / "invoice_lines.csv", dtype={"hsn_code": str}, low_memory=False,
                        keep_default_na=False, na_values=[""])  # "NA" is a real category value (not plastic)
    tx = pd.read_csv(data / "transactions.csv", low_memory=False)
    rec = pd.read_csv(data / "recycling.csv")
    gt = pd.read_csv(data / "anomaly_ground_truth.csv")
    splits = pd.read_csv(data / "splits.csv")
    return inv, lines, tx, rec, gt, splits, labels


def _masters(cfg):
    m = ROOT / cfg["masters_dir"]
    comps = pd.read_csv(m / "packaging_components.csv", keep_default_na=False, na_values=[""]).set_index("component_id")
    sups = pd.read_csv(m / "suppliers.csv").set_index("supplier_id")
    gst = {}
    for name, key in (("companies", "company_id"), ("suppliers", "supplier_id"), ("buyers", "buyer_id"),
                      ("recyclers", "recycler_id")):
        t = pd.read_csv(m / f"{name}.csv")
        for k, v in zip(t[key], t["fake_gstin"]):
            gst[k] = isinstance(v, str) and len(v) > 0
    recs = pd.read_csv(m / "recyclers.csv").set_index("recycler_id")
    return comps, sups, gst, recs


def build_records(cfg, train_companies=None):
    """Invoice records (all invoice types except recycler processing) + recycling records, plus contexts."""
    inv, lines, tx, rec, gt, splits, labels = load_observed(cfg)
    comps, sups, gst, recyclers = _masters(cfg)
    inv = inv[inv["invoice_type"] != "RECYCLER_PROCESSING"].copy()
    inv["inr_total"] = inv["total"] * inv["fx_rate"].fillna(1.0)
    inv["month"] = inv["invoice_date"].fillna("").str[:7]
    txd = {r["transaction_id"]: r for r in tx.to_dict("records")}
    # ---- item monthly quantities (observed records; unsupervised)
    t = tx[tx["status"] == "posted"].copy()
    t["month"] = t["date"].str[:7]
    sale = t[t["transaction_type"] == "sale"].groupby(["product_id", "month"])["units"].sum()
    purch = t[t["transaction_type"].isin(["purchase", "import"])].groupby(
        ["product_id", "supplier_id", "month"])["normalized_quantity_kg"].sum()
    sale_med = sale[sale > 0].groupby(level=0).median()
    purch_med = purch[purch > 0].groupby(level=[0, 1]).median()
    sale_d, purch_d = sale.to_dict(), purch.to_dict()
    # ---- issuer -> company statistics
    grp = inv.groupby(["supplier_id", "company_id", "invoice_type"])["inr_total"]
    med_total = grp.median().to_dict()
    cnt = inv.groupby(["supplier_id", "company_id"]).size().to_dict()
    # ---- duplicate composite key
    key_cols = ["supplier_id", "invoice_number", "invoice_date", "buyer_id", "total"]
    kk = inv[key_cols].astype(object).where(inv[key_cols].notna(), "").map(str).agg("|".join, axis=1)
    first_by_key = {}
    earlier = {}
    for iid, k in sorted(zip(inv["invoice_id"], kk)):
        if k in first_by_key:
            earlier[iid] = [first_by_key[k]]
        else:
            first_by_key[k] = iid
    # ---- reference rate per kg (supplier|material) from TRAIN companies only
    li = lines.merge(inv[["invoice_id", "supplier_id", "company_id", "fx_rate", "invoice_type"]], on="invoice_id")
    li = li[li["normalized_quantity_kg"] > 0]
    if train_companies is not None:
        li_tr = li[li["company_id"].isin(train_companies)]
    else:
        li_tr = li
    rate = (li_tr["taxable_value"] * li_tr["fx_rate"].fillna(1.0) / li_tr["normalized_quantity_kg"])
    rate_ref = rate.groupby(li_tr["supplier_id"] + "|" + li_tr["material"].fillna("")).median().to_dict()
    rate_ref = {k: float(v) for k, v in rate_ref.items() if not k.endswith("|")}
    # ---- assemble
    lines_by = {}
    for l in lines.to_dict("records"):
        lines_by.setdefault(l["invoice_id"], []).append(l)
    records = []
    for h in inv.to_dict("records"):
        iid = h["invoice_id"]
        header = {k: _none(h.get(k)) for k in ("invoice_id", "invoice_number", "invoice_type", "company_id",
                                               "supplier_id", "buyer_id", "invoice_date", "status", "supplier_gstin",
                                               "buyer_gstin", "currency", "fx_rate", "total_taxable_value", "gst",
                                               "total", "original_invoice_id")}
        month = h["month"]
        ls, ctx = [], {"item_month_qty": {}, "item_median_qty": {}, "item_prev_month_qty": {}}
        for l in sorted(lines_by.get(iid, []), key=lambda x: x["line_no"]):
            line = {k: _none(l.get(k)) for k in ("line_no", "item_description", "product_id", "component_id",
                                                 "material", "plastic_category", "hsn_code", "raw_quantity",
                                                 "raw_unit", "weight_per_unit_g", "normalized_quantity_kg",
                                                 "recorded_quantity_kg", "rate", "taxable_value", "gst_rate",
                                                 "gst_amount", "transaction_id")}
            if line["hsn_code"] is not None:
                line["hsn_code"] = str(line["hsn_code"])
            txr = txd.get(l["transaction_id"]) if isinstance(l["transaction_id"], str) else None
            line["transaction"] = None if txr is None else {k: _none(txr[k]) for k in (
                "transaction_id", "transaction_type", "status", "raw_quantity", "raw_unit", "normalized_quantity_kg",
                "supplier_id", "date")}
            cid = line["component_id"]
            line["master_component"] = None if cid is None else {
                "material": comps.at[cid, "material"], "synthetic_category": comps.at[cid, "synthetic_category"],
                "weight_per_unit_g": float(comps.at[cid, "weight_per_unit_g"]),
                "component_form": comps.at[cid, "component_form"]}
            m = month or (line["transaction"] or {}).get("date", "")[:7]
            key = str(line["line_no"])
            prev = ff.month_add(m, -1) if m else None
            if h["invoice_type"] == "FG_SALES" and line["product_id"]:
                ctx["item_month_qty"][key] = _f(sale_d.get((line["product_id"], m)))
                ctx["item_median_qty"][key] = _f(sale_med.get(line["product_id"]))
                ctx["item_prev_month_qty"][key] = _f(sale_d.get((line["product_id"], prev)))
            elif h["invoice_type"] in ("PKG_PURCHASE", "PKG_COMPONENT", "MULTI_MATERIAL", "IMPORT_COMMERCIAL") \
                    and line["product_id"]:
                k2 = (line["product_id"], h["supplier_id"])
                ctx["item_month_qty"][key] = _f(purch_d.get((*k2, m)))
                ctx["item_median_qty"][key] = _f(purch_med.get(k2))
                ctx["item_prev_month_qty"][key] = _f(purch_d.get((*k2, prev)))
            ls.append(line)
        ctx["issuer_company_median_total_inr"] = _f(med_total.get((h["supplier_id"], h["company_id"], h["invoice_type"])))
        ctx["issuer_company_invoice_count"] = int(cnt.get((h["supplier_id"], h["company_id"]), 0))
        ctx["earlier_same_key_invoice_ids"] = earlier.get(iid, [])
        sup = None
        if h["supplier_id"] in sups.index:
            sup = {"supported_materials": str(sups.at[h["supplier_id"], "supported_materials"]).split("|"),
                   "supported_component_forms": [x for x in str(sups.at[h["supplier_id"], "supported_component_forms"]).split("|") if x and x != "nan"]}
        records.append({"record_type": "invoice", "record_id": iid, "company_id": h["company_id"],
                        "invoice": header, "lines": ls, "context": ctx,
                        "master": {"issuer_has_gstin": gst.get(h["supplier_id"], False), "issuer_supplier": sup}})
    for r in rec.to_dict("records"):
        records.append({"record_type": "recycling", "record_id": r["recycling_record_id"], "company_id": r["company_id"],
                        "recycling": {k: _none(v) for k, v in r.items() if k != "synthetic_flag"},
                        "master": {"recycler_registered": bool(recyclers.at[r["recycler_id"], "registered"])}})
    return records, rate_ref, (labels, gt, splits)


def _f(v):
    if v is None:
        return None
    v = float(v)
    return None if v != v else v


def build_labels(records, labels, gt, splits):
    """Evaluation labels per record — kept separate from features (never model inputs)."""
    split = dict(zip(splits["company_id"], splits["anomaly_split"]))
    lab = labels.set_index("invoice_id")
    rec_gt = gt[(gt["record_type"] == "recycling") & (gt["is_anomaly"])].set_index("record_id")["anomaly_type"].to_dict()
    an17 = set(gt[(gt["anomaly_type"] == "AN17")]["invoice_id"])
    rows = []
    for r in records:
        if r["record_type"] == "invoice":
            row = lab.loc[r["record_id"]]
            y = bool(row["is_anomaly"])
            at = row["anomaly_type"] if y else None
            inv = r["invoice"]
            if r["record_id"] in an17:
                group = "tricky_AN17_shared_number"
            elif y:
                group = "anomaly"
            elif inv["status"] == "cancelled" or inv["invoice_type"] in ("CREDIT_NOTE", "RETURN"):
                group = "legit_special_document"
            else:
                group = "routine_normal"
        else:
            at = rec_gt.get(r["record_id"])
            y = at is not None
            group = "anomaly" if y else "routine_normal"
        rows.append({"record_id": r["record_id"], "record_type": r["record_type"], "company_id": r["company_id"],
                     "split": split[r["company_id"]], "y": int(y), "anomaly_type": at, "group": group})
    return pd.DataFrame(rows)


def anomaly_feature_table(records, rate_ref):
    rows = []
    for r in records:
        if r["record_type"] != "invoice":
            continue
        f = af.anomaly_features(r, rate_ref)
        f["record_id"] = r["record_id"]
        rows.append(f)
    return pd.DataFrame(rows)[["record_id"] + af.FEATURES]
