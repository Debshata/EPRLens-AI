import json
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
import torch
import torch.nn as nn
from torchvision import models


ROOT = Path(__file__).resolve().parents[2]

CHECKPOINT_PATH = ROOT / "ml/models/mobilenetv3-v1-finetuned.pth"
LABEL_MAP_PATH = ROOT / "ml/datasets/label_map.json"
CONFIG_PATH = ROOT / "ml/configs/image_classifier.yaml"

ONNX_PATH = ROOT / "ml/models/mobilenetv3-v1.onnx"
MANIFEST_PATH = ROOT / "ml/models/model_manifest.json"

IMAGE_SIZE = 224
OPSET_VERSION = 17


def build_model(num_classes):
    model = models.mobilenet_v3_small(weights=None)
    model.classifier[3] = nn.Linear(
        model.classifier[3].in_features, num_classes
    )
    return model


def main():
    if not CHECKPOINT_PATH.exists():
        raise FileNotFoundError(
            f"Fine-tuned checkpoint not found: {CHECKPOINT_PATH}"
        )

    with open(LABEL_MAP_PATH, encoding="utf-8-sig") as file:
        label_map = json.load(file)

    with open(CONFIG_PATH, encoding="utf-8-sig") as file:
        import yaml
        config = yaml.safe_load(file)

    class_names = [
        label_map["classes"][str(i)]
        for i in range(len(label_map["classes"]))
    ]

    checkpoint = torch.load(
        CHECKPOINT_PATH,
        map_location="cpu",
        weights_only=True,
    )

    state_dict = checkpoint["model_state_dict"]

    model = build_model(len(class_names))
    model.load_state_dict(state_dict, strict=True)
    model.eval()

    # A batch of two images tests dynamic batch support.
    dummy_input = torch.randn(2, 3, IMAGE_SIZE, IMAGE_SIZE)

    ONNX_PATH.parent.mkdir(parents=True, exist_ok=True)

    torch.onnx.export(
        model,
        dummy_input,
        str(ONNX_PATH),
        export_params=True,
        opset_version=OPSET_VERSION,
        do_constant_folding=True,
        input_names=["images"],
        output_names=["logits"],
        dynamic_axes={
            "images": {0: "batch_size"},
            "logits": {0: "batch_size"},
        },
        dynamo=False,
    )

    # Validate the exported ONNX graph.
    onnx_model = onnx.load(str(ONNX_PATH))
    onnx.checker.check_model(onnx_model)

    # Compare PyTorch and ONNX Runtime on identical input tensors.
    session = ort.InferenceSession(
        str(ONNX_PATH),
        providers=["CPUExecutionProvider"],
    )

    with torch.no_grad():
        pytorch_logits = model(dummy_input).cpu().numpy()

    onnx_logits = session.run(
        ["logits"],
        {"images": dummy_input.numpy().astype(np.float32)},
    )[0]

    max_abs_diff = float(
        np.max(np.abs(pytorch_logits - onnx_logits))
    )
    parity_passed = bool(
        np.allclose(
            pytorch_logits,
            onnx_logits,
            rtol=1e-3,
            atol=1e-4,
        )
    )

    print(f"PyTorch vs ONNX max absolute difference: {max_abs_diff:.8f}")
    print(f"Numerical parity: {'PASS' if parity_passed else 'FAIL'}")

    if not parity_passed:
        raise RuntimeError(
            "ONNX output differs from PyTorch beyond the allowed tolerance."
        )

    mean = config["inference"]["normalization"]["mean"]
    std = config["inference"]["normalization"]["std"]

    manifest = {
        "model_version": "mobilenetv3-v1-finetuned",
        "architecture": "MobileNetV3-Small",
        "source_checkpoint": CHECKPOINT_PATH.name,
        "onnx_artifact": ONNX_PATH.name,
        "selected_epoch": checkpoint.get("epoch"),
        "validation_macro_f1": checkpoint.get("val_macro_f1"),
        "input": {
            "name": "images",
            "shape": ["batch_size", 3, IMAGE_SIZE, IMAGE_SIZE],
            "color": "RGB",
            "normalization": {
                "mean": mean,
                "std": std,
            },
        },
        "output": {
            "name": "logits",
            "classes": class_names,
            "postprocessing": "softmax",
        },
        "onnx_opset": OPSET_VERSION,
        "parity_check": {
            "passed": parity_passed,
            "max_absolute_difference": max_abs_diff,
            "test_input_shape": list(dummy_input.shape),
        },
    }

    with open(MANIFEST_PATH, "w", encoding="utf-8") as file:
        json.dump(manifest, file, indent=2)

    print(f"ONNX model saved: {ONNX_PATH}")
    print(f"Model manifest saved: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
