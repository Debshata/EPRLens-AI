"""Copy small committed samples, refresh demo fixtures (frontend mocks + Lambda
test events) and write the committed provenance manifest after a FULL run.
SYNTHETIC — EPRLens Demo."""
import json
import shutil
from pathlib import Path

from .tableio import write_csv, write_json
from .world import fy_label

DEMO = "COMP_0001"
PLASTIC = {"CAT_I", "CAT_II", "CAT_III", "CAT_IV"}
META = {"synthetic": True, "watermark": "SYNTHETIC — EPRLens Demo",
        "source_of_truth": "synthetic-data/masters + data/generated (regenerate with synthetic-data/generate.py)"}


def _meta(ctx, note):
    return {**META, "seed": ctx["manifest"]["seed"], "generator_version": ctx["manifest"]["generator_version"],
            "dataset_sha256": ctx["manifest"]["dataset_sha256"], "note": note}


def pick_samples(results, n=20):
    by_doc = {r["document_id"]: r for r in results}
    chosen = []
    demo = [r for r in results if r["company_id"] == DEMO and "AN08" in r["anomaly_types"]]
    chosen += [d["document_id"] for d in demo[:1]]
    for layout in sorted({r["template_id"] for r in results}):
        d = min((r for r in results if r["template_id"] == layout), key=lambda r: r["document_id"])
        if d["document_id"] not in chosen:
            chosen.append(d["document_id"])
    for case in sorted({r["test_case"] for r in results}):
        if len(chosen) >= n:
            break
        d = min((r for r in results if r["test_case"] == case), key=lambda r: r["document_id"])
        if d["document_id"] not in chosen:
            chosen.append(d["document_id"])
    return sorted(chosen[:n]), by_doc


def publish(ctx, root: Path):
    out, w = ctx["out"], ctx["w"]
    sample = root / "synthetic-data" / "outputs" / "sample"
    for sub in ("pdf", "json", "csv"):
        shutil.rmtree(sample / sub, ignore_errors=True)
        (sample / sub).mkdir(parents=True, exist_ok=True)
    chosen, by_doc = pick_samples(ctx["pdf_results"])
    for d in chosen:
        shutil.copy2(out / "invoices" / "pdf" / f"{d}.pdf", sample / "pdf" / f"{d}.pdf")
        shutil.copy2(out / "invoices" / "json" / f"{d}.json", sample / "json" / f"{d}.json")
    t = ctx["tables"]
    last_q = {"2026-01", "2026-02", "2026-03"}
    slices = {
        "transactions": [r for r in t["transactions"] if r["company_id"] == DEMO and r["date"][:7] in last_q],
        "invoices": [r for r in t["invoices"] if r["company_id"] == DEMO and (r["invoice_date"] or "")[:7] in last_q],
        "recycling": [r for r in t["recycling"] if r["company_id"] == DEMO],
        "anomaly_ground_truth": [r for r in t["anomaly_ground_truth"] if r["company_id"] == DEMO]
        + t["anomaly_ground_truth"][:40],
        "scenarios": [r for r in t["scenarios"] if r["company_id"] == DEMO],
        "scenario_results": [r for r in t["scenario_results"] if r["company_id"] == DEMO],
        "forecast_panel": [r for r in t["forecast_panel"] if r["company_id"] == DEMO and r["month"] >= "2025-09"],
        "business_descriptions": t["business_descriptions"][:10],
        "material_events": [r for r in t["material_events"] if r["company_id"] == DEMO and r["period"] == "2026-03"],
        "splits": t["splits"],
    }
    inv_ids = {r["invoice_id"] for r in slices["invoices"]}
    slices["invoice_lines"] = [r for r in t["invoice_lines"] if r["invoice_id"] in inv_ids]
    seen = set()
    slices["anomaly_ground_truth"] = [r for r in slices["anomaly_ground_truth"]
                                      if not (r["anomaly_instance_id"] in seen or seen.add(r["anomaly_instance_id"]))]
    for name, rows in slices.items():
        write_csv(rows, sample / "csv" / f"{name}.csv", name)
    (sample / "README.md").write_text(
        "# Committed samples — SYNTHETIC — EPRLens Demo\n\n"
        f"- `pdf/`, `json/`: {len(chosen)} of the 1,000 generated invoice documents and their ground truth "
        "(one per layout, the EcoFizz 0.5 MT vs 500 MT demo anomaly, and one per test case where room allows).\n"
        "- `csv/`: small slices of the full tables, mostly the demo company COMP_0001 (Jan–Mar 2026).\n"
        "- `illustrative/`: the hand-composed example from the entity phase (99-range IDs).\n\n"
        "The full dataset lives in `data/generated/` (git-ignored). Regenerate it with "
        "`python synthetic-data/generate.py --config synthetic-data/config.yaml --out data/generated`.\n",
        encoding="utf-8", newline="\n")

    # ------------------------------------------------------------ demo fixtures
    mocks = root / "frontend" / "src" / "lib" / "mocks"
    events_dir = root / "backend" / "test-events"
    gt_demo = [g for g in t["anomaly_ground_truth"] if g["company_id"] == DEMO]
    inv_num = {i["invoice_id"]: i["invoice_number"] for i in t["invoices"]}
    pom = {}
    for e in ctx["events"]:
        if e["company_id"] == DEMO and e["event_type"] == "PLACED_ON_MARKET":
            k = e["period"]
            d = pom.setdefault(k, {"month": k, "plastic_kg": 0.0, "total_packaging_kg": 0.0})
            d["total_packaging_kg"] += e["kg"]
            if e["synthetic_category"] in PLASTIC:
                d["plastic_kg"] += e["kg"]
    monthly = [{**v, "plastic_kg": round(v["plastic_kg"], 1), "total_packaging_kg": round(v["total_packaging_kg"], 1)}
               for _, v in sorted(pom.items())]
    mix = {}
    for e in ctx["events"]:
        if e["company_id"] == DEMO and e["event_type"] == "PLACED_ON_MARKET" and fy_label(e["period"]) == "FY2025-26":
            mix[e["material"]] = mix.get(e["material"], 0.0) + e["kg"]
    rec_fy = {}
    for r in t["recycling"]:
        if r["company_id"] == DEMO:
            d = rec_fy.setdefault(fy_label(r["month"]), {"waste_generated_kg": 0.0, "waste_collected_kg": 0.0,
                                                          "waste_recycled_kg": 0.0, "credits_documented_kg": 0.0})
            for k in d:
                d[k] += r[k]
    rec_fy = {k: {kk: round(vv, 1) for kk, vv in v.items()} for k, v in sorted(rec_fy.items())}
    anomaly_counts = {}
    for g in gt_demo:
        if g["is_anomaly"]:
            anomaly_counts[g["anomaly_type"]] = anomaly_counts.get(g["anomaly_type"], 0) + 1
    demo_txns = sorted((r for r in t["transactions"] if r["company_id"] == DEMO and r["date"][:7] == "2026-03"),
                       key=lambda r: r["transaction_id"])[:40]
    write_json({"_meta": _meta(ctx, "COMP_0001 transactions, March 2026 (first 40). Observed world."),
                "transactions": demo_txns}, mocks / "transactions.json")
    write_json({"_meta": _meta(ctx, "Ground-truth anomaly labels for COMP_0001. A real app would show detector findings, "
                                    "not labels; use for UI development only."),
                "anomalies": [{**g, "invoice_number": inv_num.get(g["invoice_id"])} for g in gt_demo]},
               mocks / "anomalies.json")
    write_json({"_meta": _meta(ctx, "Deterministic what-if results (docs/scenario-formulas.md). Hypothetical."),
                "scenarios": [s for s in ctx["scenarios"] if s["company_id"] == DEMO],
                "results": [s for s in ctx["scenario_results"] if s["company_id"] == DEMO]}, mocks / "scenario.json")
    write_json({"_meta": _meta(ctx, "Aggregates for COMP_0001. No risk score: weights/bands are pending (D007/D031). "
                                    "Recycling figures are a synthetic proxy, not obligations."),
                "company_id": DEMO, "monthly_placed_on_market": monthly,
                "material_mix_fy2025_26_kg": {k: round(v, 1) for k, v in sorted(mix.items())},
                "recycling_by_fy": rec_fy, "anomaly_label_counts": dict(sorted(anomaly_counts.items()))},
               mocks / "dashboard.json")
    write_json({"_meta": _meta(ctx, "History only. Forecasts are produced in the ML phase (D027 pending)."),
                "company_id": DEMO, "history": [{"month": m["month"], "packaging_kg": m["total_packaging_kg"]}
                                               for m in monthly], "forecast": None}, mocks / "forecast.json")
    demo_inv = [i for i in t["invoices"] if i["company_id"] == DEMO and i["document_id"]]
    an_docs = [i for i in demo_inv if i["is_anomaly"]][:5]
    write_json({"_meta": _meta(ctx, "Invocation envelope TBD (D056)."), "action": "validate_transactions",
                "company_id": DEMO,
                "s3": {"bucket": "<uploads-bucket-placeholder>", "key": "uploads/COMP_0001/csv/transactions_2026-03.csv"},
                "expected": {"row_count": sum(1 for r in t["transactions"]
                                              if r["company_id"] == DEMO and r["date"][:7] == "2026-03")}},
               events_dir / "transaction-upload.json")
    write_json({"_meta": _meta(ctx, "Invocation envelope TBD (D056)."), "action": "detect_anomalies", "company_id": DEMO,
                "invoice_ids": [i["invoice_id"] for i in an_docs],
                "expected_anomaly_types": {i["invoice_id"]: i["anomaly_type"] for i in an_docs}},
               events_dir / "anomaly.json")
    write_json({"_meta": _meta(ctx, "Invocation envelope TBD (D056)."), "action": "forecast", "company_id": DEMO,
                "history_months": [m["month"] for m in monthly][-12:], "target_month": "2026-04",
                "expected": "model output (ML phase pending)"}, events_dir / "forecast.json")

    # ------------------------------------------------------------ committed manifest
    m = dict(ctx["manifest"])
    m["dataset_location"] = "data/generated (git-ignored; regenerate or fetch from private storage)"
    m["committed_samples"] = sorted(p.relative_to(root).as_posix() for p in sample.rglob("*") if p.is_file())
    write_json(m, root / "synthetic-data" / "MANIFEST.json")
