# Pilot Generation Plan (Phase 15) — 20-file pilot

> **Status:** PLAN ONLY. Runs after the owner approves the decisions it depends on (DS-01, -03, -05, -07, -09, -11, -13, -16, -18). SYNTHETIC — EPRLens Demo.

## Scope

| Item | Count | Source |
|---|---|---|
| Companies | 5 | the approved entity test pack (`synthetic-data/masters/`) |
| Products | 10–15 | test pack |
| Transactions | ≈ 100 | 3 months × the 5 companies, sales + purchases |
| Invoice records | 20 headers | aggregated from those transactions |
| PDF invoices | 20 | one per invoice record |
| Ground-truth JSON | 20 | one per PDF |
| Anomaly types | 8 | AN01, AN04, AN05, AN07, AN08 (0.5 MT vs 500 MT), AN13, AN14, AN17 (hard negative) |

## Composition of the 20 PDFs

| # | Type | Layout | Case |
|---|---|---|---|
| 1–8 | IT01, IT02, IT08, IT09, IT03, IT07, IT05, IT06 | L01, L02, L03, L04, L10, L12, L11, L08 | routine |
| 9–10 | IT02 ×2 | L05 | multi-page legit, AN17 shared number pair (legit) |
| 11 | IT07 | L12 | AN08 0.5 MT printed vs 500 MT recorded (demo company) |
| 12 | IT01 | L06 | AN01 extra zero |
| 13 | IT09 | L03 | AN04 wrong category |
| 14–15 | IT01 ×2 | L07 | AN05 duplicate pair |
| 16 | IT08 | L09 | AN07 quantity mismatch |
| 17 | IT03 | L10 | AN13 unregistered recycler (REC_TEST_001) |
| 18 | IT02 | L02 | AN14 cancelled but counted |
| 19 | IT01 | L01 | legit 0.5 MT (hard negative) |
| 20 | IT02 | L08 | legit IGST ship-to other state |

10 of 12 layouts covered in the pilot; all 12 in the full run.

## What will be shown for review

1. CSV schemas (from `schemas/*.schema.json`)
2. Sample rows from each CSV
3. 3–5 rendered sample invoices
4. Matching JSON ground truth
5. Anomaly examples with original vs modified values
6. Calculated material flow for the demo company (inventory identity, POM, returns, recycling proxy)
7. Generator assumptions used

## Acceptance checks before showing

- PDF text re-extraction matches JSON for every printed field.
- Watermark present on every page.
- All IDs resolve to masters.
- MF1–MF7 invariants hold on clean records.
- Two runs with the same seed produce identical hashes.
