# PDF Generation Rules

> **Status:** PROPOSED. Rendering library pending DS-18 (recommended ReportLab). SYNTHETIC — EPRLens Demo.

1. **Digital, searchable PDFs only.** Text is drawn as text objects; no rasterised pages; no OCR needed for MVP.
2. **Pages:** 1–3. **Line items:** 1–12 (multi-page only via L05 or long dense tables).
3. **Layouts:** 12 templates (`invoice-layout-guide.md`); seeded assignment, stratified by type and test case.
4. **Types:** IT01–IT10 plus cancelled status (`invoice-types.md`).
5. **Units:** kg, g, MT, pcs (with g/pc), cartons (with units/case), bottles, bags, rolls.
6. **Dates:** Indian formats (`india-invoice-formatting-guide.md` §5).
7. **Currency:** Indian grouping and ₹/Rs./INR variants; import invoices in USD with INR equivalent.
8. **Watermark:** every page: diagonal light-grey text **SYNTHETIC — EPRLens Demo**, plus footer `SYNTHETIC — EPRLens Demo · <document_id> · page n/N`. PDF metadata: Title = invoice number, Author = "EPRLens synthetic generator", Subject = "SYNTHETIC — EPRLens Demo", Keywords include `synthetic`.
9. **Prohibited:** real logos, real companies, real GSTINs/PAN/CIN, real addresses, real bank details, scannable QR codes, copied invoice designs, signatures, licensed fonts.
10. **Single source of truth:** the renderer receives one `InvoiceDocument` object; both the PDF and the JSON are produced from it in the same function call. The JSON stores `render_hash` (sha256 of PDF bytes). A test re-extracts text from each PDF (pypdf) and checks invoice number, date, every line quantity/unit and invoice total against the JSON.
11. **Reproducibility:** ReportLab `invariant=1` (fixed creation date and document ID) → byte-identical output for the same seed; fonts are the 14 standard PDF fonts (no embedding variance).
12. **Exactly 1,000 PDFs and 1,000 JSON**, named `DOC_000001.pdf` / `DOC_000001.json`; the generator fails (non-zero exit) if counts differ.
13. **Cancelled documents** show a red "CANCELLED" stamp; still searchable.
14. **Storage:** full set under `data/generated/` (git-ignored) → private S3 or release asset; 20 samples committed under `synthetic-data/outputs/sample/`.
