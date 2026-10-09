"""Forecasting experiments: baselines, Linear Regression, Random Forest, XGBoost
(validation-only tuning, one final test evaluation). SYNTHETIC — EPRLens Demo."""
import json
import math
import time

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import ParameterSampler
from scipy.stats import loguniform, randint, uniform

from . import forecast_features as ff

TARGET = "next_month_packaging_kg"


def metrics(y, p):
    y, p = np.asarray(y, float), np.asarray(p, float)
    err = p - y
    ss = ((y - y.mean()) ** 2).sum()
    mask = y > 1.0
    return {"mae_kg": float(np.abs(err).mean()), "rmse_kg": float(np.sqrt((err ** 2).mean())),
            "r2": float(1 - (err ** 2).sum() / ss) if ss > 0 else None,
            "mape_pct_y_gt_1kg": float(np.abs(err[mask] / y[mask]).mean() * 100) if mask.any() else None,
            "median_ape_pct": float(np.median(np.abs(err[mask] / y[mask])) * 100) if mask.any() else None,
            "r2_log": float(1 - ((np.log1p(np.maximum(p, 0)) - np.log1p(y)) ** 2).sum()
                            / ((np.log1p(y) - np.log1p(y).mean()) ** 2).sum()), "rows": int(len(y))}


def X_of(df):
    return df[ff.FEATURES].to_numpy(dtype=np.float64)


def y_logratio(df):
    return np.log(df[TARGET].to_numpy(float) / df["packaging_kg"].to_numpy(float))


def from_logratio(df, pred):
    return df["packaging_kg"].to_numpy(float) * np.exp(np.clip(pred, -10, 10))


def weights(df, mode):
    kg = df["packaging_kg"].to_numpy(float)
    if mode == "sqrt":
        w = np.sqrt(kg)
    elif mode == "linear":
        w = kg
    else:
        return None
    return w / w.mean()


# ----------------------------------------------------------------- baselines
def baseline_last_value(df):
    return df["packaging_kg"].to_numpy(float)


def baseline_seasonal_naive(df):
    """Same month last year (t-11 relative to origin t); falls back to last value where history is short."""
    s = df["raw_lag_11"].to_numpy(float)
    has = ~np.isnan(s)
    return np.where(has, s, df["packaging_kg"].to_numpy(float)), has


RAW_LR = ["packaging_kg", "raw_lag_1", "raw_lag_2", "raw_lag_3", "raw_lag_12", "raw_rolling_mean_3", "raw_units_sold"]


def raw_matrix(df):
    m = df[RAW_LR].copy()
    for c in RAW_LR[1:]:
        m[c] = m[c].fillna(df["packaging_kg"]) if c != "raw_units_sold" else m[c].fillna(0)
    return m.to_numpy(float)


# ----------------------------------------------------------------- model fitting
def fit_predict(algo, params, tr, va, seed, n_jobs=-1, es_rounds=50, max_est=2000):
    """Fit on train, return (model, pred_train_kg, pred_val_kg, info)."""
    info = {}
    if algo == "linear_regression_raw":
        m = LinearRegression().fit(raw_matrix(tr), tr[TARGET].to_numpy(float))
        return m, m.predict(raw_matrix(tr)), m.predict(raw_matrix(va)), info
    if algo == "linear_regression_logratio":
        m = LinearRegression().fit(X_of(tr), y_logratio(tr))
        return m, from_logratio(tr, m.predict(X_of(tr))), from_logratio(va, m.predict(X_of(va))), info
    if algo == "random_forest":
        p = dict(params)
        wmode = p.pop("weighting", "none")
        m = RandomForestRegressor(random_state=seed % (2**31), n_jobs=n_jobs, **p)
        m.fit(X_of(tr), y_logratio(tr), sample_weight=weights(tr, wmode))
        return m, from_logratio(tr, m.predict(X_of(tr))), from_logratio(va, m.predict(X_of(va))), info
    if algo == "xgboost":
        import xgboost as xgb
        p = dict(params)
        wmode = p.pop("weighting", "none")
        m = xgb.XGBRegressor(n_estimators=max_est, early_stopping_rounds=es_rounds, tree_method="hist",
                             random_state=seed % (2**31), n_jobs=n_jobs, objective="reg:squarederror",
                             eval_metric="rmse", **p)
        m.fit(X_of(tr), y_logratio(tr), sample_weight=weights(tr, wmode), eval_set=[(X_of(va), y_logratio(va))],
              sample_weight_eval_set=[weights(va, wmode)] if wmode != "none" else None, verbose=False)
        info["best_iteration"] = int(m.best_iteration)
        return m, from_logratio(tr, m.predict(X_of(tr))), from_logratio(va, m.predict(X_of(va))), info
    raise ValueError(algo)


def predict_kg(algo, model, df):
    if algo == "linear_regression_raw":
        return model.predict(raw_matrix(df))
    return from_logratio(df, model.predict(X_of(df)))


XGB_SPACE = {
    "max_depth": randint(3, 11), "learning_rate": loguniform(0.01, 0.3), "min_child_weight": loguniform(1, 50),
    "subsample": uniform(0.5, 0.5), "colsample_bytree": uniform(0.5, 0.5), "reg_alpha": loguniform(1e-3, 10),
    "reg_lambda": loguniform(1e-2, 50), "weighting": ["none", "sqrt", "linear"],
}
RF_SPACE = {"n_estimators": [200, 300, 500], "max_depth": [None, 12, 18, 24], "min_samples_leaf": [1, 3, 5, 10],
            "max_features": [0.33, 0.5, 0.8, 1.0], "weighting": ["none", "sqrt", "linear"]}


def run_search(stage_dir, df, cfg, seed, elog, log, state):
    """Validation-only search. Resumable: completed trials are read back from trials.jsonl."""
    fc = cfg["forecast"]
    tr, va = df[df.fsplit == "train"], df[df.fsplit == "validation"]
    trials_path = stage_dir / "trials.jsonl"
    done = [json.loads(x) for x in trials_path.read_text(encoding="utf-8").splitlines()] if trials_path.exists() else []
    done_keys = {(d["algorithm"], json.dumps(d["params"], sort_keys=True)) for d in done}

    def record(algo, params, notes=""):
        key = (algo, json.dumps(params, sort_keys=True, default=str))
        if key in done_keys:
            return next(d for d in done if (d["algorithm"], json.dumps(d["params"], sort_keys=True)) == key)
        t0 = time.time()
        try:
            _, ptr, pva, info = fit_predict(algo, params, tr, va, seed, fc["n_jobs"], fc["xgb_early_stopping_rounds"],
                                            fc["xgb_max_estimators"])
            res = {"algorithm": algo, "params": params, "train": metrics(tr[TARGET], ptr),
                   "validation": metrics(va[TARGET], pva), "info": info, "ok": True}
        except Exception as e:  # log the failure and continue
            res = {"algorithm": algo, "params": params, "ok": False, "error": repr(e)}
        res["seconds"] = round(time.time() - t0, 2)
        res["experiment_id"] = elog.add("forecast", algo, {**params, **res.get("info", {})},
                                        res.get("train", {}).get("mae_kg"), res.get("validation"),
                                        duration=res["seconds"], notes=notes or ("FAILED " + res.get("error", "") if not res["ok"] else ""))
        with trials_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(res, default=float) + "\n")
        done.append(res)
        done_keys.add(key)
        if res["ok"]:
            v = res["validation"]
            log.info(f"  [{res['experiment_id']}] {algo} val MAE {v['mae_kg']:.1f} kg RMSE {v['rmse_kg']:.1f} "
                     f"R2 {v['r2']:.4f} ({res['seconds']}s)")
        else:
            log.warning(f"  [{res['experiment_id']}] {algo} FAILED: {res['error']}")
        return res

    budget = fc["budget_configs"]
    record("linear_regression_raw", {}, "classic LR on raw kg lags")
    record("linear_regression_logratio", {}, "LR on scale-free features, log(next/current) target")
    rng_seed = seed % (2**31)
    for p in ParameterSampler(RF_SPACE, n_iter=fc["rf_configs"], random_state=rng_seed):
        record("random_forest", dict(p))
    used = sum(1 for d in done if d["algorithm"] != "baseline")
    best, stall, n_xgb = math.inf, 0, 0
    for p in ParameterSampler(XGB_SPACE, n_iter=budget, random_state=rng_seed + 1):
        if used >= budget:
            log.info("forecast search: budget of %d configurations reached", budget)
            break
        params = {k: (float(v) if isinstance(v, (float, np.floating)) else (int(v) if isinstance(v, (int, np.integer)) else v))
                  for k, v in p.items()}
        res = record("xgboost", params)
        used += 1
        n_xgb += 1
        if not res["ok"]:
            stall += 1
            continue
        mae = res["validation"]["mae_kg"]
        if mae < best * (1 - fc["min_relative_gain"]):
            best, stall = mae, 0
        else:
            stall += 1
        if stall >= fc["patience"]:
            log.info("forecast search: %d consecutive XGBoost trials without >%.1f%% validation-MAE gain — stopping",
                     fc["patience"], fc["min_relative_gain"] * 100)
            break
    return [d for d in done if d["ok"]]


def choose(trials):
    """Best per algorithm and overall winner by validation MAE (RMSE tie-break)."""
    best = {}
    for t in trials:
        a = t["algorithm"]
        key = (t["validation"]["mae_kg"], t["validation"]["rmse_kg"])
        if a not in best or key < (best[a]["validation"]["mae_kg"], best[a]["validation"]["rmse_kg"]):
            best[a] = t
    family = {"linear_regression_raw": "linear_regression", "linear_regression_logratio": "linear_regression"}
    fam_best = {}
    for a, t in best.items():
        f = family.get(a, a)
        if f not in fam_best or t["validation"]["mae_kg"] < fam_best[f]["validation"]["mae_kg"]:
            fam_best[f] = t
    winner = min(fam_best.values(), key=lambda t: (t["validation"]["mae_kg"], t["validation"]["rmse_kg"]))
    return fam_best, winner


def final_fit(algo, params, df, cfg, seed):
    """Refit the chosen configuration on TRAIN (early stopping on VALIDATION) — test untouched until scoring."""
    fc = cfg["forecast"]
    tr, va = df[df.fsplit == "train"], df[df.fsplit == "validation"]
    model, _, _, info = fit_predict(algo, params, tr, va, seed, fc["n_jobs"], fc["xgb_early_stopping_rounds"],
                                    fc["xgb_max_estimators"])
    return model, info


def save_model(model, path):
    joblib.dump(model, path)
