
"""Train the EPRLens MobileNetV3-Small packaging classifier."""

from __future__ import annotations

import json
import random
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import yaml
from PIL import Image
from sklearn.metrics import accuracy_score, f1_score
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small
from tqdm import tqdm


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "ml" / "configs" / "image_classifier.yaml"
LABEL_MAP_PATH = ROOT / "ml" / "datasets" / "label_map.json"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


class PackagingDataset(Dataset):
    def __init__(self, frame: pd.DataFrame, label_to_id: dict[str, int],
                 training: bool = False):
        self.frame = frame.reset_index(drop=True)
        self.label_to_id = label_to_id

        normalize = transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225],
        )
        if training:
            self.transform = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.RandomHorizontalFlip(),
                transforms.RandomRotation(10),
                transforms.ColorJitter(
                    brightness=0.15, contrast=0.15, saturation=0.10
                ),
                transforms.ToTensor(),
                normalize,
            ])
        else:
            self.transform = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                normalize,
            ])

    def __len__(self) -> int:
        return len(self.frame)

    def __getitem__(self, index: int):
        row = self.frame.iloc[index]
        with Image.open(row["path"]) as image:
            image = image.convert("RGB")
            tensor = self.transform(image)
        return tensor, self.label_to_id[row["label"]]


def build_model(num_classes: int, pretrained: bool) -> nn.Module:
    weights = MobileNet_V3_Small_Weights.DEFAULT if pretrained else None
    model = mobilenet_v3_small(weights=weights)

    # Freeze the feature extractor for the initial baseline.
    for parameter in model.features.parameters():
        parameter.requires_grad = False

    in_features = model.classifier[3].in_features
    model.classifier[3] = nn.Linear(in_features, num_classes)
    return model


def evaluate(model, loader, criterion):
    model.eval()
    losses = []
    actual, predicted = [], []

    with torch.no_grad():
        for images, labels in loader:
            images, labels = images.to(DEVICE), labels.to(DEVICE)
            logits = model(images)
            losses.append(criterion(logits, labels).item())
            predicted.extend(logits.argmax(dim=1).cpu().tolist())
            actual.extend(labels.cpu().tolist())

    return {
        "loss": float(np.mean(losses)),
        "accuracy": float(accuracy_score(actual, predicted)),
        "macro_f1": float(f1_score(actual, predicted, average="macro",
                                   zero_division=0)),
    }


def main():
    with CONFIG_PATH.open("r", encoding="utf-8-sig") as file:
        config = yaml.safe_load(file)

    with LABEL_MAP_PATH.open("r", encoding="utf-8-sig") as file:
        label_config = json.load(file)

    class_names = list(label_config["classes"].values())
    label_to_id = {name: index for index, name in enumerate(class_names)}
    seed_everything(config["dataset"]["seed"])

    manifest_path = ROOT / config["dataset"]["manifest"]
    frame = pd.read_csv(manifest_path)

    if not {"path", "label", "split"}.issubset(frame.columns):
        raise ValueError("Manifest must contain path, label, and split columns.")

    unknown = set(frame["label"]) - set(class_names)
    if unknown:
        raise ValueError(f"Unknown labels in manifest: {unknown}")

    train_frame = frame[frame["split"] == "train"].copy()
    val_frame = frame[frame["split"] == "validation"].copy()

    if train_frame.empty or val_frame.empty:
        raise ValueError("Training or validation split is empty.")

    batch_size = config["training"]["batch_size"]
    workers = config["training"]["num_workers"]

    train_loader = DataLoader(
        PackagingDataset(train_frame, label_to_id, training=True),
        batch_size=batch_size, shuffle=True, num_workers=workers,
    )
    val_loader = DataLoader(
        PackagingDataset(val_frame, label_to_id),
        batch_size=batch_size, shuffle=False, num_workers=workers,
    )

    # Inverse-frequency class weights reduce the influence of the
    # heavily represented trash_other class.
    counts = train_frame["label"].value_counts()
    weights = torch.tensor(
        [len(train_frame) / (len(class_names) * counts.get(name, 1))
         for name in class_names],
        dtype=torch.float32,
        device=DEVICE,
    )

    model = build_model(
        len(class_names), pretrained=config["model"]["pretrained"]
    ).to(DEVICE)

    criterion = nn.CrossEntropyLoss(weight=weights)
    optimizer = torch.optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=config["training"]["learning_rate"],
        weight_decay=config["training"]["weight_decay"],
    )

    artifact_dir = ROOT / "ml" / "models"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = artifact_dir / "mobilenetv3-v1.pth"
    history_path = ROOT / "ml" / "evaluation" / "training_history.json"
    history_path.parent.mkdir(parents=True, exist_ok=True)

    best_f1 = -1.0
    best_epoch = 0
    patience = config["training"]["early_stopping_patience"]
    stale_epochs = 0
    history = []

    print(f"Device: {DEVICE}")
    print(f"Training images: {len(train_frame)}")
    print(f"Validation images: {len(val_frame)}")
    print(f"Classes: {class_names}")

    for epoch in range(config["training"]["epochs"]):
        model.train()
        running_loss = []

        progress = tqdm(train_loader, desc=f"Epoch {epoch + 1}")
        for images, labels in progress:
            images, labels = images.to(DEVICE), labels.to(DEVICE)
            optimizer.zero_grad(set_to_none=True)
            logits = model(images)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()
            running_loss.append(loss.item())
            progress.set_postfix(loss=f"{loss.item():.4f}")

        val_metrics = evaluate(model, val_loader, criterion)
        record = {
            "epoch": epoch + 1,
            "train_loss": float(np.mean(running_loss)),
            "validation": val_metrics,
        }
        history.append(record)

        print(json.dumps(record, indent=2))

        if val_metrics["macro_f1"] > best_f1:
            best_f1 = val_metrics["macro_f1"]
            best_epoch = epoch + 1
            stale_epochs = 0
            torch.save({
                "state_dict": model.state_dict(),
                "class_names": class_names,
                "model_version": config["model"]["version"],
                "image_size": config["model"]["image_size"],
                "normalization": {
                    "mean": [0.485, 0.456, 0.406],
                    "std": [0.229, 0.224, 0.225],
                },
                "best_validation_macro_f1": best_f1,
                "best_epoch": best_epoch,
            }, checkpoint_path)
        else:
            stale_epochs += 1
            if stale_epochs >= patience:
                print("Early stopping: validation macro F1 did not improve.")
                break

    history_path.write_text(
        json.dumps({
            "device": str(DEVICE),
            "best_epoch": best_epoch,
            "best_validation_macro_f1": best_f1,
            "history": history,
        }, indent=2),
        encoding="utf-8",
    )

    print(f"Best checkpoint: {checkpoint_path}")
    print(f"Training history: {history_path}")


if __name__ == "__main__":
    main()
