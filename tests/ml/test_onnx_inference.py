import json
from pathlib import Path

import numpy as np
import onnxruntime as ort
import pytest
from PIL import Image

from ml.scripts.predict_image import (
    LABEL_MAP_PATH,
    MANIFEST_PATH,
    MODEL_PATH,
    load_metadata,
    preprocess_image,
)


def test_model_and_manifest_exist():
    assert MODEL_PATH.is_file()
    assert MANIFEST_PATH.is_file()
    assert LABEL_MAP_PATH.is_file()


def test_manifest_has_seven_classes():
    manifest, class_names = load_metadata()

    assert len(class_names) == 7
    assert len(set(class_names)) == 7
    assert manifest["input"]["color"] == "RGB"


def test_preprocessing_output_shape_and_type(tmp_path):
    manifest, _ = load_metadata()

    image_path = tmp_path / "sample.png"
    Image.new("RGB", (320, 180), color=(120, 80, 40)).save(image_path)

    tensor = preprocess_image(image_path, manifest)

    assert tensor.shape == (1, 3, 224, 224)
    assert tensor.dtype == np.float32
    assert np.isfinite(tensor).all()


def test_onnx_prediction_output(tmp_path):
    manifest, class_names = load_metadata()

    image_path = tmp_path / "sample.png"
    Image.new("RGB", (224, 224), color=(120, 80, 40)).save(image_path)

    tensor = preprocess_image(image_path, manifest)

    session = ort.InferenceSession(
        str(MODEL_PATH),
        providers=["CPUExecutionProvider"],
    )

    logits = session.run(
        [manifest["output"]["name"]],
        {manifest["input"]["name"]: tensor},
    )[0]

    assert logits.shape == (1, len(class_names))
    assert np.isfinite(logits).all()

    shifted = logits[0] - np.max(logits[0])
    probabilities = np.exp(shifted) / np.exp(shifted).sum()

    assert np.isclose(probabilities.sum(), 1.0, atol=1e-6)
    assert np.all(probabilities >= 0.0)
    assert np.all(probabilities <= 1.0)
