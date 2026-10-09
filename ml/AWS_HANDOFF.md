# EPRLens AI — ML → AWS Handoff

> SYNTHETIC — EPRLens Demo. Plain-language guide for the AWS engineer (S3 + Lambda + DynamoDB only — no SageMaker,
> ECR, Textract, Bedrock or API Gateway). The same content, with diagrams, is in
> `docs/EPRLens_ML_to_AWS_Engineer_Guide.pdf`.

## 1. What has the ML team built?

We have trained two models.

1. **Forecast model** — takes a product's packaging history (kg per month) and predicts **next month's packaging kg**.
   Model: xgboost exported as `model.onnx` (runs with onnxruntime, numpy, joblib).
2. **Anomaly model** — takes one invoice (or one recycling record) and says whether it looks wrong. It first runs
   simple **rules** (duplicate, missing field, quantity mismatch, wrong unit, …) and then an **Isolation Forest**
   score for unusual patterns. If any rule fires **or** the score is above the saved threshold, the record is flagged.

Both were trained on synthetic data. Treat outputs as decision support, not legal findings.

## 2. Files you are receiving

```
ml/artifacts/forecast/v1/
    feature_schema.json
    features.py
    model.onnx
    model_metadata.json
    preprocessor.joblib
    requirements-lambda.txt
    sample_input.json
    sample_output.json
    SHA256SUMS.txt
ml/artifacts/anomaly/v1/
    feature_schema.json
    features.py
    isolation_forest.joblib
    model_metadata.json
    preprocessor.joblib
    requirements-lambda.txt
    rules.py
    rules_config.json
    sample_input.json
    sample_output.json
    SHA256SUMS.txt
    threshold.json
ml/aws_examples/
    lambda_forecast_handler.py     reference Lambda handler (forecast)
    lambda_anomaly_handler.py      reference Lambda handler (anomaly)
    test_forecast_local.py         run locally, no retraining
    test_anomaly_local.py          run locally, no retraining
```

Check integrity with `SHA256SUMS.txt` in each folder.

## 3. Where to put the files in S3

| Local folder | S3 prefix |
|---|---|
| `ml/artifacts/forecast/v1/` | `s3://<model-bucket>/models/forecast/v1/` |
| `ml/artifacts/anomaly/v1/` | `s3://<model-bucket>/models/anomaly/v1/` |

```bash
aws s3 cp ml/artifacts/forecast/v1/ s3://<model-bucket>/models/forecast/v1/ --recursive
aws s3 cp ml/artifacts/anomaly/v1/ s3://<model-bucket>/models/anomaly/v1/ --recursive
```

## 4. What each Lambda does

**Forecast Lambda:** receive JSON → load artifacts (once per cold start) → build features with `features.py` →
predict → return JSON.

**Anomaly Lambda:** receive record → run rules (`rules.py`) → build features (`features.py`) → Isolation Forest score →
compare with `threshold.json` → combine → return JSON.

The handlers download from `s3://$MODEL_BUCKET/models/<model>/v1/` into `/tmp` when `MODEL_BUCKET` is set
(needs `s3:GetObject` on that prefix only), otherwise they read a local folder.

| Lambda | Handler | Files it needs | Python packages (pinned) | Suggested start memory |
|---|---|---|---|---|
| forecast | `lambda_forecast_handler.handler` | model.onnx, preprocessor.joblib, features.py, model_metadata.json | onnxruntime==1.31.0 numpy==2.5.1 joblib==1.6.0 | 512 MB |
| anomaly | `lambda_anomaly_handler.handler` | isolation_forest.joblib, preprocessor.joblib, threshold.json, rules_config.json, features.py, rules.py, model_metadata.json | scikit-learn==1.9.0 numpy==2.5.1 scipy==1.18.1 joblib==1.6.0 | 1024 MB |

Build Linux wheels for the Lambda architecture (`pip install --platform manylinux2014_x86_64 --only-binary=:all: …`
or `manylinux2014_aarch64` for arm64). Put heavy packages (scikit-learn, scipy, numpy) in a layer. Limits: 50 MB zipped
direct upload (larger via S3), 250 MB unzipped including layers.

## 5. Forecast request / response

Request (only the last 3 history months shown; the full sample is `sample_input.json`; send up to 13 months, oldest
first, last entry = latest month):

```json
{
  "company_id": "COMP_0001",
  "product_id": "PROD_000001",
  "industry": "Beverages",
  "history": [
    {
      "month": "2025-12",
      "packaging_kg": 419.017,
      "units_sold": 9395,
      "weight_per_unit_g": 44.6
    },
    {
      "month": "2026-01",
      "packaging_kg": 406.083,
      "units_sold": 9105,
      "weight_per_unit_g": 44.6
    },
    {
      "month": "2026-02",
      "packaging_kg": 511.74,
      "units_sold": 11474,
      "weight_per_unit_g": 44.6
    }
  ]
}
```

Response:

```json
{
  "company_id": "COMP_0001",
  "product_id": "PROD_000001",
  "target_month": "2026-03",
  "forecast_kg": 603.748,
  "model_version": "forecast-v1",
  "model_name": "xgboost",
  "status": "success"
}
```

No confidence interval is returned — the model does not support one honestly.

## 6. Anomaly request / response

The caller (backend) sends one invoice with its lines. Each line carries the linked internal record
(`transaction`) and the product-master component (`master_component`); `context` holds statistics the backend computes
from the company's own history; `master` holds supplier facts. Never send label fields (`is_anomaly`, `anomaly_type`,
…) — the handler rejects them. Abbreviated sample (first line only; full sample in `sample_input.json`):

```json
{
  "record_type": "invoice",
  "record_id": "INV_00017685",
  "company_id": "COMP_0001",
  "invoice": {
    "invoice_id": "INV_00017685",
    "invoice_number": "SYEC/2526/00004",
    "invoice_type": "PKG_PURCHASE",
    "company_id": "COMP_0001",
    "supplier_id": "SUP_TEST_001",
    "buyer_id": "COMP_0001",
    "invoice_date": "2025-11-17",
    "status": "issued",
    "supplier_gstin": "06ODQCM2783K1Z4",
    "buyer_gstin": "07OLWCZ2975K3ZF",
    "currency": "INR",
    "fx_rate": null,
    "total_taxable_value": 105529.09,
    "gst": 18995.24,
    "total": 124524.33,
    "original_invoice_id": null
  },
  "lines": [
    {
      "line_no": 1,
      "item_description": "PET bottle for 750 ml - PET",
      "product_id": "PROD_000001",
      "component_id": "PKGCOMP_000002",
      "material": "PET",
      "plastic_category": "CAT_I",
      "hsn_code": "3923",
      "raw_quantity": 0.5,
      "raw_unit": "MT",
      "weight_per_unit_g": null,
      "normalized_quantity_kg": 500.0,
      "recorded_quantity_kg": 500000.0,
      "rate": 211058.17,
      "taxable_value": 105529.09,
      "gst_rate": 18,
      "gst_amount": 18995.24,
      "transaction_id": "TXN_00121740",
      "transaction": {
        "transaction_id": "TXN_00121740",
        "transaction_type": "purchase",
        "status": "posted",
        "raw_quantity": 500.0,
        "raw_unit": "MT",
        "normalized_quantity_kg": 500000.0,
        "supplier_id": "SUP_TEST_001",
        "date": "2025-11-17"
      },
      "master_component": {
        "material": "PET",
        "synthetic_category": "CAT_I",
        "weight_per_unit_g": 25.0,
        "component_form": "bottle"
      }
    }
  ],
  "context": {
    "item_month_qty": {
      "1": 500000.0
    },
    "item_median_qty": {
      "1": 30.1
    },
    "item_prev_month_qty": {
      "1": 49.125
    },
    "issuer_company_median_total_inr": 7496.84,
    "issuer_company_invoice_count": 13,
    "earlier_same_key_invoice_ids": []
  },
  "master": {
    "issuer_has_gstin": true,
    "issuer_supplier": {
      "supported_materials": [
        "PET"
      ],
      "supported_component_forms": [
        "bottle",
        "jar"
      ]
    }
  }
}
```

Response:

```json
{
  "record_id": "INV_00017685",
  "is_anomaly": true,
  "anomaly_score": 0.599222,
  "threshold": 0.53867,
  "ml_flag": true,
  "rule_findings": [
    {
      "rule_id": "QTY_MATCH_TOL",
      "severity": "medium",
      "reason": "line1: invoice 500.000 kg vs record 500000.000 kg"
    },
    {
      "rule_id": "QTY_RATIO_POW10",
      "severity": "high",
      "reason": "record differs by a power of ten on lines [1]"
    }
  ],
  "model_version": "anomaly-v1",
  "status": "success"
}
```

Recycling records use `{"record_type": "recycling", "recycling": {…}, "master": {"recycler_registered": true}}`;
they are checked by rules only (`anomaly_score` is `null`).

## 7. What goes into DynamoDB

Store results only — never the model files:

| Attribute | Example |
|---|---|
| `company_id` (PK) | `COMP_0001` |
| `run_ts` (SK) | `2026-10-09T10:00:00Z#forecast` |
| `analysis_type` | `forecast` / `anomaly` |
| `model_version` | `forecast-v1` / `anomaly-v1` |
| `result` | the Lambda JSON response (forecast_kg or is_anomaly, score, rule_findings) |
| `record_id` / `product_id` | `INV_…` / `PROD_…` |

## 8. Test locally (no retraining)

```bash
python ml/aws_examples/test_forecast_local.py
python ml/aws_examples/test_anomaly_local.py
```

Both print the response and check it equals `sample_output.json`.

## 9. Common errors

| Symptom | Cause | Fix |
|---|---|---|
| `FileNotFoundError` for a model file | wrong S3 prefix or env var | check `models/<model>/v1/` and `MODEL_BUCKET` / `*_ARTIFACT_DIR` |
| `feature order … does not match` | mixed artifact versions | upload the whole v1 folder together; verify SHA256SUMS |
| `KeyError` / missing feature | request missing a field | follow the request examples above |
| `ModuleNotFoundError: onnxruntime/sklearn` | package not in the Lambda zip/layer | install the pinned versions for Linux |
| `AccessDenied` from S3 | role lacks `s3:GetObject` | grant read on `models/*` only |
| `Object of type float32 is not JSON serializable` | returning numpy values | handlers already convert to plain floats — keep that |
| slow first call | cold start loads libraries + model | measured locally: forecast 1981.9 ms, anomaly 1619.9 ms (local machine, not AWS) |

## 10. Final checklist

- [ ] Both v1 folders uploaded; SHA256SUMS verified
- [ ] Lambda layers built for the right architecture with the pinned versions
- [ ] Env vars set: `MODEL_BUCKET` (or artifact dirs)
- [ ] IAM: `s3:GetObject` on `models/*`; DynamoDB `PutItem` on the results table only
- [ ] `test_*_local.py` pass locally; the same sample event passes in Lambda
- [ ] Responses stored in DynamoDB with `model_version`
- [ ] UI labels results "synthetic demo" and "not a compliance determination"
