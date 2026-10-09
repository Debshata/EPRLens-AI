# EPR Domain Summary (handbook-derived)

> **Status:** DRAFT for owner review. SYNTHETIC — EPRLens Demo project documentation.
> **Primary source:** *Decoding Extended Producer Responsibility (EPR) in India — From Registration to Compliance: A Business Leader's Handbook*, ed. Santanu Goswami (TrackEPR). File `V3_ebook-A Simple Guide to EPR.pdf`, 59 pages. Page references below (`p.N`) are PDF page numbers.
> **Rule:** Statements are paraphrased from the handbook. Anything the handbook does not support is marked **TBD — requires owner approval or official-source verification.** Nothing here is legal advice, and EPRLens AI does not file returns, issue certificates or guarantee compliance.

---

## 1. EPR meaning

- EPR is described as a "cradle-to-grave" responsibility: a business that places products or packaging on the Indian market is also responsible for managing them after consumers are done with them (p.5).
- Example used by the handbook: a water-bottle manufacturer is responsible for the bottles after use (p.5); a bottled-water brand remains responsible even if bottle manufacturing is outsourced, because it places plastic packaging on the market under its brand (p.8).
- Common principles across regimes (p.7): registration with the authority; meeting collection and recycling targets; regular reporting and documentation; working with authorised recyclers; maintaining proper records.

## 2. Relevant entity types (as named in the handbook)

| Regime | Entity types named | Pages |
|---|---|---|
| Plastic packaging | Producer (incl. MSME), Importer (products), Importer (raw material), Brand Owner, Manufacturer, Seller/Trader, Plastic Waste Processor (PWP). Collectively PIBO; raw-material actors handled in a "SIMP" module | p.8, p.11, p.20–21, p.42 |
| Plastic (local bodies) | Urban Local Bodies (ULBs) — can exchange EPR credits or register as PWP | p.19–20 |
| E-waste | Manufacturer, Producer, Refurbisher, Dismantler, Recycler, Bulk Consumer; "orphaned products" defined | p.9, p.25–29, p.58 |
| Batteries | Producer (several sub-types), Recycler (R1–R4), Refurbisher | p.9, p.29–32, p.58–59 |
| Tyres | Producer, Recycler, Retreader | p.10, p.33–36 |
| Used oil | Producer (P1–P9), Collection Agent, Recycler, Used-Oil Importer | p.10, p.37–40 |

**EPRLens synthetic-data scope (proposal, see DECISIONS-REQUIRED DS-06):** plastic packaging roles only. Other regimes are listed for completeness and for the "multi-role" rules-engine test case.

## 3. Producer (plastic)

- Organisations that manufacture plastic packaging, including MSME enterprises (p.20). The self-assessment asks "Do you produce plastic packaging (bags, pouches, wraps, bottles, etc.)?" (p.11).
- Compliance: every producer, including MSME producers, must comply and report **invoice-wise sales and purchases** (p.42).
- Sales to a **registered** entity shift the liability for that plastic packaging to the buyer; sales to an **unregistered** entity are reported as unregistered sales and the liability stays with the producer (p.42).
- For an **MSME producer**, liability for unregistered sales sits with the manufacturer or importer from whom the virgin granules were procured (p.42).
- Annual return: report annual consumption (= pre-consumer + post-consumer), report sales with the exact recycled-content percentage, close category-wise targets with EPR credits; for MSME producers the handbook says these already appear closed (p.43–44).
- Registration Part B (technical information on production facilities) applies to producers only (p.21–22).

## 4. Importer (plastic)

- Two kinds: **Importer (products)** — imports products with plastic packaging; **Importer (raw material)** — imports plastic raw materials or granules (p.20).
- Importer of packaging reports every consignment with the plastic-packaging quantity only, and also reports sales if it sells with that imported packaging (p.42).
- Importer of raw material must also register in the **SIMP module**; obligation = raw material imported − raw material sold to registered entities, excluding MSME producers. Raw material sold to micro and small producers remains the importer's obligation (p.42).
- Annual return: consumption based only on imported packaging (not locally sourced packaging); state-wise sales; if it does not sell products with imported packaging, post-consumer reporting is zero (p.43).
- Importers provide an Import Export Code (IEC) at registration (p.21).

## 5. Brand Owner (plastic)

- Organisations using plastic packaging with **annual turnover exceeding ₹50 crore** (p.8, p.11, p.20). → threshold **TBD — official-source verification**.
- Purchases from **registered vendors** auto-reflect as the brand owner's procurement; **unregistered procurement** is reported by the brand owner itself; total category-wise sales are reported **state-wise** (p.42).
- Annual return: consumption = pre-consumer + post-consumer; sales reported with exact recycled-content %; close category-wise targets by adding EPR credits; **exports are deducted from the next year's target**; transaction details in an Excel sheet plus a zip of invoices; pay annual processing fee then submit (p.43).

## 6. Plastic Waste Processor (PWP)

- Entities engaged in recycling, waste-to-energy, waste-to-oil, co-processing or industrial composting (p.8, p.11, p.20).
- Registration includes plant machinery, capacity, process flow, geo-tagged photos/videos, consents, HWM authorisation (p.23–25). Fee by processing capacity (p.25) → **TBD — verify**.
- Compliance (p.42–43): GST-registered suppliers → upload GST invoices for procured scrap; unregistered vendors → keep transaction records and vendor identity documentation; maintain daily production records on the portal; to generate EPR credits, upload GST **sales** invoices, allow real-time **QR-code** validation, and wait for a **100 % match** before certificate credit potential is generated.
- **PWP sales entries are non-editable after submission** (p.43).

## 7. Recycler

- The handbook uses "PWP" for plastic and "Recycler" for e-waste, batteries, tyres and used oil.
- Plastic-side annual return note under "Recyclers": procurement quantity, production quantity and sales quantity must be reconciled before filing; mismatches must be rectified (p.44).
- Battery recyclers R1 lead-acid; R2 dismantling/physical separation (black mass); R3 refiners; R4 comprehensive (p.32).
- **EPRLens convention (proposal):** the synthetic `recyclers` master represents plastic PWPs (recycling-type processors). Naming "recycler" is kept because the brief uses it.

## 8. Refurbisher (where relevant)

- E-waste: repairs or rebuilds used electronic equipment to extend its life for the original purpose and resells it (p.58); registration details on p.28–29.
- Batteries: repairs or reconditions used batteries for second-life applications (p.9).
- **Not relevant to plastic packaging synthetic data.** Retained only for the multi-role applicability test case.

## 9. EPR waste streams in the handbook

Active (five): plastic packaging, e-waste, batteries, tyres, used oil (p.2, p.6–7). Portals listed on p.16.
Being developed: non-ferrous metals, end-of-life vehicles, glass and metal packaging, construction & demolition waste, wastewater (p.7); the preface also lists paper packaging (p.2).

**Implication:** paper, cardboard, glass and metal packaging carry **no current packaging-EPR obligation per the handbook**. Status must be **TBD — official-source verification** before any product claim.

## 10. Plastic packaging concepts

- Who registers: users of plastic packaging, importers of packaging or packaged products, raw-material importers/manufacturers/sellers, producers of packaging (incl. MSME), brand owners above the turnover threshold, PWPs (p.8).
- Registration Part C "Waste Generation Profile": prior two years of plastic consumption; category-wise breakdown (illustrated "Cat I 40 %, Cat II 30 %"); process-flow diagram (producers); **state-wise** distribution of plastic placed on market; sources of raw material from **registered and unregistered suppliers**; plastic sold to other entities; category-wise waste generation (p.22).
- Part D: the portal computes category-wise targets from historical usage; "progressive target structure for future years" (p.22). Actual target percentages are **not given** → **TBD**.
- Circular-design levers to reduce liability: recyclability, material reduction (packaging size/weight), disassembly, modularity (p.47–48).
- **Packaging vs product distinction:** a gloves importer reduced liability by separating plastic packaging from plastic items (p.47) — the obligation attaches to packaging, not to plastic products themselves (as presented by the handbook).

## 11. Plastic categories (Appendix, p.52)

| Cat | Handbook description |
|---|---|
| I | Rigid plastic packaging and thermocol (expanded polystyrene) |
| II | Flexible plastic packaging including single- or multi-layer plastic, sheets, covers, carry bags, sachets and pouches |
| III | Multi-material plastic packaging with at least one plastic layer and one non-plastic layer |
| IV | Compostable plastic packaging and carry bags |

See `plastic-category-mapping.md` for internal codes and TBD notes.

## 12. Registration-related concepts

- Account creation on the respective CPCB portal using business email and mobile with OTP verification (p.16).
- Basic documents: certificate of incorporation, PAN, GST registration certificate, business licence, authorised signatory letter (p.16). Plastic-specific: declaration of plastic consumption/production, packaging specification details, brand registration certificates (p.17).
- Company name entered without "M/s"; address must match GST records; CIN; IEC for importers (p.21).
- Operational presence: all states/UTs selected; applications routed to State Pollution Control Boards (p.21).
- **Multi-category registration:** separate registration for each applicable role, e.g. raw-material importer + brand owner (p.20–21); multiple roles → multiple registrations (p.11).
- Fees (plastic PIBO by plastic waste generation, p.23): < 1,000 TPA ₹10,000; 1,000–10,000 TPA ₹20,000; > 10,000 TPA ₹50,000; annual processing fee 25 % of application fee. A different generic example (₹10k/₹25k/₹50k) appears on p.17. → **TBD — verify; the handbook is internally inconsistent.**
- Timelines (generic, p.18): pre-application 1–2 weeks; processing 2–4 weeks; post-approval 1–2 weeks.

## 13. Data / reporting concepts

- Records of all materials produced, imported, sold or processed must be maintained (p.14).
- Data-management needs (p.50): production volumes and packaging usage; waste generation across categories; collection and recycling achievements; documentary evidence.
- Compliance may be done monthly, quarterly or yearly but must be complete before **30 June** of the following financial year (p.41).
- E-waste and battery: quarterly data by the end of the month following each quarter (p.44–45).

## 14. Invoice / reporting concepts

- **Every invoice must be reported on the EPR portal** (p.41).
- An invoice covering all four plastic categories must be reported **four times**, once per category with that category's quantity (p.41). → EPRLens must support category-split invoice lines.
- **Up to 5 invoices may share the same invoice number** (p.41). → Duplicate detection must not rely on invoice number alone (AN17).
- Producers: invoice-wise sales and purchases; registered vs unregistered sales (p.42).
- Brand owners: registered-vendor sales auto-reflect into BO procurement; unregistered procurement self-reported (p.42).
- PWPs: GST invoice upload for procurement; GST sales invoice upload, QR validation, 100 % match, non-editable (p.42–43).
- Annual return attachments: Excel of transactions + zip of invoices (p.43).
- GST invoice *format* rules (number length, tax breakup) are **not** in the handbook → **TBD — official-source verification** (see `india-invoice-formatting-guide.md`).

## 15. Historical-data requirements

| Regime | Requirement | Page |
|---|---|---|
| Plastic | Plastic consumption for previous **two** years; drives next year's targets | p.22 |
| E-waste | Established producers: FY sales by weight for a period equal to the product's average life; new producers: since start | p.26–27 |
| Tyres | Manufacturing/import data since FY 2019-20 in MT | p.35 |
| Used oil | Sales and procurement for FY 2022-23 and 2023-24, CA-certified | p.40 |

**Synthetic-data implication:** a 36-month history covers the two prior years plus a current year, which supports forecasting of next-period consumption (planning value only, not a target calculation).

## 16. Recycling / processing concepts

- PWP activities: recycling, waste-to-energy, waste-to-oil, co-processing, industrial composting (p.8, p.11).
- PWP daily production records on the portal; credit generation tied to validated GST sales invoices (p.42–43).
- Recyclers must reconcile procurement, production and sales quantities before annual return (p.44).
- The handbook does **not** define collection rates, recycling yields, or material-specific losses → all such synthetic parameters are engineering assumptions.

## 17. Annual-return concepts

- Due **30 June** following the FY (Apr–Mar) (p.41, p.43–45).
- BO/Producer: consumption = pre-consumer + post-consumer; sales with exact recycled-content %; close category-wise targets with EPR credits; exports deducted from next year's target; Excel + zipped invoices; annual processing fee; submit (p.43–44).
- Importer: consumption only for imported packaging; state-wise sales (p.43).
- MSME producer: targets appear closed; no credits added (p.44).
- Definitions of "pre-consumer" and "post-consumer" are **not given** → **TBD**.
- The handbook uses the abbreviation "EC" when describing closing targets (p.43–44) without defining it → **TBD — meaning unconfirmed**.

## 18. EPR credit-related concepts

- Compliance is closed by adding EPR credits in the annual return (p.43).
- PWPs generate EPR certificate credit potential after 100 % invoice match (p.43).
- ULBs have a digital wallet for EPR credits; PWPs can transfer certificates to ULBs in exchange for services, and ULBs can transfer to PIBOs; trading year-round (p.19).
- Tyre certificate value band ₹2.52–₹8.40/kg (p.45) — tyres only; **TBD — verify**.
- **Plastic credit prices are not given.** EPRLens synthetic data uses `credits_documented_kg` (a quantity of *documented claims*), never a verified certificate, and no price.

## 19. Multi-role companies

- Register separately for each applicable category/role (p.11, p.20–21).
- Example: importer of calculators with built-in batteries packaged in plastic may need Battery EPR, Plastic EPR (importer), e-waste EPR, and possibly Brand Owner if sold under its own label with turnover above ₹50 Cr (p.14).
- Example: company that imports plastic raw material and sells under its own brand → Importer (Raw Material) + Brand Owner (p.20–21).
- **Synthetic-data implication:** `manufacturer`, `importer`, `brand_owner` are independent booleans; a company may hold several.

## 20. Important examples from the handbook

| Example | Page | EPRLens use |
|---|---|---|
| Bottled-water brand outsourcing bottles still responsible | p.8 | Demo company narrative (EcoFizz) |
| Category misclassification: registered Cat I, operations Cat II, target computed on wrong category | p.15 | AN04 wrong plastic category |
| Data-entry error: 500 MT reported instead of 0.5 MT | p.15 | AN01/AN08 and the demo anomaly |
| Gloves importer: packaging vs product separation, ~95 % liability reduction (handbook author's claim) | p.47 | Explanation copy only; attribute if shown |
| Auto-parts maker: ~₹51 lakh saved on next year's target after corrections (author's claim) | p.47 | Not used numerically |
| Unauthorised liability transfers ~₹320 crore for a cement brand (author's claim) | p.47 | Registered/unregistered transfer checks (future scope) |
| Calculator importer multi-role | p.14 | Rules-engine test case |

## 21. Known data-quality risks (handbook-derived)

1. Wrong category selection at registration (p.15, p.18).
2. Magnitude/unit entry errors (500 MT vs 0.5 MT) (p.15).
3. Underestimating waste quantities; missing mandatory fields; inconsistent information across documents (p.18).
4. Shared invoice numbers (≤ 5) mistaken for duplicates, or real duplicates hidden behind shared numbers (p.41).
5. Multi-category invoices reported once instead of once per category (p.41).
6. Registered vs unregistered buyer status wrong → liability transferred incorrectly (p.42, p.47).
7. PWP sales entries non-editable → errors become permanent (p.43).
8. Recycler procurement / production / sales mismatch (p.44).
9. Packaging vs product misclassification (p.47).

## 22. Limitations of the handbook

- **Secondary, commercial source.** Written by a consultancy; includes promotional sections (p.46–47). Case-study figures are the author's claims.
- **Currency:** reflects roughly December 2024 (p.46). Later amendments unknown.
- **Internal inconsistencies:** two different registration fee tables (p.17 vs p.23); the Importer annual-return paragraph refers to "Brand owner" (p.43); typographical errors (e.g. "noat", "Wate").
- **Editorial artefact:** p.37 contains the sentence "Based on my analysis of the document, I'll explain…", suggesting AI-assisted drafting → lower confidence in paraphrased regulatory detail.
- **Missing:** plastic target percentages; definitions of pre/post-consumer; definition of "EC"; polymer-level guidance (PET, HDPE …); the term "MLP"; GST/HSN rules for plastics; penalty/compensation amounts for plastic; recycled-content obligations; collection/recycling rate assumptions; "Important dates" sections are empty (p.44–46).
- **Not a legal text.** It paraphrases rules; it does not quote them.

## 23. Regulatory facts requiring official-source verification

All of the following are **TBD — requires owner approval or official-source verification** before any rule, UI text or calculation relies on them:

| # | Fact as stated by handbook | Page |
|---|---|---|
| R1 | Brand Owner threshold: turnover > ₹50 crore | p.8, p.20 |
| R2 | Five active regimes and portal URLs | p.6–7, p.16 |
| R3 | Glass/metal/paper packaging EPR "under development" | p.2, p.7 |
| R4 | Plastic categories I–IV definitions | p.52 |
| R5 | Annual return due 30 June | p.41, p.43 |
| R6 | Up to 5 invoices may share a number | p.41 |
| R7 | Multi-category invoice reported once per category | p.41 |
| R8 | Liability shift on sales to registered entities; MSME rule | p.42 |
| R9 | SIMP obligation formula for raw-material importers | p.42 |
| R10 | Exports deducted from next year's target | p.43 |
| R11 | PWP 100 % match and non-editable sales entries | p.43 |
| R12 | PIBO and PWP registration fees, 25 % annual processing fee | p.23, p.25 |
| R13 | Targets computed from prior two years' consumption | p.22 |
| R14 | Battery, e-waste, tyre, used-oil thresholds, fees, cycles | p.26–41 |
| R15 | Any GST invoice format, HSN mapping or GST rate (not in handbook) | — |

**Three concepts are kept separate throughout this project:** (1) synthetic business reality, (2) ML-generated predictions, (3) legal/regulatory interpretation.
