# Generator Assumptions

> **Status:** PROPOSED — every number here is an **illustrative engineering assumption**, not a market statistic, regulatory fact or handbook value. Synthetic pricing and quantities do **not** represent current Indian market averages. SYNTHETIC — EPRLens Demo.

## 1. Hierarchical generation

```
Companies ─► Products ─► Packaging components ─► Suppliers/Buyers/Recyclers (+ relationships)
         ─► Monthly sales ─► Transactions ─► Material events ─► Invoices
         ─► Recycling records ─► Scenarios ─► Anomaly injection ─► Ground truth ─► PDFs
```
Nothing below the company level is drawn independently of its parents.

## 2. Company level

| Attribute | Assumption |
|---|---|
| turnover_cr | LogNormal(median ₹40 Cr, σ = 1.4), clipped [0.5, 2,500] → ≈ 44 % above ₹50 Cr |
| company_size | micro < 5, small 5–50, medium 50–250, large > 250 (₹ Cr; illustrative bands, **not** official MSME criteria) |
| msme_flag | synthetic: true with p = 0.85 for micro/small, 0.4 medium, 0 large (DS-14) |
| industry | weights in `entity_seed.yaml` (DS-15) |
| roles | manufacturer p by industry (0.3 retail/e-com → 0.9 FMCG/Food/Beverages/Pharma); importer p (0.6 Electronics/Appliances, 0.1–0.3 others); brand_owner p 0.85 (consumer industries), 0.4 Industrial; at least one role true |
| states_operated | micro 1–2, small 1–4, medium 3–8, large 6–14 states; HQ state always included |
| epr_registered | declared status: p = 0.9 large, 0.75 medium, 0.55 small, 0.4 micro |
| n_products | 3–15, increasing with log(turnover): `3 + round(12·q) ± 2`, q = turnover percentile |
| n_suppliers / n_buyers | small 2–4 / 2–5; medium 3–6 / 4–8; large 5–10 / 6–15 |

## 3. Product and packaging

- Each industry has 3–8 **product archetypes** (e.g. Beverages: PET soft drink, PET water, glass bottled drink, juice pouch); each archetype lists components with form, material, weight range (g) and recycled-content range.
- Product weight drawn uniformly within the archetype range, rounded to 0.1 g; components of one product are consistent (cap matches bottle).
- `recycled_content_pct`: 0 for most; PET bottles 0–30 %; cartons 30–80 % (illustrative).
- `units_per_case`: archetype-specific (Beverages 12/24, FMCG 24–144, Electronics 1–4).
- Spec versions: ~8 % of components get a second version mid-window with −5 % to −20 % weight (light-weighting) → supports AN18 and scenario baselines.

## 4. Sales volume

```
annual_units_c   = turnover_cr × 1e7 × packaged_share_c / unit_price_ind        (packaged_share ~ U(0.6, 0.9))
product_share_p  ~ Dirichlet(α = 1.2) over the company's products
units[p, t]      = annual_units_c × product_share_p / 12
                   × (1 + g_c)^(t/12) × season_ind(month_t) × launch_ramp_p(t) × (1 + ε),  ε ~ N(0, 0.08)
```

| Industry | unit_price ₹ (illustrative) | Seasonality |
|---|---|---|
| Beverages | 25–60 | summer peak Mar–Jun (+35 %), monsoon dip |
| FMCG | 10–150 | festive Oct–Nov (+20 %) |
| Food | 10–100 | festive Oct–Nov (+25 %) |
| Personal Care | 60–300 | mild (±8 %) |
| Cosmetics | 150–800 | festive + wedding season Nov–Feb (+15 %) |
| Pharmaceuticals | 30–300 | monsoon Jul–Sep (+15 %) |
| Electronics | 800–20,000 | festive Sep–Nov (+40 %) |
| Appliances | 1,500–40,000 | summer (cooling) Mar–May (+30 %), festive (+20 %) |
| Automotive | 200–5,000 | flat (±5 %), festive bump |
| Retail | 50–1,000 | festive (+30 %) |
| E-commerce | 200–2,000 | sale events Oct, Jan (+50 %) |
| Household Products | 40–300 | festive (+15 %) |
| Industrial Goods | 500–20,000 | flat; March year-end push (+15 %) |

- Annual growth `g_c ~ N(0.08, 0.10)`, clipped [−0.2, 0.5]; ~10 % of companies declining.
- Launch ramp: products launched inside the window ramp linearly over 3–6 months.

## 5. Sales split

- State shares: Dirichlet over `states_operated` with HQ weight boosted ×3.
- Buyer split: each state-month split across 1–3 buyers from the company's buyer set; buyer EPR-registered share per company ~ Beta(4, 3).
- Exports: 85 % of companies none; others 2–15 % of units.
- Returns: 0.5–2 % of units, lagged 0–1 month.

## 6. Purchases and inventory (DS-03 A)

- Packaging purchased per component from its supplier(s); reorder each month (or every 2 months for small companies) to cover next period consumption × (1 + safety 10–30 %).
- Opening inventory at window start = 1–2 months of consumption.
- Written-off = 0–1 % of consumption (pre-consumer scrap).
- Importers source 30–100 % of packaging via IT07 import invoices.

## 7. Prices and tax (DS-13 A) — illustrative ₹/kg ranges

| Material | ₹/kg | Material | ₹/kg |
|---|---|---|---|
| PET | 110–160 | MLP | 180–320 |
| HDPE | 100–150 | Compostable | 250–450 |
| LDPE / LLDPE | 100–145 | Paper | 60–100 |
| PP | 100–150 | Cardboard | 40–80 |
| PVC | 90–140 | Glass | 15–35 |
| PS / EPS | 120–200 | Metal (aluminium) | 250–400 |

Per-piece rate = ₹/kg × g/1000 × (1 + conversion margin 20–60 %). GST default 18 %, some lines 12 % / 5 % for tax-math variety. Finished-goods sales price = unit_price_ind range.

## 8. Invoices

- Sales invoices aggregate one buyer × month (lines = products × state); 1–12 lines.
- Purchase invoices aggregate one supplier × 1–2 months; lines = components.
- ~2 % multi-category invoices (IT09) explicitly mix Cat I/II/III + non-plastic.
- Legit shared invoice-number groups (AN17): 300 groups of 2–5.
- Cancelled invoices: 0.5 % (with matching cancelled transactions in the clean world).

## 9. Recycling (DS-11 A, synthetic proxy)

```
waste_generated[c,k,t] = 0.5·POM[t−1] + 0.3·POM[t−2] + 0.2·POM[t−3]      (POM = placed_on_market plastic kg, cat k)
collected  = waste_generated × r_col,  r_col ~ Beta(6, 4)    (mean 0.6)
recycled   = collected × r_rec,         r_rec ~ Beta(17, 3)   (mean 0.85)
credits_documented = recycled × r_doc,  r_doc ~ Beta(9, 1)    (mean 0.9) — only if recycler registered & supports k
```
So `recycled ≤ collected ≤ generated` holds by construction in the clean world.
Each company uses 1–3 recyclers whose `supported_materials` cover its categories.

## 10. Business descriptions (DS-20 A)

Template sentences with paraphrase slots: industry, products, packaging, roles, import/export, states, turnover band. Ground truth: expected_manufacturer / importer / brand_owner / industry. ~10 % deliberately vague or contradictory (e.g. "we source finished goods abroad" → importer=true without the word "import").

## 11. What is *not* modelled

Customs duty, freight, discounts beyond a flat %, payment terms, FG inventory (DS-03 A), real EPR targets, certificate prices, ULB transfers, SIMP raw-material obligations, other regimes.

## 12. Implementation notes — generator 1.0.0 (2026-10-09)

Mechanical choices made while implementing the approved design; none changes an approved decision.

| Topic | Implementation |
|---|---|
| Randomness | Python `random` streams seeded by SHA-256 of (seed, stage, entity key) instead of NumPy PCG64; reproducible across 3.12/3.14. |
| Company GSTIN | Added `fake_gstin` to companies (separate random stream; no other master value changed) so sales invoices issued by companies carry a GSTIN-like value. |
| Sales rows | Each month a company invoices ~50 % of its buyers; a product-month splits across 1–3 of those buyers (weights 0.15 / 0.35 / 0.50). Ship-to state = buyer state if the company sells there, else a fixed company state. 25 % of companies export 2–15 % of units. |
| Purchases | Order cycle by size (large 2, medium 4, small/micro 6 months); covers the next cycle plus 10–30 % safety stock; 60 % of deliveries arrive in two lots (two records, two invoice lines). kg suppliers sometimes invoice in MT (≥ 2,000 kg: 40 %; 300–1,000 kg: 15 % → legitimate small-MT cases). |
| Invoices | Sales: one per company × buyer × month (≤ 12 lines). Purchases: one per company × supplier × month × domestic/import. Recycler processing and scrap-sale invoices: one per company × recycler × FY (chunked at 12 lines). Service invoices for 50 % of company–recycler–FY pairs. Credit notes: 2 % of purchase invoices, price-only. Cancelled twins: 0.5 % of sales/purchase invoices. |
| Types | `MULTI_MATERIAL` = a purchase invoice whose lines span ≥ 2 plastic categories; `PKG_COMPONENT` = cap/closure/label/carton/component suppliers. |
| GST / HSN | Illustrative per industry for sales (config `sales_gst_by_industry`, `sales_hsn_by_industry`); purchases 18 % (15 % of supplier–material pairs at 12 %). Not verified tax treatment. |
| Anomalies | Injected without overlap (each record has at most one label). AN09 also scales the matching invoice lines (distributional, not a mismatch). AN13 moves the recycling line onto a new invoice from the unregistered recycler. The demo AN08 instance (EcoFizz, SUP_TEST_001, Nov 2025: 0.5 MT printed, 500 MT recorded) is always present. |
| PDFs | ReportLab 5.0.1, `invariant=1`; 12 layouts; 1–3 pages (L05 and L11 paginate); built-in fonts so ₹ prints as "Rs."/"INR". |
