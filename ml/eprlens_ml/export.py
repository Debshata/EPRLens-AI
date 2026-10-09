"""Export AWS-ready artifacts (S3 + Lambda only). SYNTHETIC — EPRLens Demo."""
import json
import shutil
from pathlib import Path

import joblib
import numpy as np

from . import anomaly_features as af
from . import forecast_features as ff
from .common import ML_DIR, ROOT, library_versions, now, sha256_file, write_json

FORECAST_REQ_ONNX = ["onnxruntime==1.31.0", "numpy==2.5.1", "joblib==1.6.0"]
FORECAST_REQ_JOBLIB = {"xgboost": ["xgboost==3.4.0", "numpy==2.5.1", "scipy==1.18.1", "joblib==1.6.0"],
                       "random_forest": ["scikit-learn==1.9.0", "numpy==2.5.1", "scipy==1.18.1", "joblib==1.6.0"],
                       "linear_regression": ["scikit-learn==1.9.0", "numpy==2.5.1", "scipy==1.18.1", "joblib==1.6.0"]}
ANOMALY_REQ = ["scikit-learn==1.9.0", "numpy==2.5.1", "scipy==1.18.1", "joblib==1.6.0"]


def _sha_list(folder):
    lines = []
    for p in sorted(Path(folder).iterdir()):
        if p.is_file() and p.name != "SHA256SUMS.txt":
            lines.append(f"{sha256_file(p)}  {p.name}")
    (Path(folder) / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


# ================================================================ forecast
def try_onnx_forecast(algo, model, n_features, X_check, log):
    """Convert to ONNX and verify predictions match Python. Returns bytes or None."""
    try:
        if algo == "xgboost":
            from onnxmltools import convert_xgboost
            from onnxmltools.convert.common.data_types import FloatTensorType
            booster = model.get_booster()
            if getattr(model, "best_iteration", None) is not None:
                booster = booster[: model.best_iteration + 1]   # early stopping keeps extra trees; predict() ignores them
            booster.feature_names = None
            onx = convert_xgboost(booster, initial_types=[("features", FloatTensorType([None, n_features]))],
                                  target_opset=15)
        else:
            from skl2onnx import convert_sklearn
            from skl2onnx.common.data_types import FloatTensorType
            onx = convert_sklearn(model, initial_types=[("features", FloatTensorType([None, n_features]))],
                                  target_opset=15)
        data = onx.SerializeToString()
        import onnxruntime as ort
        sess = ort.InferenceSession(data, providers=["CPUExecutionProvider"])
        p_onnx = sess.run(None, {"features": X_check.astype(np.float32)})[0].ravel()
        p_py = model.predict(X_check).ravel()
        diff_log = float(np.max(np.abs(p_onnx - p_py)))
        rel_kg = float(np.max(np.abs(np.exp(p_onnx - p_py) - 1)))
        log.info(f"ONNX parity: max |Δ log-ratio| {diff_log:.2e}, max relative kg difference {rel_kg:.2e}")
        if rel_kg <= 1e-3:
            return data, {"max_abs_diff_log_ratio": diff_log, "max_rel_diff_kg": rel_kg, "rows_checked": len(X_check)}
        log.warning("ONNX predictions differ by more than 0.1 % — falling back to joblib")
    except Exception as e:  # conversion problems → joblib fallback (documented)
        log.warning(f"ONNX conversion failed ({e!r}) — using joblib")
    return None, None


def export_forecast(cfg, run_dir, winner, model, season, df, metrics_all, log, git, dataset_sha):
    out = ROOT / cfg["export"]["forecast_dir"]
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    algo = winner["algorithm"]
    family = "linear_regression" if algo.startswith("linear") else algo
    va = df[df.fsplit == "validation"]
    X_check = va[ff.FEATURES].to_numpy(float)[:2000]
    onnx_bytes, parity = (None, None)
    if algo != "linear_regression_raw":
        onnx_bytes, parity = try_onnx_forecast(algo, model, len(ff.FEATURES), X_check, log)
    if onnx_bytes:
        (out / "model.onnx").write_bytes(onnx_bytes)
        model_file, runtime, reqs = "model.onnx", "onnxruntime", FORECAST_REQ_ONNX
    else:
        joblib.dump(model, out / "model.joblib")
        model_file, runtime, reqs = "model.joblib", "joblib", FORECAST_REQ_JOBLIB[family]
    prep = {"feature_order": ff.FEATURES, "industries": ff.INDUSTRIES, "season_table": season,
            "fill_values": ff.FILL, "ratio_clip": ff.CLIP, "target_transform": "log(next_kg / latest_kg)",
            "inverse_transform": "forecast_kg = latest_kg * exp(prediction)", "max_history_months_used": 13,
            "algorithm": algo, "model_file": model_file, "runtime": runtime}
    joblib.dump(prep, out / "preprocessor.joblib")
    shutil.copy2(ML_DIR / "eprlens_ml" / "forecast_features.py", out / "features.py")
    schema = {
        "model_version": "forecast-v1", "feature_order": ff.FEATURES, "n_features": len(ff.FEATURES),
        "input_dtype": "float32 (ONNX) / float64 (joblib)",
        "request": {"company_id": "string", "product_id": "string", "industry": f"one of {ff.INDUSTRIES}",
                    "history": "list of {month: 'YYYY-MM', packaging_kg: number>=0, units_sold: int (optional), "
                               "weight_per_unit_g: number (optional)}; ascending; last entry = latest month "
                               "(packaging_kg > 0); up to 13 months are used"},
        "response": {"forecast_kg": "number", "target_month": "YYYY-MM", "model_version": "forecast-v1",
                     "model_name": algo, "status": "success | error"},
        "notes": ["No confidence interval is returned: none is statistically supported by this model.",
                  "Features are built by features.py (shipped in this folder) — do not reimplement them."],
    }
    write_json(schema, out / "feature_schema.json")
    sample = sample_forecast_request(cfg, df)
    write_json(sample, out / "sample_input.json")
    (out / "requirements-lambda.txt").write_text("\n".join(reqs) + "\n", encoding="utf-8", newline="\n")
    tr = df[df.fsplit == "train"]
    meta = {
        "model_name": algo, "model_version": "forecast-v1", "algorithm": algo, "training_timestamp": now(),
        "git_commit": git, "dataset_sha256": dataset_sha, "seed": cfg["seed"], "features": ff.FEATURES,
        "target": "next_month_packaging_kg", "training_rows": int(len(tr)), "validation_rows": int(len(va)),
        "test_rows": int((df.fsplit == "test").sum()), "metrics": metrics_all, "python_version": library_versions()["python"],
        "library_versions": library_versions(), "params": winner["params"], "model_file": model_file,
        "runtime": runtime, "onnx_parity": parity, "synthetic_only": True,
        "warning": "Trained and evaluated on SYNTHETIC data — metrics are not real-world accuracy.",
    }
    meta["artifact_sha256"] = sha256_file(out / model_file)
    write_json(meta, out / "model_metadata.json")
    return out, model_file


def sample_forecast_request(cfg, df):
    import pandas as pd
    panel = pd.read_csv(ROOT / cfg["data_dir"] / "csv" / "forecast_panel.csv")
    p = panel[(panel.product_id == "PROD_000001")].sort_values("month").tail(13)
    hist = [{"month": r.month, "packaging_kg": round(float(r.packaging_kg), 3), "units_sold": int(r.units_sold),
             "weight_per_unit_g": round(float(r.weight_per_unit_g), 3)} for r in p.itertuples()]
    return {"company_id": "COMP_0001", "product_id": "PROD_000001", "industry": "Beverages", "history": hist}


# ================================================================ anomaly
def try_onnx_iforest(model, X_check, log):
    if model.max_features != 1.0:
        log.info("IsolationForest ONNX export skipped: skl2onnx supports it only with max_features=1.0 (joblib is used)")
        return None, None
    try:
        from skl2onnx import to_onnx
        onx = to_onnx(model, X_check[:1].astype(np.float32), target_opset={"": 15, "ai.onnx.ml": 3})
        import onnxruntime as ort
        sess = ort.InferenceSession(onx.SerializeToString(), providers=["CPUExecutionProvider"])
        outs = sess.run(None, {sess.get_inputs()[0].name: X_check.astype(np.float32)})
        dec = np.asarray(outs[1]).ravel()  # decision_function
        ref = model.decision_function(X_check)
        diff = float(np.max(np.abs(dec - ref)))
        log.info(f"IsolationForest ONNX parity: max |Δ decision_function| {diff:.2e}")
        if diff <= 1e-4:
            return onx.SerializeToString(), {"max_abs_diff_decision_function": diff, "rows_checked": len(X_check),
                                             "score_from_onnx": "anomaly_score = -(decision_function + offset)"}
    except Exception as e:
        log.warning(f"IsolationForest ONNX conversion skipped ({e!r})")
    return None, None


def export_anomaly(cfg, model, params, rate_ref, tol, thresholds, metrics_all, counts, sample_record, X_check, log,
                   git, dataset_sha):
    out = ROOT / cfg["export"]["anomaly_dir"]
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    joblib.dump(model, out / "isolation_forest.joblib")
    onnx_bytes, parity = try_onnx_iforest(model, X_check, log)
    if onnx_bytes:
        (out / "isolation_forest.onnx").write_bytes(onnx_bytes)
    prep = {"feature_order": af.FEATURES, "rate_reference_per_kg": rate_ref, "score": "-IsolationForest.score_samples",
            "offset": float(model.offset_), "invoice_types": af.INVOICE_TYPES}
    joblib.dump(prep, out / "preprocessor.joblib")
    write_json({"threshold": thresholds["combined"], "iforest_only_threshold": thresholds["iforest"],
                "score_definition": "anomaly_score = -IsolationForest.score_samples(x); higher = more unusual",
                "decision": "is_anomaly = any deterministic rule triggered OR anomaly_score >= threshold",
                "chosen_on": "validation companies only", "max_fpr_constraint": cfg["anomaly"]["max_fpr"]},
               out / "threshold.json")
    from rules import anomaly_rules as ar
    write_json({"rules_version": ar.RULES_VERSION, "tolerances": tol,
                "rules": {k: {"severity": v[0], "designed_for": v[1]} for k, v in ar.RULE_CATALOGUE.items()}},
               out / "rules_config.json")
    shutil.copy2(ML_DIR / "eprlens_ml" / "anomaly_features.py", out / "features.py")
    shutil.copy2(ML_DIR / "rules" / "anomaly_rules.py", out / "rules.py")
    write_json({"model_version": "anomaly-v1", "feature_order": af.FEATURES, "n_features": len(af.FEATURES),
                "record_types": ["invoice", "recycling"],
                "request": "see ml/AWS_HANDOFF.md §Anomaly request — invoice header, lines (+ linked internal record "
                           "and master component), master, context; or a recycling record",
                "response": {"is_anomaly": "bool", "anomaly_score": "number | null (null for recycling records)",
                             "threshold": "number", "rule_findings": "list of {rule_id, severity, reason}",
                             "ml_flag": "bool", "model_version": "anomaly-v1", "status": "success | error"},
                "forbidden_inputs": sorted(af.LABEL_LIKE)}, out / "feature_schema.json")
    write_json(sample_record, out / "sample_input.json")
    (out / "requirements-lambda.txt").write_text("\n".join(ANOMALY_REQ) + "\n", encoding="utf-8", newline="\n")
    meta = {
        "model_name": "isolation_forest+rules", "model_version": "anomaly-v1",
        "algorithm": "sklearn.ensemble.IsolationForest + deterministic rules", "training_timestamp": now(),
        "git_commit": git, "dataset_sha256": dataset_sha, "seed": cfg["seed"], "features": af.FEATURES,
        "target": "none (unsupervised); evaluated against anomaly_ground_truth labels", **counts,
        "metrics": metrics_all, "python_version": library_versions()["python"], "library_versions": library_versions(),
        "params": params, "rules_tolerances": tol, "onnx_parity": parity, "synthetic_only": True,
        "warning": "Trained and evaluated on SYNTHETIC data — metrics are not real-world accuracy.",
    }
    meta["artifact_sha256"] = sha256_file(out / "isolation_forest.joblib")
    write_json(meta, out / "model_metadata.json")
    return out


def finalize_hashes(folder):
    _sha_list(folder)
