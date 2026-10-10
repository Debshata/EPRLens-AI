# AWS data flow

```
Browser (localhost) ──► Next.js route handlers /api/*  (server-only creds of IAM user *-frontend)
        │                    │ lambda:InvokeFunction            │ presigned PUT (5 min, pinned type+size)
        │                    ▼                                  ▼
        │            Lambda functions (7)                S3 uploads bucket  uploads/<company_id>/{images,invoices,csv}/…
        │                    │ read                              ▲
        │                    ├──────────────► S3 models bucket   models/{material-classifier,forecast,anomaly}/v1/…  reference/…
        │                    └─ write/read ─► DynamoDB  eprlens-demo-analysis  (pk=company_id, sk=KIND#id, payload JSON)
        └── browser uploads file straight to S3 using the presigned URL; no AWS keys in the browser
```

| Function | Reads | Writes (DynamoDB sk) |
|---|---|---|
| classify-image | uploads image, `models/material-classifier/v1/*` | `IMAGE#<file>` |
| parse-invoice | uploads PDF | `INVOICE#<DOC id>` (parsed invoice + S3 key; the PDF itself stays in S3) |
| reconcile | uploads CSV, `INVOICE#…`, `reference/invoice_index.json` | `RUN#<id>` (findings) |
| forecast | `models/forecast/v1/*`, `reference/<company>/forecast_history.json` | `FORECAST#<month>` |
| detect-anomaly | `models/anomaly/v1/*` | – |
| scenario-engine | – | – |
| company-data | `reference/<company>/*.json` | `COMPANY#profile` (created companies) |

Every stored result carries model/rule versions (`anomaly-v1`, `forecast-v1`, `rules-v1`, `pdf-text-v1`, classifier `model_version`). Raw PDFs/images/CSVs are never stored in DynamoDB.

## Things that are deliberately simple (and honest)
- **Invoice ↔ record link.** A PDF carries no internal ids, so `reference/invoice_index.json` (number + date + vendor → internal invoice/transaction ids) plays the role of the company's ERP link. Invoice number alone is never used.
- **Company data** (profile, dashboard totals, simulator catalogue, forecast history) is seeded demo data for `COMP_0001` (synthetic).
- **Uncertain image result** uses a 0.60 confidence threshold (`UNCERTAIN_THRESHOLD`) — an assumption; the image-model team defined none.
- **Forecast** months after the first are recursive and labelled `projected`; no uncertainty interval is returned.
