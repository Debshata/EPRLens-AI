import argparse
import json
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image, UnidentifiedImageError


ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = ROOT / "ml/models/mobilenetv3-v1.onnx"
MANIFEST_PATH = ROOT / "ml/models/model_manifest.json"
LABEL_MAP_PATH = ROOT / "ml/datasets/label_map.json"


def load_metadata():
    with open(MANIFEST_PATH, encoding="utf-8-sig") as file:
        manifest = json.load(file)

    with open(LABEL_MAP_PATH, encoding="utf-8-sig") as file:
        label_map = json.load(file)

    class_names = [
        label_map["classes"][str(i)]
        for i in range(len(label_map["classes"]))
    ]

    return manifest, class_names


def preprocess_image(image_path, manifest):
    image_config = manifest["input"]
    image_size = image_config["shape"][2]
    normalization = image_config["normalization"]

    mean = np.array(normalization["mean"], dtype=np.float32).reshape(1, 1, 3)
    std = np.array(normalization["std"], dtype=np.float32).reshape(1, 1, 3)

    try:
        with Image.open(image_path) as image:
            image = image.convert("RGB")
            image = image.resize(
                (image_size, image_size),
                Image.Resampling.BILINEAR,
            )
            array = np.asarray(image, dtype=np.float32) / 255.0
    except (OSError, UnidentifiedImageError) as exc:
        raise ValueError(f"Could not read image: {image_path}") from exc

    array = (array - mean) / std
    array = np.transpose(array, (2, 0, 1))
    array = np.expand_dims(array, axis=0)

    return np.ascontiguousarray(array, dtype=np.float32)


def main():
    parser = argparse.ArgumentParser(
        description="Classify a packaging image using the EPRLens ONNX model."
    )
    parser.add_argument(
        "image",
        type=Path,
        help="Path to an image file to classify",
    )
    args = parser.parse_args()

    image_path = args.image.expanduser()
    if not image_path.is_absolute():
        image_path = (Path.cwd() / image_path).resolve()

    if not image_path.is_file():
        raise FileNotFoundError(f"Image not found: {image_path}")

    if not MODEL_PATH.is_file():
        raise FileNotFoundError(f"ONNX model not found: {MODEL_PATH}")

    manifest, class_names = load_metadata()

    session = ort.InferenceSession(
        str(MODEL_PATH),
        providers=["CPUExecutionProvider"],
    )

    input_name = manifest["input"]["name"]
    output_name = manifest["output"]["name"]

    input_tensor = preprocess_image(image_path, manifest)
    logits = session.run(
        [output_name],
        {input_name: input_tensor},
    )[0]

    # Convert the seven output logits to probabilities.
    logits = logits[0].astype(np.float64)
    exp_logits = np.exp(logits - np.max(logits))
    probabilities = exp_logits / exp_logits.sum()

    top_indices = np.argsort(probabilities)[::-1][:3]
    predicted_index = int(top_indices[0])

    print("\nEPRLens AI — Packaging Image Classification")
    print("-" * 48)
    print(f"Image: {image_path}")
    print(f"Predicted class: {class_names[predicted_index]}")
    print(f"Confidence: {probabilities[predicted_index]:.2%}")
    print("\nTop 3 predictions:")

    for index in top_indices:
        print(f"  {class_names[index]:<15} {probabilities[index]:.2%}")

    print("\nNote: confidence is a model score, not a guarantee of correctness.")


if __name__ == "__main__":
    main()
