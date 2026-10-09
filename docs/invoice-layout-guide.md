# Invoice Layout Guide (template plan)

> **Status:** PROPOSED. SYNTHETIC — EPRLens Demo. 12 original layouts; none copies a real brand's design. Fonts: built-in PDF fonts only (Helvetica, Times, Courier families) — no licensed fonts. Every page carries the diagonal watermark **SYNTHETIC — EPRLens Demo** plus a footer line with the same text and `document_id`.
> Rendering library: pending DS-18 (recommended ReportLab).

| ID | Name | Page | Structure | Variation it tests | Used for types |
|---|---|---|---|---|---|
| L01 | Simple GST invoice | A4 portrait | Title "TAX INVOICE" centred; supplier block top-left, buyer below; single table; tax lines under table | Baseline extraction | IT01, IT02, IT08 |
| L02 | Modern corporate | A4 portrait | Coloured header band with text-only "logo" (initials in a circle); right-aligned meta box (no., date, PO); light zebra table | Meta in a box, labels right-aligned | IT01, IT02, IT09 |
| L03 | Dense table | A4 landscape | 12+ columns incl. HSN, Cat, qty, unit, g/unit, rate, disc, taxable, CGST, SGST, IGST, total | Narrow columns, small font, many numbers | IT09, IT08 |
| L04 | Two-column header | A4 portrait | Supplier (left) and Buyer (right) side by side; invoice meta in a strip below | Party disambiguation by position | IT01, IT06 |
| L05 | Multi-page | A4 portrait, 2–3 pages | Line table spans pages with "Continued…" and carried-forward subtotals; totals only on last page | Page breaks, repeated headers, c/f totals | IT02, IT09 |
| L06 | QR placeholder | A4 portrait | e-invoice-style top block: grey box "QR — SYNTHETIC (not scannable)" and "IRN: SYNTHETIC-NOT-AN-IRN" | Noise text near header; must not be read as invoice no. | IT01, IT02 |
| L07 | Bank-details block | A4 portrait | Footer with fake bank block (`SYN-ACCT-…`, `SYNT0DEMO01`), terms list | Numeric noise in footer | IT01, IT08, IT10 |
| L08 | Billing + shipping | A4 portrait | Three party blocks: Seller, Bill-to, Ship-to (different state possible) | Place of supply vs ship-to; IGST logic | IT02, IT06 |
| L09 | Tax summary | A4 portrait | Lines without tax columns; separate HSN-wise tax summary table at bottom | Tax must be read from summary table | IT01, IT09, IT05 |
| L10 | Recycler service | A4 portrait | Recycler header with "EPR Reg. (claimed): SYN-PWP-…"; sections "Material processed (kg)" and "Service charges" | Service vs material lines | IT03, IT10, IT04 |
| L11 | Minimal / plain text | A4 portrait | Courier font, label: value pairs, ASCII-ruled table | Monospace, no grid lines | IT05, IT06, IT04 |
| L12 | Import commercial | A4 portrait | "COMMERCIAL INVOICE", exporter/consignee, Incoterm, currency USD with INR equivalent column, gross/net weight | Foreign currency, MT/kg in weight column | IT07 |

## Per-document variation knobs (seeded)

- Date format: `DD/MM/YYYY`, `DD-MM-YYYY`, `DD-Mon-YYYY`, `YYYY-MM-DD`.
- Number format: Indian grouping `1,23,456.78` (default), western `123,456.78` (≈15 %), no grouping (≈10 %).
- Currency mark: `₹`, `Rs.`, `INR` (₹ requires a font with the glyph — if the built-in font lacks it the template prints `Rs.`; decided at implementation, mechanical).
- Unit spelling: `kg`/`Kg`/`KGS`, `MT`/`M.T.`/`Tonne`, `pcs`/`Nos`, `g`/`gm`.
- Material column present / absent (then material only in description).
- Category column present / absent.
- Line count 1–12; page count 1–3.

## Safety rules

No real logos, no images of marks, no real company/brand names, no real GSTIN/PAN/CIN/IEC, no real addresses, no real bank details, no scannable QR codes, no signatures.
