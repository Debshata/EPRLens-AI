# What-if Scenario Formulas

> **Status:** PROPOSED (DS-21 A). Deterministic; no ML. SYNTHETIC — EPRLens Demo.
> Outputs are **hypothetical future material avoided**, not measured waste reduction, not EPR liability, not cost savings (context §49, C25).

## Inputs

`baseline_weight_g` (verified weight in force), `proposed_weight_g` or `reduction_pct`, `units` (baseline period units, or forecast units), optional `units_change_pct`.

## Formulas

```
proposed_weight_g     = baseline_weight_g × (1 − reduction_pct / 100)      (if reduction_pct given)
baseline_kg           = units × baseline_weight_g / 1000
proposed_units        = units × (1 + units_change_pct / 100)               (default 0)
proposed_kg           = proposed_units × proposed_weight_g / 1000
projected_reduction_kg = baseline_kg − proposed_kg
reduction_pct_effective = projected_reduction_kg / baseline_kg × 100
```
Multi-SKU: sum per product, report per product and total. Plastic-only totals filter `plastic_epr_relevant=true`.

## Worked examples

- Context §49: 100,000 units × 25 g = 2,500 kg; 20 % reduction → 20 g → 2,000 kg; reduction 500 kg.
- Context §25: 52.8 t baseline, 15 % reduction → 44.88 t; reduction 7.92 t.

## scenario_results.csv (calculated fields)

`scenario_id, company_id, product_id, baseline_kg, proposed_kg, projected_reduction_kg, reduction_pct_effective, plastic_baseline_kg, plastic_proposed_kg, plastic_reduction_kg, units_basis (historical|forecast), period, assumptions, disclaimer ("Hypothetical; assumes unchanged sales and a feasible redesign; not a compliance or cost claim"), synthetic_flag`

## Invariants (tests)

1. reduction_pct = 0 and units_change = 0 ⇒ projected_reduction_kg = 0.
2. For fixed units, projected_reduction_kg increases monotonically with reduction_pct.
3. Multi-SKU total = Σ per-SKU.
4. proposed_weight_g > 0; reduction_pct ∈ [0, 90] (feasibility cap is an assumption).
