# Invoice / Document Types

> **Status:** PROPOSED. SYNTHETIC — EPRLens Demo. Codes are internal (`invoice_type`). Share of the 1,000 PDFs is proposed in `anomaly-distribution.md`.

| Code | Type | Issuer → Recipient | Business purpose | Typical lines | Related CSV records | Possible anomaly cases |
|---|---|---|---|---|---|---|
| IT01 `PKG_PURCHASE` | Packaging material purchase invoice | Supplier → Company | Company buys packaging (bottles, preforms, film, pouches) | 1–6 lines; kg, MT or pcs + g/pc | `transactions` (type `purchase`), `material_events` `PURCHASED` | AN01, AN02, AN03, AN05, AN07, AN08, AN20 |
| IT02 `FG_SALES` | Finished-goods sales invoice | Company → Buyer | Company sells packaged products; packaging travels with goods | 1–12 product lines in cartons/bottles/pcs | `transactions` (`sale`), `material_events` `PLACED_ON_MARKET` | AN06, AN07, AN09, AN19 |
| IT03 `RECYCLER_PROCESSING` | Recycler processing invoice | Recycler → Company | PWP invoices company for processing a quantity of plastic waste; may state claimed EPR documentation | 1–4 lines by category, kg/MT | `recycling.csv`, `material_events` `RECYCLED` / `CREDITS_DOCUMENTED` | AN11, AN12, AN13 |
| IT04 `WASTE_PROCUREMENT` | Waste procurement invoice | Recycler ← aggregator / company (recycler buys scrap) | Recycler's input-side evidence | 1–5 lines, kg/MT, "post-consumer PET flakes" etc. | `recycling.csv` (collected), `material_events` `COLLECTED` | AN08, AN12 |
| IT05 `CREDIT_NOTE` | Credit note | Supplier → Company or Company → Buyer | Reduces a prior invoice (rate dispute, short supply) | references original; negative effect | `transactions` (`credit_adjustment`) | AN15 not applied |
| IT06 `RETURN` | Return / debit note for goods returned | Buyer → Company (sales return) or Company → Supplier | Physical goods returned | qty returned, original ref | `transactions` (`return`), `material_events` `RETURNED` | AN16 not applied |
| IT07 `IMPORT_COMMERCIAL` | Import commercial invoice | Foreign fictional supplier → Company | Imported packaged goods or packaging; foreign currency | 1–6 lines; USD rate + INR equivalent; no GST lines (customs separate) | `transactions` (`import`), `material_events` `PURCHASED` with `origin=import` | AN08 (MT ↔ kg, the 0.5 vs 500 case), AN02 |
| IT08 `PKG_COMPONENT` | Packaging component invoice | Component maker (caps, labels, cartons) → Company | Secondary components priced per piece | pcs with g/pc; rolls for labels | `transactions` (`purchase`) | AN10, AN18, AN20 |
| IT09 `MULTI_MATERIAL` | Multi-material invoice | Supplier → Company | One invoice mixing Cat I/II/III and non-plastic lines (handbook: report once per category) | 4–12 lines, mixed units | several transactions | AN03, AN04, AN19 |
| IT10 `RECYCLING_SERVICE` | Recycling service invoice | Recycler/collector → Company | Service fee (collection, logistics, documentation) — **fee lines are not material quantities** | service lines (no kg) + optional reference kg | `recycling.csv` (reference only) | Parser must not count service kg as recycled; AN13 |
| IT11 `CANCELLED` (status variant) | Any of the above with status cancelled | — | Tests cancellation handling | stamp "CANCELLED" | transaction `status=cancelled` | AN14 |

## Field expectations by type

| Type | GST block | Weight per unit printed | Category column | Reference to original | Currency |
|---|---|---|---|---|---|
| IT01 | CGST+SGST or IGST | if pcs | ~50 % | — | INR |
| IT02 | yes | sometimes (pack size in description) | rarely | — | INR |
| IT03 | yes | — | yes (category of waste processed) | — | INR |
| IT04 | yes, or blank GSTIN for unregistered vendor | — | sometimes | — | INR |
| IT05 | yes (negative/credit) | — | — | **yes** | INR |
| IT06 | yes | if pcs | — | **yes** | INR |
| IT07 | no GST; customs reference placeholder | often | rarely | — | USD + INR |
| IT08 | yes | **yes** | ~50 % | — | INR |
| IT09 | yes | mixed | ~70 % | — | INR |
| IT10 | yes (services) | — | — | — | INR |

## Notes

- Who is the "company" for recycler invoices: the EPRLens client receiving the invoice.
- Import invoices: customs duty and IGST-on-import are **not modelled** (TBD) — they show a placeholder "Bill of Entry: SYN-BE-…".
- Credit notes and returns always reference an existing synthetic invoice number; AN15/AN16 test that the adjustment is ignored downstream.
