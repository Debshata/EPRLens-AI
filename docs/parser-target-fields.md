# Parser Target Fields

> **Status:** PROPOSED. Defines exactly what the EPRLens invoice parser (method pending D055) must extract from each PDF, and how it is scored against ground truth. SYNTHETIC — EPRLens Demo.

## 1. Document-level

| Field | Type | Normalisation | Scoring |
|---|---|---|---|
| document_id | string | from file name / footer | exact |
| invoice_number | string | trim, upper-case | exact |
| invoice_date | date | to ISO; assume DD/MM | exact |
| vendor (supplier_name) | string | whitespace/case-folded | normalised exact; fuzzy ≥ 0.9 reported separately |
| vendor_gstin | string | upper-case | exact (format check separate from checksum) |
| buyer (buyer_name) | string | as above | as above |
| buyer_gstin | string | | exact / null |
| gst (total tax) | decimal ₹ | Σ CGST+SGST+IGST | abs diff ≤ ₹1 |
| invoice_total | decimal ₹ | parse Indian/western grouping | abs diff ≤ ₹1 |
| invoice_type | enum | from title keywords | exact |
| page_count | int | | exact |

## 2. Line-level (one record per line)

| Field | Type | Normalisation | Scoring |
|---|---|---|---|
| line_reference | `<document_id>:p<page>:l<line_no>` | | key |
| page_number | int | | exact |
| item_description | string | whitespace-folded | normalised exact |
| material | taxonomy code | keyword map from description/column | exact |
| plastic_category | CAT code / null | from column; null if not printed | exact when printed |
| quantity | decimal | parse | relative diff ≤ 0.1 % |
| unit | canonical unit | spelling map (`units-and-conversions.md`) | exact |
| normalized_quantity_kg | decimal | conversion rules; null if unconvertible | relative diff ≤ 0.1 % |
| rate | decimal ₹ | | abs diff ≤ ₹0.01 |
| amount (taxable_value) | decimal ₹ | | abs diff ≤ ₹0.5 |
| hsn_code | string | digits only | exact |

## 3. Confidence

`extraction_confidence` ∈ [0, 1] per field **if the method provides one**; for rule-based parsing a proxy is used (1.0 regex-anchored match, 0.7 positional fallback, 0.0 missing). It is reported, not trusted: every field also carries `source_ref` (page, line, bounding text) per context §48.

## 4. Metrics (on the synthetic corpus only)

Field-level exact/normalised accuracy; line-item recall and precision (matched by line_reference); kg accuracy after normalisation; per-template and per-type breakdown; hard-negative false-positive rate (AN17, legit MT, legit credit notes). Results are "synthetic PDF test performance only" (context §51).
