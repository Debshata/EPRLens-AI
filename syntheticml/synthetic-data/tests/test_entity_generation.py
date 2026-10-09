"""Generator-level tests: determinism, core-pack stability, optional full mode."""
from pathlib import Path

import pytest
import yaml

import generate_entities as ge

SD = Path(__file__).resolve().parents[1]
CONFIG = SD / "config" / "entity_seed.yaml"


def _run(tmp_path, pack="full"):
    return ge.run(CONFIG, pack, tmp_path, masters_dir=tmp_path / "masters", fixtures_too=True)


def test_same_seed_gives_identical_files(tmp_path):
    _, m1 = _run(tmp_path / "a")
    _, m2 = _run(tmp_path / "b")
    assert m1["master_file_hashes"] == m2["master_file_hashes"]
    assert m1["fixture_file_hashes"] == m2["fixture_file_hashes"]


def test_different_seed_changes_output(tmp_path):
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    cfg["seed"] = cfg["seed"] + 1
    alt = tmp_path / "alt.yaml"
    alt.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    _, m1 = _run(tmp_path / "a")
    _, m2 = ge.run(alt, "full", tmp_path / "b", masters_dir=tmp_path / "b" / "masters")
    assert m1["master_file_hashes"]["masters/companies.csv"] != m2["master_file_hashes"]["masters/companies.csv"]


def test_committed_masters_match_generator(tmp_path):
    """The committed test pack is exactly what the generator produces."""
    _, m = _run(tmp_path)
    committed = SD / "masters"
    for name in ("companies.csv", "products.csv", "packaging_components.csv", "suppliers.csv", "buyers.csv",
                 "recyclers.csv", "addresses.csv", "entity_relationships.csv"):
        assert (committed / name).read_bytes() == (tmp_path / "masters" / name).read_bytes(), name


def test_demo_company_is_fixed():
    ctx = ge.entities.generate(yaml.safe_load(CONFIG.read_text(encoding="utf-8")), "test")
    demo = next(c for c in ctx.companies if c["company_id"] == "COMP_0001")
    assert demo["company_name"] == "EcoFizz Beverages Pvt Ltd"
    assert demo["manufacturer"] and demo["brand_owner"] and not demo["importer"]
    assert [p["product_id"] for p in ctx.products if p["company_id"] == "COMP_0001"] == \
        [f"PROD_00000{i}" for i in range(1, 6)]


def test_full_pack_counts_and_core_stability(tmp_path):
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    core = ge.entities.generate(cfg, "test")
    full = ge.entities.generate(cfg, "full")
    assert len(full.companies) == 200
    assert len([s for s in full.suppliers if not s["test_entity"]]) == 120
    assert len([b for b in full.buyers if not b["test_entity"]]) == 150
    assert len([r for r in full.recyclers if not r["test_entity"]]) == 50
    assert len(full.users) == 15
    per_company = {}
    for p in full.products:
        if not p["test_entity"]:
            per_company[p["company_id"]] = per_company.get(p["company_id"], 0) + 1
    assert all(3 <= n <= 15 for n in per_company.values())
    core_rows = {c["company_id"]: c for c in core.companies}
    for c in full.companies[:5]:
        assert c == core_rows[c["company_id"]]
