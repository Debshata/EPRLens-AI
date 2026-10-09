# Synthetic Data Specification

> **Status:** PROPOSED — awaiting owner approval (see `DECISIONS-REQUIRED.md`). SYNTHETIC — EPRLens Demo.
> Values marked *(DS-nn)* follow the recommended option of that decision and change if the owner picks differently.

## 1. Purpose

One reproducible synthetic world that feeds:

| # | Consumer | Files used |
|---|---|---|
| 1 | Forecasting ML | `transactions.csv` → `forecast_panel.csv` (derived) |
| 2 | Anomaly detection ML | `invoices*.csv`, `transactions.csv`, `recycling.csv`, `anomaly_ground_truth.csv` |
| 3 | Invoice extraction testing | 1,000 PDFs + 1,000 ground-truth JSON |
| 4 | Material-flow calculations | `material_events.csv` |
| 5 | Invoice ↔ CSV reconciliation | `invoices.csv`, `invoice_lines.csv`, `transactions.csv` |
| 6 | What-if simulation | `scenarios.csv`, `scenario_results.csv` |
| 7 | Demo company | `demo/demo_company.json` + its slice of every table |
| 8 | Rules-engine tests | `business_descriptions.csv`, masters, ground truth |
| 9 | Frontend mocks | `frontend/src/lib/mocks/*.json` (same IDs) |
| 10 | AWS Lambda tests | `backend/test-events/*.json` (same IDs) |

It is **not** evidence of real-world accuracy, market prices or regulatory outcomes.

## 2. Entities and relationships

```
Company 1─* Product 1─* PackagingComponent *─1 Supplier
Company *─* Supplier   (BUYS_FROM, entity_relationships)
Company *─* Buyer      (SELLS_TO)
Company *─* Recycler   (USES_RECYCLER)
Company 1─* Transaction *─0..1 InvoiceLine *─1 Invoice
Transaction 1─* MaterialEvent (one per component per movement)
Company 1─* RecyclingRecord *─1 Recycler
Company 1─* Scenario 1─1 ScenarioResult
Company 1─0..1 BusinessDescription
Any record 1─* AnomalyGroundTruth (separate file; detectors never read it)
Invoice 0..1─1 InvoiceDocument (PDF + JSON, only the 1,000 sampled invoices)
Every party 1─1 Address (hq) and 0..* extra addresses
```

## 3. Time horizon *(DS-01 B)*

- 36 monthly periods, **2023-04 → 2026-03** = FY 2023-24, FY 2024-25, FY 2025-26 (Indian FY Apr–Mar).
- Dates inside a month are drawn deterministically from the seed; invoice dates fall on business days (Mon–Sat).
- Product `launch_date` may precede the window; products launched inside the window have no earlier rows.

## 4. Identifiers

Full rules in `dummy-identifier-rules.md`.

| Entity | Format | Example |
|---|---|---|
| Company | `COMP_####` | COMP_0001 |
| Supplier | `SUP_####` / `SUP_TEST_###` | SUP_0004 |
| Buyer | `BUY_####` / `BUY_TEST_###` | BUY_0032 |
| Recycler | `REC_####` / `REC_TEST_###` | REC_0012 |
| Product | `PROD_######` / `PROD_TEST_###` | PROD_000001 |
| Packaging component | `PKGCOMP_######` | PKGCOMP_000231 |
| Address | `ADDR_######` | ADDR_000010 |
| Relationship | `REL_######` | REL_000001 |
| Transaction | `TXN_########` | TXN_00012345 |
| Material event | `MEV_#########` | MEV_000045678 |
| Invoice (internal) | `INV_########` | INV_00001234 |
| Invoice line | `INVL_#########` | INVL_000004567 |
| Invoice number (printed) | per-supplier series, ≤ 16 chars, contains `SY` marker | `SYEF/2425/00123` |
| Document (PDF) | `DOC_######` | DOC_000001 |
| Recycling record | `RCY_#######` | RCY_0000123 |
| Scenario | `SCN_######` | SCN_000010 |
| Anomaly instance | `ANM_#######` | ANM_0000042 |
| Business description | `DESC_####` | DESC_0001 |
| Test user | `USR_####` | USR_0001 |

IDs are assigned in generation order after deterministic sorting, so the same seed yields the same IDs.

## 5. Naming conventions

- Files: `snake_case.csv`; columns `snake_case`; booleans `true`/`false`; dates ISO `YYYY-MM-DD`; months `YYYY-MM`; empty string = null in CSV (JSON uses `null`).
- Units appear in column names: `_kg`, `_g`, `_pct`, `_cr` (₹ crore), `_inr`.
- Every row and JSON object carries `synthetic_flag=true`. Every rendered document carries the watermark **SYNTHETIC — EPRLens Demo**.

## 6. Seed strategy

- One master seed in config (`seed: 20261009`).
- Each generator stage derives its own sub-seed: `sub_seed = int(sha256(f"{seed}:{stage}:{key}").hexdigest()[:16], 16)`. Stages never share a random stream, so adding a column in one stage does not shift random draws in another.
- Per-entity streams (e.g. per company) use `key=company_id`, so regenerating one company's history does not change others.
- Python's built-in `hash()` is never used (it is salted per process).
- Full generation will use `numpy.random.Generator(PCG64(sub_seed))`; the entity pilot uses `random.Random(sub_seed)` (stdlib only).

## 7. Units

All internal mass is stored in **kg** (see `units-and-conversions.md`). Raw value, raw unit, normalised kg and the conversion rule are preserved on every quantity that came from a "document".

## 8. Core assumptions (all synthetic; details in `generator-assumptions.md`)

1. Company turnover drives annual units, product count, state count, supplier count and invoice count.
2. Industry drives material mix, unit packaging weight, seasonality and price bands.
3. Units sold × weight_per_unit_g / 1000 = packaging kg associated with units sold.
4. Units produced = units sold per month *(DS-03 A)*.
5. recycled ≤ collected ≤ generated unless an anomaly is injected *(DS-11 A)*.
6. Non-plastic components are generated but flagged `plastic_epr_relevant=false` *(DS-02 A)*.
7. Prices and GST rates are illustrative *(DS-13 A)*.

## 9. Realistic dependencies (hierarchical, not independent draws)

```
turnover_cr ─► company_size ─► n_products, n_states, n_suppliers, n_buyers
industry ─► archetypes ─► components(material, category, weight range)
          ─► seasonality profile, price band
product base volume = f(turnover, industry, product share)
units[t] = base × growth^t × season(month) × noise
packaging_kg[t] = Σ components units[t] × weight_g / 1000
purchases lead consumption (reorder policy) ─► inventory events
sales split by state (Dirichlet) and buyer (registered share)
invoices aggregate transactions by counterparty-month
recycling proxy from placed_on_market with lag and rates ≤ 1
```

## 10. Generation order

1. Companies → 2. Products → 3. Packaging components → 4. Suppliers, buyers, recyclers, addresses, relationships, test users → 5. Monthly sales (clean) → 6. Transactions (sales + purchases) → 7. Material events → 8. Invoices + lines → 9. Recycling records → 10. Scenarios + results → 11. Business descriptions → 12. **Anomaly injection** → 13. Ground-truth labels → 14. PDF sampling + rendering + JSON → 15. Manifest + hashes.

Steps 1–4 are the *entity master* (this phase's pilot). Steps 5–15 wait for approval.

## 11. Anomaly-generation order

1. Generate a fully clean world and hash it (`clean_data_sha256`).
2. Select anomaly targets with a dedicated sub-seed per anomaly type, stratified by company split (so instances stay in one split).
3. Apply mutations in a fixed type order (AN01 … AN20). A record receives at most one anomaly except a small configured share of compound cases.
4. Each mutation writes one `anomaly_ground_truth` row (original value, modified value, field, method, severity, seed).
5. Legitimate "hard negatives" (e.g. AN17 legitimate shared invoice numbers) are created in the clean world and labelled `is_anomaly=false` with `test_case_type`.
6. Derived tables (flat views, forecast panel) are rebuilt **after** injection; the clean versions are also kept for evaluation.

## 12. Train / validation / test principles *(DS-08 A)*

- Forecast: chronological — months 1–24 train, 25–30 validation, 31–36 test; plus 40 held-out companies never seen in training.
- Anomaly: split by company 60 / 20 / 20 using a hash of `company_id`; anomaly instances inherit their company's split.
- Features use only data at or before the forecast origin.
- Ground-truth columns are never present in feature tables.
- Invoice extraction: evaluation only; all 1,000 documents, reported per template and per invoice type.

## 13. Reproducibility requirements

- Same `seed` + same `config.yaml` + same generator version ⇒ byte-identical CSV/JSON and (with ReportLab `invariant=1`) byte-identical PDFs.
- `MANIFEST.json` records generator_version, git_commit, seed, config_sha256, generated_at, counts, per-file sha256, schema versions, clean_data_sha256.
- `generated_at` is excluded from data hashes.
- A test regenerates a small pack twice and asserts identical hashes.
