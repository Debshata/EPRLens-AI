# Backend (Lambda) contracts

Bare JSON on success. A user-facing failure returns `{ "statusCode": 4xx, "body": { "code", "message", "next_step" } }`; the Next.js route handlers pass `message` and `next_step` straight to the UI. Response shapes equal the frontend zod contracts in `frontend/src/lib/contracts.ts` (see also [`frontend-api-contracts.md`](frontend-api-contracts.md)).

| Function | Request | Response |
|---|---|---|
| classify-image | `{company_id?, s3:{bucket,key}}` | `{predicted_class, confidence, uncertain, model_version}` |
| parse-invoice | `{company_id, s3:{bucket,key}}` | `Invoice` (original value + unit, `normalized_quantity_kg`, `fields[]` with source refs; `quantity: null` when the PDF has none) |
| reconcile `validate_transactions` | `{action, company_id, s3}` | `CsvSummary` |
| reconcile `reconcile` | `{action, company_id, document_id, csv:{bucket,key}}` | `{analysis_id, schema_version, company_id, rules_version, tolerances, findings[]}` |
| forecast | `{action:"forecast", company_id}` | `ForecastResponse` (history, point forecast + projected months, baseline, test metrics, `interval:null`) |
| detect-anomaly | the anomaly model request (`record_type`, `invoice`, `lines`, `context`, `master`) or `{use_sample:true}` | `{record_id, is_anomaly, anomaly_score, threshold, ml_flag, rule_findings[], model_version, status}` |
| scenario-engine | `{units, current_g_per_unit, proposed_g_per_unit}` | `{baseline_kg, proposed_kg, reduction_kg, reduction_pct, formula, hypothetical:true, disclaimer}` |
| company-data | `{action: get_company_profile\|dashboard_summary\|simulator_catalog\|create_company, company_id}` | seeded demo JSON / created `CompanyBundle` |

Limits: PDF ≤ 10 MB, CSV ≤ 5 MB, image ≤ 8 MB. Units are normalised to kg (kg, g, MT/tonne, pieces with a known weight); anything that cannot be converted is `null`, never zero.
