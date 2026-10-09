"""Generate the dummy-entity master and its derived fixtures.

SYNTHETIC — EPRLens Demo.

    python synthetic-data/generate_entities.py                 # full master: 200 companies (approved 2026-10-09)
    python synthetic-data/generate_entities.py --pack test     # core pack only (5 companies), for quick checks

Outputs (paths relative to the repository root):
    synthetic-data/masters/*.csv, test_users.json, entity_manifest.json
    synthetic-data/demo/demo_company.json
    synthetic-data/seed/*.sample.json
    synthetic-data/outputs/sample/illustrative/example_invoice.{json,txt}
    frontend/src/lib/mocks/*.json
    backend/test-events/*.json
"""
import argparse
import hashlib
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "schemas"))

from generators import entities, fixtures  # noqa: E402
from generators.tableio import sha256_file, validate_rows, write_csv, write_json  # noqa: E402
import spec  # noqa: E402

MASTER_TABLES = [
    ("companies", "companies"), ("products", "products"), ("packaging_components", "components"),
    ("suppliers", "suppliers"), ("buyers", "buyers"), ("recyclers", "recyclers"),
    ("addresses", "addresses"), ("entity_relationships", "relationships"),
]


def git_sha(root: Path):
    try:
        out = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10)
        return out.stdout.strip() if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def run(config_path: Path, pack: str, root: Path, masters_dir: Path = None, fixtures_too: bool = True):
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    ctx = entities.generate(cfg, pack)
    masters_dir = masters_dir or root / "synthetic-data" / "masters"

    written = []
    masters = []
    for table, attr in MASTER_TABLES:
        rows = getattr(ctx, attr)
        validate_rows(rows, table)
        path = masters_dir / f"{table}.csv"
        write_csv(rows, path, table)
        masters.append(path)
    validate_rows(ctx.users, "test_users")
    users_path = masters_dir / "test_users.json"
    write_json({"_meta": fixtures.meta(cfg, pack, "TEST FIXTURES ONLY — not a production authorization model. "
                                                  "No passwords are stored."), "users": ctx.users}, users_path)
    masters.append(users_path)

    if fixtures_too:
        as_of = date.fromisoformat(cfg["window"]["end"])
        demo = fixtures.demo_bundle(ctx, cfg, pack, as_of)
        invoice_doc, invoice_txt = fixtures.example_invoice(ctx, cfg)
        outs = {root / "synthetic-data" / "demo" / "demo_company.json": demo}
        for name, obj in fixtures.seed_samples(ctx, cfg, pack).items():
            outs[root / "synthetic-data" / "seed" / name] = obj
        ill = root / "synthetic-data" / "outputs" / "sample" / "illustrative"
        outs[ill / "example_invoice.json"] = invoice_doc
        for name, obj in fixtures.frontend_mocks(ctx, cfg, pack, demo, invoice_doc).items():
            outs[root / "frontend" / "src" / "lib" / "mocks" / name] = obj
        for name, obj in fixtures.lambda_events(ctx, cfg, pack, demo, invoice_doc).items():
            outs[root / "backend" / "test-events" / name] = obj
        for path, obj in outs.items():
            write_json(obj, path)
            written.append(path)
        txt = ill / "example_invoice.txt"
        txt.write_text(invoice_txt, encoding="utf-8", newline="\n")
        written.append(txt)

    test_ids = sorted(
        [x["supplier_id"] for x in ctx.suppliers if x["test_entity"]]
        + [x["buyer_id"] for x in ctx.buyers if x["test_entity"]]
        + [x["recycler_id"] for x in ctx.recyclers if x["test_entity"]]
        + [x["product_id"] for x in ctx.products if x["test_entity"]])
    manifest = {
        "synthetic": True,
        "watermark": fixtures.WATERMARK,
        "seed": cfg["seed"],
        "generator_version": cfg["generator_version"],
        "schema_version": spec.SCHEMA_VERSION,
        "entity_pack": pack,
        "git_sha": git_sha(root),
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "company_count": len(ctx.companies),
        "supplier_count": len(ctx.suppliers),
        "buyer_count": len(ctx.buyers),
        "recycler_count": len(ctx.recyclers),
        "product_count": len(ctx.products),
        "packaging_component_count": len(ctx.components),
        "address_count": len(ctx.addresses),
        "relationship_count": len(ctx.relationships),
        "test_user_count": len(ctx.users),
        "normal_counts": {
            "companies": sum(not x["test_entity"] for x in ctx.companies),
            "suppliers": sum(not x["test_entity"] for x in ctx.suppliers),
            "buyers": sum(not x["test_entity"] for x in ctx.buyers),
            "recyclers": sum(not x["test_entity"] for x in ctx.recyclers),
            "recyclers_registered": sum(x["registered"] and not x["test_entity"] for x in ctx.recyclers),
            "recyclers_unregistered": sum(not x["registered"] and not x["test_entity"] for x in ctx.recyclers),
            "products": sum(not x["test_entity"] for x in ctx.products),
        },
        "test_entity_count": len(test_ids),
        "test_entity_ids": test_ids,
        "test_scenarios": cfg.get("test_scenarios", {}),
        "master_file_hashes": {p.relative_to(root).as_posix(): sha256_file(p) for p in masters},
        "fixture_file_hashes": {p.relative_to(root).as_posix(): sha256_file(p) for p in written},
        "note": ("generated_at and git_sha are excluded from reproducibility checks; compare *_file_hashes. "
                 "git_sha is the commit checked out when the files were generated (null if not a git repo)."),
    }
    write_json(manifest, masters_dir / "entity_manifest.json")
    return ctx, manifest


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=str(HERE / "config" / "entity_seed.yaml"))
    ap.add_argument("--pack", choices=["test", "full"], default="full")
    ap.add_argument("--root", default=str(HERE.parent), help="repository root")
    args = ap.parse_args()
    ctx, manifest = run(Path(args.config), args.pack, Path(args.root))
    counts = {k: v for k, v in manifest.items() if k.endswith("_count")}
    print(f"entity pack '{args.pack}' written: {counts}")


if __name__ == "__main__":
    main()
