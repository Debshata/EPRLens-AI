# Anomaly Distribution — PROPOSAL (not final)

> **Status:** awaiting owner approval (DS-07). SYNTHETIC — EPRLens Demo. Counts assume DS-04 A sizes (~42,000 invoice headers, ~65,000 product-months, ~14,000 recycling rows).

## 1. Tabular anomalies (≈ 5 % of records per table)

### Invoices (~42,000 headers)

| Type | Count | Notes |
|---|---|---|
| AN01 extra_zero | 200 | ×10 (50 %), ×100 (30 %), ×1000 (20 %) |
| AN02 decimal_error | 150 | |
| AN03 wrong_material | 120 | |
| AN04 wrong_plastic_category | 150 | |
| AN05 duplicate_invoice | 150 | duplicates added |
| AN06 missing_field | 200 | qty 25 %, unit 15 %, date 15 %, category 20 %, GSTIN 15 %, HSN 10 % |
| AN07 qty_mismatch | 250 | |
| AN08 unit_conversion_error | 200 | MT↔kg 50 %, g↔kg 25 %, pcs-as-kg 25 % |
| AN10 implausible_unit_weight | 80 | |
| AN14 cancelled_invoice_counted | 80 | |
| AN15 credit_note_not_applied | 80 | |
| AN16 return_not_applied | 80 | |
| AN18 stale_product_master_weight | 60 | concentrated on products with ≥ 2 spec versions |
| AN19 split_line_aggregation_error | 80 | |
| AN20 supplier_product_mismatch | 100 | |
| **Total anomalous** | **1,980 (≈ 4.7 %)** | |
| AN17 legit shared numbers (hard negative) | 300 groups (~900 invoices) | `is_anomaly=false` |

### Product-months (~65,000)

| Type | Count |
|---|---|
| AN09 extreme_monthly_spike | 330 (≈ 0.5 %; kept low so forecasting is not dominated by injected noise; forecasting trains on the **clean** panel by default, anomaly panel reported separately) |

### Recycling rows (~14,000)

| Type | Count |
|---|---|
| AN11 recycled_gt_collected | 300 |
| AN12 collected_gt_generated | 250 |
| AN13 unregistered_recycler_claim | 150 |
| **Total** | **700 (≈ 5 %)** |

Compound anomalies (two types on one record): ≤ 2 % of anomalous records, labelled with both types.

## 2. The 1,000 PDFs

### 600 routine documents (clean, `test_case_type=routine`)

| Type | Count |
|---|---|
| IT01 packaging purchase | 150 |
| IT02 finished-goods sales | 150 |
| IT08 packaging component | 80 |
| IT09 multi-material | 60 |
| IT03 recycler processing | 50 |
| IT04 waste procurement | 30 |
| IT07 import commercial | 30 |
| IT10 recycling service | 20 |
| IT05 credit note | 15 |
| IT06 return | 15 |

### 400 targeted test-case documents

**280 anomalous (`targeted_anomaly`)**

| Anomaly | PDFs | | Anomaly | PDFs |
|---|---|---|---|---|
| AN01 | 25 | | AN11 | 10 |
| AN02 | 20 | | AN12 | 10 |
| AN03 | 15 | | AN13 | 15 |
| AN04 | 20 | | AN14 | 15 (CANCELLED stamp) |
| AN05 | 20 (10 duplicate pairs) | | AN15 | 10 |
| AN06 | 20 | | AN16 | 10 |
| AN07 | 30 | | AN18 | 10 |
| AN08 | 30 (incl. 10 "0.5 MT vs 500 MT") | | AN19 | 5 |
| AN10 | 10 | | AN20 | 5 |

AN09 (monthly spike) is distributional and not represented as a single-document anomaly.

**120 legitimate but difficult (`targeted_legit_hard`, `is_anomaly=false`)**

| Case | PDFs |
|---|---|
| AN17 legitimate shared invoice numbers (10 groups × 3) | 30 |
| Multi-page with carried-forward subtotals | 15 |
| Large but valid seasonal quantities | 15 |
| Correct g / pcs-with-weight units | 15 |
| Correct small MT quantities (e.g. 0.5 MT = 500 kg) | 10 |
| Credit note correctly applied | 10 |
| Return correctly applied | 10 |
| IGST with ship-to in another state | 10 |
| Unregistered buyer with blank GSTIN (legit) | 5 |

### Template coverage

Each of the 12 layouts is used for ≥ 50 documents; each invoice type appears on ≥ 2 layouts; targeted documents are stratified so that every anomaly type appears on ≥ 3 layouts.

### Split of PDFs for evaluation

PDFs inherit the company split (60/20/20). Extraction evaluation uses all 1,000; anomaly-model evaluation on documents uses only the test-split companies.
