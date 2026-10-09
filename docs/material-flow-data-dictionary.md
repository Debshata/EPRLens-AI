# Material-Flow Data Dictionary

> **Status:** PROPOSED. SYNTHETIC — EPRLens Demo. Machine-readable versions: `synthetic-data/schemas/*.schema.json` (generated from `synthetic-data/schemas/spec.py`). Provenance tags: **H** handbook-supported concept, **E** engineering assumption, **GT** ground-truth only, **M** internal metadata.

## material_events.csv

| Column | Type | Prov. | Description |
|---|---|---|---|
| event_id | `MEV_#########` | M | Primary key |
| company_id | FK companies | M | Owner of the ledger |
| product_id | FK products, nullable | M | Null for pure component purchases |
| component_id | FK packaging_components | M | Packaging component the mass belongs to |
| material | taxonomy code | E | Denormalised from component |
| plastic_category | `CAT_I`…`CAT_IV`/`NA`/`UNKNOWN` | H | Handbook categories (p.52) |
| event_type | enum (see material-flow-rules §1) | E | |
| date | date | M | Event date |
| period | `YYYY-MM` | M | Month bucket |
| kg | decimal ≥ 0 | E | Always positive; direction from `direction` |
| direction | `in` / `out` / `memo` | E | memo = proxy/claim events outside inventory |
| source_document_id | `INV_`/`DOC_`/`TXN_` | M | Evidence link |
| source_line_id | `INVL_` nullable | M | Line-level evidence |
| counterparty_id | SUP/BUY/REC id nullable | M | |
| status | `document_supported` / `estimated` / `declared` / `unknown` / `cancelled` | E | Context §47.2 statuses |
| supersedes_event_id | nullable | M | Correction chain |
| synthetic_flag | bool | M | Always true |

## transactions.csv

| Column | Type | Prov. | Description |
|---|---|---|---|
| transaction_id | `TXN_########` | M | |
| company_id, product_id | FK | M | product_id null for packaging purchases not tied to a product |
| component_id | FK nullable | M | For packaging purchases |
| date | date | M | |
| transaction_type | `sale` / `purchase` / `import` / `return` / `export_sale` / `credit_adjustment` | E | |
| units | int nullable | E | Finished units (sales) or pieces (purchases) |
| state | state name | H | State-wise sales are reported per handbook p.42 |
| buyer_id / supplier_id | FK nullable | M | |
| buyer_epr_registered | bool nullable | H | Liability shift concept (p.42) |
| raw_quantity, raw_unit | as recorded internally | E | |
| normalized_quantity_kg | decimal | E | Packaging kg (sales: Σ components) |
| plastic_kg | decimal | E | Plastic-relevant subset |
| invoice_id | FK nullable | M | |
| status | `posted` / `cancelled` | E | |
| synthetic_flag | bool | M | |

## recycling.csv

| Column | Type | Prov. | Description |
|---|---|---|---|
| recycling_record_id | `RCY_#######` | M | |
| company_id | FK | M | |
| month | `YYYY-MM` | M | |
| plastic_category | CAT code | H | |
| waste_generated_kg | decimal | E | **Synthetic proxy** (basis column says so) |
| waste_collected_kg | decimal | E | |
| waste_recycled_kg | decimal | E | |
| recycler_id | FK recyclers | M | |
| recycler_registered | bool | H | Work with registered/authorised recyclers (p.7) |
| credits_documented_kg | decimal | E | Documented claims, not verified certificates |
| basis | `synthetic_proxy_v1` | M | |
| synthetic_flag | bool | M | |

## Derived: forecast_panel.csv (DS-06 A)

company_id, product_id, industry, month, month_num, units_sold, weight_per_unit_g (total across components), packaging_kg, lag_1, lag_2, lag_3, lag_6, lag_12, rolling_mean_3, rolling_mean_6, sales_growth, seasonality_index, split, target `next_month_packaging_kg`.
Lags computed only from rows at or before the origin month; rows without a full lag set are dropped from training but kept for completeness flags.
