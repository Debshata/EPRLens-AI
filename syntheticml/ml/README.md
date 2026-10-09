# EPRLens AI — Synthetic ML

> **SYNTHETIC — EPRLens Demo.** Both models are trained and evaluated on synthetic data
> (`synthetic-data/generate.py`). Metrics show the pipeline works; they are not real-world accuracy.
> Results: `docs/ml-model-report.md`.

## 1. What models exist

| Model | Job | Algorithm | Artifact |
|---|---|---|---|
| Forecast (`forecast-v1`) | predict next-month packaging kg for a product | selected on validation from last value, seasonal naive, Linear Regression, Random Forest, XGBoost | `ml/artifacts/forecast/v1/` (ONNX when it matches Python, otherwise joblib) |
| Anomaly (`anomaly-v1`) | flag suspicious invoices / recycling records | deterministic rules (`ml/rules/anomaly_rules.py`) + Isolation Forest | `ml/artifacts/anomaly/v1/` |

## 2. Install (Python 3.12)

```bash
python -m venv .venv
```
Windows:
```bash
.venv\Scripts\activate
```
Linux/macOS:
```bash
source .venv/bin/activate
```
```bash
pip install -r ml/requirements.txt
```

The synthetic dataset must exist in `data/generated/` (git-ignored). Regenerate it if needed:
```bash
python synthetic-data/generate.py --config synthetic-data/config.yaml --out data/generated
```

## 3–5. Train, run overnight, resume

One command runs everything (validate → features → forecast search → anomaly search → final test → plots → export →
AWS check → reports → notebook → PDF guide → tests):
```bash
python ml/run_overnight.py --config ml/configs/synthetic_ml.yaml
```
- Progress prints to the terminal and `ml/logs/overnight.log`.
- Each stage is checkpointed in `ml/runs/<run_id>/status.json`. If the process stops, run the **same command** again —
  completed stages are skipped.
- Redo everything: add `--force`. Redo one stage: `--force-stage export`. Stop early: `--until forecast_final`.
- Quick end-to-end check with tiny budgets: `--smoke`.
- Forecast only: `python ml/scripts/train_forecast.py` · up to anomaly: `python ml/scripts/train_anomaly.py`.

Search budgets, stopping rules and seeds are in `ml/configs/synthetic_ml.yaml`. Tuning uses validation data only; the
test split is scored once for the final models.

## 6. Evaluate

Outputs (committed): `ml/evaluation/forecast/` and `ml/evaluation/anomaly/` (metrics.json, model_comparison.csv,
graphs), `ml/evaluation/experiment_log.csv`, `ml/evaluation/aws_artifact_report.json`, `docs/ml-model-report.md`.

## 7. Notebook

```bash
jupyter notebook ml/notebooks/EPRLens_Synthetic_ML_Training.ipynb
```
It is executed by the overnight run (`notebook` stage) and saved with outputs. Re-execute headless:
```bash
jupyter nbconvert --to notebook --execute --inplace ml/notebooks/EPRLens_Synthetic_ML_Training.ipynb
```

## 8. Test the final artifacts

```bash
pytest tests/ml
python ml/aws_examples/test_forecast_local.py
python ml/aws_examples/test_anomaly_local.py
```

## 9. How AWS uses the files

Copy `ml/artifacts/forecast/v1/` → `s3://<bucket>/models/forecast/v1/` and `ml/artifacts/anomaly/v1/` →
`s3://<bucket>/models/anomaly/v1/`. The reference handlers in `ml/aws_examples/` load them in Lambda. Full guide:
`ml/AWS_HANDOFF.md` and `docs/EPRLens_ML_to_AWS_Engineer_Guide.pdf`.
