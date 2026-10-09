# Invoice Field Specification

> **Status:** PROPOSED. SYNTHETIC — EPRLens Demo.
> Three field classes are kept strictly apart:
> - **PRINTED** — normal invoice fields that appear on the PDF and a parser can extract.
> - **INTERNAL** — EPRLens metadata (IDs that link to masters/CSVs). Never printed as such; may be printed only where a real invoice would show an equivalent (e.g. buyer's PO reference).
> - **GROUND-TRUTH** — exists only in the ground-truth JSON / `anomaly_ground_truth.csv`. Never printed, never given to detectors.

GST layout rules (number length, tax breakup, mandatory particulars) come from general Indian invoicing practice, **not** from the handbook → **TBD — official-source verification**. They are used here only to make synthetic documents realistic.

## 1. Header fields

| Field | Class | Mandatory | Type | Notes |
|---|---|---|---|---|
| invoice_id | INTERNAL | yes | `INV_########` | Primary key in `invoices.csv` |
| invoice_number | PRINTED | yes | string ≤ 16 | Up to 5 invoices may share a number legitimately (handbook p.41) |
| invoice_type | PRINTED (as title) + INTERNAL code | yes | enum, see `invoice-types.md` | Title text varies by template ("Tax Invoice", "Credit Note"…) |
| invoice_date | PRINTED | yes | date | Printed in one of 4 formats; stored ISO |
| supplier_id | INTERNAL | yes | `SUP_`/`COMP_`/`REC_` id | Issuer of the document |
| supplier_name | PRINTED | yes | string | Fictional |
| supplier_address | PRINTED | yes | multiline | From `addresses.csv` |
| supplier_gstin | PRINTED | yes* | fake GSTIN-like | *Blank allowed only for AN06 / unregistered vendors |
| buyer_id | INTERNAL | yes | `COMP_`/`BUY_` id | |
| buyer_name | PRINTED | yes | string | |
| buyer_address | PRINTED | yes | multiline | Billing address |
| buyer_gstin | PRINTED | conditional | fake GSTIN-like | Blank for unregistered business customers |
| shipping_address | PRINTED | optional | multiline | Templates L08 |
| place_of_supply | PRINTED | yes | state name + code | Drives CGST/SGST vs IGST |
| currency | PRINTED | yes | `INR` (import invoices may show `USD` + INR equivalent) | |
| company_id | INTERNAL | yes | `COMP_####` | The EPRLens client whose records this invoice belongs to |
| transaction_id(s) | INTERNAL | conditional | list of `TXN_` | Empty for documents with no CSV counterpart (tested deliberately) |
| po_reference | PRINTED | optional | string | Fake PO number |
| irn_placeholder / qr_placeholder | PRINTED | optional | text box "QR — SYNTHETIC" | Never a real IRN or scannable e-invoice QR |
| original_invoice_number | PRINTED | credit/return notes | string | Reference to the invoice being adjusted |
| status | INTERNAL | yes | `issued` / `cancelled` | Cancelled documents print a "CANCELLED" stamp |
| page_count | INTERNAL | yes | 1–3 | |

## 2. Line-item fields

| Field | Class | Mandatory | Type | Notes |
|---|---|---|---|---|
| line_no | PRINTED | yes | int | 1–12 per invoice |
| item_description | PRINTED | yes | string | e.g. "PET Preform Bottle 750 ml — clear" |
| product_id | INTERNAL | conditional | `PROD_` id | Present for finished-goods lines |
| component_id | INTERNAL | conditional | `PKGCOMP_` id | Present for packaging lines |
| material | PRINTED (often inside description or own column) + INTERNAL code | yes | taxonomy code | Templates vary: own column, in description, or absent (parser must infer → tests) |
| plastic_category | PRINTED (optional column "EPR Cat") + INTERNAL | conditional | `CAT_I`…`CAT_IV`, `NA` | Printed on ~50 % of templates |
| hsn_code | PRINTED | yes | 4–8 digit string | Illustrative mapping (DS-13) |
| quantity | PRINTED | yes | decimal | Raw value as printed |
| unit | PRINTED | yes | `kg`, `g`, `MT`, `pcs`, `cartons`, `bottles`, `bags`, `rolls` | |
| weight_per_unit_g | PRINTED (when unit is count-based) | conditional | decimal | Needed to normalise pieces → kg |
| rate | PRINTED | yes | ₹ per unit | |
| taxable_value | PRINTED | yes | ₹ | quantity × rate − discount |
| discount | PRINTED | optional | ₹ | |
| gst_rate | PRINTED | yes | % | 5 / 12 / 18 illustrative |
| cgst_amount / sgst_amount | PRINTED | intra-state | ₹ | each = taxable × rate/2 |
| igst_amount | PRINTED | inter-state | ₹ | taxable × rate |
| gst_amount | INTERNAL (derived) | yes | ₹ | sum of tax heads |
| line_total | PRINTED | optional | ₹ | |

## 3. Totals

| Field | Class | Mandatory | Notes |
|---|---|---|---|
| total_taxable_value | PRINTED | yes | Σ taxable_value |
| total_cgst / total_sgst / total_igst | PRINTED | yes | |
| round_off | PRINTED | optional | to nearest rupee |
| invoice_total | PRINTED | yes | taxable + tax ± round_off |
| amount_in_words | PRINTED | optional | Indian numbering words |

## 4. Optional blocks (layout-dependent)

Bank details (fake, non-routable), terms & conditions, authorised-signatory placeholder ("for <Supplier> — Authorised Signatory", no signature image), transporter/vehicle placeholder, e-way-bill placeholder (text only), EPR registration line ("EPR Reg. (claimed): SYN-PWP-…") on recycler invoices.

## 5. EPRLens internal metadata (all documents)

`document_id`, `template_id`, `generator_version`, `seed`, `render_hash`, `linked_transaction_ids`, `linked_invoice_line_ids`, `normalized_quantity_kg` per line, `recorded_quantity_kg` (value in the internal CSV the invoice should reconcile to), `synthetic_flag`.

## 6. Ground-truth-only fields

`is_anomaly`, `anomaly_types[]`, `anomaly_instance_ids[]`, `original_value`, `modified_value`, `test_case_type` (`routine` / `targeted_anomaly` / `targeted_legit_hard`), `expected_detection_method`, `expected_findings[]` (rule IDs that should fire), `difficulty` (layout / unit / tax / reference tags).

## 7. Mandatory candidate list from the brief — classification

| Brief field | Class |
|---|---|
| invoice_id | INTERNAL |
| invoice_number, invoice_type, invoice_date | PRINTED |
| supplier_id, buyer_id, company_id, transaction_id, product_id | INTERNAL |
| supplier_name, buyer_name, supplier_address, buyer_address, supplier_gstin, buyer_gstin | PRINTED |
| item_description, material, plastic_category, hsn_code, quantity, unit, rate, taxable_value, gst_rate, gst_amount, invoice_total, currency | PRINTED |
