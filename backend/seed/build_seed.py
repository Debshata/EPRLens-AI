"""Builds the small reference/demo data the Lambdas read (S3 `reference/…` on AWS, $LOCAL_SEED_DIR locally).

Sources are the committed synthetic dataset in syntheticml/ (SYNTHETIC — EPRLens Demo). Run from the repo root:
    python backend/seed/build_seed.py
Needs the full generated data (syntheticml/data/generated) which is in git. Output: backend/seed/reference/
"""
from __future__ import annotations

import collections
import csv
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GEN = ROOT / "syntheticml" / "data" / "generated"
MOCKS = ROOT / "frontend" / "src" / "lib" / "mocks"
OUT = ROOT / "backend" / "seed" / "reference"
COMPANY = "COMP_0001"


def write(rel: str, obj) -> None:
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def invoice_index() -> dict:
    """invoice number + date + vendor -> internal invoice id and per-line transaction ids (the company's own record link)."""
    lines = collections.defaultdict(list)
    with open(GEN / "csv" / "invoice_lines.csv", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            lines[r["invoice_id"]].append({"line_no": int(r["line_no"]), "transaction_id": r["transaction_id"], "component_id": r["component_id"]})
    entries = []
    for f in sorted((GEN / "invoices" / "json").glob("DOC_*.json")):
        g = json.loads(f.read_text(encoding="utf-8"))
        e = g["expected_fields"]
        entries.append(
            {
                "document_id": g["document_id"],
                "invoice_id": g["invoice_id"],
                "invoice_number": e["invoice_number"],
                "invoice_date": e.get("invoice_date"),
                "vendor": e.get("vendor"),
                "lines": sorted(lines.get(g["invoice_id"], []), key=lambda x: x["line_no"]),
            }
        )
    return {"_meta": {"synthetic": True, "note": "Company record link for the synthetic invoices (stands in for an ERP lookup)."}, "invoices": entries}


def forecast_history() -> dict:
    panel = [r for r in csv.DictReader(open(GEN / "csv" / "forecast_panel.csv", encoding="utf-8")) if r["company_id"] == COMPANY]
    by_prod: dict[str, dict] = collections.defaultdict(dict)
    for r in panel:
        by_prod[r["product_id"]][r["month"]] = {"month": r["month"], "packaging_kg": float(r["packaging_kg"]), "units_sold": int(r["units_sold"]), "weight_per_unit_g": float(r["weight_per_unit_g"])}
    last = max(r["month"] for r in panel)
    for r in panel:  # the panel's target for the last origin month is the last actual month
        if r["month"] == last:
            w, kg = float(r["weight_per_unit_g"]), float(r["next_month_packaging_kg"])
            nxt = r["target_month"]
            by_prod[r["product_id"]][nxt] = {"month": nxt, "packaging_kg": kg, "units_sold": round(kg * 1000 / w), "weight_per_unit_g": w}
    months = sorted({m for p in by_prod.values() for m in p})
    history = [{"month": m, "packaging_kg": round(sum(p[m]["packaging_kg"] for p in by_prod.values() if m in p), 3), "kind": "observed"} for m in months]
    fc = json.loads((MOCKS / "forecast.json").read_text(encoding="utf-8"))["forecast"]
    meta = json.loads((ROOT / "syntheticml" / "ml" / "artifacts" / "forecast" / "v1" / "model_metadata.json").read_text(encoding="utf-8"))
    return {
        "company_id": COMPANY,
        "industry": "Beverages",
        "basis": "packaging_mass_of_units_sold_kg",
        "history": history,
        "products": {pid: [p[m] for m in sorted(p)][-13:] for pid, p in by_prod.items()},
        "model": {"model_version": fc["model_version"], "model_name": fc["model_name"], "target": fc["target"], "warning": meta["warning"], "metrics_test": fc["metrics_test"]},
    }


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    write("invoice_index.json", invoice_index())
    for n in ("company", "dashboard", "simulator"):
        shutil.copy(MOCKS / f"{n}.json", (OUT / COMPANY / f"{n}.json") if (OUT / COMPANY).mkdir(parents=True, exist_ok=True) is None else None)
    write(f"{COMPANY}/forecast_history.json", forecast_history())
    print("seed written to", OUT, "->", sorted(str(p.relative_to(OUT)) for p in OUT.rglob("*.json")))


if __name__ == "__main__":
    main()
