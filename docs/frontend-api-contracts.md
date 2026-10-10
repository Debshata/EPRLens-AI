# Frontend ⇄ backend contracts

Source of truth: `frontend/src/lib/contracts.ts` (zod). Fixtures in `frontend/src/lib/mocks/*.json` conform to the same schemas (checked by `tests/unit/contracts-fixtures.test.ts`).
The browser only calls the Next.js route handlers below (`/api/*`). Those handlers hold AWS credentials, mint presigned URLs and invoke Lambda; **no AWS keys ever reach the browser**.

General rules
- Quantities are **kg**. Original value + unit travel next to the normalised kg value.
- Every JSON error uses `{ "code": string, "message": string, "next_step": string }` (HTTP 4xx/5xx).
- `legal_determination` is always `false`. A model score is never a probability of non-compliance. Forecasts carry no invented interval.
- `NEXT_PUBLIC_API_MODE=mock` → handlers answer `503 mock_mode`; the UI uses fixtures instead.

## Endpoints (browser → Next route handler → Lambda)

| Route | Request | Response | Lambda (server env) | Lambda payload (proposal) |
|---|---|---|---|---|
| `POST /api/uploads/presign` | `{company_id, kind: csv\|invoice\|image, name, size, mime, sha256}` | `{upload_url, s3_key}` (PUT, 5 min, pinned type + size) | — (S3 presign) | key `uploads/<company_id>/{csv\|invoices\|images}/<uuid>.<ext>` |
| `POST /api/vision/classify` | `{company_id, s3_key}` | `ImageResult` | `LAMBDA_CLASSIFY_IMAGE` | `{action:"classify_image", company_id, s3:{bucket,key}}` |
| `POST /api/documents/analyze` | `{company_id, s3_key}` | `Invoice` | `LAMBDA_PARSE_INVOICE` | `{action:"parse_invoice", …}` |
| `POST /api/transactions/validate` | `{company_id, s3_key}` | `CsvSummary` | `LAMBDA_RECONCILE` | `{action:"validate_transactions", …}` |
| `POST /api/reconcile` | `{company_id, document_id, csv_s3_key}` | `ReconciliationResponse` | `LAMBDA_RECONCILE` | `{action:"reconcile", …}` |
| `GET /api/forecast?company_id=` | — | `ForecastResponse` | `LAMBDA_FORECAST` | `{action:"forecast", company_id}` |
| `POST /api/scenario` | `ScenarioRequest` | `ScenarioResult` | `LAMBDA_SCENARIO_ENGINE` | `{action:"what_if", units, current_g_per_unit, proposed_g_per_unit}` → `{baseline_kg, proposed_kg, reduction_kg}` |
| `GET /api/dashboard?company_id=` | — | `DashboardSummary` | `LAMBDA_COMPANY_DATA` *(optional)* | `{action:"dashboard_summary"}` |
| `GET /api/simulator?company_id=` | — | `SimulatorFixture` | `LAMBDA_COMPANY_DATA` *(optional)* | `{action:"simulator_catalog"}` |
| `GET/POST /api/company` | `CompanyInput` / `?demo=1` | `CompanyBundle` | `LAMBDA_COMPANY_DATA` *(optional)* | `{action:"get_company_profile"\|"create_company"}` |

Lambda responses may be a bare JSON object or an API-style `{statusCode, body}` envelope (envelope still TBD — context.md D056).

## Shapes (abridged — see contracts.ts for all fields)

**ImageResult** (exactly WP1): `{ predicted_class: plastic|paper|cardboard|metal|glass|battery|trash_other, confidence: 0..1, uncertain: boolean, model_version: string }`

**Invoice**: `{ document_id, invoice_id?, invoice_number, invoice_date, vendor{name,gstin}, currency, total_amount, page_count, lines[{line_reference "DOC:p1:l1", transaction_id?, product_id?, component_id?, quantity, unit, normalized_quantity_kg, conversion_rule, amount, …}], fields[EvidenceField], source{file_name, sha256, synthetic}, extraction{method, status, parser_version} }`

**Finding** (reconcile + detect-anomaly): `{ finding_id, type, anomaly_code, title, severity low|medium|high, review_state, expected{label, raw_value, raw_unit, value_kg, source_ref}, observed{…}, difference_kg, rule_ids[], rule_version, detected_by[rule|ml_outlier], model_score|null, explanation, legal_determination:false }`

**ForecastResponse**: `{ company_id, basis, history[{month, packaging_kg, kind:"observed"}], forecast{ model_version, model_name, target, interval:null, interval_note, synthetic_only, warning, baseline{name,next_month_kg}, metrics_test{…}, points[{month, packaging_kg, kind: model|projected, per_product?}] } }`

**ScenarioRequest / Result**: `{product_id, component_id, units, baseline_g_per_unit, proposed_g_per_unit}` → `{baseline_kg, proposed_kg, reduction_kg, reduction_pct, formula, hypothetical:true, disclaimer}` (formula: `kg = units × g ÷ 1000`; 0% change ⇒ 0 kg).

## Backend status (WP3 delivered 2026-10-10)
Implemented in `backend/lambdas/` and deployed by `infrastructure/scripts/`; the contracts above are verified end to end by `infrastructure/scripts/65-live-api-check.py`.
- `parse-invoice` returns the **Invoice** shape (`fields[]`, `quantity: null` when the PDF has none). Measured on the 1,000 synthetic invoices: invoice number/date/vendor/total 100%, line quantity 3,839/3,846, kg 3,846/3,846 (`backend/evaluation/invoice_parser_metrics.json`).
- `company-data` (a 7th Lambda beyond the runbook's six) serves the seeded demo company profile, dashboard summary and simulator catalogue, and stores created companies.
- `reconcile` links an invoice PDF to the CSV through `reference/invoice_index.json` (invoice number + date + vendor → internal ids), standing in for an ERP link. Invoice number alone is never used.
- Lambda user-facing failures are `{statusCode, body:{code,message,next_step}}` and reach the UI unchanged.

Still open: review actions (accept/reject) live in the browser only — no audit endpoint exists yet; the uncertainty threshold for the image model (0.60) is an assumption; forecast months after the first are recursive.
