"""Generate the full EPRLens synthetic dataset from the committed entity master.

SYNTHETIC — EPRLens Demo.

    python synthetic-data/generate.py --config synthetic-data/config.yaml --out data/generated
    python synthetic-data/generate.py --out data/pilot --companies 5 --pdfs 20      # quick pilot

Outputs (under --out, git-ignored):
    csv/*.csv              observed world (with injected anomalies) + panels, splits, ground truth
    csv/clean/*.csv        the same tables before anomaly injection
    invoices/pdf/*.pdf     exactly 1,000 searchable synthetic invoices (full run)
    invoices/json/*.json   exactly 1,000 matching ground-truth files
    manifests/MANIFEST.json
Committed provenance copy: synthetic-data/MANIFEST.json (full run only).
"""
import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "schemas"))

import spec  # noqa: E402
from generators import activity, anomalies, documents, extras, invoicing  # noqa: E402
from generators.tableio import sha256_file, validate_rows, write_csv, write_json  # noqa: E402
from generators.world import World, fy_label  # noqa: E402

EVENT_ORDER = {e: i for i, e in enumerate(spec.EVENT_TYPES)}


def strip(rows):
    return [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]


def git_sha():
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10)
        return out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def scale_counts(cfg, factor, pdf_total):
    """Pilot runs shrink anomaly and PDF quotas proportionally (full run: factor = 1)."""
    if factor == 1 and pdf_total == 1000:
        return
    a = cfg["anomalies"]
    for key in ("invoice_counts", "product_month_counts", "recycling_counts", "supplier_spike_counts"):
        a[key] = {k: max(1, int(round(v * factor))) for k, v in a[key].items()}
    a["shared_number_groups"] = max(1, int(round(a["shared_number_groups"] * factor)))
    p = cfg["pdfs"]
    s = pdf_total / 1000.0
    for key in ("routine_by_type", "targeted_anomaly_by_type", "targeted_legit_hard"):
        p[key] = {k: int(round(v * s)) for k, v in p[key].items()}
    p["total"] = pdf_total


def log(msg, t0):
    print(f"[{time.time() - t0:7.1f}s] {msg}", flush=True)


def run(config_path, out, company_limit=None, pdf_total=1000, render=True):
    t0 = time.time()
    cfg = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    w = World(cfg, ROOT / cfg["masters_dir"], company_limit)
    factor = len(w.companies) / 200.0
    scale_counts(cfg, factor, pdf_total)
    out = Path(out)
    csv_dir, clean_dir = out / "csv", out / "csv" / "clean"
    log(f"world: {len(w.companies)} companies, {len(w.product)} products, {len(w.months)} months", t0)

    # ---------------------------------------------------------------- clean world
    sales, price, _growth = activity.build_sales(w)
    sale_txns = activity.build_sales_transactions(w, sales)
    returns = activity.build_returns(w, sale_txns)
    purchases, inv_events = activity.build_purchases_and_events(w, sale_txns)
    txns = sale_txns + returns + purchases
    log(f"transactions: sales/exports {len(sale_txns)}, returns {len(returns)}, purchases {len(purchases)}", t0)
    mkt_events = activity.market_events(w, txns)
    recycling = activity.build_recycling(w, mkt_events)
    rec_events = activity.recycling_events(w, recycling)

    reg = invoicing.Register(w)
    invoicing.build_trade_invoices(w, reg, sale_txns, returns, purchases, price)
    invoicing.build_credit_notes(w, reg, txns)
    txn_by_id = {t["transaction_id"]: t for t in txns}
    twins = invoicing.build_cancelled_twins(w, reg, txn_by_id, txns)
    invoicing.build_waste_procurement(w, reg, inv_events)
    invoicing.build_recycler_invoices(w, reg, recycling)
    invoicing.assign_numbers(w, reg)
    shared_groups = invoicing.assign_shared_numbers(w, reg, cfg["anomalies"]["shared_number_groups"])
    log(f"invoices: {len(reg.invoices)} headers, {sum(len(v) for v in reg.lines.values())} lines", t0)

    # link market / purchase events to their evidence
    for ev in mkt_events:
        line = reg.txn_line.get(ev.pop("_txn"))
        if line:
            ev["source_document_id"] = line["invoice_id"]
            ev["source_line_id"] = line["invoice_line_id"]
    events = inv_events + mkt_events + rec_events
    events.sort(key=lambda e: (e["company_id"], e["date"], EVENT_ORDER[e["event_type"]], e["component_id"] or "",
                               e["source_line_id"] or "", e["source_document_id"] or ""))
    for i, e in enumerate(events, start=1):
        e["event_id"] = f"MEV_{i:09d}"
    for ev in events:
        if ev["synthetic_category"] is None:
            ev["synthetic_category"] = "UNKNOWN"

    anomaly_split, hold, split_rows = extras.build_splits(w)
    scenarios, scenario_results = extras.build_scenarios(w, sales)
    descriptions = extras.build_descriptions(w)
    panel = extras.build_forecast_panel(w, sales, hold)
    log(f"events {len(events)}, recycling {len(recycling)}, scenarios {len(scenarios)}, panel {len(panel)}", t0)

    # ---------------------------------------------------------------- snapshot clean, inject anomalies
    clean_txns = strip(txns)
    clean_invoices = strip(list(reg.invoices.values()))
    clean_lines = strip([l for iid in reg.lines for l in reg.lines[iid]])
    clean_recycling = strip(recycling)
    inj, observed = anomalies.inject(w, reg, txns, recycling, anomaly_split, shared_groups, twins)
    gt = inj.gt
    log(f"anomalies: {sum(g['is_anomaly'] for g in gt)} instances + {sum(not g['is_anomaly'] for g in gt)} hard negatives", t0)

    # ---------------------------------------------------------------- documents
    pdf_results = []
    if render:
        chosen = documents.Selector(w, reg, inj).run()
        layouts, layout_counts = documents.assign_layouts(w, reg, chosen)
        pdf_results = documents.render_all(w, reg, inj, chosen, layouts, out / "invoices" / "pdf", out / "invoices" / "json",
                                           cfg["generator_version"])
        log(f"documents rendered: {len(pdf_results)} (layouts {layout_counts})", t0)
        if company_limit is None and len(pdf_results) != cfg["pdfs"]["total"]:
            raise SystemExit(f"expected exactly {cfg['pdfs']['total']} PDFs, got {len(pdf_results)}")

    # ---------------------------------------------------------------- write tables
    obs_invoices = sorted(reg.invoices.values(), key=lambda i: i["invoice_id"])
    obs_lines = [l for i in obs_invoices for l in sorted(reg.lines[i["invoice_id"]], key=lambda x: x["line_no"])]
    flat = []
    for inv in obs_invoices:
        for l in reg.lines[inv["invoice_id"]]:
            flat.append({
                "invoice_line_id": l["invoice_line_id"], "invoice_id": inv["invoice_id"],
                "invoice_number": inv["invoice_number"], "invoice_type": inv["invoice_type"],
                "company_id": inv["company_id"], "supplier_id": inv["supplier_id"], "buyer_id": inv["buyer_id"],
                "invoice_date": inv["invoice_date"], "material": l["material"], "plastic_category": l["plastic_category"],
                "raw_quantity": l["raw_quantity"], "raw_unit": l["raw_unit"],
                "normalized_quantity_kg": l["normalized_quantity_kg"], "recorded_quantity_kg": l["recorded_quantity_kg"],
                "rate": l["rate"], "amount": l["taxable_value"], "gst": l["gst_amount"],
                "total": round(l["taxable_value"] + l["gst_amount"], 2), "is_anomaly": inv["is_anomaly"],
                "anomaly_type": inv["anomaly_type"], "synthetic_flag": True,
            })
    observed_txns = sorted(strip(observed), key=lambda t: t["transaction_id"])
    tables = {
        "transactions": observed_txns, "material_events": events, "invoices": strip(obs_invoices),
        "invoice_lines": strip(obs_lines), "invoices_flat": flat, "recycling": strip(recycling),
        "anomaly_ground_truth": gt, "scenarios": scenarios, "scenario_results": scenario_results,
        "business_descriptions": descriptions, "splits": split_rows, "forecast_panel": panel,
    }
    clean_tables = {"transactions": sorted(clean_txns, key=lambda t: t["transaction_id"]),
                    "invoices": sorted(clean_invoices, key=lambda i: i["invoice_id"]), "invoice_lines": clean_lines,
                    "recycling": clean_recycling}
    written = {}
    for name, rows in tables.items():
        sample = rows if name != "material_events" else rows[::25]
        validate_rows(sample, name)
        p = csv_dir / f"{name}.csv"
        write_csv(rows, p, name)
        written[p] = len(rows)
    for name, rows in clean_tables.items():
        validate_rows(rows if name != "transactions" else rows[::5], name)
        p = clean_dir / f"{name}.csv"
        write_csv(rows, p, name)
        written[p] = len(rows)
    log("csv written + schema-validated", t0)

    # ---------------------------------------------------------------- manifest
    counts = {
        "companies": len(w.companies), "products": len(w.product),
        "packaging_components": sum(len(v) for v in w.versions.values()),
        "transactions": len(observed_txns), "transactions_clean": len(clean_txns), "material_events": len(events),
        "invoices": len(obs_invoices), "invoice_lines": len(obs_lines), "recycling": len(recycling),
        "anomaly_ground_truth": len(gt), "anomaly_instances": sum(g["is_anomaly"] for g in gt),
        "hard_negative_labels": sum(not g["is_anomaly"] for g in gt), "scenarios": len(scenarios),
        "scenario_results": len(scenario_results), "business_descriptions": len(descriptions),
        "forecast_panel_rows": len(panel), "invoice_pdfs": len(pdf_results), "invoice_json": len(pdf_results),
    }
    clean_hash = hashlib.sha256()
    for name in sorted(clean_tables):
        clean_hash.update(sha256_file(clean_dir / f"{name}.csv").encode())
    file_hashes = {p.relative_to(out).as_posix(): sha256_file(p) for p in written}
    doc_hashes = {}
    if render:
        for kind in ("pdf", "json"):
            for p in sorted((out / "invoices" / kind).glob(f"*.{kind}")):
                doc_hashes[p.relative_to(out).as_posix()] = sha256_file(p)
    agg = hashlib.sha256("".join(f"{k}:{v}\n" for k, v in sorted({**file_hashes, **doc_hashes}.items())).encode()).hexdigest()
    entity_manifest = json.loads((ROOT / cfg["masters_dir"] / "entity_manifest.json").read_text(encoding="utf-8"))
    manifest = {
        "synthetic": True, "watermark": "SYNTHETIC — EPRLens Demo", "generator_version": cfg["generator_version"],
        "git_commit": git_sha(), "seed": cfg["seed"],
        "config_sha256": sha256_file(config_path),
        "entity_config_sha256": entity_manifest["config_sha256"],
        "entity_master_hashes": entity_manifest["master_file_hashes"],
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "python": sys.version.split()[0], "run": {"company_limit": company_limit, "pdf_total": pdf_total},
        "window": cfg["window"], "schema_versions": {"tables": spec.SCHEMA_VERSION},
        "counts": counts, "clean_data_sha256": clean_hash.hexdigest(), "dataset_sha256": agg,
        "anomaly_counts": _count(g["anomaly_type"] for g in gt if g["is_anomaly"]),
        "pdf_strata": _count(r["test_case_type"] for r in pdf_results),
        "pdf_layouts": _count(r["template_id"] for r in pdf_results),
        "pdf_types": _count(r["invoice_type_code"] for r in pdf_results),
        "file_hashes": file_hashes, "document_hashes": doc_hashes,
        "note": ("generated_at, git_commit and python are excluded from reproducibility checks. Metrics computed on this "
                 "data are pipeline validation on synthetic data, not real-world accuracy."),
    }
    write_json(manifest, out / "manifests" / "MANIFEST.json")
    log(f"manifest written: dataset_sha256 {agg[:16]}…", t0)
    ctx = dict(w=w, reg=reg, inj=inj, tables=tables, events=events, pdf_results=pdf_results, out=out,
               manifest=manifest, recycling=recycling, scenarios=scenarios, scenario_results=scenario_results)
    return ctx


def _count(items):
    out = {}
    for x in items:
        out[x] = out.get(x, 0) + 1
    return dict(sorted(out.items()))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=str(HERE / "config.yaml"))
    ap.add_argument("--out", default=str(ROOT / "data" / "generated"))
    ap.add_argument("--companies", type=int, default=None, help="pilot: limit to the first N companies")
    ap.add_argument("--pdfs", type=int, default=1000, help="pilot: number of PDFs")
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--publish", action="store_true",
                    help="full run only: refresh committed samples, demo fixtures and synthetic-data/MANIFEST.json")
    args = ap.parse_args()
    ctx = run(args.config, args.out, args.companies, args.pdfs, not args.no_render)
    if args.publish:
        from generators import publish
        publish.publish(ctx, ROOT)
        print("published samples, fixtures and synthetic-data/MANIFEST.json")
    print(json.dumps(ctx["manifest"]["counts"], indent=1))


if __name__ == "__main__":
    main()
