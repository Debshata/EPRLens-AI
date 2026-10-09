# EPRLens AI — Synthetic Data

> **SYNTHETIC — EPRLens Demo.** Every company, product, address, identifier and number here is fictional. Nothing is real client data, a market statistic or a regulatory fact. Metrics computed on this data do not represent real-world accuracy.

## Status

| Part | Status |
|---|---|
| Reference pack (`../docs/`) | DS-01…DS-25 approved 2026-10-09 (`../docs/DECISIONS-REQUIRED.md`) |
| Schemas (`schemas/`) | v0.2.0 (entity tables final for this phase; activity tables still proposals) |
| Entity master — full: 200 companies, 120+2 suppliers, 150+1 buyers, 50+1 recyclers (`masters/`) | generated 2026-10-09, verified on Python 3.12.14 |
| Transactions, invoices, recycling, scenarios, 1,000 PDFs (`generate.py`) | not built — after `APPROVED — GENERATE FULL SYNTHETIC DATASET` |

## Requirements

- Python **3.12** (DS-19, approved). Verified on 3.12.14; 3.14.3 produces byte-identical masters. The entity code needs only the standard library + PyYAML + jsonschema.
- Dependencies pinned in `requirements.txt`.

## Fresh-clone commands (run from the repository root)

```bash
python -m venv .venv
```
Windows:
```bash
.venv\Scripts\activate
```
Linux/macOS:
```bash
source .venv/bin/activate
```
```bash
pip install -r synthetic-data/requirements.txt
```
```bash
python synthetic-data/schemas/build_schemas.py
```
```bash
python synthetic-data/generate_entities.py
```
(`--pack test` regenerates only the 5-company core pack, for quick checks — do not commit its output over the full master.)
```bash
pytest
```

After approval (not yet implemented):
```bash
python synthetic-data/generate.py --config synthetic-data/config.yaml --out data/generated
```
```bash
python ml/scripts/train_forecast.py --data data/generated
```
```bash
python ml/scripts/train_anomaly.py --data data/generated
```

## Layout

See `../docs/output-folder-spec.md`. Generated full outputs go to `data/generated/` (git-ignored) and to private S3 / release assets — never into normal Git history.

## Reproducibility

`config/entity_seed.yaml` holds the seed (`20261009`). `masters/entity_manifest.json` records seed, generator version, git SHA, config SHA-256, counts and SHA-256 hashes of every master and fixture file. `generated_at` and `git_sha` are excluded from reproducibility comparisons.
