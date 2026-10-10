"""Packaging image classifier (MobileNetV3-Small ONNX from WP1). Returns a PROBABLE material, never a legal EPR category.

Preprocessing is identical to ml/scripts/predict_image.py: RGB, bilinear resize to 224x224, /255, ImageNet mean/std, NCHW float32.
"""
from __future__ import annotations

import io
import json
import os
from pathlib import Path

import numpy as np

UNCERTAIN_THRESHOLD = float(os.environ.get("UNCERTAIN_THRESHOLD", "0.60"))  # assumption: WP1 defines no threshold
_STATE: dict = {}


def model_dir() -> Path:
    d = os.environ.get("MODEL_DIR")
    if d:
        return Path(d)
    bucket = os.environ.get("MODELS_BUCKET")
    if bucket:
        target = Path("/tmp/models/material-classifier/v1")
        if not (target / "mobilenetv3-v1.onnx").exists():
            import boto3

            s3 = boto3.client("s3")
            target.mkdir(parents=True, exist_ok=True)
            for name in ("mobilenetv3-v1.onnx", "model_manifest.json"):
                s3.download_file(bucket, f"models/material-classifier/v1/{name}", str(target / name))
        return target
    return Path(__file__).resolve().parents[3] / "ml" / "models"  # repo layout (local runs)


def _load():
    if _STATE:
        return _STATE
    import onnxruntime as ort

    d = model_dir()
    manifest = json.loads((d / "model_manifest.json").read_text(encoding="utf-8-sig"))
    sess = ort.InferenceSession(str(d / manifest["onnx_artifact"]), providers=["CPUExecutionProvider"])
    _STATE.update(manifest=manifest, session=sess, input=sess.get_inputs()[0].name)
    return _STATE


def preprocess(image_bytes: bytes, manifest: dict) -> np.ndarray:
    from PIL import Image, UnidentifiedImageError

    cfg = manifest["input"]
    size = cfg["shape"][2]
    mean = np.array(cfg["normalization"]["mean"], dtype=np.float32).reshape(1, 1, 3)
    std = np.array(cfg["normalization"]["std"], dtype=np.float32).reshape(1, 1, 3)
    try:
        with Image.open(io.BytesIO(image_bytes)) as im:
            arr = np.asarray(im.convert("RGB").resize((size, size), Image.Resampling.BILINEAR), dtype=np.float32) / 255.0
    except (OSError, UnidentifiedImageError) as e:
        raise ValueError("The file is not a readable JPG or PNG image. Upload a clear photo and try again.") from e
    arr = (arr - mean) / std
    return np.ascontiguousarray(np.expand_dims(np.transpose(arr, (2, 0, 1)), 0), dtype=np.float32)


def classify(image_bytes: bytes) -> dict:
    st = _load()
    x = preprocess(image_bytes, st["manifest"])
    logits = st["session"].run(None, {st["input"]: x})[0][0].astype(np.float64)
    e = np.exp(logits - logits.max())
    probs = e / e.sum()
    classes = st["manifest"]["output"]["classes"]
    i = int(probs.argmax())
    conf = float(probs[i])
    return {
        "predicted_class": classes[i],
        "confidence": round(conf, 4),
        "uncertain": conf < UNCERTAIN_THRESHOLD,
        "model_version": st["manifest"]["model_version"],
    }
