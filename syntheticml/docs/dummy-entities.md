# Dummy Entities

> SYNTHETIC — EPRLens Demo. Status: **full entity master generated 2026-10-09** (approval `APPROVED — GENERATE FULL ENTITY MASTER`, DS-01…DS-25). Verified on Python 3.12.14. Activity data (transactions, invoices, recycling history, PDFs) is **not** generated yet.

## Why they exist

Every part of EPRLens (synthetic CSVs, PDF invoices, ground-truth JSON, ML datasets, frontend mocks, AWS Lambda test events, DB seeds, dashboard demos) must reference the **same** fictional companies, products, suppliers, buyers and recyclers. `synthetic-data/masters/` is that single source of truth. No other part of the project may invent its own entities; `tests/synthetic/test_entity_integrity.py` fails if a fixture references an unknown ID.

## Contents

| Master file | Entity | Count |
|---|---|---|
| companies.csv | Client companies COMP_0001–COMP_0200 (incl. fake GSTIN-like value, added 2026-10-09) | 200 |
| products.csv | Products, 3–15 per company (mean 8.9) | 1,774 + PROD_TEST_001 |
| packaging_components.csv | Components, one row per effective-dated spec version | 4,522 (213 are v2 light-weighting rows) |
| suppliers.csv | SUP_0001–SUP_0120 + SUP_TEST_001/002 | 122 |
| buyers.csv | BUY_0001–BUY_0150 + BUY_TEST_001 | 151 |
| recyclers.csv | REC_0001–REC_0050 (42 registered, 8 unregistered) + REC_TEST_001 | 51 |
| addresses.csv | Fictional HQ / plant / warehouse addresses | 598 |
| entity_relationships.csv | BUYS_FROM, SELLS_TO, USES_RECYCLER, OWNS_PRODUCT, USES_COMPONENT, SUPPLIED_BY | 15,084 |
| test_users.json | 15 fixture users, 7 roles, no passwords | 15 |
| entity_manifest.json | seed, versions, git SHA, config hash, counts, SHA-256 of every file | — |

The core pack (COMP_0001–0005, SUP_0001–0010, BUY_0001–0010, REC_0001–0005, USR_0001–0005, all `_TEST_` entities) is generated first and identically in `--pack test` and full mode, so demo/mock/fixture IDs are stable.

## Key fields and safeguards

- **Packaging category:** `synthetic_category` (form-based modelling convention, DS-09), `category_basis = synthetic_convention_by_form`, `category_confidence`, `legal_verification_status = TBD`. Not a legal classification. Non-plastic materials always get `NA`. MLP → CAT_III is a configurable synthetic default (the handbook does not define MLP).
- **Buyers:** `gst_registered` and `epr_registered` are separate fields.
- **Companies:** `brand_owner` is a business attribute; `epr_registered` / `registration_status` are declared synthetic statuses. No applicability logic is encoded in the master.
- **Suppliers:** `supported_materials` and `supported_component_forms` follow the supplier type; components are only ever assigned to a supplier whose type supplies that form *and* material (no carton supplier ships PET bottles). Resin and raw-material suppliers own no component forms; they exist for later raw-material purchase invoices.
- **Recyclers:** processing type → materials (PET recycling → PET, PP recycling → PP, mixed-plastic → HDPE/LDPE/LLDPE/PP/PS/PVC, MLP processing → MLP, industrial composting → COMPOSTABLE). `SYN-PWP-…` numbers are fictional and never represent a CPCB authorization.
- **Test users:** fixtures only (`fixture_only = true`), not the production authorization model (DS-25).

## Naming rules

Fused invented stems (`Kira` + `wave`) + type word + legal suffix; product names = brand stem + descriptor + size. A denylist test rejects well-known real brands; coincidental resemblance is possible and unintended. Every row has `synthetic_flag = true`.

## Demo company — COMP_0001 EcoFizz Beverages Pvt Ltd (FICTIONAL / SYNTHETIC)

Beverages; manufacturer + brand owner; HQ Delhi, plant Haryana; sells in Delhi, Haryana, UP, Rajasthan, Punjab; ₹180 Cr (illustrative). Products PROD_000001–000005: four PET-bottle drinks (bottle + cap + label + carton) and one glass-bottle soda (non-plastic bottle, PP cap). Cola 750 ml bottle: 28.0 g (v1, to 2025-03-31) → 25.0 g (v2, from 2025-04-01). Full profile: `synthetic-data/demo/demo_company.json`.

## Test entities (scenario codes)

| ID | test_scenario | Purpose |
|---|---|---|
| REC_TEST_001 | TS01_UNREGISTERED_RECYCLER | Unregistered recycler with a claimed SYN-PWP number; used by COMP_0003 (AN13) |
| SUP_TEST_001 | TS02_SUPPLIER_ABNORMAL_QUANTITY | PET bottle supplier with irregular ×5 spikes; secondary supplier of COMP_0001 (AN09/AN01) |
| SUP_TEST_002 | TS03_SUPPLIER_MATERIAL_CHANGE | Cap supplier; master says PP only, later invoices switch to HDPE from 2025-07 (AN20/AN03) |
| BUY_TEST_001 | TS04_BUYER_INCOMPLETE_REGISTRATION | Truncated 14-char GSTIN, not EPR-registered; buyer of COMP_0001 (AN06) |
| PROD_TEST_001 | TS05_STALE_PACKAGING_WEIGHT | Pouch 6.5 g → 5.2 g on 2025-01-01 (AN18) |

Non-test edge cases: COMP_0004's PROD_000014 discontinued 2025-06-30; one COMP_0002 BUYS_FROM ended 2024-12-31; 8 unregistered normal recyclers; ~10 % of extension companies also use an unregistered recycler that handles one of their materials.

## Consumers

| Consumer | Location | Status |
|---|---|---|
| Frontend mocks | `frontend/src/lib/mocks/` company, products, suppliers, recyclers, invoice (illustrative) | generated from masters |
| AWS Lambda test events | `backend/test-events/` company, invoice-upload, classify-image, scenario | generated from masters |
| DB seed | `synthetic-data/seed/*.sample.json` (core pack only) | generated from masters |
| Transactions, invoices, recycling, forecasts, anomalies, PDFs | — | after `APPROVED — GENERATE FULL SYNTHETIC DATASET` |

## Regenerate

```bash
python synthetic-data/generate_entities.py
```
