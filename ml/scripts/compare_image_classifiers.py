import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
import yaml

from PIL import Image
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms


ROOT = Path(__file__).resolve().parents[2]

CONFIG_PATH = ROOT / "ml/configs/image_classifier.yaml"
LABEL_MAP_PATH = ROOT / "ml/datasets/label_map.json"
MANIFEST_PATH = ROOT / "ml/datasets/image_manifest.csv"

BASELINE_PATH = ROOT / "ml/models/mobilenetv3-v1.pth"
CANDIDATE_PATH = ROOT / "ml/models/mobilenetv3-v1-finetuned.pth"

OUTPUT_DIR = ROOT / "ml/evaluation"
BATCH_SIZE = 32


class PackagingDataset(Dataset):
    def __init__(self, frame, class_to_id, transform):
        self.frame = frame.reset_index(drop=True)
        self.class_to_id = class_to_id
        self.transform = transform

    def __len__(self):
        return len(self.frame)

    def __getitem__(self, index):
        row = self.frame.iloc[index]
        image_path = Path(str(row["path"]))

        if not image_path.is_absolute():
            image_path = ROOT / image_path

        with Image.open(image_path) as image:
            image = self.transform(image.convert("RGB"))

        return image, self.class_to_id[str(row["label"])]


def build_model(num_classes):
    model = models.mobilenet_v3_small(weights=None)
    model.classifier[3] = torch.nn.Linear(
        model.classifier[3].in_features, num_classes
    )
    return model


def load_model(path, device, num_classes):
    checkpoint = torch.load(
        path,
        map_location=device,
        weights_only=True,
    )

    # Baseline is a raw state_dict; fine-tuned checkpoint is a dictionary.
    if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
        state_dict = checkpoint["model_state_dict"]
    elif isinstance(checkpoint, dict) and "state_dict" in checkpoint:
        state_dict = checkpoint["state_dict"]
    else:
        state_dict = checkpoint

    model = build_model(num_classes)
    model.load_state_dict(state_dict, strict=True)
    model.to(device)
    model.eval()

    return model, checkpoint


def evaluate(model, loader, class_names, device):
    y_true, y_pred = [], []

    with torch.no_grad():
        for images, labels in loader:
            logits = model(images.to(device))
            predictions = logits.argmax(dim=1).cpu().tolist()

            y_pred.extend(predictions)
            y_true.extend(labels.tolist())

    labels = list(range(len(class_names)))

    report = classification_report(
        y_true,
        y_pred,
        labels=labels,
        target_names=class_names,
        output_dict=True,
        zero_division=0,
    )

    cm = confusion_matrix(
        y_true,
        y_pred,
        labels=labels,
    )

    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(
            f1_score(
                y_true,
                y_pred,
                average="macro",
                zero_division=0,
            )
        ),
        "weighted_f1": float(
            f1_score(
                y_true,
                y_pred,
                average="weighted",
                zero_division=0,
            )
        ),
        "classification_report": report,
        "confusion_matrix": cm.tolist(),
    }


def save_confusion_matrix(cm, class_names, model_name):
    """Save a confusion matrix with counts annotated in every cell."""
    fig, ax = plt.subplots(figsize=(10, 8))

    image = ax.imshow(cm, cmap="Blues")
    fig.colorbar(image, ax=ax)

    ax.set(
        xticks=range(len(class_names)),
        yticks=range(len(class_names)),
        xticklabels=class_names,
        yticklabels=class_names,
        xlabel="Predicted class",
        ylabel="True class",
        title=f"{model_name.title()} — Test Confusion Matrix",
    )

    # Write the actual prediction count into each cell.
    threshold = cm.max() / 2 if cm.size else 0

    for row in range(cm.shape[0]):
        for col in range(cm.shape[1]):
            value = int(cm[row, col])
            ax.text(
                col,
                row,
                str(value),
                ha="center",
                va="center",
                color="white" if value > threshold else "black",
                fontsize=9,
            )

    plt.setp(
        ax.get_xticklabels(),
        rotation=40,
        ha="right",
    )

    fig.tight_layout()

    output_path = OUTPUT_DIR / f"confusion_matrix_{model_name}.png"
    fig.savefig(output_path, dpi=160, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved confusion matrix: {output_path}")


def save_metrics(result, model_name, test_samples):
    """Save detailed test metrics for one model."""
    filename = (
        "metrics.json"
        if model_name == "baseline"
        else "metrics_finetuned.json"
    )

    metrics_output = {
        "model": model_name,
        "test_samples": test_samples,
        "accuracy": result["accuracy"],
        "macro_f1": result["macro_f1"],
        "weighted_f1": result["weighted_f1"],
        "classification_report": result["classification_report"],
        "confusion_matrix": result["confusion_matrix"],
    }

    output_path = OUTPUT_DIR / filename

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(metrics_output, file, indent=2)

    print(f"Saved metrics: {output_path}")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(CONFIG_PATH, encoding="utf-8-sig") as file:
        config = yaml.safe_load(file)

    with open(LABEL_MAP_PATH, encoding="utf-8-sig") as file:
        label_map = json.load(file)

    class_names = [
        label_map["classes"][str(i)]
        for i in range(len(label_map["classes"]))
    ]
    class_to_id = {
        name: i for i, name in enumerate(class_names)
    }

    frame = pd.read_csv(MANIFEST_PATH)
    test_frame = frame[frame["split"] == "test"].copy()

    if test_frame.empty:
        raise ValueError("The test split is empty.")

    image_size = config["model"]["image_size"]
    mean = config["inference"]["normalization"]["mean"]
    std = config["inference"]["normalization"]["std"]

    test_transform = transforms.Compose([
        transforms.Resize((image_size, image_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=mean, std=std),
    ])

    dataset = PackagingDataset(
        test_frame,
        class_to_id,
        test_transform,
    )

    loader = DataLoader(
        dataset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        num_workers=0,
    )

    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    print(f"Device: {device}")
    print(f"Test images: {len(dataset)}")

    models_to_test = {
        "baseline": BASELINE_PATH,
        "finetuned": CANDIDATE_PATH,
    }

    results = {}

    for model_name, checkpoint_path in models_to_test.items():
        if not checkpoint_path.exists():
            raise FileNotFoundError(
                f"Checkpoint not found: {checkpoint_path}"
            )

        model, checkpoint = load_model(
            checkpoint_path,
            device,
            len(class_names),
        )

        result = evaluate(
            model,
            loader,
            class_names,
            device,
        )

        results[model_name] = {
            "accuracy": result["accuracy"],
            "macro_f1": result["macro_f1"],
            "weighted_f1": result["weighted_f1"],
            "classification_report": result["classification_report"],
            "confusion_matrix": result["confusion_matrix"],
        }

        save_metrics(result, model_name, len(dataset))

        save_confusion_matrix(
            np.array(result["confusion_matrix"]),
            class_names,
            model_name,
        )

        print(f"\n{model_name.upper()}")
        print(f"Accuracy: {result['accuracy']:.4f}")
        print(f"Macro F1: {result['macro_f1']:.4f}")
        print(f"Weighted F1: {result['weighted_f1']:.4f}")

        if model_name == "finetuned" and isinstance(checkpoint, dict):
            print(
                "Selected training epoch: "
                f"{checkpoint.get('epoch', 'unknown')}"
            )

    comparison = {
        "test_samples": len(dataset),
        "class_names": class_names,
        "results": results,
        "selection_rule": (
            "Validation macro F1 is used for checkpoint selection. "
            "Both models are evaluated on the same held-out test split "
            "for final reporting."
        ),
    }

    output_path = OUTPUT_DIR / "model_comparison.json"

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(comparison, file, indent=2)

    print("\nSAME-TEST-SET COMPARISON")
    print(
        f"{'Model':<12} {'Accuracy':>10} "
        f"{'Macro F1':>10} {'Weighted F1':>13}"
    )

    for name, result in results.items():
        print(
            f"{name:<12} {result['accuracy']:>10.4f} "
            f"{result['macro_f1']:>10.4f} "
            f"{result['weighted_f1']:>13.4f}"
        )

    print(f"\nDetailed results: {output_path}")
    print("Both annotated confusion matrices have been regenerated.")


if __name__ == "__main__":
    main()
