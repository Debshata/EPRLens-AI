# Synthetic Data Provenance

> SYNTHETIC — EPRLens Demo. Full dataset generated 2026-10-09 after owner approval ("APPROVED — GENERATE FULL SYNTHETIC DATASET"). Exact values and file hashes: `synthetic-data/MANIFEST.json` (committed copy) and `data/generated/manifests/MANIFEST.json`.

## Why synthetic data

Real company-level EPR operational data (packaging bills of material, invoices, recycler records) is not publicly available and is commercially sensitive. The owner decided (context D024) to use synthetic invoices and synthetic EPR tables only.

## What was generated (generator 1.0.0, seed 20261009, Python 3.12.14)

| Output | Count |
|---|---|
| Companies / products / packaging component rows (entity master) | 200 / 1,775 / 4,522 |
| Transactions (observed; clean: 173,778) | 174,224 |
| Material-flow events (clean ledger) | 718,353 |
| Invoice headers / lines | 46,501 / 179,616 |
| Recycling proxy rows | 14,649 |
| Anomaly ground-truth rows (3,010 anomalies + 693 legitimate hard negatives) | 3,703 |
| Scenarios / results | 600 / 600 |
| Business descriptions | 150 |
| Forecast panel rows (product-month, clean) | 52,931 |
| Invoice PDFs / ground-truth JSON | 1,000 / 1,000 |

Reproducibility: three consecutive full runs produced the same `dataset_sha256` (`0c8f6d5a…`); a pilot-run test asserts byte-identical CSVs, PDFs and JSON for the same seed.

## How it is generated

`synthetic-data/generate.py` reads the committed entity master (never adds entities), then: monthly sales per product → sale / export / return transactions → packaging purchases with an inventory model (units produced = units sold, DS-03) → material events → recycling proxy → invoice register (sales, purchases, imports, returns, credit notes, cancelled twins, scrap sales, recycler processing and service invoices) → shared invoice numbers (AN17 hard negatives) → splits, scenarios, descriptions, forecast panel → **clean snapshot** → anomaly injection with ground truth → selection of exactly 1,000 invoices → one document model per invoice rendered to PDF (ReportLab) **and** written to JSON from the same object.

## Handbook-derived elements

Entity roles (producer, importer, brand owner, plastic waste processor); plastic categories I–IV used as names; invoice-wise and category-wise reporting; up to 5 invoices sharing a number (p.41); registered vs unregistered buyers and vendors; state-wise sales; exports as distinct events; recycled-content field; the 500 MT vs 0.5 MT error pattern (p.15); category misclassification (p.15). All are **TBD — official-source verification** (`epr-domain-summary.md` §23).

## Engineering assumptions (artificial)

Every distribution, growth rate, seasonality profile, price, GST rate, HSN heading, FX rate, packaging weight, recycled-content value, category-by-form convention (`legal_verification_status = TBD`), reorder policy, lot splitting, recycling-chain proxy, anomaly rate and every name, address and identifier. See `generator-assumptions.md` (including the implementation notes at the end).

## Known simplifications

- Import invoices name the entity-master supplier as exporter of record ("overseas dispatch unit, location not modelled"); no foreign entities exist in the master.
- Export sales have no invoice (shipping documents not modelled); they appear as `export_sale` transactions and `EXPORTED` events.
- Credit notes are price-only (no quantity change). Returned goods are not re-stocked into packaging inventory.
- `material_events.csv` is the clean-world ledger; anomalies live in transactions, invoices and recycling (observed) with clean copies in `csv/clean/`.
- `invoices.csv` / `invoices_flat.csv` carry the brief's `is_anomaly` / `anomaly_type` columns as **ground-truth summaries**; detectors and training scripts must drop them.
- The generator uses Python's `random` (seeded per stage and entity via SHA-256) rather than NumPy; output is byte-identical on Python 3.12 and 3.14 for the entity master.

## Limitations

- Models learn the generator's own equations; metrics measure pipeline correctness, not real-world accuracy.
- Prices and quantities do not represent the Indian market; tax treatment is illustrative.
- Categories are a synthetic convention, not legal classification; recycling figures are a proxy, not obligations or certificates.
- Names were checked against a denylist only; coincidental resemblance to a real business is possible and unintended.

## Warning

**ML metrics produced on this synthetic data do not represent real-world accuracy and must be presented as "pipeline validation on synthetic data".**

## Reproduction

```bash
python synthetic-data/generate.py --config synthetic-data/config.yaml --out data/generated
```
Add `--publish` to refresh the committed samples, demo fixtures and `synthetic-data/MANIFEST.json`.
