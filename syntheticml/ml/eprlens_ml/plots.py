"""Diagnostic graphs (matplotlib, Agg backend). Every chart has a title, axis labels
and a legend where needed. SYNTHETIC — EPRLens Demo."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import precision_recall_curve  # noqa: E402

NOTE = "SYNTHETIC data — pipeline validation, not real-world accuracy"
C = {"main": "#1b7f4b", "alt": "#7a8ca3", "warn": "#c0392b", "amber": "#d68910", "grey": "#9aa5b1"}


def _save(fig, path):
    fig.text(0.99, 0.005, NOTE, ha="right", va="bottom", fontsize=7, color="#666")
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130)
    plt.close(fig)


# ================================================================ forecast
def forecast_plots(pred, comparison, importances, winner_name, out_dir, xgb_importances=None):
    out = Path(out_dir)
    y, p = pred["actual_kg"].to_numpy(), pred["predicted_kg"].to_numpy()
    files = []

    fig, ax = plt.subplots(figsize=(6.5, 6))
    ax.scatter(y, p, s=6, alpha=0.35, color=C["main"], label="test rows")
    lim = [max(1, min(y.min(), p.min())), max(y.max(), p.max())]
    ax.plot(lim, lim, color=C["warn"], lw=1, label="perfect forecast")
    ax.set_xscale("log"), ax.set_yscale("log")
    ax.set_xlabel("Actual next-month packaging (kg, log scale)")
    ax.set_ylabel("Predicted next-month packaging (kg, log scale)")
    ax.set_title(f"Actual vs predicted — {winner_name} (test)")
    ax.legend()
    _save(fig, out / "actual_vs_predicted.png"); files.append("actual_vs_predicted.png")

    rel = (p - y) / np.maximum(y, 1.0) * 100
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.hist(np.clip(rel, -60, 60), bins=80, color=C["main"], alpha=0.85)
    ax.axvline(0, color=C["warn"], lw=1)
    ax.set_xlabel("Forecast error (% of actual, clipped to ±60 %)")
    ax.set_ylabel("Number of test rows")
    ax.set_title("Residual distribution (test)")
    _save(fig, out / "residual_distribution.png"); files.append("residual_distribution.png")

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.scatter(p, p - y, s=5, alpha=0.3, color=C["alt"])
    ax.axhline(0, color=C["warn"], lw=1)
    ax.set_xscale("log")
    ax.set_xlabel("Predicted kg (log scale)")
    ax.set_ylabel("Residual: predicted − actual (kg)")
    ax.set_title("Residual vs prediction (test)")
    _save(fig, out / "residual_vs_prediction.png"); files.append("residual_vs_prediction.png")

    tl = pred.groupby("target_month")[["actual_kg", "predicted_kg", "last_value_kg"]].sum() / 1000.0
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(tl.index, tl["actual_kg"], marker="o", color="black", label="actual")
    ax.plot(tl.index, tl["predicted_kg"], marker="o", color=C["main"], label=winner_name)
    ax.plot(tl.index, tl["last_value_kg"], marker="o", ls="--", color=C["grey"], label="last-value baseline")
    ax.set_xlabel("Target month")
    ax.set_ylabel("Total packaging, all test products (tonnes)")
    ax.set_title("Forecast timeline — test window (all companies)")
    ax.legend()
    plt.setp(ax.get_xticklabels(), rotation=30)
    _save(fig, out / "forecast_timeline.png"); files.append("forecast_timeline.png")

    for col, fname, title in (("industry", "error_by_industry.png", "Error by industry"),
                              ("company_size", "error_by_company_size.png", "Error by company size")):
        g = pred.assign(ape=np.abs(p - y) / np.maximum(y, 1.0) * 100).groupby(col)["ape"].median().sort_values()
        b = pred.assign(ape=np.abs(pred["last_value_kg"] - y) / np.maximum(y, 1.0) * 100).groupby(col)["ape"].median()
        fig, ax = plt.subplots(figsize=(8, 4.8))
        xs = np.arange(len(g))
        ax.barh(xs - 0.2, g.values, height=0.4, color=C["main"], label=winner_name)
        ax.barh(xs + 0.2, b.reindex(g.index).values, height=0.4, color=C["grey"], label="last-value baseline")
        ax.set_yticks(xs, g.index)
        ax.set_xlabel("Median absolute % error (test)")
        ax.set_title(title + " (test)")
        ax.legend()
        _save(fig, out / fname); files.append(fname)

    imp = importances.sort_values()
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.barh(imp.index, imp.values, color=C["main"])
    ax.set_xlabel("Importance (permutation, Δ validation MAE in kg)")
    ax.set_title(f"Feature importance — {winner_name}")
    _save(fig, out / "feature_importance.png"); files.append("feature_importance.png")

    if xgb_importances is not None:
        imp = xgb_importances.sort_values().tail(20)
        fig, ax = plt.subplots(figsize=(7, 6))
        ax.barh(imp.index, imp.values, color=C["alt"])
        ax.set_xlabel("XGBoost gain importance (normalised)")
        ax.set_title("XGBoost feature importance (gain)")
        _save(fig, out / "xgboost_feature_importance.png"); files.append("xgboost_feature_importance.png")

    comp = comparison.copy()
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(comp["model"], comp["test_mae_kg"], color=[C["main"] if w else C["grey"] for w in comp["winner"]])
    ax.set_ylabel("Test MAE (kg)")
    ax.set_title("Forecast models — test MAE (lower is better)")
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    _save(fig, out / "model_comparison.png"); files.append("model_comparison.png")
    return files


# ================================================================ anomaly
def anomaly_plots(df, comp, by_type, by_group, thr_curve, thresholds, out_dir):
    """df: test records with columns y, rules, iforest_score, combined, iforest_pred, group, anomaly_type."""
    out = Path(out_dir)
    files = []
    from sklearn.metrics import confusion_matrix
    cm = confusion_matrix(df["y"], df["combined"], labels=[0, 1])
    fig, ax = plt.subplots(figsize=(5, 4.5))
    ax.imshow(cm, cmap="Greens")
    for (i, j), v in np.ndenumerate(cm):
        ax.text(j, i, f"{v:,}", ha="center", va="center", fontsize=12, color="black")
    ax.set_xticks([0, 1], ["predicted normal", "predicted anomaly"])
    ax.set_yticks([0, 1], ["actual normal", "actual anomaly"])
    ax.set_title("Confusion matrix — rules + Isolation Forest (test)")
    _save(fig, out / "confusion_matrix.png"); files.append("confusion_matrix.png")

    inv = df[df.record_type == "invoice"]
    pr, rc, _ = precision_recall_curve(inv["y"], inv["iforest_score"])
    combo_score = np.where(df["rules"] == 1, 2.0, df["iforest_score"])
    pr2, rc2, _ = precision_recall_curve(df["y"], combo_score)
    fig, ax = plt.subplots(figsize=(6.5, 5))
    ax.plot(rc, pr, color=C["alt"], label="Isolation Forest score only (invoice records)")
    ax.plot(rc2, pr2, color=C["main"], label="rules first, then IF score (all records)")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title("Precision–recall curve (test)")
    ax.legend()
    _save(fig, out / "precision_recall_curve.png"); files.append("precision_recall_curve.png")

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    bins = np.linspace(inv["iforest_score"].min(), inv["iforest_score"].max(), 60)
    for lbl, col, name in ((0, C["grey"], "normal"), (1, C["warn"], "labelled anomaly")):
        ax.hist(inv.loc[inv.y == lbl, "iforest_score"], bins=bins, alpha=0.6, color=col, label=name, density=True)
    t9 = inv[inv.anomaly_type == "AN09"]["iforest_score"]
    if len(t9):
        ax.hist(t9, bins=bins, alpha=0.6, color=C["amber"], label="AN09 spikes", density=True)
    ax.axvline(thresholds["combined"], color="black", ls="--", label="chosen threshold")
    ax.set_xlabel("Isolation Forest anomaly score (higher = more unusual)")
    ax.set_ylabel("Density")
    ax.set_title("Anomaly score distribution (test invoices)")
    ax.legend()
    _save(fig, out / "anomaly_score_distribution.png"); files.append("anomaly_score_distribution.png")

    t = pd.DataFrame(by_type).T.sort_index()
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.bar(t.index, t["recall"], color=C["main"])
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Recall (share detected)")
    ax.set_xlabel("Anomaly type")
    ax.set_title("Detection rate by anomaly type — combined system (test)")
    for i, (n, r) in enumerate(zip(t["n"], t["recall"])):
        ax.text(i, r + 0.02, f"n={int(n)}", ha="center", fontsize=7)
    _save(fig, out / "f1_by_anomaly_type.png"); files.append("f1_by_anomaly_type.png")

    g = pd.DataFrame(by_group).T
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.bar(g.index, g["fpr"] * 100, color=[C["warn"] if v > 0 else C["main"] for v in g["false_positives"]])
    for i, (fp, n) in enumerate(zip(g["false_positives"], g["n"])):
        ax.text(i, g["fpr"].iloc[i] * 100 + 0.05, f"{int(fp)} / {int(n)}", ha="center", fontsize=8)
    ax.set_ylabel("False-positive rate (%)")
    ax.set_title("False positives by kind of correct record (test)")
    plt.setp(ax.get_xticklabels(), rotation=12, ha="right")
    _save(fig, out / "false_positive_breakdown.png"); files.append("false_positive_breakdown.png")

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    x = np.arange(len(comp))
    for k, (metric, col) in enumerate((("precision", C["alt"]), ("recall", C["amber"]), ("f1", C["main"]), ("fpr", C["warn"]))):
        ax.bar(x + (k - 1.5) * 0.2, comp[metric], width=0.2, color=col, label=metric.upper())
    ax.set_xticks(x, comp["system"])
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Score (test)")
    ax.set_title("Rules vs Isolation Forest vs combined (test)")
    ax.legend(ncol=4, fontsize=8)
    _save(fig, out / "rules_vs_iforest.png"); files.append("rules_vs_iforest.png")

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.plot(thr_curve["threshold"], thr_curve["f1"], marker="o", color=C["main"], label="F1 (combined)")
    ax.plot(thr_curve["threshold"], thr_curve["fpr"], marker="o", color=C["warn"], label="FPR (combined)")
    ax.axvline(thresholds["combined"], color="black", ls="--", label="chosen on validation")
    ax.set_xlabel("Isolation Forest score threshold")
    ax.set_ylabel("Validation metric")
    ax.set_title("Threshold vs F1 / FPR (validation)")
    ax.legend()
    _save(fig, out / "threshold_vs_f1.png"); files.append("threshold_vs_f1.png")
    return files
