"""Data-quality tests for the generated full dataset (brief Phase 10).
Runs against data/generated (or $EPRLENS_DATA); skipped if it has not been generated.
SYNTHETIC — EPRLens Demo."""
import csv
import json
import os
import sys
from functools import lru_cache
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[2]
SD = ROOT / "synthetic-data"
sys.path.insert(0, str(SD))
from generators import identifiers as ids  # noqa: E402
from generators.entity_index import EntityIndex  # noqa: E402
from generators.tableio import read_csv_typed  # noqa: E402

DATA = Path(os.environ.get("EPRLENS_DATA", ROOT / "data" / "generated"))
pytestmark = pytest.mark.skipif(not (DATA / "manifests" / "MANIFEST.json").exists(),
                                reason="full dataset not generated (run synthetic-data/generate.py)")
TOL = 0.011


@lru_cache(maxsize=None)
def table(name, clean=False):
    return read_csv_typed(DATA / "csv" / ("clean" if clean else "") / f"{name}.csv", name)


@lru_cache(maxsize=None)
def masters():
    return EntityIndex(SD / "masters")


@lru_cache(maxsize=None)
def manifest():
    return json.loads((DATA / "manifests" / "MANIFEST.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def docs():
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted((DATA / "invoices" / "json").glob("*.json"))}


@lru_cache(maxsize=None)
def gt():
    return table("anomaly_ground_truth")


# ------------------------------------------------------------------ counts & targets
def test_exactly_1000_pdfs_and_1000_json():
    pdfs = sorted(p.stem for p in (DATA / "invoices" / "pdf").glob("*.pdf"))
    jsons = sorted((DATA / "invoices" / "json").glob("*.json"))
    assert len(pdfs) == 1000 and len(jsons) == 1000
    assert pdfs == [p.stem for p in jsons] == [f"DOC_{i:06d}" for i in range(1, 1001)]


def test_volume_targets():
    c = manifest()["counts"]
    assert c["companies"] == 200
    assert 150_000 <= c["transactions"] <= 250_000
    assert 30_000 <= c["invoices"] <= 50_000
    assert c["business_descriptions"] == 150


def test_pdf_strata_and_layouts():
    m = manifest()
    assert m["pdf_strata"] == {"routine": 600, "targeted_anomaly": 280, "targeted_legit_hard": 120}
    assert len(m["pdf_layouts"]) >= 10 and min(m["pdf_layouts"].values()) >= 50
    assert all(1 <= d["expected_fields"]["page_count"] <= 3 for d in docs().values())
    assert all(1 <= len(d["expected_fields"]["lines"]) <= 12 for d in docs().values())
    hard = [d for d in docs().values() if d["test_case_type"] == "targeted_legit_hard"]
    assert hard and all(not d["is_anomaly"] for d in hard)


def test_anomaly_counts_match_config():
    import yaml
    cfg = yaml.safe_load((SD / "config.yaml").read_text(encoding="utf-8"))["anomalies"]
    want = {**cfg["invoice_counts"], **cfg["recycling_counts"]}
    want["AN09"] = cfg["product_month_counts"]["AN09"] + cfg["supplier_spike_counts"]["AN09"]
    assert manifest()["anomaly_counts"] == dict(sorted(want.items()))


# ------------------------------------------------------------------ PDF ↔ JSON
def _pdf_pages(path):
    from pypdf import PdfReader
    return [p.extract_text() or "" for p in PdfReader(str(path)).pages]


def test_pdf_text_matches_json_ground_truth():
    failures = []
    for doc_id, d in docs().items():
        pages = _pdf_pages(DATA / "invoices" / "pdf" / f"{doc_id}.pdf")
        e = d["expected_fields"]
        allt = "\n".join(pages)
        checks = [e["invoice_number"], e["printed_total"], e["vendor"]]
        if e["printed_date"]:
            checks.append(e["printed_date"])
        for c in checks:
            if c not in allt:
                failures.append((doc_id, c))
        if len(pages) != e["page_count"]:
            failures.append((doc_id, "page_count"))
        for line in e["lines"]:
            text = pages[line["page_number"] - 1]
            for c in (line["printed_quantity"], line["printed_amount"], line["printed_rate"]):
                if c and c not in text:
                    failures.append((doc_id, line["line_reference"], c))
            for part in line["printed_description_lines"]:
                if part not in text:
                    failures.append((doc_id, line["line_reference"], part))
        for n, t in enumerate(pages, start=1):
            if "SYNTHETIC" not in t or f"{doc_id} · page {n}/{len(pages)}" not in t:
                failures.append((doc_id, f"watermark/footer p{n}"))
    assert not failures, failures[:10]


def test_json_schema_and_hashes():
    import hashlib
    schema = json.loads((SD / "schemas" / "invoice_document.schema.json").read_text(encoding="utf-8"))
    for doc_id, d in docs().items():
        jsonschema.validate(d, schema)
        pdf = (DATA / "invoices" / "pdf" / f"{doc_id}.pdf").read_bytes()
        assert hashlib.sha256(pdf).hexdigest() == d["render_sha256"]
        assert d["watermark"] == "SYNTHETIC — EPRLens Demo" and d["synthetic_flag"] is True


def test_json_matches_invoice_tables():
    inv = {r["invoice_id"]: r for r in table("invoices")}
    lines = {}
    for l in table("invoice_lines"):
        lines.setdefault(l["invoice_id"], []).append(l)
    for doc_id, d in docs().items():
        h = inv[d["invoice_id"]]
        assert h["document_id"] == doc_id
        e = d["expected_fields"]
        assert e["invoice_number"] == h["invoice_number"] and e["invoice_date"] == h["invoice_date"]
        assert abs(e["invoice_total"] - h["total"]) < 0.005
        ls = sorted(lines[d["invoice_id"]], key=lambda x: x["line_no"])
        assert [l["raw_quantity"] for l in ls] == [x["quantity"] for x in e["lines"]]
        assert d["is_anomaly"] == bool(d["anomaly_types"])


# ------------------------------------------------------------------ integrity
def test_foreign_keys_resolve():
    ix = masters()
    companies = ix.by_id["companies"]
    for t in table("transactions"):
        assert t["company_id"] in companies
        for k in ("product_id", "component_id", "buyer_id", "supplier_id"):
            if t[k]:
                assert ix.resolve(t[k]) is not None, (t["transaction_id"], k)
    for i in table("invoices"):
        assert ix.resolve(i["supplier_id"]) is not None and ix.resolve(i["buyer_id"]) is not None
    for r in table("recycling"):
        assert r["recycler_id"] in ix.by_id["recyclers"]
    inv_ids = {i["invoice_id"] for i in table("invoices")}
    assert all(t["invoice_id"] in inv_ids for t in table("transactions") if t["invoice_id"])


def test_no_valid_gstins_on_invoices():
    for i in table("invoices"):
        for g in (i["supplier_gstin"], i["buyer_gstin"]):
            if g:
                assert not ids.gstin_checksum_valid(g)


def test_unit_conversion_in_clean_records():
    comps = masters().by_id["packaging_components"]
    for t in table("transactions", clean=True):
        if t["transaction_type"] not in ("purchase", "import"):
            continue
        c = comps[t["component_id"]]
        q, u, kg = t["raw_quantity"], t["raw_unit"], t["normalized_quantity_kg"]
        expect = {"kg": q, "MT": q * 1000, "pcs": q * c["weight_per_unit_g"] / 1000.0}[u]
        assert abs(expect - kg) < 0.002, t["transaction_id"]


def _events():
    return table("material_events")


def test_material_balance_closes():
    comps = masters().by_id["packaging_components"]
    grp = {}
    for e in _events():
        if e["direction"] == "memo" and e["event_type"] not in ("OPENING_BALANCE", "CLOSING_BALANCE"):
            continue
        if not e["component_id"]:
            continue
        key = (e["product_id"], comps[e["component_id"]]["component_name"])
        g = grp.setdefault(key, {"open": None, "in": 0.0, "out": 0.0, "close": None, "close_date": ""})
        if e["event_type"] == "OPENING_BALANCE":
            g["open"] = e["kg"]
        elif e["event_type"] == "PURCHASED":
            g["in"] += e["kg"]
        elif e["event_type"] in ("CONSUMED", "WRITTEN_OFF"):
            g["out"] += e["kg"]
        elif e["event_type"] == "CLOSING_BALANCE" and e["date"] >= g["close_date"]:
            g["close"], g["close_date"] = e["kg"], e["date"]
    assert grp
    bad = [k for k, g in grp.items() if abs(g["open"] + g["in"] - g["out"] - g["close"]) > 0.05]
    assert not bad, bad[:5]


def test_consumed_equals_placed_plus_exported():
    comps = masters().by_id["packaging_components"]
    cons, mkt = {}, {}
    for e in _events():
        if not e["component_id"]:
            continue
        key = (e["product_id"], comps[e["component_id"]]["component_name"], e["period"])
        if e["event_type"] == "CONSUMED":
            cons[key] = cons.get(key, 0.0) + e["kg"]
        elif e["event_type"] in ("PLACED_ON_MARKET", "EXPORTED"):
            mkt[key] = mkt.get(key, 0.0) + e["kg"]
    assert set(cons) == set(mkt)
    assert all(abs(cons[k] - mkt[k]) < 0.05 for k in cons)


def test_recycling_invariants_hold_unless_labelled():
    clean = table("recycling", clean=True)
    assert all(r["waste_recycled_kg"] <= r["waste_collected_kg"] <= r["waste_generated_kg"] + 1e-9 for r in clean)
    assert all(r["credits_documented_kg"] <= r["waste_recycled_kg"] + 1e-9 and r["recycler_registered"] for r in clean)
    labelled = {(g["record_id"], g["anomaly_type"]) for g in gt() if g["record_type"] == "recycling"}
    for r in table("recycling"):
        rid = r["recycling_record_id"]
        if r["waste_recycled_kg"] > r["waste_collected_kg"]:
            assert (rid, "AN11") in labelled
        if r["waste_collected_kg"] > r["waste_generated_kg"]:
            assert (rid, "AN12") in labelled
        if not r["recycler_registered"]:
            assert (rid, "AN13") in labelled


def test_invoice_math():
    lines = {}
    for l in table("invoice_lines"):
        lines.setdefault(l["invoice_id"], []).append(l)
        q = l["raw_quantity"] if l["raw_quantity"] is not None else 1
        if l["raw_quantity"] is not None or l["raw_unit"] is None:
            assert abs(round(q * l["rate"], 2) - l["taxable_value"]) < 0.011 or l["raw_quantity"] is None
    for i in table("invoices"):
        ls = lines.get(i["invoice_id"], [])
        assert abs(sum(l["taxable_value"] for l in ls) - i["total_taxable_value"]) < TOL * max(1, len(ls))
        assert abs(i["total_taxable_value"] + i["gst"] - i["total"]) < TOL
        assert abs(i["cgst"] + i["sgst"] + i["igst"] - i["gst"]) < TOL


# ------------------------------------------------------------------ labels vs injected changes
def test_every_changed_transaction_is_labelled():
    clean = {t["transaction_id"]: t for t in table("transactions", clean=True)}
    obs = {t["transaction_id"]: t for t in table("transactions")}
    labelled_txn = {g["record_id"] for g in gt() if g["record_type"] == "transaction"}
    pm = {g["record_id"] for g in gt() if g["record_type"] == "product_month"}
    inv_labels = {g["invoice_id"] for g in gt() if g["is_anomaly"] and g["invoice_id"]}
    fields = ("raw_quantity", "raw_unit", "normalized_quantity_kg", "status", "units")
    for tid, o in obs.items():
        c = clean.get(tid)
        if c is None:
            assert o["invoice_id"] in inv_labels, tid           # AN05 duplicates
            continue
        if any(o[f] != c[f] for f in fields):
            assert (tid in labelled_txn or f"{o['product_id']}:{o['date'][:7]}" in pm
                    or o["invoice_id"] in inv_labels), tid
    for tid in set(clean) - set(obs):
        assert clean[tid]["invoice_id"] in inv_labels, tid       # AN15/AN16/AN19 removals


def test_labels_describe_real_mutations():
    clean = {t["transaction_id"]: t for t in table("transactions", clean=True)}
    obs = {t["transaction_id"]: t for t in table("transactions")}
    cl = {l["invoice_line_id"]: l for l in table("invoice_lines", clean=True)}
    ol = {l["invoice_line_id"]: l for l in table("invoice_lines")}
    for g in gt():
        if not g["is_anomaly"]:
            continue
        if g["record_type"] == "transaction":
            a, b = clean[g["record_id"]], obs[g["record_id"]]
            assert any(a[f] != b[f] for f in ("raw_quantity", "raw_unit", "normalized_quantity_kg")), g
        elif g["record_type"] == "invoice_line":
            a, b = cl[g["record_id"]], ol[g["record_id"]]
            assert a[g["field"]] != b[g["field"]], g


def test_shared_numbers_are_legitimate():
    inv = {i["invoice_id"]: i for i in table("invoices")}
    groups = {}
    for g in gt():
        if g["anomaly_type"] == "AN17":
            assert g["is_anomaly"] is False
            groups.setdefault(g["original_value"] + inv[g["invoice_id"]]["supplier_id"], []).append(g["invoice_id"])
    assert groups
    for members in groups.values():
        assert 2 <= len(members) <= 5
        assert len({inv[m]["buyer_id"] for m in members}) == len(members)


def test_splits_are_company_level():
    splits = {r["company_id"]: r["anomaly_split"] for r in table("splits")}
    assert sorted(list(splits.values()).count(s) for s in ("train", "validation", "test")) == [40, 40, 120]
    assert sum(r["forecast_holdout"] for r in table("splits")) == 40
    for g in gt():
        assert g["split"] == splits[g["company_id"]]


def test_forecast_panel_has_no_lookahead():
    rows = table("forecast_panel")
    by = {(r["product_id"], r["t_index"]): r for r in rows}
    for r in rows[::7]:
        prev = by.get((r["product_id"], r["t_index"] - 1))
        if prev and r["lag_1"] is not None:
            assert abs(prev["packaging_kg"] - r["lag_1"]) < 1e-6
        nxt = by.get((r["product_id"], r["t_index"] + 1))
        if nxt:
            assert abs(nxt["packaging_kg"] - r["next_month_packaging_kg"]) < 1e-6
    splits = {r["time_split"] for r in rows}
    assert splits == {"train", "validation", "test"}
