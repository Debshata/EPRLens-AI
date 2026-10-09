# Decisions Required — Synthetic Data & Dummy Entities

> **Status:** **APPROVED 2026-10-09** — owner approved DS-01 … DS-25 with the recommended options, subject to these safeguards:
> - DS-09: form-based category is a *synthetic modelling convention* only. Stored as `synthetic_category`, `category_basis`, `category_confidence`, `legal_verification_status` (= `TBD`).
> - DS-10: MLP → Cat III is a configurable synthetic default, `legal_verification_status = TBD`; the handbook does not define MLP.
> - DS-11: generated → collected → recycled are synthetic material-flow test relationships, not regulatory obligations or target calculations.
> - DS-13: prices, GST rates and HSN codes are illustrative, configurable test values — not verified market or regulatory values.
> - DS-14: `brand_owner` is a business attribute, kept separate from any EPR applicability / registration logic.
> - DS-16: GSTIN-like values stay structurally useful but deliberately invalid.
> - DS-17: real city/state names only; streets, contacts, phones, banking and identities are fictional.
> - DS-18: ReportLab approved. DS-19: Python 3.12 target. DS-25: the seven roles are test fixtures only, not the production authorization model.
> - Buyers carry `gst_registered` and `epr_registered` as separate fields (DS-12).
>
> Original options are kept below for traceability.
> IDs use the prefix **DS-** to avoid clashing with the D0xx log in `context_updated_v0.4.md`. On approval they should be appended to that file's Decision Log (Section 38).
> **Provisional choices in the pilot entity pack:** the small test pack was generated with each *Recommendation* below so the owner can see concrete output. Every file is regenerable; any rejected option is a config change plus one command.

Reply format suggestion: `DS-01 B, DS-02 A, …` or "accept all recommendations except …".

---

## A. Scope and time

### DS-01 Time horizon of the 36 months

Why it matters: sets every date, FY label, invoice-number series and the train/validation/test cut-offs.

- **Option A — Apr 2022 → Mar 2025 (FY 2022-23 … FY 2024-25).** Impact: matches context §43.4 and the handbook era (~Dec 2024). Data looks ~18 months stale against today (Oct 2026).
- **Option B — Apr 2023 → Mar 2026 (FY 2023-24 … FY 2025-26).** Impact: three complete FYs ending recently; forecasts point at the "next" FY; still FY-aligned for annual-return logic.
- **Option C — Oct 2023 → Sep 2026 (rolling to last month).** Impact: most current; FY boundaries split mid-series, complicating FY aggregates.

Recommendation: **B** — complete FYs and recent.

### DS-02 Plastic-only EPR scope with non-plastic components present

Why it matters: the handbook says only plastic packaging currently carries packaging EPR; glass/metal/paper are "under development".

- **Option A — Generate plastic and non-plastic components; non-plastic flagged `plastic_epr_relevant=false`; Battery never a packaging component.** Impact: realistic packaging bills of material (cartons, glass bottles); tests that the rules engine ignores non-plastic mass.
- **Option B — Plastic components only.** Impact: simpler; less realistic; cannot test relevance filtering.

Recommendation: **A**.

### DS-03 Material-flow accounting boundary

Why it matters: defines what opening/closing inventory means and prevents conflation (context C21).

- **Option A — Boundary = packaging-material inventory held by the company.** Purchased packaging enters inventory; consumption = packaging attached to units produced; assume **units produced = units sold** each month (no finished-goods inventory). Impact: simple, closes exactly; ignores FG stock timing.
- **Option B — Two boundaries: packaging inventory and finished-goods inventory.** Impact: more realistic timing differences; roughly double the event types and tests.

Recommendation: **A** for MVP; revisit if reconciliation demos need timing gaps.

## B. Dataset size and structure

### DS-04 Dataset quantities (Phase 5)

Why it matters: drives runtime, file sizes and ML evaluation power. Full table in `docs/dataset-size-proposal.md`.

- **Option A — As proposed:** 200 companies, 36 months, 3–15 products, ~180–200k transaction rows, ~38–45k invoice headers (~70–90k lines), exactly 1,000 PDFs + 1,000 JSON, 150 business descriptions, 120 suppliers, 150 buyers, 50 recyclers, 15 test users. Impact: fits all stated ranges; full run est. a few minutes plus PDF rendering.
- **Option B — Half size (100 companies).** Impact: faster; transaction rows fall below the 150k floor.

Recommendation: **A**.

### DS-05 Invoice table structure

Why it matters: the brief's `invoices.csv` carries material and quantity (line-level facts) but real invoices have many lines and several materials/categories.

- **Option A — `invoices.csv` (one row per invoice, header) + `invoice_lines.csv` (one row per line), plus a derived `invoices_flat.csv` with exactly the brief's columns for ML.** Impact: faithful to multi-line, multi-category invoices (handbook p.41 per-category reporting); 30–50k target counts headers.
- **Option B — Single line-level `invoices.csv` with `line_no`.** Impact: one file; header fields repeated; easier ML, harder reconciliation.

Recommendation: **A**.

### DS-06 Forecast granularity

Why it matters: defines rows, features and what "next_month_packaging_kg" means.

- **Option A — Product-month rows** (~1,800 products × 36 months ≈ 65k rows); company totals evaluated by aggregation. Impact: uses weight_per_unit_g directly; most rows.
- **Option B — Company-month rows** (200 × 36 = 7,200 rows). Impact: matches dashboard metric; few rows, weak ML signal.
- **Option C — Company × plastic-category-month.** Impact: closest to category-wise EPR reporting; weight_per_unit_g becomes an average.

Recommendation: **A**, with B reported as a secondary evaluation.

### DS-07 Anomaly rate and PDF split

Why it matters: sets class balance for detectors and the 400 targeted PDFs.

- **Option A — ~5 % of tabular records anomalous (ML runbook), stratified by type; PDFs 600 routine + 400 targeted, of which 280 anomalous and 120 legitimate-but-difficult.** Impact: matches runbook; enough positives per type.
- **Option B — ~3 % tabular (context D005 low end); PDFs 600 + 400 with 200/200.** Impact: more realistic rarity; fewer positives for rare types.

Recommendation: **A**. Full distribution in `docs/anomaly-distribution.md`.

### DS-08 Train / validation / test

Why it matters: prevents leakage; defines reported metrics.

- **Option A — Forecast:** chronological 24 / 6 / 6 months **and** 20 % of companies (40) held out entirely. **Anomaly:** split by company 60 / 20 / 20; each injected anomaly instance lives in exactly one split. Impact: matches brief and context §43.9.
- **Option B — Forecast chronological only; anomaly chronological.** Impact: simpler; no unseen-company test.

Recommendation: **A**.

## C. Domain interpretation (engineering assumptions not in the handbook)

### DS-09 Plastic category assignment for synthetic components

Why it matters: the handbook defines Cat I–IV (p.52) but gives no polymer or component mapping.

- **Option A — Assign a *declared* category by component form** (rigid → I, flexible film/pouch/label/wrap → II, plastic + non-plastic laminate → III, compostable → IV), stored as `plastic_category` with `category_basis="synthetic_declared_by_form"`. Ambiguous forms (PVC blister, laminated tube, label on glass) marked `category_confidence="ambiguous"`. Impact: usable ground truth; clearly labelled as not a legal classification.
- **Option B — Leave category unknown for ambiguous components.** Impact: more honest; fewer usable rows for AN04.

Recommendation: **A**, ambiguous items labelled.

### DS-10 "MLP" material code

Why it matters: the brief lists MLP; the handbook never uses the term — it describes Cat III "multi-material plastic packaging".

- **Option A — Keep internal code `MLP` meaning "multi-layer/multi-material laminate containing plastic", default category III, flagged TBD.** Impact: matches industry vocabulary used in the brief.
- **Option B — Drop MLP; use `MULTI_MATERIAL`.** Impact: closer to handbook wording.

Recommendation: **A** with handbook wording in the display name.

### DS-11 Recycling-chain semantics in `recycling.csv`

Why it matters: "waste generated / collected / recycled" for a brand owner is not defined in the handbook (context C21).

- **Option A — Keep the three-stage chain as an explicitly labelled synthetic proxy per company × month × category:** generated = post-consumer proxy of placed-on-market kg; collected ≤ generated; recycled ≤ collected; credits_documented = documented claims, never "verified". Impact: supports AN11/AN12 tests; columns carry `basis` metadata.
- **Option B — Drop generated/collected; model only credits_documented vs placed-on-market.** Impact: closer to compliance reality; loses two anomaly tests requested in the brief.

Recommendation: **A**.

### DS-12 Buyer registration flags

Why it matters: the handbook's liability shift depends on whether the buyer is an EPR-*registered* entity (p.42), which is different from being GST-registered.

- **Option A — Buyers carry both `registered_business` (GST-registered) and `epr_registered` (synthetic declared EPR registration).** Impact: adds one field beyond the brief; enables registered/unregistered sales split.
- **Option B — Single `registered_business` flag.** Impact: conflates GST and EPR registration.

Recommendation: **A** (already in the pilot pack).

### DS-13 Prices, GST rates and HSN codes

Why it matters: invoices need rates and tax; the handbook covers none of this.

- **Option A — Config-driven illustrative ₹/kg ranges per material, GST rate default 18 % with a configurable set (5 / 12 / 18 %) to exercise tax math, real HSN headings (e.g. 3923, 3920, 4819) mapped per component, all labelled "illustrative — not market prices — tax treatment TBD verification".** Impact: realistic parser tests; explicit disclaimers.
- **Option B — Single flat 18 % and abstract prices.** Impact: fewer tax-logic test cases.

Recommendation: **A**.

### DS-14 Company-size, MSME and brand-owner attributes

Why it matters: MSME criteria are not in the handbook; brand-owner registration depends on a ₹50 Cr threshold (TBD-verify).

- **Option A — Turnover ~ log-normal (median ₹40 Cr, tail to ~₹2,000 Cr); `company_size` from illustrative turnover bands; `msme_flag` assigned synthetically (not derived from official MSME criteria); `brand_owner` = sells under own brand (business fact), kept separate from any rule-derived "BO registration expected".** Impact: keeps business reality separate from regulatory interpretation.
- **Option B — Derive `brand_owner` from turnover > ₹50 Cr.** Impact: bakes a TBD legal threshold into ground truth.

Recommendation: **A**.

### DS-15 Industry and state distributions

Why it matters: drives material mix, seasonality and tax (intra- vs inter-state).

- **Option A — Weights as in `synthetic-data/config/entity_seed.yaml`** (FMCG 14, Food 14, Beverages 9, Personal Care 9, Pharma 9, Electronics 7, Automotive 6, Cosmetics 6, Retail 6, E-commerce 6, Household 6, Appliances 5, Industrial 3; HQ states weighted toward MH, GJ, TN, KA, UP, DL, HR). Impact: unequal and plausible; explicitly illustrative.
- **Option B — Owner supplies weights.**

Recommendation: **A** unless the owner wants a specific story.

## D. Identifiers, safety and rendering

### DS-16 Fake GSTIN-like identifiers

Why it matters: must look structurally useful but never be a valid real GSTIN.

- **Option A — Real-format layout (2-digit state code + 5 letters + 4 digits + letter + entity digit + `Z` + check character) with a check character that is *deliberately wrong*.** Impact: every value fails the standard GSTIN checksum, so it cannot be a valid registered GSTIN; state code still drives CGST/SGST vs IGST. A test asserts 100 % invalid checksums.
- **Option B — Invalid state code `00`.** Impact: obviously fake, but breaks state-based tax logic.
- **Option C — Valid checksum.** Impact: most realistic; risk of matching a real registration.

Recommendation: **A** (used in the pilot pack).

### DS-17 Addresses, phones, PINs, bank details

Why it matters: brief forbids real addresses, phone numbers, bank accounts.

- **Option A — Real city/state names (needed for tax logic); fictional locality and plot names; PIN codes 6 digits with a region-consistent first digit (field marked synthetic); no personal phone numbers — business phones rendered `+91-00000-0NNNN` (leading zero, not a valid mobile); bank account `SYN-ACCT-NNNNNN` and IFSC-like `SYNT0DEMO01` (non-numeric, cannot be real).** Impact: plausible formatting; nothing routable.
- **Option B — Fully fictional cities/states.** Impact: breaks GST place-of-supply logic.

Recommendation: **A**.

### DS-18 PDF rendering library (Phase 6)

Why it matters: dependency, determinism, Windows setup effort.

- **Option A — ReportLab (pure-Python wheel).** Impact: no system deps on Windows; searchable text; `invariant=1` gives byte-reproducible PDFs; layouts coded in Python (more code per template).
- **Option B — Jinja2 HTML → WeasyPrint.** Impact: templates easy to design in HTML/CSS; WeasyPrint needs GTK/Pango on Windows (fragile setup); reproducibility needs metadata pinning.
- **Option C — Jinja2 HTML → Playwright/Chromium.** Impact: best CSS fidelity; ~150 MB browser download; slower; harder byte-reproducibility.

Recommendation: **A** (new dependency `reportlab` needs approval).

### DS-19 Python version and pinned dependencies

Why it matters: reproducibility and Lambda parity (Lambda Python 3.12 per context §44.6).

- **Option A — Python 3.12.x; pins: numpy, pandas, PyYAML, jsonschema, reportlab, scikit-learn, xgboost, pytest (versions in `synthetic-data/requirements.txt`).** Impact: matches Lambda runtime. Local default interpreter here is 3.14; 3.12.14 is also installed.
- **Option B — Python 3.13/3.14.** Impact: newer; diverges from Lambda.

Recommendation: **A**. (Pilot entity code is stdlib + PyYAML only and runs on 3.12–3.14.)

### DS-20 Business descriptions

- **Option A — 150 template-generated descriptions with paraphrase variation (no LLM, no cost), ground truth = company attributes.** Impact: deterministic, free.
- **Option B — LLM-paraphrased.** Impact: more natural; cost; non-deterministic; needs D054.

Recommendation: **A**.

### DS-21 What-if scenarios in `scenarios.csv`

- **Option A — Weight-reduction % and unit-volume change only (ML runbook formulas).** Impact: deterministic, matches F13 scope.
- **Option B — Also material switch and recycled-content change.** Impact: richer; implies claims (recyclability, EPR effect) the handbook cannot support numerically.

Recommendation: **A**; B later with approval.

## E. Dummy entities (follow-up phase)

### DS-22 Entity counts and test entities

- **Option A — 200 companies, 120 suppliers, 150 buyers, 50 recyclers (8 deliberately unregistered = 16 %), 15 test users; test entities REC_TEST_001, SUP_TEST_001, SUP_TEST_002, BUY_TEST_001, PROD_TEST_001 kept in the same masters with `test_entity=true`.** Impact: one source of truth; tests can filter them.
- **Option B — Test entities in separate files.** Impact: risk of two sources of truth.

Recommendation: **A**.

### DS-23 Extra master columns beyond the brief

Added for traceability: `test_entity`, `test_scenario` (all masters); `effective_from`, `effective_to`, `spec_version`, `category_basis`, `category_confidence`, `plastic_epr_relevant` (packaging components); `epr_registered` (buyers, DS-12); `hq_address_id` (entities); `company_scope` (test users); material code `COMPOSTABLE` and recycler processing type `industrial composting` (handbook p.8 lists composting among PWP activities; needed to represent Cat IV).

- **Option A — Keep.** Impact: needed for stale-weight (AN18), relevance and test-entity handling.
- **Option B — Remove; encode in a side table.**

Recommendation: **A**.

### DS-24 Demo company profile

- **Option A — `COMP_0001` "EcoFizz Beverages Pvt Ltd" (FICTIONAL), Beverages, manufacturer + brand owner, HQ Delhi, turnover ₹180 Cr (illustrative), 5 products (4 PET bottles + 1 glass bottle with PP cap), demo anomaly mirrors the handbook's 0.5 MT vs 500 MT error.** Impact: story aligned to handbook p.8 and p.15.
- **Option B — Owner supplies profile.**

Recommendation: **A**. Name-collision note: any invented name may coincide with a real business; we use a denylist test, not a guarantee.

### DS-25 Test-user roles vs pending D034

Why it matters: context D034 (user roles) is pending with "single role for MVP" recommended; the brief asks for 7 roles.

- **Option A — Generate the 7-role fixture as test data only; it does not decide D034.** Impact: fixtures ready either way.
- **Option B — Single role until D034.**

Recommendation: **A**.

## F. Conflicts with `context_updated_v0.4.md` to acknowledge

| # | Conflict | Proposed resolution |
|---|---|---|
| X1 | Context §43.6 / D061 proposes 500 PDFs (300/200); this brief says exactly 1,000 (600/400) | Brief wins; record D061 resolution on approval |
| X2 | Context §43.6 suggests Jinja2 + WeasyPrint/Playwright; DS-18 recommends ReportLab | Owner chooses in DS-18 |
| X3 | Context §43.9 forecast split "Apr 2022–Mar 2025" assumes DS-01 A | Follows DS-01 |
| X4 | Context D034 single role vs 7 test roles | DS-25 |
| X5 | Brief example IDs `PROD_0003` / `PKGCOMP_00231` vs specified `PROD_000001` / `PKGCOMP_000001` | Use 6-digit forms everywhere |
| X6 | Context recommends no Hindi labels decision yet | English only for MVP unless owner asks |
