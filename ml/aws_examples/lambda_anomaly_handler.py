"""Reference AWS Lambda handler — EPRLens anomaly system (anomaly-v1).

Flow: receive record -> deterministic rules -> ML features -> Isolation Forest score ->
saved threshold -> combine -> JSON. NOT infrastructure.
Package with: this file + artifact folder (isolation_forest.joblib, preprocessor.joblib, threshold.json,
rules_config.json, features.py, rules.py, model_metadata.json).

Environment variables: ANOMALY_ARTIFACT_DIR, MODEL_BUCKET (s3://$MODEL_BUCKET/models/anomaly/v1/).
SYNTHETIC — EPRLens Demo.
"""
import json
import os
import sys
from pathlib import Path

ARTIFACT_FILES = ["isolation_forest.joblib", "preprocessor.joblib", "threshold.json", "rules_config.json",
                  "features.py", "rules.py", "model_metadata.json"]
_DEFAULT = Path(__file__).resolve().parents[1] / "artifacts" / "anomaly" / "v1"
_STATE = {}


def _artifact_dir():
    bucket = os.environ.get("MODEL_BUCKET")
    if bucket:
        target = Path("/tmp/models/anomaly/v1")
        if not (target / "isolation_forest.joblib").exists():
            import boto3
            s3 = boto3.client("s3")
            target.mkdir(parents=True, exist_ok=True)
            for name in ARTIFACT_FILES:
                s3.download_file(bucket, f"models/anomaly/v1/{name}", str(target / name))
        return target
    return Path(os.environ.get("ANOMALY_ARTIFACT_DIR", _DEFAULT))


def _module(path, name):
    """Import a .py file from the artifact folder under a unique module name."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _load():
    if _STATE:
        return _STATE
    import joblib
    import numpy as np
    d = _artifact_dir()
    features = _module(d / "features.py", "eprlens_anomaly_features")   # shipped inside the artifact
    rules = _module(d / "rules.py", "eprlens_anomaly_rules")
    prep = joblib.load(d / "preprocessor.joblib")
    if list(prep["feature_order"]) != list(features.FEATURES):
        raise RuntimeError("feature order in preprocessor does not match features.py")
    _STATE.update(model=joblib.load(d / "isolation_forest.joblib"), prep=prep, np=np, features=features, rules=rules,
                  threshold=json.loads((d / "threshold.json").read_text(encoding="utf-8")),
                  rules_config=json.loads((d / "rules_config.json").read_text(encoding="utf-8")),
                  meta=json.loads((d / "model_metadata.json").read_text(encoding="utf-8")))
    return _STATE


def handler(event, context=None):
    try:
        rec = event.get("body", event) if isinstance(event, dict) else event
        if isinstance(rec, str):
            rec = json.loads(rec)
        st = _load()
        st["features"].assert_no_label_fields(_all_keys(rec))
        rtype = rec.get("record_type", "invoice")
        if rtype == "invoice" and "invoice" not in rec:
            raise ValueError("invoice record needs an 'invoice' object")
        if rtype == "recycling" and "recycling" not in rec:
            raise ValueError("recycling record needs a 'recycling' object")
        findings = [f for f in st["rules"].run_rules(rec, st["rules_config"]["tolerances"]) if f["triggered"]]
        score, ml_flag = None, False
        thr = float(st["threshold"]["threshold"])
        if rtype == "invoice":
            feats = st["features"].anomaly_features(rec, st["prep"]["rate_reference_per_kg"])
            X = st["np"].asarray([st["features"].vector(feats)], dtype="float64")
            score = float(-st["model"].score_samples(X)[0])
            ml_flag = score >= thr
        return {"record_id": rec.get("record_id"), "is_anomaly": bool(findings) or ml_flag,
                "anomaly_score": None if score is None else round(score, 6), "threshold": round(thr, 6),
                "ml_flag": bool(ml_flag),
                "rule_findings": [{"rule_id": f["rule_id"], "severity": f["severity"], "reason": f["reason"]}
                                  for f in findings],
                "model_version": st["meta"]["model_version"], "status": "success"}
    except Exception as e:
        return {"status": "error", "error": f"{type(e).__name__}: {e}", "model_version": "anomaly-v1"}


def _all_keys(obj, out=None):
    out = set() if out is None else out
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.add(k)
            _all_keys(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _all_keys(v, out)
    return out


if __name__ == "__main__":
    sample = json.loads((_artifact_dir() / "sample_input.json").read_text(encoding="utf-8"))
    print(json.dumps(handler(sample), indent=2))
