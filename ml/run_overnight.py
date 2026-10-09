"""EPRLens AI — overnight synthetic ML run (restartable).

    python ml/run_overnight.py --config ml/configs/synthetic_ml.yaml
    python ml/run_overnight.py --config ml/configs/synthetic_ml.yaml --smoke        # quick end-to-end check
    python ml/run_overnight.py --config ml/configs/synthetic_ml.yaml --force        # redo every stage
    python ml/run_overnight.py --config ml/configs/synthetic_ml.yaml --force-stage export

Stages (each checkpointed in ml/runs/<run_id>/status.json; a rerun resumes after the last completed stage):
  validate, features, forecast_baselines, forecast_search, forecast_final, anomaly_search, anomaly_final,
  plots, export, aws_check, reports, notebook, pdf_guide, tests
SYNTHETIC — EPRLens Demo. Metrics on synthetic data are pipeline validation, not real-world accuracy.
"""
import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import yaml

ML = Path(__file__).resolve().parent
ROOT = ML.parent
sys.path.insert(0, str(ML))
sys.path.insert(0, str(ROOT))

from eprlens_ml import anomaly as an  # noqa: E402
from eprlens_ml import data as dt  # noqa: E402
from eprlens_ml import forecast as fc  # noqa: E402
from eprlens_ml.common import (ExperimentLog, RunState, Timer, get_logger, git_commit, read_json,  # noqa: E402
                               seed_everything, sha256_file, write_json)

STAGES = ["validate", "features", "forecast_baselines", "forecast_search", "forecast_final", "anomaly_search",
          "anomaly_final", "plots", "export", "aws_check", "reports", "notebook", "pdf_guide", "tests"]
EVAL = ML / "evaluation"


class Run:
    def __init__(self, cfg, run_dir, log):
        self.cfg, self.dir, self.log = cfg, run_dir, log
        self.seed = cfg["seed"]
        self.elog = ExperimentLog(run_dir / "experiment_log.csv")
        for sub in ("forecast", "anomaly", "plots", "artifacts", "logs"):
            (run_dir / sub).mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ data
    def validate(self):
        res = dt.validate_dataset(self.cfg, self.log)
        write_json(res, self.dir / "validation.json")
        return {"dataset_sha256": res["dataset_sha256"]}

    def features(self):
        import joblib
        df, season = dt.build_forecast_frame(self.cfg)
        df.to_csv(self.dir / "forecast" / "features.csv", index=False)
        write_json(season, self.dir / "forecast" / "season.json")
        splits = __import__("pandas").read_csv(ROOT / self.cfg["data_dir"] / "csv" / "splits.csv")
        train_companies = set(splits[splits.anomaly_split == "train"].company_id)
        records, rate_ref, (labels, gt, sp) = dt.build_records(self.cfg, train_companies)
        lab = dt.build_labels(records, labels, gt, sp)
        feat = dt.anomaly_feature_table(records, rate_ref)
        joblib.dump(records, self.dir / "anomaly" / "records.joblib", compress=3)
        lab.to_csv(self.dir / "anomaly" / "labels.csv", index=False)
        feat.to_csv(self.dir / "anomaly" / "features.csv", index=False)
        write_json(rate_ref, self.dir / "anomaly" / "rate_reference.json")
        self.log.info(f"forecast rows {len(df)} ({df.fsplit.value_counts().to_dict()}); anomaly records {len(records)}")
        return {"forecast_rows": len(df), "anomaly_records": len(records)}

    def fdf(self):
        import pandas as pd
        return pd.read_csv(self.dir / "forecast" / "features.csv")

    # ------------------------------------------------------------------ forecast
    def forecast_baselines(self):
        df = self.fdf()
        out = {}
        for split in ("train", "validation"):
            d = df[df.fsplit == split]
            sn, has = fc.baseline_seasonal_naive(d)
            out[split] = {"F0_last_value": fc.metrics(d[fc.TARGET], fc.baseline_last_value(d)),
                          "F1_seasonal_naive_with_fallback": fc.metrics(d[fc.TARGET], sn),
                          "F1_seasonal_naive_rows_with_history": fc.metrics(d[fc.TARGET][has], sn[has])}
        for name in ("F0_last_value", "F1_seasonal_naive_with_fallback"):
            self.elog.add("forecast", name, {}, out["train"][name]["mae_kg"], out["validation"][name], notes="baseline")
        write_json(out, self.dir / "forecast" / "baselines.json")
        v = out["validation"]["F0_last_value"]
        self.log.info(f"F0 last-value validation: MAE {v['mae_kg']:.1f} kg RMSE {v['rmse_kg']:.1f} R2 {v['r2']:.4f}")
        return {}

    def forecast_search(self):
        trials = fc.run_search(self.dir / "forecast", self.fdf(), self.cfg, self.seed, self.elog, self.log, None)
        return {"trials": len(trials)}

    def forecast_final(self):
        import numpy as np
        import pandas as pd
        df = self.fdf()
        trials = [json.loads(x) for x in (self.dir / "forecast" / "trials.jsonl").read_text(encoding="utf-8").splitlines()]
        ok = [t for t in trials if t.get("ok")]
        fam_best, winner = fc.choose(ok)
        te = df[df.fsplit == "test"]
        va = df[df.fsplit == "validation"]
        base = read_json(self.dir / "forecast" / "baselines.json")
        rows, test_metrics, models = [], {}, {}
        sn, _ = fc.baseline_seasonal_naive(te)
        f0 = fc.metrics(te[fc.TARGET], fc.baseline_last_value(te))
        f1 = fc.metrics(te[fc.TARGET], sn)
        rows.append({"model": "F0 last value", "algorithm": "baseline", **_cmp(base["validation"]["F0_last_value"], f0)})
        rows.append({"model": "F1 seasonal naive", "algorithm": "baseline",
                     **_cmp(base["validation"]["F1_seasonal_naive_with_fallback"], f1)})
        names = {"linear_regression": "F2 Linear Regression", "random_forest": "F3 Random Forest", "xgboost": "F4 XGBoost"}
        preds = {}
        for fam in ("linear_regression", "random_forest", "xgboost"):
            t = fam_best[fam]
            with Timer() as tm:
                model, info = fc.final_fit(t["algorithm"], t["params"], df, self.cfg, self.seed)
            p = fc.predict_kg(t["algorithm"], model, te)
            preds[fam] = p
            m = fc.metrics(te[fc.TARGET], p)
            test_metrics[t["experiment_id"]] = m
            models[fam] = (t, model)
            rows.append({"model": names[fam], "algorithm": t["algorithm"], **_cmp(t["validation"], m),
                         "params": json.dumps(t["params"]), "experiment_id": t["experiment_id"]})
            self.log.info(f"final {names[fam]}: test MAE {m['mae_kg']:.1f} RMSE {m['rmse_kg']:.1f} R2 {m['r2']:.4f}")
        win_fam = "linear_regression" if winner["algorithm"].startswith("linear") else winner["algorithm"]
        comp = pd.DataFrame(rows)
        comp["winner"] = comp["model"] == names[win_fam]
        comp["test_mae_improvement_vs_last_value_pct"] = (1 - comp["test_mae_kg"] / f0["mae_kg"]) * 100
        self.elog.mark_selected(list(test_metrics), test_metrics)
        t_win, model = models[win_fam]
        p = preds[win_fam]
        pred = te[["company_id", "product_id", "industry", "company_size", "month", "target_month", "company_holdout"]].copy()
        pred["actual_kg"] = te[fc.TARGET].to_numpy()
        pred["predicted_kg"] = p
        pred["last_value_kg"] = te["packaging_kg"].to_numpy()
        pred.to_csv(self.dir / "forecast" / "test_predictions.csv", index=False)
        seen = pred[~pred.company_holdout]
        held = pred[pred.company_holdout]
        breakdown = {"seen_companies": fc.metrics(seen.actual_kg, seen.predicted_kg),
                     "held_out_companies": fc.metrics(held.actual_kg, held.predicted_kg),
                     "last_value_seen": fc.metrics(seen.actual_kg, seen.last_value_kg),
                     "last_value_held_out": fc.metrics(held.actual_kg, held.last_value_kg)}
        # permutation importance on VALIDATION (kg MAE increase)
        rng = np.random.default_rng(self.seed)
        base_mae = fc.metrics(va[fc.TARGET], fc.predict_kg(t_win["algorithm"], model, va))["mae_kg"]
        imp = {}
        if t_win["algorithm"] != "linear_regression_raw":
            for col in fc.ff.FEATURES:
                v2 = va.copy()
                v2[col] = rng.permutation(v2[col].to_numpy())
                imp[col] = fc.metrics(va[fc.TARGET], fc.predict_kg(t_win["algorithm"], model, v2))["mae_kg"] - base_mae
        xgb_imp = None
        if t_win["algorithm"] == "xgboost":
            g = model.get_booster().get_score(importance_type="gain")
            tot = sum(g.values()) or 1.0
            xgb_imp = {fc.ff.FEATURES[int(k[1:])] if k.startswith("f") and k[1:].isdigit() else k: v / tot for k, v in g.items()}
        import joblib
        joblib.dump(model, self.dir / "forecast" / "model.joblib")
        target_ok = comp.loc[comp.winner, "test_r2"].iloc[0] >= self.cfg["forecast"]["desired_test_r2"]
        n_trials = len(trials)
        final = {"winner": {"family": win_fam, "algorithm": t_win["algorithm"], "params": t_win["params"],
                            "experiment_id": t_win["experiment_id"], "validation": t_win["validation"],
                            "test": test_metrics[t_win["experiment_id"]], "info": t_win.get("info", {})},
                 "test_baselines": {"F0_last_value": f0, "F1_seasonal_naive_with_fallback": f1},
                 "test_breakdown": breakdown, "target_r2": self.cfg["forecast"]["desired_test_r2"],
                 "target_met": bool(target_ok), "experiments": n_trials,
                 "experiments_by_algorithm": pd.Series([t["algorithm"] for t in trials]).value_counts().to_dict(),
                 "permutation_importance_val_mae_kg": imp, "xgb_gain_importance": xgb_imp,
                 "split": {"train_rows": int((df.fsplit == "train").sum()), "validation_rows": int(len(va)),
                           "test_rows": int(len(te)), "unused_holdout_window_rows": int((df.fsplit == "unused_holdout_window").sum()),
                           "train_companies": int(df[df.fsplit == "train"].company_id.nunique()),
                           "test_companies": int(te.company_id.nunique()),
                           "held_out_companies": int(df[df.company_holdout].company_id.nunique())}}
        write_json(final, self.dir / "forecast" / "final.json")
        comp.to_csv(self.dir / "forecast" / "model_comparison.csv", index=False)
        self.log.info(f"FORECAST WINNER {names[win_fam]} — test R2 {final['winner']['test']['r2']:.4f} "
                      f"({'TARGET MET' if target_ok else 'TARGET NOT REACHED'})")
        return {"winner": win_fam}

    # ------------------------------------------------------------------ anomaly
    def _anomaly_inputs(self):
        import joblib
        import pandas as pd
        records = joblib.load(self.dir / "anomaly" / "records.joblib")
        lab = pd.read_csv(self.dir / "anomaly" / "labels.csv", keep_default_na=False, na_values=[""])
        feat = pd.read_csv(self.dir / "anomaly" / "features.csv")
        return records, lab, feat

    def anomaly_search(self):
        records, lab, feat = self._anomaly_inputs()
        tol, *_rest, trials = an.run(self.dir / "anomaly", records, lab, feat, self.cfg, self.seed, self.elog, self.log)
        write_json({"rules_tolerance": tol}, self.dir / "anomaly" / "rules_choice.json")
        return {"trials": len(trials)}

    def anomaly_final(self):
        import joblib
        import numpy as np
        import pandas as pd
        records, lab, feat = self._anomaly_inputs()
        tol, rmat, rpred, feat_index, X, trials = an.run(self.dir / "anomaly", records, lab, feat, self.cfg, self.seed,
                                                         self.elog, self.log)
        best = an.select(trials)
        params = best["params"]
        split = lab.split.to_numpy()
        fsplit = split[feat_index]
        clean_tr = np.array([split[i] == "train" and rpred[i] == 0 for i in feat_index])
        Xtr = X[clean_tr] if params["fit_on"] == "rules_clean" else X[fsplit == "train"]
        model = an.fit_if(params, Xtr, self.seed)
        s = an.full_scores(lab, feat_index, an.if_scores(model, X))
        t_c, t_i = best["threshold_combined"], best["threshold_iforest"]
        y = lab.y.to_numpy()
        preds = {"rules_only": rpred, "iforest_only": (s >= t_i).astype(int),
                 "rules_plus_iforest": np.maximum(rpred, (s >= t_c).astype(int))}
        out = {}
        for name, p in preds.items():
            out[name] = {sp: an.binary_metrics(y[split == sp], p[split == sp]) for sp in ("train", "validation", "test")}
        # system selection on VALIDATION
        cand = {k: v["validation"] for k, v in out.items()}
        chosen = max(cand, key=lambda k: (cand[k]["fpr"] <= self.cfg["anomaly"]["max_fpr"], cand[k]["f1"], -cand[k]["fpr"]))
        te = lab[lab.split == "test"]
        detail = {}
        for name, p in preds.items():
            bt, bg = an.breakdown(te, pd.Series(p, index=lab.index))
            detail[name] = {"by_anomaly_type": bt, "by_normal_group": bg}
        cur = []
        cand_t = np.quantile(s[(split == "train") & (lab.record_type == "invoice").to_numpy()],
                             self.cfg["anomaly"]["threshold_quantiles"])
        for t in cand_t:
            m = an.binary_metrics(y[split == "validation"], np.maximum(rpred, (s >= t).astype(int))[split == "validation"])
            cur.append({"threshold": float(t), "f1": m["f1"], "fpr": m["fpr"], "precision": m["precision"], "recall": m["recall"]})
        pd.DataFrame(cur).to_csv(self.dir / "anomaly" / "threshold_curve_validation.csv", index=False)
        scores = lab.copy()
        scores["rules"] = rpred
        scores["rule_ids"] = ["|".join(r) for r in rmat]
        scores["iforest_score"] = s
        scores["iforest_pred"] = preds["iforest_only"]
        scores["combined"] = preds["rules_plus_iforest"]
        scores.to_csv(self.dir / "anomaly" / "all_scores.csv", index=False)
        joblib.dump(model, self.dir / "anomaly" / "model.joblib")
        self.elog.mark_selected([best["experiment_id"]], {best["experiment_id"]: out["rules_plus_iforest"]["test"]})
        test = out[chosen]["test"]
        final = {"chosen_system": chosen, "chosen_on": "validation", "params": params, "rules_tolerance": tol,
                 "thresholds": {"combined": t_c, "iforest": t_i}, "experiment_id": best["experiment_id"],
                 "systems": out, "detail_test": detail, "target_f1": self.cfg["anomaly"]["desired_test_f1"],
                 "max_fpr": self.cfg["anomaly"]["max_fpr"],
                 "target_met": bool(test["f1"] >= self.cfg["anomaly"]["desired_test_f1"] and test["fpr"] <= self.cfg["anomaly"]["max_fpr"]),
                 "experiments": len(trials) + len(an.RULE_TOLERANCES),
                 "units": {"invoice_records": int((lab.record_type == "invoice").sum()),
                           "recycling_records": int((lab.record_type == "recycling").sum()),
                           "by_split": lab.split.value_counts().to_dict()}}
        write_json(final, self.dir / "anomaly" / "final.json")
        rows = []
        for name in ("rules_only", "iforest_only", "rules_plus_iforest"):
            v, t = out[name]["validation"], out[name]["test"]
            rows.append({"system": name, "val_precision": v["precision"], "val_recall": v["recall"], "val_f1": v["f1"],
                         "val_fpr": v["fpr"], "precision": t["precision"], "recall": t["recall"], "f1": t["f1"],
                         "specificity": t["specificity"], "fpr": t["fpr"], "tp": t["tp"], "fp": t["fp"], "tn": t["tn"],
                         "fn": t["fn"], "selected": name == chosen})
        pd.DataFrame(rows).to_csv(self.dir / "anomaly" / "model_comparison.csv", index=False)
        self.log.info(f"ANOMALY SYSTEM {chosen} — test P {test['precision']:.3f} R {test['recall']:.3f} F1 {test['f1']:.3f} "
                      f"FPR {test['fpr']:.4f} ({'TARGET MET' if final['target_met'] else 'TARGET NOT REACHED'})")
        return {"chosen": chosen}

    # ------------------------------------------------------------------ outputs
    def plots(self):
        import pandas as pd
        from eprlens_ml import plots
        ff_final = read_json(self.dir / "forecast" / "final.json")
        comp = pd.read_csv(self.dir / "forecast" / "model_comparison.csv")
        pred = pd.read_csv(self.dir / "forecast" / "test_predictions.csv")
        imp = pd.Series(ff_final["permutation_importance_val_mae_kg"]).sort_values().tail(20)
        xgb = pd.Series(ff_final["xgb_gain_importance"]) if ff_final["xgb_gain_importance"] else None
        name = {"linear_regression": "Linear Regression", "random_forest": "Random Forest", "xgboost": "XGBoost"}[ff_final["winner"]["family"]]
        f_files = plots.forecast_plots(pred, comp, imp, name, self.dir / "plots" / "forecast", xgb)
        a_final = read_json(self.dir / "anomaly" / "final.json")
        scores = pd.read_csv(self.dir / "anomaly" / "all_scores.csv", keep_default_na=False, na_values=[""])
        te = scores[scores.split == "test"].copy()
        acomp = pd.read_csv(self.dir / "anomaly" / "model_comparison.csv")
        sysd = a_final["detail_test"]["rules_plus_iforest"]
        curve = pd.read_csv(self.dir / "anomaly" / "threshold_curve_validation.csv")
        a_files = plots.anomaly_plots(te, acomp, sysd["by_anomaly_type"], sysd["by_normal_group"], curve,
                                      a_final["thresholds"], self.dir / "plots" / "anomaly")
        return {"forecast_plots": f_files, "anomaly_plots": a_files}

    def export(self):
        import joblib
        import numpy as np
        import pandas as pd
        from eprlens_ml import export as ex
        git = git_commit()
        sha = read_json(self.dir / "validation.json")["dataset_sha256"]
        f_final = read_json(self.dir / "forecast" / "final.json")
        df = self.fdf()
        season = read_json(self.dir / "forecast" / "season.json")
        model = joblib.load(self.dir / "forecast" / "model.joblib")
        winner = {"algorithm": f_final["winner"]["algorithm"], "params": f_final["winner"]["params"]}
        fmetrics = {"validation": f_final["winner"]["validation"], "test": f_final["winner"]["test"],
                    "test_last_value_baseline": f_final["test_baselines"]["F0_last_value"],
                    "test_breakdown": f_final["test_breakdown"], "target_r2": f_final["target_r2"],
                    "target_met": f_final["target_met"]}
        fdir, _ = ex.export_forecast(self.cfg, self.dir, winner, model, season, df, fmetrics, self.log, git, sha)
        a_final = read_json(self.dir / "anomaly" / "final.json")
        records, lab, feat = self._anomaly_inputs()
        amodel = joblib.load(self.dir / "anomaly" / "model.joblib")
        rate_ref = read_json(self.dir / "anomaly" / "rate_reference.json")
        gt = pd.read_csv(ROOT / self.cfg["data_dir"] / "csv" / "anomaly_ground_truth.csv", keep_default_na=False, na_values=[""])
        demo_inv = gt[gt.note.astype(str).str.startswith("DEMO")].invoice_id.iloc[0]
        sample = next(r for r in records if r["record_id"] == demo_inv)
        X_check = feat[an.af.FEATURES].to_numpy(float)[:2000]
        counts = {"training_rows": int(((lab.split == "train") & (lab.record_type == "invoice")).sum()),
                  "validation_rows": int((lab.split == "validation").sum()), "test_rows": int((lab.split == "test").sum())}
        ametrics = {"chosen_system": a_final["chosen_system"], "test": a_final["systems"][a_final["chosen_system"]]["test"],
                    "validation": a_final["systems"][a_final["chosen_system"]]["validation"],
                    "systems_test": {k: v["test"] for k, v in a_final["systems"].items()},
                    "target_f1": a_final["target_f1"], "target_met": a_final["target_met"]}
        adir = ex.export_anomaly(self.cfg, amodel, a_final["params"], rate_ref, a_final["rules_tolerance"],
                                 a_final["thresholds"], ametrics, counts, sample, X_check, self.log, git, sha)
        # sample outputs through the reference Lambda handlers (exactly what AWS will run)
        import os
        os.environ["FORECAST_ARTIFACT_DIR"], os.environ["ANOMALY_ARTIFACT_DIR"] = str(fdir), str(adir)
        sys.path.insert(0, str(ML / "aws_examples"))
        import importlib
        import lambda_anomaly_handler as lah
        import lambda_forecast_handler as lfh
        importlib.reload(lfh), importlib.reload(lah)
        lfh._STATE.clear(), lah._STATE.clear()
        fout = lfh.handler(read_json(fdir / "sample_input.json"))
        aout = lah.handler(read_json(adir / "sample_input.json"))
        assert fout["status"] == "success" and aout["status"] == "success", (fout, aout)
        write_json(fout, fdir / "sample_output.json")
        write_json(aout, adir / "sample_output.json")
        ex.finalize_hashes(fdir)
        ex.finalize_hashes(adir)
        del np
        return {"forecast_dir": str(fdir.relative_to(ROOT)), "anomaly_dir": str(adir.relative_to(ROOT))}

    def aws_check(self):
        report = _aws_report(self.cfg, self.log)
        write_json(report, EVAL / "aws_artifact_report.json")
        return {"forecast_model_mb": report["forecast_model_mb"], "anomaly_model_mb": report["anomaly_model_mb"]}

    def reports(self):
        from eprlens_ml import reports
        reports.publish_evaluation(self.dir, EVAL, ROOT, self.cfg)
        return {}

    def notebook(self):
        from eprlens_ml import notebook_builder
        path = notebook_builder.build_and_execute(self.dir, self.cfg, self.log)
        return {"notebook": str(path.relative_to(ROOT))}

    def pdf_guide(self):
        from eprlens_ml import pdf_guide
        path = pdf_guide.build(self.dir, self.cfg)
        return {"pdf": str(path.relative_to(ROOT))}

    def tests(self):
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/ml", "-p", "no:cacheprovider"], cwd=ROOT,
                           capture_output=True, text=True)
        tail = (r.stdout or "").strip().splitlines()[-3:]
        self.log.info("ML tests: " + " | ".join(tail))
        (self.dir / "logs" / "pytest_ml.txt").write_text(r.stdout + r.stderr, encoding="utf-8")
        if r.returncode != 0:
            raise RuntimeError("ML test suite failed — see logs/pytest_ml.txt")
        return {"summary": tail[-1] if tail else ""}


def _cmp(v, t):
    return {"val_mae_kg": v["mae_kg"], "val_rmse_kg": v["rmse_kg"], "val_r2": v["r2"], "test_mae_kg": t["mae_kg"],
            "test_rmse_kg": t["rmse_kg"], "test_r2": t["r2"], "test_r2_log": t["r2_log"],
            "test_mape_pct": t["mape_pct_y_gt_1kg"], "test_median_ape_pct": t["median_ape_pct"]}


def _dir_mb(paths):
    total = 0
    for p in paths:
        p = Path(p)
        if p.is_file():
            total += p.stat().st_size
        elif p.exists():
            total += sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
    return round(total / 1e6, 1)


def _aws_report(cfg, log):
    import site
    sp = Path(site.getsitepackages()[-1]) if site.getsitepackages() else Path(sys.prefix) / "Lib" / "site-packages"
    cands = [Path(p) for p in site.getsitepackages()]
    sp = next((p for p in cands if (p / "numpy").exists()), sp)
    pkg_dirs = {"onnxruntime": ["onnxruntime"], "numpy": ["numpy", "numpy.libs"], "joblib": ["joblib"],
                "scikit-learn": ["sklearn"], "scipy": ["scipy", "scipy.libs"], "xgboost": ["xgboost"]}
    fdir, adir = ROOT / cfg["export"]["forecast_dir"], ROOT / cfg["export"]["anomaly_dir"]
    fmeta, ameta = read_json(fdir / "model_metadata.json"), read_json(adir / "model_metadata.json")
    freq = [l.split("==")[0] for l in (fdir / "requirements-lambda.txt").read_text().split() if l]
    areq = [l.split("==")[0] for l in (adir / "requirements-lambda.txt").read_text().split() if l]

    def deps(reqs):
        return {r: _dir_mb([sp / d for d in pkg_dirs.get(r, [r])]) for r in reqs}

    timing = {}
    for name, script in (("forecast", "lambda_forecast_handler"), ("anomaly", "lambda_anomaly_handler")):
        code = (f"import sys,time,json;sys.path.insert(0,r'{ML / 'aws_examples'}');t0=time.perf_counter();"
                f"import {script} as h;s=h._artifact_dir();h._load();t1=time.perf_counter();"
                f"req=json.loads((s/'sample_input.json').read_text(encoding='utf-8'));ts=[];"
                f"[ts.append((lambda a:(h.handler(req),time.perf_counter()-a)[1])(time.perf_counter())) for _ in range({cfg['export']['timing_repeats']})];"
                f"print(json.dumps({{'load_ms':(t1-t0)*1000,'infer_ms_median':sorted(ts)[len(ts)//2]*1000,'infer_ms_max':max(ts)*1000}}))")
        env = dict(__import__("os").environ, FORECAST_ARTIFACT_DIR=str(fdir), ANOMALY_ARTIFACT_DIR=str(adir))
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=ROOT, env=env)
        timing[name] = json.loads(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 else {"error": r.stderr[-500:]}
    f_model = fdir / fmeta["model_file"]
    rep = {
        "note": ("All timings are measured on the LOCAL development machine (Windows, Python 3.12) in a fresh process, "
                 "not on AWS. Dependency sizes are local installed sizes (Windows wheels); Linux/Lambda wheels differ."),
        "forecast_model_file": fmeta["model_file"], "forecast_model_mb": round(f_model.stat().st_size / 1e6, 3),
        "forecast_artifact_folder_mb": _dir_mb([fdir]), "forecast_dependencies": deps(freq),
        "forecast_dependencies_total_mb": round(sum(deps(freq).values()), 1),
        "anomaly_model_file": "isolation_forest.joblib",
        "anomaly_model_mb": round((adir / "isolation_forest.joblib").stat().st_size / 1e6, 3),
        "anomaly_artifact_folder_mb": _dir_mb([adir]), "anomaly_dependencies": deps(areq),
        "anomaly_dependencies_total_mb": round(sum(deps(areq).values()), 1),
        "anomaly_onnx_available": (adir / "isolation_forest.onnx").exists(),
        "measured_local_load_time_ms": {k: round(v.get("load_ms", -1), 1) for k, v in timing.items()},
        "measured_local_inference_time_ms": {k: {"median": round(v.get("infer_ms_median", -1), 2),
                                                 "max": round(v.get("infer_ms_max", -1), 2)} for k, v in timing.items()},
        "recommended_lambda_memory_mb": {"forecast": 512, "anomaly": 1024},
        "recommendation_basis": ("Starting points only: forecast uses onnxruntime+numpy (small); anomaly loads "
                                 "scikit-learn+scipy. Verify memory and cold start in AWS CloudWatch-free testing per D057."),
        "lambda_limits_reminder": "zip <= 50 MB direct upload (or via S3), <= 250 MB unzipped including layers",
        "timing_raw": timing,
    }
    log.info(f"AWS check: forecast model {rep['forecast_model_mb']} MB, anomaly model {rep['anomaly_model_mb']} MB; "
             f"local load {rep['measured_local_load_time_ms']}")
    return rep


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=str(ML / "configs" / "synthetic_ml.yaml"))
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--force", action="store_true", help="redo every stage")
    ap.add_argument("--force-stage", action="append", default=[], help="redo one stage (repeatable)")
    ap.add_argument("--until", default=None, help="stop after this stage")
    ap.add_argument("--smoke", action="store_true", help="tiny budgets in a separate run folder (end-to-end check)")
    args = ap.parse_args()
    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    run_id = args.run_id or cfg["run_id"]
    if args.smoke:
        run_id += "-smoke"
        cfg["forecast"].update(budget_configs=6, rf_configs=1, patience=3)
        cfg["anomaly"].update(budget_configs=5, patience=3)
        cfg["export"]["forecast_dir"] = f"ml/runs/{run_id}/artifacts/forecast/v1"
        cfg["export"]["anomaly_dir"] = f"ml/runs/{run_id}/artifacts/anomaly/v1"
    run_dir = ML / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    log = get_logger([ML / "logs" / "overnight.log", run_dir / "logs" / "run.log"])
    write_json({"config": cfg, "config_file": str(Path(args.config)), "config_sha256": sha256_file(args.config),
                "run_id": run_id, "git_commit": git_commit()}, run_dir / "config.json")
    seed_everything(cfg["seed"])
    state = RunState(run_dir)
    run = Run(cfg, run_dir, log)
    stages = STAGES if not args.smoke else [s for s in STAGES if s not in ("reports", "notebook", "pdf_guide", "tests")]
    t_all = time.time()
    log.info(f"=== EPRLens overnight ML run '{run_id}' — {len(stages)} stages ===")
    for stage in stages:
        if state.done(stage) and not args.force and stage not in args.force_stage:
            log.info(f"[skip] {stage} (completed {state.data['stages'][stage]['at']})")
        else:
            log.info(f"[start] {stage}")
            state.mark(stage, "running")
            t0 = time.time()
            try:
                info = getattr(run, stage)() or {}
            except Exception as e:
                state.mark(stage, "failed", error=repr(e))
                log.exception(f"[failed] {stage}: {e!r}")
                raise SystemExit(1)
            state.mark(stage, "completed", seconds=round(time.time() - t0, 1), **{k: v for k, v in info.items()
                                                                                    if isinstance(v, (str, int, float, bool, list, dict))})
            log.info(f"[done] {stage} in {time.time() - t0:.1f}s {info if len(str(info)) < 300 else ''}")
        if args.until == stage:
            break
    shutil.copy2(run_dir / "experiment_log.csv", run_dir / "experiment_log.snapshot.csv")
    log.info(f"=== run finished in {time.time() - t_all:.1f}s — status {run_dir / 'status.json'} ===")


if __name__ == "__main__":
    main()
