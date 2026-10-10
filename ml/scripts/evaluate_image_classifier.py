
"""Evaluate the saved MobileNetV3-Small checkpoint on the test split."""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from PIL import Image
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from torchvision.models import mobilenet_v3_small
from torch import nn
from tqdm import tqdm


ROOT = Path(__file__).resolve().parents[2]
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

CHECKPOINT = ROOT / "ml" / "models" / "mobilenetv3-v1.pth"
MANIFEST = ROOT / "ml" / "datasets" / "image_manifest.csv"
OUTPUT_DIR = ROOT / "ml" / "evaluation"


class TestDataset(Dataset):
    def __init__(self, frame, label_to_id):
        self.frame = frame.reset_index(drop=True)
        self.label_to_id = label_to_id
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ])

    def __len__(self):
        return len(self.frame)

    def __getitem__(self, index):
        row = self.frame.iloc[index]
        with Image.open(row["path"]) as image:
            image = image.convert("RGB")
            tensor = self.transform(image)
        return tensor, self.label_to_id[row["label"]]


def main():
    if not CHECKPOINT.exists():
        raise FileNotFoundError(f"Checkpoint not found: {CHECKPOINT}")
    if not MANIFEST.exists():
        raise FileNotFoundError(f"Manifest not found: {MANIFEST}")

    checkpoint = torch.load(
        CHECKPOINT, map_location=DEVICE, weights_only=True
    )
    class_names = checkpoint["class_names"]
    label_to_id = {name: i for i, name in enumerate(class_names)}

    frame = pd.read_csv(MANIFEST)
    test_frame = frame[frame["split"] == "test"].copy()

    if test_frame.empty:
        raise ValueError("The test split is empty.")

    dataset = TestDataset(test_frame, label_to_id)
    loader = DataLoader(
        dataset, batch_size=32, shuffle=False, num_workers=0
    )

    model = mobilenet_v3_small(weights=None)
    in_features = model.classifier[3].in_features
    model.classifier[3] = nn.Linear(in_features, len(class_names))
    model.load_state_dict(checkpoint["state_dict"])
    model.to(DEVICE)
    model.eval()

    y_true, y_pred = [], []
    all_probabilities = []

    with torch.no_grad():
        for images, labels in tqdm(loader, desc="Evaluating test set"):
            images = images.to(DEVICE)
            logits = model(images)
            probabilities = torch.softmax(logits, dim=1)
            predictions = probabilities.argmax(dim=1)

            y_true.extend(labels.tolist())
            y_pred.extend(predictions.cpu().tolist())
            all_probabilities.extend(probabilities.cpu().tolist())

    accuracy = accuracy_score(y_true, y_pred)
    macro_f1 = f1_score(
        y_true, y_pred, average="macro", zero_division=0
    )

    report = classification_report(
        y_true,
        y_pred,
        labels=list(range(len(class_names))),
        target_names=class_names,
        output_dict=True,
        zero_division=0,
    )

    cm = confusion_matrix(
        y_true, y_pred, labels=list(range(len(class_names)))
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    metrics = {
        "model_version": checkpoint["model_version"],
        "checkpoint_epoch": checkpoint["best_epoch"],
        "evaluation_split": "test",
        "test_samples": len(y_true),
        "accuracy": float(accuracy),
        "macro_f1": float(macro_f1),
        "per_class": {
            name: {
                "precision": float(report[name]["precision"]),
                "recall": float(report[name]["recall"]),
                "f1_score": float(report[name]["f1-score"]),
                "support": int(report[name]["support"]),
            }
            for name in class_names
        },
        "confusion_matrix_labels": class_names,
        "confusion_matrix": cm.tolist(),
    }

    (OUTPUT_DIR / "metrics.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8"
    )

    fig, ax = plt.subplots(figsize=(10, 8))
    image = ax.imshow(cm, interpolation="nearest", cmap="Blues")
    fig.colorbar(image, ax=ax)
    ax.set(
        xticks=np.arange(len(class_names)),
        yticks=np.arange(len(class_names)),
        xticklabels=class_names,
        yticklabels=class_names,
        xlabel="Predicted class",
        ylabel="True class",
        title="Packaging Classifier — Test Confusion Matrix",
    )
    plt.setp(ax.get_xticklabels(), rotation=35, ha="right")

    threshold = cm.max() / 2 if cm.size else 0
    for row in range(cm.shape[0]):
        for col in range(cm.shape[1]):
            ax.text(
                col, row, str(cm[row, col]),
                ha="center", va="center",
                color="white" if cm[row, col] > threshold else "black",
                fontsize=8,
            )

    fig.tight_layout()
    fig.savefig(
        OUTPUT_DIR / "confusion_matrix.png",
        dpi=160, bbox_inches="tight"
    )
    plt.close(fig)

    print(f"Device: {DEVICE}")
    print(f"Test samples: {len(y_true)}")
    print(f"Test accuracy: {accuracy:.4f}")
    print(f"Test macro F1: {macro_f1:.4f}")
    print("\nPer-class report:")
    print(classification_report(
        y_true, y_pred,
        labels=list(range(len(class_names))),
        target_names=class_names,
        zero_division=0,
    ))
    print(f"\nMetrics: {OUTPUT_DIR / 'metrics.json'}")
    print(f"Confusion matrix: {OUTPUT_DIR / 'confusion_matrix.png'}")


if __name__ == "__main__":
    main()
