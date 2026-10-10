#!/usr/bin/env python3
"""End-to-end check of LIVE mode through the Next.js /api/* routes (browser -> route -> presigned S3 -> Lambda -> DynamoDB).

    cd frontend && npm run build && npm run start -- -p 3200      # needs frontend/.env.local from 70-frontend-env.sh
    python3 infrastructure/scripts/65-live-api-check.py http://localhost:3200
"""
import hashlib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:3200").rstrip("/")
SAMPLES = Path(__file__).resolve().parents[2] / "frontend" / "public" / "samples"
CO = "COMP_0001"
failed = 0


def call(method, path, body=None):
    req = urllib.request.Request(BASE + path, method=method, data=json.dumps(body).encode() if body is not None else None, headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def check(name, ok, detail=""):
    global failed
    failed += 0 if ok else 1
    print(("PASS " if ok else "FAIL ") + name, "" if ok else str(detail)[:300])


def upload(kind, file_name, mime):
    data = (SAMPLES / file_name).read_bytes()
    st, p = call("POST", "/api/uploads/presign", {"company_id": CO, "kind": kind, "name": file_name, "size": len(data), "mime": mime, "sha256": hashlib.sha256(data).hexdigest()})
    assert st == 200, (st, p)
    put = urllib.request.Request(p["upload_url"], method="PUT", data=data, headers={"content-type": mime})
    with urllib.request.urlopen(put, timeout=120) as r:
        assert r.status == 200
    return p["s3_key"]


st, r = call("GET", "/api/company?demo=1")
check("company (demo)", st == 200 and r["company"]["company_name"].startswith("EcoFizz"), r)

inv_key = upload("invoice", "DOC_000832.pdf", "application/pdf")
st, inv = call("POST", "/api/documents/analyze", {"company_id": CO, "s3_key": inv_key})
check("parse invoice 0.5 MT = 500 kg", st == 200 and inv["lines"][0]["normalized_quantity_kg"] == 500 and inv["invoice_number"] == "SYEC/2526/00004", inv)

csv_key = upload("csv", "transactions_demo.csv", "text/csv")
st, csv = call("POST", "/api/transactions/validate", {"company_id": CO, "s3_key": csv_key})
check("validate CSV (15 rows)", st == 200 and csv["row_count"] == 15 and not csv["missing_required_columns"], csv)

st, rec = call("POST", "/api/reconcile", {"company_id": CO, "document_id": inv["document_id"], "csv_s3_key": csv_key})
f = rec["findings"][0] if st == 200 and rec.get("findings") else {}
check("reconcile: 500 kg vs 500,000 kg, diff 499,500", f.get("difference_kg") == 499500 and f.get("observed", {}).get("value_kg") == 500000, rec)

img_key = upload("image", "sample-carton.png", "image/png")
st, img = call("POST", "/api/vision/classify", {"company_id": CO, "s3_key": img_key})
check("classify carton photo", st == 200 and img["predicted_class"] == "cardboard" and set(img) == {"predicted_class", "confidence", "uncertain", "model_version"}, img)

st, fc = call("GET", f"/api/forecast?company_id={CO}")
check("forecast next month 403,261.78 kg, no interval", st == 200 and fc["forecast"]["points"][0]["month"] == "2026-04" and abs(fc["forecast"]["points"][0]["packaging_kg"] - 403261.78) < 0.01 and fc["forecast"]["interval"] is None, fc.get("forecast", fc))

st, sc = call("POST", "/api/scenario", {"product_id": "PROD_000001", "component_id": "PKGCOMP_000002", "units": 100000, "baseline_g_per_unit": 25, "proposed_g_per_unit": 20})
check("what-if 25 -> 20 g = -500 kg", st == 200 and sc["reduction_kg"] == 500 and sc["hypothetical"] is True, sc)

st, d = call("GET", f"/api/dashboard?company_id={CO}")
check("dashboard summary", st == 200 and len(d["monthly_placed_on_market"]) == 36, d)
st, s = call("GET", f"/api/simulator?company_id={CO}")
check("simulator catalogue", st == 200 and len(s["products"]) == 5, s)

st, bad = call("POST", "/api/uploads/presign", {"company_id": CO, "kind": "invoice", "name": "notes.exe", "size": 10, "mime": "application/x-msdownload", "sha256": "a" * 64})
check("bad file type rejected with a next step", st == 400 and bad.get("next_step"), bad)
st, miss = call("POST", "/api/reconcile", {"company_id": "COMP_NEW", "document_id": "DOC_999999", "csv_s3_key": csv_key})
check("reconcile before upload -> friendly 404", st == 404 and "upload" in miss.get("next_step", "").lower(), miss)

print("ALL PASSED" if not failed else f"{failed} FAILED")
sys.exit(1 if failed else 0)
