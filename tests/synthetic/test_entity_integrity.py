"""Cross-cutting integrity tests over the committed entity masters and every
fixture that references them (one source of truth — brief §21).
SYNTHETIC — EPRLens Demo."""
import json
import re
import sys
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[2]
SD = ROOT / "synthetic-data"
sys.path.insert(0, str(SD))

from generators import identifiers as ids  # noqa: E402
from generators.entity_index import EntityIndex  # noqa: E402
from generators.names import contains_denylisted  # noqa: E402
from generators.tableio import load_schema, sha256_file  # noqa: E402

MASTERS = SD / "masters"
ID_RE = re.compile(r"\b(?:COMP_\d{4}|SUP_(?:\d{4}|TEST_\d{3})|BUY_(?:\d{4}|TEST_\d{3})|REC_(?:\d{4}|TEST_\d{3})|"
                   r"PROD_(?:\d{6}|TEST_\d{3})|PKGCOMP_\d{6}|ADDR_\d{6}|REL_\d{6}|USR_\d{4})\b")


@pytest.fixture(scope="module")
def ix():
    return EntityIndex(MASTERS)


@pytest.fixture(scope="module")
def users():
    return json.loads((MASTERS / "test_users.json").read_text(encoding="utf-8"))["users"]


# ------------------------------------------------------------------ schema & safety
@pytest.mark.parametrize("table", ["companies", "products", "packaging_components", "suppliers", "buyers",
                                   "recyclers", "addresses", "entity_relationships"])
def test_rows_match_schema(ix, table):
    v = jsonschema.Draft202012Validator(load_schema(table))
    for row in ix.tables[table]:
        errs = list(v.iter_errors(row))
        assert not errs, (row, errs[0].message)


def test_users_match_schema_and_have_no_passwords(users):
    v = jsonschema.Draft202012Validator(load_schema("test_users"))
    for u in users:
        assert not list(v.iter_errors(u))
        assert u["fake_email"].endswith("@example.com")
        assert not any("pass" in k.lower() or "secret" in k.lower() for k in u)


def test_every_row_is_marked_synthetic(ix, users):
    for table in ix.tables.values():
        assert all(r["synthetic_flag"] is True for r in table)
    assert all(u["synthetic_flag"] is True for u in users)


def test_no_valid_real_gstins(ix):
    values = [r["fake_gstin"] for t in ("suppliers", "buyers", "recyclers") for r in ix.tables[t] if r["fake_gstin"]]
    assert values
    for g in values:
        assert not ids.gstin_checksum_valid(g), g


def test_gstin_state_code_matches_entity_state(ix):
    for t in ("suppliers", "buyers", "recyclers"):
        for r in ix.tables[t]:
            if r["fake_gstin"]:
                addr = ix.resolve(r["hq_address_id"])
                assert r["fake_gstin"][:2] == addr["state_code"]


def test_no_real_brand_names(ix):
    names = ([r["company_name"] for r in ix.tables["companies"]] + [r["product_name"] for r in ix.tables["products"]]
             + [r["supplier_name"] for r in ix.tables["suppliers"]] + [r["buyer_name"] for r in ix.tables["buyers"]]
             + [r["recycler_name"] for r in ix.tables["recyclers"]])
    assert not [n for n in names if contains_denylisted(n)]
    assert len(set(names)) == len(names)


# ------------------------------------------------------------------ foreign keys
def test_all_foreign_keys_resolve(ix):
    for table in ix.tables:
        props = load_schema(table)["properties"]
        for col, prop in props.items():
            fk = prop.get("x-foreign-key")
            if not fk:
                continue
            ref_table, ref_col = fk.split(".")
            keys = {r[ref_col] for r in ix.tables[ref_table]}
            for row in ix.tables[table]:
                if row[col] is not None:
                    assert row[col] in keys, (table, col, row[col])


def test_addresses_belong_to_existing_entities(ix):
    for a in ix.tables["addresses"]:
        assert ix.resolve(a["entity_id"]) is not None


def test_relationship_endpoints_exist(ix):
    for r in ix.tables["entity_relationships"]:
        assert ix.resolve(r["source_entity_id"]) is not None, r
        assert ix.resolve(r["target_entity_id"]) is not None, r


def test_product_belongs_to_company(ix):
    owns = {(r["source_entity_id"], r["target_entity_id"]) for r in ix.relationships(rtype="OWNS_PRODUCT")}
    for p in ix.tables["products"]:
        assert ix.resolve(p["company_id"]) is not None
        assert (p["company_id"], p["product_id"]) in owns


def test_component_belongs_to_product(ix):
    uses = {(r["source_entity_id"], r["target_entity_id"]) for r in ix.relationships(rtype="USES_COMPONENT")}
    for c in ix.tables["packaging_components"]:
        assert (c["product_id"], c["component_id"]) in uses


def test_every_product_has_components_in_force_today(ix):
    for p in ix.tables["products"]:
        if p["launch_date"] <= "2026-03-31":
            assert ix.components_in_force(p["product_id"], "2026-03-31"), p["product_id"]


def test_supplier_supplies_expected_material(ix):
    for c in ix.tables["packaging_components"]:
        s = ix.resolve(c["supplier_id"])
        assert c["material"] in s["supported_materials"], (c["component_id"], c["material"], s["supplier_id"])


def test_company_buys_from_each_component_supplier(ix):
    for c in ix.tables["packaging_components"]:
        company = ix.resolve(c["product_id"])["company_id"]
        targets = {r["target_entity_id"] for r in ix.relationships(company, "BUYS_FROM")}
        assert c["supplier_id"] in targets


def test_recycler_supports_company_plastics(ix):
    for co in ix.tables["companies"]:
        recs = [ix.resolve(r["target_entity_id"]) for r in ix.relationships(co["company_id"], "USES_RECYCLER")]
        pids = {p["product_id"] for p in ix.tables["products"] if p["company_id"] == co["company_id"]}
        mats = {c["material"] for c in ix.tables["packaging_components"]
                if c["product_id"] in pids and c["plastic_epr_relevant"]}
        for rec in recs:
            assert set(rec["supported_materials"]) & mats, (co["company_id"], rec["recycler_id"])
        registered = [rec for rec in recs if rec["registered"]]
        for m in mats:
            assert any(m in rec["supported_materials"] for rec in registered), (co["company_id"], m)


def test_category_rules(ix):
    for c in ix.tables["packaging_components"]:
        if not c["plastic_epr_relevant"]:
            assert c["synthetic_category"] == "NA"
        else:
            assert c["synthetic_category"] in ("CAT_I", "CAT_II", "CAT_III", "CAT_IV")
        assert c["material"] != "BATTERY"
        if c["material"] == "MLP":
            assert c["synthetic_category"] == "CAT_III"
        if c["material"] == "COMPOSTABLE":
            assert c["synthetic_category"] == "CAT_IV"


def test_spec_versions_do_not_overlap(ix):
    groups = {}
    for c in ix.tables["packaging_components"]:
        groups.setdefault((c["product_id"], c["component_name"]), []).append(c)
    for rows in groups.values():
        rows.sort(key=lambda r: r["spec_version"])
        assert [r["spec_version"] for r in rows] == list(range(1, len(rows) + 1))
        for a, b in zip(rows, rows[1:]):
            assert a["effective_to"] is not None and a["effective_to"] < b["effective_from"]


# ------------------------------------------------------------------ scenarios
def test_inactive_entity_handling(ix):
    ended = [r for r in ix.tables["entity_relationships"] if r["end_date"]]
    assert any(r["relationship_type"] == "BUYS_FROM" for r in ended)
    assert any(r["relationship_type"] == "OWNS_PRODUCT" for r in ended)
    for r in ix.tables["entity_relationships"]:
        assert r["active"] == (r["end_date"] is None)
        if r["end_date"]:
            assert r["end_date"] >= r["start_date"]
    inactive = [p for p in ix.tables["products"] if not p["active"]]
    assert inactive
    for p in inactive:
        rel = ix.relationships(p["company_id"], "OWNS_PRODUCT")
        assert any(r["target_entity_id"] == p["product_id"] and r["end_date"] for r in rel)
    active_on_2026 = {r["target_entity_id"] for r in ix.relationships("COMP_0002", "BUYS_FROM", active_on="2026-01-01")}
    ever = {r["target_entity_id"] for r in ix.relationships("COMP_0002", "BUYS_FROM")}
    assert ever - active_on_2026, "ended supplier relationship must not be active in 2026"


def test_unregistered_recycler_scenario(ix):
    rec = ix.resolve("REC_TEST_001")
    assert rec["test_entity"] and rec["registered"] is False
    assert rec["fake_registration_number"]  # a *claimed* number
    registered_numbers = {r["fake_registration_number"] for r in ix.tables["recyclers"] if r["registered"]}
    assert rec["fake_registration_number"] not in registered_numbers
    assert ix.relationships(rtype="USES_RECYCLER") and any(
        r["target_entity_id"] == "REC_TEST_001" for r in ix.relationships(rtype="USES_RECYCLER"))


def test_unknown_supplier_scenario(ix):
    assert ix.resolve("SUP_9999") is None
    assert ix.resolve("XYZ_0001") is None


def test_stale_product_master_scenario(ix):
    p = ix.resolve("PROD_TEST_001")
    assert p["test_entity"]
    before = ix.weight_in_force("PROD_TEST_001", "Laminate snack pouch", "2024-12-31")
    after = ix.weight_in_force("PROD_TEST_001", "Laminate snack pouch", "2025-01-01")
    assert before == 6.5 and after == 5.2


def test_supplier_test_entities(ix):
    s1, s2 = ix.resolve("SUP_TEST_001"), ix.resolve("SUP_TEST_002")
    assert s1["test_entity"] and s2["test_entity"]
    assert s2["supported_materials"] == ["PP"]
    assert any(r["target_entity_id"] == "SUP_TEST_001" for r in ix.relationships("COMP_0001", "BUYS_FROM"))


def test_buyer_with_incomplete_gst(ix):
    b = ix.resolve("BUY_TEST_001")
    assert b["test_entity"] and len(b["fake_gstin"]) == 14
    assert not ids.gstin_format_ok(b["fake_gstin"])


# ------------------------------------------------------------------ one source of truth
FIXTURE_DIRS = [SD / "demo", SD / "seed", SD / "outputs" / "sample" / "illustrative",
                ROOT / "frontend" / "src" / "lib" / "mocks", ROOT / "backend" / "test-events"]


def _fixture_files():
    return [p for d in FIXTURE_DIRS if d.exists() for p in sorted(d.glob("*.json"))]


@pytest.mark.parametrize("path", _fixture_files(), ids=lambda p: p.name)
def test_fixture_ids_exist_in_masters(ix, users, path):
    text = path.read_text(encoding="utf-8")
    user_ids = {u["user_id"] for u in users}
    for entity_id in set(ID_RE.findall(text)):
        assert ix.resolve(entity_id) is not None or entity_id in user_ids, (path.name, entity_id)
    assert "SYNTHETIC — EPRLens Demo" in text or '"synthetic": true' in text


def test_example_invoice_parties_and_math(ix):
    doc = json.loads((SD / "outputs" / "sample" / "illustrative" / "example_invoice.json").read_text(encoding="utf-8"))
    assert ix.resolve(doc["supplier_id"]) and ix.resolve(doc["buyer_id"]) and ix.resolve(doc["company_id"])
    e = doc["expected_fields"]
    assert e["vendor_gstin"] == ix.resolve(doc["supplier_id"])["fake_gstin"]
    for line in e["lines"]:
        comp = ix.resolve(line["component_id"])
        assert comp["supplier_id"] == doc["supplier_id"]
        assert line["normalized_quantity_kg"] == round(line["quantity"] * comp["weight_per_unit_g"] / 1000, 3)
        assert line["amount"] == round(line["quantity"] * line["rate"], 2)
    assert abs(e["total_taxable_value"] + e["gst"] - e["invoice_total"]) < 0.01
    jsonschema.validate(doc, json.loads((SD / "schemas" / "invoice_document.schema.json").read_text(encoding="utf-8")))


def test_transaction_references_valid_invoice():
    pytest.skip("transactions/invoices are generated only after full-dataset approval")


def test_manifest_hashes_and_counts():
    m = json.loads((MASTERS / "entity_manifest.json").read_text(encoding="utf-8"))
    for key in ("generator_version", "seed", "git_sha", "config_sha256", "company_count", "supplier_count",
                "buyer_count", "recycler_count", "product_count", "packaging_component_count", "relationship_count",
                "test_user_count", "test_entity_count", "generated_at", "master_file_hashes"):
        assert key in m, key
    for rel, digest in {**m["master_file_hashes"], **m["fixture_file_hashes"]}.items():
        assert sha256_file(ROOT / rel) == digest, rel
    assert m["company_count"] == 200 and m["test_user_count"] == 15 and m["test_entity_count"] == 5


# ------------------------------------------------------------------ full-master counts (brief §16)
def _normal(rows):
    return [r for r in rows if not r["test_entity"]]


def test_exact_normal_counts(ix):
    assert len(_normal(ix.tables["companies"])) == 200
    assert [c["company_id"] for c in ix.tables["companies"]] == [f"COMP_{i:04d}" for i in range(1, 201)]
    assert len(_normal(ix.tables["suppliers"])) == 120
    assert len(_normal(ix.tables["buyers"])) == 150
    recs = _normal(ix.tables["recyclers"])
    assert len(recs) == 50
    assert sum(not r["registered"] for r in recs) == 8
    assert sum(r["registered"] for r in recs) == 42


def test_normal_ids_are_contiguous(ix):
    for table, prefix, n in (("suppliers", "SUP", 120), ("buyers", "BUY", 150), ("recyclers", "REC", 50)):
        key = {"suppliers": "supplier_id", "buyers": "buyer_id", "recyclers": "recycler_id"}[table]
        assert [r[key] for r in _normal(ix.tables[table])] == [f"{prefix}_{i:04d}" for i in range(1, n + 1)]


def test_products_per_company_between_3_and_15(ix):
    counts = {}
    for p in _normal(ix.tables["products"]):
        counts[p["company_id"]] = counts.get(p["company_id"], 0) + 1
    assert set(counts) == {c["company_id"] for c in ix.tables["companies"]}
    assert all(3 <= n <= 15 for n in counts.values()), counts


def test_products_match_company_industry(ix):
    for p in ix.tables["products"]:
        assert p["industry"] == ix.resolve(p["company_id"])["industry"]


def test_all_industries_present_and_unequal(ix):
    counts = {}
    for c in ix.tables["companies"]:
        counts[c["industry"]] = counts.get(c["industry"], 0) + 1
    assert len(counts) == 13
    assert len(set(counts.values())) > 3


def test_supplier_form_and_material_are_sensible(ix):
    for c in ix.tables["packaging_components"]:
        s = ix.resolve(c["supplier_id"])
        assert c["component_form"] in s["supported_component_forms"], (c["component_id"], s["supplier_type"])
    for s in ix.tables["suppliers"]:
        if s["supplier_type"] == "carton supplier":
            assert set(s["supported_materials"]) <= {"CARDBOARD", "PAPER"}


def test_category_is_convention_not_legal(ix):
    for c in ix.tables["packaging_components"]:
        assert c["category_basis"] == "synthetic_convention_by_form"
        assert c["legal_verification_status"] == "TBD"


def test_gst_and_epr_registration_are_separate_fields(ix):
    b = ix.tables["buyers"]
    assert all(isinstance(x["gst_registered"], bool) and isinstance(x["epr_registered"], bool) for x in b)
    assert any(x["gst_registered"] and not x["epr_registered"] for x in b)
    assert any(not x["gst_registered"] for x in b)
    for x in b:
        if not x["gst_registered"]:
            assert x["fake_gstin"] is None


def test_test_entities_flagged_with_codes(ix):
    expected = {"REC_TEST_001", "SUP_TEST_001", "SUP_TEST_002", "BUY_TEST_001", "PROD_TEST_001"}
    found = set()
    for t in ("suppliers", "buyers", "recyclers", "products", "companies"):
        key = ix.tables[t] and next(k for k in ix.tables[t][0] if k.endswith("_id"))
        for r in ix.tables[t]:
            if "_TEST_" in r[key]:
                assert r["test_entity"] is True and re.match(r"^TS\d{2}_[A-Z0-9_]+$", r["test_scenario"])
                found.add(r[key])
            else:
                assert r["test_entity"] is False and r["test_scenario"] is None
    assert found == expected


def test_recycler_registration_numbers_are_synthetic(ix):
    for r in ix.tables["recyclers"]:
        if r["fake_registration_number"]:
            assert r["fake_registration_number"].startswith("SYN-PWP-")


def test_users_are_fixtures(users):
    assert len(users) == 15
    assert {u["role"] for u in users} == {"company_admin", "sustainability_manager", "compliance_manager",
                                         "finance_user", "operations_user", "consultant", "demo_user"}
    assert all(u["fixture_only"] is True for u in users)


def test_mocks_and_events_reference_entities():
    for d in (ROOT / "frontend" / "src" / "lib" / "mocks", ROOT / "backend" / "test-events"):
        files = sorted(d.glob("*.json"))
        assert files
        for f in files:
            assert ID_RE.search(f.read_text(encoding="utf-8")), f.name
    company = json.loads((ROOT / "frontend" / "src" / "lib" / "mocks" / "company.json").read_text(encoding="utf-8"))
    assert company["company"]["company_id"] == "COMP_0001"


def test_ecofizz_profile(ix):
    c = ix.resolve("COMP_0001")
    assert c["company_name"] == "EcoFizz Beverages Pvt Ltd" and "FICTIONAL" in c["business_description"]
    prods = [p for p in ix.tables["products"] if p["company_id"] == "COMP_0001"]
    assert len(prods) == 5
    comps = [x for x in ix.tables["packaging_components"] if x["product_id"] in {p["product_id"] for p in prods}]
    assert any(x["material"] == "PET" for x in comps)
    assert any(not x["plastic_epr_relevant"] for x in comps)
    assert any(x["spec_version"] == 2 for x in comps)
