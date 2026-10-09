# ML Evaluation Plan (Phases 7–9)

> **Status:** PROPOSED. Scripts `ml/scripts/train_forecast.py` and `ml/scripts/train_anomaly.py` will be written after the dataset is approved and generated. No metrics exist yet — all results **TBD**. Metrics on synthetic data measure pipeline correctness, **not** real-world accuracy (context C7, C22).

## Forecasting

- **Problem:** predict `next_month_packaging_kg` (DS-06 A: product-month; company-month secondary).
- **Baselines:** last value; seasonal-naive (same month last year).
- **Models:** Linear Regression, Random Forest Regressor, XGBoost Regressor. No deep learning. XGBoost is chosen only if it wins on validation **and** test MAE and RMSE.
- **Features:** month (sin/cos + number), company_id (target-free encoding: frequency or one-hot only on train companies; never target-encoded across splits), industry one-hot, units_sold, weight_per_unit_g, lag_1/2/3/6/12, rolling_mean_3/6, sales_growth, seasonality_index (computed from train months only).
- **Split (DS-08 A):** months 1–24 train, 25–30 validation, 31–36 test; 40 held-out companies evaluated on all their months with models trained on the other 160.
- **Metrics:** MAE, RMSE, R² per split; per industry; held-out-company block reported separately.
- **Output:** `ml/evaluation/forecast_metrics.json`, model artefact under `ml/models/` (git-ignored), experiment card per context §18.2.

## Anomaly detection

- **A. Rules:** duplicates, missing fields, unit ratio 10ⁿ/1000, impossible values, invoice vs record mismatch, recycled > collected, registry lookups (rule IDs in `anomaly-catalogue.md`).
- **B. Isolation Forest (scikit-learn):** features — log quantity kg, invoice/record ratio (log), month-over-month change, z-score of weight per unit within component form, amount per kg z-score within material, supplier invoice frequency, deviation from company rolling median, seasonal z-score.
- **Systems compared:** rules only; IF only; rules ∪ IF.
- **Split:** by company 60/20/20; IF fit on train (unlabelled), threshold tuned on validation, reported on test.
- **Metrics:** precision, recall, F1, false-positive rate — overall and per anomaly type; hard-negative FP rate (AN17 and legit cases) reported separately.
- **Output:** `ml/evaluation/anomaly_metrics.json`, model artefact (git-ignored).

## Provenance recorded with every run

seed, generator_version, config_sha256, data_sha256 (from MANIFEST), git commit, library versions.
