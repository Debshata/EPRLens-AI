# Demo flow (≈3 minutes) — mock mode, no AWS

Everything on screen is **Synthetic demo data** (fictitious company *EcoFizz Beverages Pvt Ltd*, `COMP_0001`).
Start: `cd frontend && npm install && npm run dev`, open <http://localhost:3000>.

| Time | Do | Say / point at |
|---|---|---|
| 0:00 | Landing → **Explore demo** | “Pre-compliance review before filing — not a CPCB portal.” |
| 0:20 | Onboarding is prefilled → **Continue ×3 → Create workspace** | Role, turnover, states; “Potential applicability — requires verification” (never “compliant”). |
| 0:40 | **Packaging photo** tab → *Illustrative PET bottle drawing* | “Plastic, 94%” — a probable material, **not** an official EPR category. Try the blurry sample for the *uncertain* state. |
| 1:00 | **Invoice PDF** tab → *Invoice SYEC/2526/00004* | Extracted fields with page:line; original `0.500 Tonne` next to `500 kg`. |
| 1:15 | **Transaction CSV** tab → *15 EcoFizz transaction rows* → **Run reconciliation** | Real in-browser comparison of invoice vs record. |
| 1:30 | Findings: open **Invoice 0.5 MT vs recorded 500 MT** | Invoice **500 kg** vs recorded **500,000 kg**, difference **499,500 kg (499.5 t)**; rule-based explanation; outlier score labelled “not a probability”. |
| 1:55 | **Accept correction** → value `500`, reason → Save | Original `500,000 kg` stays visible; audit history keeps it. “A correction does not change physical waste or any filing.” |
| 2:15 | **Dashboard** | Next-month forecast **403,261.78 kg (403.3 t)** vs last-value baseline; “interval unavailable”; material-flow 3D with the same numbers in the table; rule vs outlier findings. |
| 2:40 | **Simulator** (default Cola 750 ml PET bottle, 25 g → 20 g) | Set units to 100,000: **2,500 kg → 2,000 kg, −500 kg** (hypothetical, not measured savings). |

Shortcuts: `/app/review?demo=1` loads the whole sample flow in one click; the sidebar **Reset demo** clears local state.

## Where the numbers come from
- Mismatch: generated invoice `DOC_000832` (`INV_00017685`) vs transaction `TXN_00121740` in `syntheticml/` (ground-truth anomaly `ANM_0000001`).
- Forecast: real `forecast-v1` ONNX model output (per product, summed) on COMP_0001 history; months after the first are recursive “projected” values.
- Anomaly score 0.599 vs threshold 0.539: real `anomaly-v1` sample output. Image result: a **fixture** in mock mode (same JSON shape as the model); live mode runs the real MobileNetV3 ONNX model.

## Live mode (real AWS backend)
Same script, but results come from deployed Lambdas. Differences to expect:
- The packaging photo is classified by the real MobileNetV3 model. The bundled *drawings* are not photos: the carton drawing returns **cardboard (≈99.9%)**, while the bottle drawing is called **trash_other (≈76%)**. For the video use a real photo of a bottle (plastic) rather than the drawing.
- The invoice and CSV are uploaded straight from the browser to S3, parsed by `parse-invoice`, and reconciled by `reconcile`; only the genuine computed finding appears (1 finding), not the 6 mock findings.
