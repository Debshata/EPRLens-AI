# Synthetic Data Provenance (DRAFT)

> **Status:** DRAFT — completed after the full dataset is generated (counts and hashes filled from `MANIFEST.json`). SYNTHETIC — EPRLens Demo.

## Why synthetic data

Real company-level EPR operational data (packaging bills of material, invoices, recycler records) is not publicly available and is commercially sensitive. The owner decided (context D024) to use synthetic invoices and synthetic EPR tables only.

## How it is generated

A single Python generator, one config file and one master seed. Hierarchical generation (`generator-assumptions.md`); anomalies injected into a clean world with separate ground truth (`anomaly-catalogue.md`); PDFs and JSON rendered from the same object (`pdf-generation-rules.md`).

## Handbook-derived elements

Entity roles (producer, importer, brand owner, PWP); plastic categories I–IV; invoice-wise and category-wise reporting; ≤ 5 invoices sharing a number; registered vs unregistered buyer/vendor distinction; state-wise sales; exports as distinct events; recycled-content field; two-year history; 500 MT vs 0.5 MT error pattern; category-misclassification pattern. All marked TBD-verify in `epr-domain-summary.md` §23.

## Engineering assumptions (artificial)

Every distribution, rate, price, weight, seasonality profile, growth rate, GST rate, HSN mapping, category-by-form mapping, recycling-chain proxy, reorder policy, company/product/supplier names, addresses, identifiers and anomaly rates.

## Limitations

- Models learn the generator's equations; metrics do not represent real-world accuracy.
- Prices and quantities do not represent the Indian market.
- Category assignment is declared by component form, not a legal classification.
- No real regulatory targets, certificate prices or liabilities are computed.
- Names were checked against a small denylist only; coincidental resemblance to a real business is possible and unintended.

## Warning

**ML metrics produced on this synthetic data do not represent real-world accuracy and must be presented as "pipeline validation on synthetic data".**

## Reproduction

See `synthetic-data/README.md`. Provenance record: generator_version, git_commit, seed, config_sha256, data hashes, schema versions in `MANIFEST.json`.
