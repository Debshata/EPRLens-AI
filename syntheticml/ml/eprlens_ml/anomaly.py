"""Anomaly experiments: rules (layer 1) + Isolation Forest (layer 2).
All tuning on the VALIDATION companies; one final evaluation on TEST companies.
SYNTHETIC — EPRLens Demo."""
import json
import time

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import ParameterSampler

from . import anomaly_features as af
from rules import anomaly_rules as ar

IF_SPACE = {"n_estimators": [100, 200, 300, 500], "max_samples": [256, 512, 1024, 2048, "auto"],
            "max_features": [0.5, 0.7, 0.85, 1.0], "bootstrap": [False, True], "fit_on": ["all", "rules_clean"]}
RULE_TOLERANCES = [{"qty_tolerance_kg": 0.5, "qty_tolerance_rel": 0.005},
                   {"qty_tolerance_kg": 0.1, "qty_tolerance_rel": 0.001},
                   {"qty_tolerance_kg": 0.01, "qty_tolerance_rel": 0.0005}]


# ----------------------------------------------------------------- metrics
def binary_metrics(y, p):
    y, p = np.asarray(y, int), np.asarray(p, int)
    tp = int(((p == 1) & (y == 1)).sum())
    fp = int(((p == 1) & (y == 0)).sum())
    tn = int(((p == 0) & (y == 0)).sum())
    fn = int(((p == 0) & (y == 1)).sum())
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    spec = tn / (tn + fp) if tn + fp else 0.0
    return {"precision": prec, "recall": rec, "f1": f1, "specificity": spec, "fpr": 1 - spec if tn + fp else 0.0,
            "tp": tp, "fp": fp, "tn": tn, "fn": fn, "n": int(len(y)), "positives": int(y.sum())}


def breakdown(lab, pred):
    by_type = {}
    for at, g in lab[lab.y == 1].groupby("anomaly_type"):
        hit = pred[g.index].sum()
        by_type[at] = {"n": int(len(g)), "detected": int(hit), "recall": float(hit / len(g))}
    by_group = {}
    for grp, g in lab[lab.y == 0].groupby("group"):
        fp = int(pred[g.index].sum())
        by_group[grp] = {"n": int(len(g)), "false_positives": fp, "fpr": float(fp / len(g)) if len(g) else 0.0}
    return by_type, by_group


# ----------------------------------------------------------------- rules
def rule_matrix(records, tol):
    """Per record: list of triggered rule ids."""
    out = []
    for r in records:
        out.append([f["rule_id"] for f in ar.run_rules(r, tol) if f["triggered"]])
    return out


# ----------------------------------------------------------------- isolation forest
def fit_if(params, X_train, seed):
    p = {k: v for k, v in params.items() if k != "fit_on"}
    m = IsolationForest(random_state=seed % (2**31), n_jobs=-1, contamination="auto", **p)
    m.fit(X_train)
    return m


def if_scores(model, X):
    return -model.score_samples(X)          # higher = more unusual, in (0, 1]


def full_scores(lab, feat_index, scores):
    """Map invoice-record scores onto all records (recycling records have no IF score → 0)."""
    s = np.zeros(len(lab))
    s[feat_index] = scores
    return s


def best_threshold(y, rules_pred, scores, cand, max_fpr, mode):
    """Pick a threshold on VALIDATION. mode 'combined' = rules OR score>=t ; 'iforest' = score>=t only."""
    best = None
    for t in cand:
        p = (scores >= t).astype(int)
        if mode == "combined":
            p = np.maximum(p, rules_pred)
        m = binary_metrics(y, p)
        ok = m["fpr"] <= max_fpr
        key = (ok, m["f1"], -m["fpr"])
        if best is None or key > best[0]:
            best = (key, float(t), m)
    return best[1], best[2]


def run(stage_dir, records, lab, feat, cfg, seed, elog, log):
    ac = cfg["anomaly"]
    lab = lab.reset_index(drop=True)
    idx_of = {rid: i for i, rid in enumerate(lab.record_id)}
    feat_index = np.array([idx_of[r] for r in feat.record_id])
    X = feat[af.FEATURES].to_numpy(float)
    af.assert_no_label_fields(af.FEATURES)
    af.assert_no_label_fields(list(feat.columns))
    split = lab.split.to_numpy()
    fsplit = split[feat_index]
    is_val, is_tr = split == "validation", split == "train"
    y = lab.y.to_numpy()

    trials_path = stage_dir / "trials.jsonl"
    done = [json.loads(x) for x in trials_path.read_text(encoding="utf-8").splitlines()] if trials_path.exists() else []

    def save(res):
        with trials_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(res, default=float) + "\n")
        done.append(res)

    # ---- (1) rule tolerance chosen on validation
    rule_cache = {}
    best_rules = None
    for tol in RULE_TOLERANCES:
        t0 = time.time()
        rm = rule_matrix(records, tol)
        rp = np.array([1 if r else 0 for r in rm])
        rule_cache[json.dumps(tol)] = (rm, rp)
        mv = binary_metrics(y[is_val], rp[is_val])
        prev = next((d for d in done if d["kind"] == "rules" and d["params"] == tol), None)
        if prev is None:
            eid = elog.add("anomaly", "rules", tol, binary_metrics(y[is_tr], rp[is_tr])["f1"], mv,
                           duration=time.time() - t0, notes="deterministic rules; tolerance chosen on validation")
            save({"kind": "rules", "params": tol, "validation": mv, "experiment_id": eid})
        log.info(f"  rules tol={tol}: val P {mv['precision']:.3f} R {mv['recall']:.3f} F1 {mv['f1']:.3f} FPR {mv['fpr']:.4f}")
        key = (mv["fpr"] <= ac["max_fpr"], mv["f1"], tol["qty_tolerance_kg"])
        if best_rules is None or key > best_rules[0]:
            best_rules = (key, tol)
    tol = best_rules[1]
    rmat, rpred = rule_cache[json.dumps(tol)]

    # ---- (2) Isolation Forest search
    n_rules = len(RULE_TOLERANCES)
    budget = ac["budget_configs"] - n_rules
    rules_clean_train = np.array([is_tr[i] and rpred[i] == 0 for i in feat_index])
    best_f1, stall = -1.0, 0
    for p in ParameterSampler(IF_SPACE, n_iter=budget, random_state=seed % (2**31)):
        params = {k: (int(v) if isinstance(v, (np.integer,)) else (float(v) if isinstance(v, np.floating) else v))
                  for k, v in p.items()}
        prev = next((d for d in done if d["kind"] == "iforest" and d["params"] == params), None)
        if prev is None:
            t0 = time.time()
            try:
                Xtr = X[rules_clean_train] if params["fit_on"] == "rules_clean" else X[fsplit == "train"]
                model = fit_if(params, Xtr, seed)
                s = full_scores(lab, feat_index, if_scores(model, X))
                cand = np.quantile(s[is_tr & (lab.record_type == "invoice").to_numpy()], ac["threshold_quantiles"])
                t_c, m_c = best_threshold(y[is_val], rpred[is_val], s[is_val], cand, ac["max_fpr"], "combined")
                t_i, m_i = best_threshold(y[is_val], np.zeros(is_val.sum(), int), s[is_val], cand, ac["max_fpr"], "iforest")
                res = {"kind": "iforest", "params": params, "ok": True, "threshold_combined": t_c,
                       "threshold_iforest": t_i, "validation_combined": m_c, "validation_iforest": m_i,
                       "seconds": round(time.time() - t0, 2)}
            except Exception as e:
                res = {"kind": "iforest", "params": params, "ok": False, "error": repr(e), "seconds": 0}
            res["experiment_id"] = elog.add("anomaly", "isolation_forest+rules", {**params, "rules": tol,
                                                                                  "threshold": res.get("threshold_combined")},
                                            None, res.get("validation_combined"), duration=res["seconds"],
                                            notes="threshold chosen on validation (max FPR %.2f)" % ac["max_fpr"]
                                            if res["ok"] else "FAILED " + res["error"])
            save(res)
            prev = res
            if res["ok"]:
                mc = res["validation_combined"]
                log.info(f"  [{res['experiment_id']}] IF {params} val combined F1 {mc['f1']:.4f} FPR {mc['fpr']:.4f} "
                         f"| IF-only F1 {res['validation_iforest']['f1']:.4f}")
        if not prev.get("ok"):
            stall += 1
            continue
        f1 = prev["validation_combined"]["f1"]
        if f1 > best_f1 + ac["min_f1_gain"]:
            best_f1, stall = f1, 0
        else:
            stall += 1
        if stall >= ac["patience"]:
            log.info("anomaly search: %d consecutive configurations without validation-F1 gain — stopping", ac["patience"])
            break
    return tol, rmat, rpred, feat_index, X, [d for d in done if d.get("kind") == "iforest" and d.get("ok")]


def select(trials):
    return max(trials, key=lambda d: (d["validation_combined"]["fpr"] <= 0.10, d["validation_combined"]["f1"],
                                      -d["validation_combined"]["fpr"], d["validation_iforest"]["f1"]))
