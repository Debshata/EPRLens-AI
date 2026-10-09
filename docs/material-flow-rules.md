# Material-Flow Accounting Rules

> **Status:** APPROVED as synthetic test design (DS-03 A, DS-11 A). SYNTHETIC — EPRLens Demo. The generated → collected → recycled chain is a synthetic material-flow relationship for testing, **not** a regulatory obligation or compliance-target calculation.
> These quantities are **not interchangeable**. Each is a distinct event type with its own evidence. None of them is a legal EPR target or a verified certificate.

## 1. Quantities

| Quantity | Meaning in the synthetic world | Evidence | Event type |
|---|---|---|---|
| `opening_inventory` | Packaging material (kg, per component) on hand at period start | prior closing | `OPENING_BALANCE` |
| `purchased` | Packaging material acquired from suppliers (domestic) | IT01/IT08/IT09 invoices | `PURCHASED` |
| `imported` (sub-type of acquired) | Packaging or packaged goods imported | IT07 | `PURCHASED` with `origin=import` |
| `produced` | Packaging made in-house (only for companies with `manufacturer=true` making their own packaging, e.g. blow-moulding from preforms) | production record | `PRODUCED` |
| `consumed` | Packaging attached to units produced in the period | production = sales (DS-03 A) | `CONSUMED` |
| `written_off` | Damaged / scrapped packaging in inventory (pre-consumer) | internal record | `WRITTEN_OFF` |
| `placed_on_market` | Packaging that left the company with goods sold domestically | IT02 sales | `PLACED_ON_MARKET` |
| `returned` | Goods (and their packaging) returned by buyers | IT06 | `RETURNED` |
| `exported` | Packaging that left India with exported goods | export sales | `EXPORTED` |
| `waste_generated` | **Synthetic proxy**: post-consumer packaging waste attributed to the company's placed-on-market quantity, lagged | model only | `WASTE_GENERATED_PROXY` |
| `collected` | Waste collected by/for a recycler in the company's cohort | IT04 / recycler records | `COLLECTED` |
| `recycled` | Waste processed by a recycler | IT03 | `RECYCLED` |
| `credits_documented` | Quantity of EPR-credit **claims** documented (not verified certificates) | recycler documentation | `CREDITS_DOCUMENTED` |
| `closing_inventory` | Packaging material on hand at period end | computed | `CLOSING_BALANCE` |

## 2. Core physical relation

```
packaging_kg_sold[p, t] = Σ_components units_sold[p, t] × weight_per_unit_g[c, t] / 1000
```
= gross packaging kg associated with units sold. Uses the weight **in force** at `t` (spec versioning).

## 3. Inventory relation (per company × component, per month)

```
opening + acquired − consumed − written_off = closing
acquired = purchased + imported + produced
closing[t] = opening[t+1]
```
- Inventory is tracked for packaging components that are purchased (bought-in packaging). Under DS-03 A, `consumed[t] = units_produced[t] × weight_g / 1000` and `units_produced = units_sold`.
- Purchases follow a reorder policy so closing ≥ 0 in the clean world. Negative closing is an anomaly signal (purchases missing or quantities wrong).

## 4. Market relation

```
consumed[t] = placed_on_market[t] + exported[t]          (clean world, DS-03 A)
net_placed[t] = placed_on_market[t] − returned[t]        (returns are explicit events)
```
Returns and exports are **explicit events**; they are never inferred from a reduced sales number.

## 5. Recycling relation (synthetic proxy cohort, DS-11 A)

```
waste_generated[c,k,t] = Σ_{lag} placed_on_market[c,k,t−lag] × w_lag      (lag 1–3 months)
collected   ≤ waste_generated
recycled    ≤ collected
credits_documented ≤ recycled   (only for registered recyclers supporting category k)
```
Holds per company × category × month **in the clean world only**. It is a synthetic test invariant for a defined cohort (context §47.2), not a universal real-world law.

## 6. Prohibitions

1. Recycling is **never** inferred from purchase invoices.
2. `placed_on_market` is never set equal to `purchased`.
3. `credits_documented` never implies a verified certificate or regulatory settlement.
4. Missing data is `null` with a status (`unknown`), never zero.
5. Non-plastic components (`plastic_epr_relevant=false`) are tracked in the ledger but excluded from plastic aggregates.
6. Corrections never overwrite originals; corrected values are new events referencing the original (`supersedes_event_id`).

## 7. Invariant tests (clean world)

| ID | Invariant |
|---|---|
| MF1 | inventory identity closes to 0.001 kg per company × component × month |
| MF2 | closing ≥ 0 |
| MF3 | consumed = placed_on_market + exported (± rounding) |
| MF4 | recycled ≤ collected ≤ waste_generated per company × category × month |
| MF5 | credits_documented ≤ recycled; only registered recyclers |
| MF6 | Σ material events per transaction = transaction normalized kg |
| MF7 | returned ≤ cumulative placed_on_market for the product |
