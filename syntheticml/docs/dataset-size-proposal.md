# Dataset Size Proposal (Phase 5)

> **Status:** awaiting approval (DS-04). Full generation will not start until the owner writes **APPROVED — GENERATE FULL SYNTHETIC DATASET.** SYNTHETIC — EPRLens Demo.

| Output | Proposed | Brief target | How the number arises |
|---|---|---|---|
| Companies | 200 | 200 | config |
| History | 36 months (Apr 2023 – Mar 2026, DS-01 B) | 36 | config |
| Products per company | 3–15 (mean ≈ 9) → ≈ 1,800 products | 3–15 | turnover-driven |
| Packaging components | ≈ 5,000–6,000 (2–5 per product) | — | archetypes |
| Product-months | ≈ 60,000–65,000 | — | products × active months |
| Transaction rows | ≈ 180,000–210,000 | 150–250k | sales ≈ 155k (state × buyer split ≈ 2.4 per product-month) + purchases/imports ≈ 40k + returns/credits/exports/cancels ≈ 5k |
| Invoice headers | ≈ 38,000–45,000 | 30–50k | sales: buyer × month; purchases: supplier × 1–2 months; + recycler/credit/return/import |
| Invoice lines | ≈ 80,000–110,000 | — | 1–12 per invoice |
| Material events | ≈ 600,000–900,000 | — | one per component per movement + monthly balances (could be aggregated monthly if size is a concern) |
| Recycling rows | ≈ 14,000 | — | company × category × month with POM > 0 |
| Scenarios / results | 600 / 600 | — | 3 per company (5 %, 15 %, 25 % weight reduction on the top product) |
| Business descriptions | 150 | 150 | template-based |
| Suppliers / Buyers / Recyclers | 120 / 150 / 50 | 100–150 / ~150 / 40–60 | DS-22 |
| Test users | 15 | 10–20 | DS-22 |
| Invoice PDFs | **exactly 1,000** | 1,000 | sampled from invoice table |
| Ground-truth JSON | **exactly 1,000** | 1,000 | one per PDF |
| Anomaly ground-truth rows | ≈ 3,000 + 900 hard-negative markers | — | `anomaly-distribution.md` |

**Estimated disk:** CSVs ≈ 150–250 MB (material events dominate); 1,000 PDFs ≈ 30–60 MB. All under `data/generated/` (git-ignored).
**Estimated runtime (single laptop):** tabular ≈ 1–3 min; PDFs ≈ 2–5 min with ReportLab. To be measured, not promised.
