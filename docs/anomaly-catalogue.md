# Anomaly Catalogue

> **Status:** PROPOSED. SYNTHETIC — EPRLens Demo. Labels live only in `anomaly_ground_truth.csv` and PDF ground-truth JSON. Detection method: **R** deterministic rule, **ML** Isolation Forest, **R+ML** either/both. Severity reflects data-quality impact in the synthetic world, not legal risk.

| ID | Label | Description | Injection | Expected detection | Method | Severity | False-positive edge cases (hard negatives generated) |
|---|---|---|---|---|---|---|---|
| AN01 | `extra_zero` | Quantity ×10 / ×100 / ×1000 (e.g. 500 kg → 50,000 kg) | Multiply `raw_quantity` (invoice or CSV side, not both) | Ratio to matching record ≈ 10ⁿ; deviation from company-component history | R+ML | high | Legit seasonal peaks 3–6× (Beverages summer); bulk annual orders |
| AN02 | `decimal_error` | Quantity ÷10ⁿ (decimal shifted left) | Divide `raw_quantity` | Ratio ≈ 10⁻ⁿ; too-low vs history | R+ML | medium | Legit small trial orders; partial deliveries |
| AN03 | `wrong_material` | Line material differs from component master (PET ↔ HDPE, PP ↔ LDPE) | Replace material code/text | Material ≠ master for component/product | R | medium | Supplier legitimately switched material with new spec version (effective_from) |
| AN04 | `wrong_plastic_category` | Category differs from master (Cat I ↔ II, II ↔ III) — mirrors handbook p.15 case | Replace category | Category ≠ master; category inconsistent with form | R | high | Ambiguous components (`category_confidence=ambiguous`) must not fire high |
| AN05 | `duplicate_invoice` | Same supplier, number, date, amount, lines entered twice | Clone invoice with new internal id | Composite key duplicate | R | high | AN17 legit shared numbers (different party/date/lines) |
| AN06 | `missing_field` | Null in a required field (quantity, unit, date, category, GSTIN, HSN) | Blank the field | Schema/required-field rule | R | medium (high if quantity/unit) | Optional fields blank by design; unregistered vendor blank GSTIN (legit) |
| AN07 | `qty_mismatch_invoice_vs_csv` | Invoice normalised kg ≠ recorded kg beyond tolerance (not a clean 10ⁿ ratio) | Perturb one side by 5–60 % | |inv − rec| > tol | R (+ML on ratio) | medium/high by size | Rounding within tolerance; partial deliveries with two invoices |
| AN08 | `unit_conversion_error` | Wrong unit applied: MT ↔ kg, g ↔ kg, pcs treated as kg (handbook 0.5 MT vs 500 MT) | Change `raw_unit` or record kg using wrong factor | Ratio 1000 / 0.001; implausible kg per piece | R | high | Legit MT invoices for bulk resin; legit g on small samples |
| AN09 | `extreme_monthly_spike` | Product-month volume ×3–6 without matching sales drivers | Multiply a product-month's units/purchases | Seasonal z-score; IF on month-over-month change | ML (+R threshold) | medium | Legit festival/summer peaks; product launches ramp-up |
| AN10 | `implausible_unit_weight` | weight_per_unit_g outside archetype range (e.g. 250 g cap) | Edit component weight or printed g/pc | Range check by component form; IF on weight z-score | R+ML | medium | Industrial drums, large EPS blocks legitimately heavy |
| AN11 | `recycled_gt_collected` | recycled_kg > collected_kg | Inflate recycled | Invariant MF4 | R | high | None in clean world (cohort invariant) |
| AN12 | `collected_gt_generated` | collected_kg > waste_generated_kg | Inflate collected | Invariant MF4 | R | medium | Proxy timing lag at FY boundary is controlled to avoid this in clean data |
| AN13 | `unregistered_recycler_claim` | credits_documented from a recycler with `registered=false` (or claimed reg. number not in master) | Reassign recycler to unregistered one | Lookup recycler registry | R | high | Registered recycler whose registration starts mid-period (start_date) |
| AN14 | `cancelled_invoice_counted` | Cancelled invoice's transaction still `posted` / counted in totals | Keep transaction posted while invoice status=cancelled | Status join rule | R | high | Cancelled-and-reissued with same number (legit, new date) |
| AN15 | `credit_note_not_applied` | Credit note exists but original transaction quantity/amount unchanged | Omit adjustment transaction | Unmatched credit note | R | medium | Credit note for price only (no quantity change) — legit |
| AN16 | `return_not_applied` | Return document exists but no `RETURNED` event / transaction | Omit return transaction | Unmatched return | R | medium | Return in next month (timing) — legit if within window |
| AN17 | `shared_invoice_number_legit` | **Hard negative**: 2–5 invoices legitimately share a number (handbook p.41) | Create groups in clean world | Must NOT be flagged as AN05 | R (negative test) | n/a (`is_anomaly=false`) | This *is* the edge case |
| AN18 | `stale_product_master_weight` | Calculation uses an old weight after a new spec version took effect | Use v1 weight on dates ≥ v2 effective_from | Spec-version-by-date rule | R | medium | Invoice dated before effective_from (legit old weight) |
| AN19 | `split_line_aggregation_error` | Multi-category invoice aggregated into one category/line, or two split lines summed twice | Merge lines / duplicate a split | Σ lines vs per-category totals; category count | R | medium | Legit single-category invoice with several lines of same item |
| AN20 | `supplier_product_mismatch` | Supplier invoices a material/component it does not supply (per master/relationships) | Swap supplier on line | Relationship lookup (SUPPLIED_BY / supported_materials) | R | low/medium | SUP_TEST_002-style legit material change with new relationship start_date |

## Ground-truth row (anomaly_ground_truth.csv)

`anomaly_instance_id, record_id, record_type (invoice|invoice_line|transaction|product_month|recycling|component), anomaly_type, field, original_value, modified_value, expected_detection_method (R|ML|R+ML), expected_rule_ids, severity, split, seed, test_case_type`

## Rule IDs (proposal, for `expected_rule_ids`)

`QTY_RATIO_POW10`, `QTY_MATCH_TOL`, `UNIT_RATIO_1000`, `MATERIAL_MASTER_MATCH`, `CATEGORY_MASTER_MATCH`, `DUP_COMPOSITE_KEY`, `REQUIRED_FIELDS`, `WEIGHT_RANGE_BY_FORM`, `RECYCLED_LE_COLLECTED`, `COLLECTED_LE_GENERATED`, `RECYCLER_REGISTERED`, `STATUS_CANCELLED_EXCLUDED`, `CREDIT_NOTE_APPLIED`, `RETURN_APPLIED`, `SPEC_VERSION_BY_DATE`, `CATEGORY_SPLIT_SUM`, `SUPPLIER_SUPPLIES_ITEM`. Tolerances are proposals pending D029/D076.
