"""Reference AWS Lambda handler — EPRLens forecast model (forecast-v1).

NOT infrastructure: it only shows load -> validate -> features -> predict -> JSON.
Package with: this file + the artifact folder (model.onnx or model.joblib, preprocessor.joblib, features.py).

Environment variables:
  FORECAST_ARTIFACT_DIR  local folder with the artifact (default: ml/artifacts/forecast/v1 in the repo,
                         or /tmp/models/forecast/v1 after an S3 download)
  MODEL_BUCKET           optional: if set, files are downloaded once per cold start from
                         s3://$MODEL_BUCKET/models/forecast/v1/  (needs s3:GetObject)
SYNTHETIC — EPRLens Demo.
"""
import json
import os
import sys
from pathlib import Path

ARTIFACT_FILES = ["model.onnx", "model.joblib", "preprocessor.joblib", "features.py", "model_metadata.json"]
_DEFAULT = Path(__file__).resolve().parents[1] / "artifacts" / "forecast" / "v1"
_STATE = {}


def _artifact_dir():
    bucket = os.environ.get("MODEL_BUCKET")
    if bucket:
        target = Path("/tmp/models/forecast/v1")
        if not (target / "preprocessor.joblib").exists():
            import boto3  # available in the AWS Lambda Python runtime
            s3 = boto3.client("s3")
            target.mkdir(parents=True, exist_ok=True)
            for name in ARTIFACT_FILES:
                try:
                    s3.download_file(bucket, f"models/forecast/v1/{name}", str(target / name))
                except Exception:
                    pass  # model.onnx OR model.joblib exists, not both
        return target
    return Path(os.environ.get("FORECAST_ARTIFACT_DIR", _DEFAULT))


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
    d = _artifact_dir()
    features = _module(d / "features.py", "eprlens_forecast_features")  # shipped inside the artifact
    prep = joblib.load(d / "preprocessor.joblib")
    meta = json.loads((d / "model_metadata.json").read_text(encoding="utf-8"))
    if prep["model_file"] == "model.onnx":
        import onnxruntime as ort
        sess = ort.InferenceSession(str(d / "model.onnx"), providers=["CPUExecutionProvider"])
        predict = lambda X: [float(v) for v in sess.run(None, {"features": X})[0].ravel()]  # noqa: E731
        as_array = lambda rows: __import__("numpy").asarray(rows, dtype="float32")  # noqa: E731
    else:
        model = joblib.load(d / prep["model_file"])
        predict = lambda X: [float(v) for v in model.predict(X)]  # noqa: E731
        as_array = lambda rows: __import__("numpy").asarray(rows, dtype="float64")  # noqa: E731
    if list(prep["feature_order"]) != list(features.FEATURES):
        raise RuntimeError("feature order in preprocessor does not match features.py")
    _STATE.update(prep=prep, meta=meta, features=features, predict=predict, as_array=as_array)
    return _STATE


def handler(event, context=None):
    try:
        req = event.get("body", event) if isinstance(event, dict) else event
        if isinstance(req, str):
            req = json.loads(req)
        st = _load()
        f = st["features"]
        for key in ("company_id", "product_id", "industry", "history"):
            if key not in req:
                raise f.HistoryError(f"missing '{key}'")
        feats, raw, origin, target = f.build_features(req["history"], req["industry"], st["prep"]["season_table"])
        pred = st["predict"](st["as_array"]([f.vector(feats)]))[0]
        kg = f.to_kg(pred, raw["packaging_kg"])
        return {"company_id": req["company_id"], "product_id": req["product_id"], "target_month": target,
                "forecast_kg": round(kg, 3), "model_version": st["meta"]["model_version"],
                "model_name": st["meta"]["model_name"], "status": "success"}
    except Exception as e:  # always return JSON, never a stack trace object
        return {"status": "error", "error": f"{type(e).__name__}: {e}", "model_version": "forecast-v1"}


if __name__ == "__main__":
    sample = json.loads((_artifact_dir() / "sample_input.json").read_text(encoding="utf-8"))
    print(json.dumps(handler(sample), indent=2))
