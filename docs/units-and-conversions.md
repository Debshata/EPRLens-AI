# Units and Conversions

> **Status:** PROPOSED. SYNTHETIC — EPRLens Demo. All internal mass is stored in **kg**.

## 1. Mass units

| Raw unit | Accepted spellings (printed) | To kg | Rule ID |
|---|---|---|---|
| `kg` | kg, Kg, KG, KGS, kgs | × 1 | `U_KG` |
| `g` | g, gm, gms, grams | ÷ 1000 | `U_G` |
| `MT` | MT, M.T., Tonne, Tonnes, t | × 1000 | `U_MT` |

`1 MT = 1000 kg`, `1000 g = 1 kg`.

## 2. Count units (need a weight per unit)

| Raw unit | Meaning | To kg | Rule ID |
|---|---|---|---|
| `pcs` | pieces (Nos) | `pcs × weight_per_unit_g / 1000` | `U_PCS` |
| `bottles` | finished bottles (packaging only) | `bottles × weight_per_unit_g / 1000` | `U_BOTTLES` |
| `bags` | bags | `bags × weight_per_unit_g / 1000` | `U_BAGS` |
| `cartons` | cartons/cases of N units | `cartons × units_per_case × weight_per_unit_g / 1000` | `U_CARTONS` |
| `rolls` | film/label rolls | `rolls × weight_per_roll_kg` (net roll weight printed or from master) | `U_ROLLS` |

Packaging mass for units sold: `units × weight_per_unit_g / 1000 = packaging kg` (gross packaging associated with the units, per component, summed over components).

If the needed weight is **missing**, normalised kg is `null` with status `unconvertible` — **never zero, never guessed**.

## 3. Preserved fields on every document-derived quantity

| Field | Example |
|---|---|
| `raw_quantity` | `0.5` |
| `raw_unit` | `MT` |
| `normalized_quantity_kg` | `500.0` |
| `conversion_rule` | `U_MT` |
| `conversion_factor` | `1000` |
| `weight_basis_g` | (count units only) `25.0` |
| `weight_basis_source` | `product_master@v2` / `printed_on_invoice` |

## 4. Normalisation rules

1. Trim and case-fold the unit; map spelling to canonical unit; unknown spelling → `unit_unrecognised` finding.
2. Parse numbers with Indian or western grouping; reject ambiguous strings (e.g. `1.234,5`) → finding.
3. Count units use the weight in force **on the document date** (`effective_from ≤ date ≤ effective_to`); a stale weight is AN18.
4. Round normalised kg to 3 decimals (gram precision) for storage; compare with tolerance (rules engine, value TBD in D029/D076; synthetic tests use 0.5 % or 0.5 kg, whichever larger — proposal).
5. Display: kg below 1,000; MT (tonnes) at ≥ 1,000 kg (context D045 proposal).

## 5. Classic error patterns (for AN01/AN02/AN08)

| Pattern | Raw | Wrongly normalised | Correct |
|---|---|---|---|
| MT entered as kg | 0.5 MT recorded as `500` with unit MT | 500,000 kg | 500 kg |
| g treated as kg | 750 g | 750 kg | 0.75 kg |
| pcs treated as kg | 10,000 pcs @ 25 g | 10,000 kg | 250 kg |
| extra zero | 500 kg | 5,000 kg | 500 kg |
| decimal shift | 1,250.0 kg | 125.0 kg | 1,250 kg |
