
import json
import random
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import yaml

from PIL import Image
from sklearn.metrics import accuracy_score, f1_score
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "ml/configs/image_classifier.yaml"
LABEL_MAP_PATH = ROOT / "ml/datasets/label_map.json"
BASELINE_PATH = ROOT / "ml/models/mobilenetv3-v1.pth"
CANDIDATE_PATH = ROOT / "ml/models/mobilenetv3-v1-finetuned.pth"
HISTORY_PATH = ROOT / "ml/evaluation/finetuning_history.json"

SEED = 42
MAX_EPOCHS = 8
PATIENCE = 3
BACKBONE_LR = 1e-5
CLASSIFIER_LR = 1e-4


def seed_everything(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


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
            image = image.convert("RGB")
            image = self.transform(image)

        label = self.class_to_id[str(row["label"])]
        return image, label


def load_checkpoint(path, device):
    # Supports either a raw state dictionary or a checkpoint dictionary.
    checkpoint = torch.load(
        path, map_location=device, weights_only=True
    )

    if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
        state_dict = checkpoint["model_state_dict"]
    elif isinstance(checkpoint, dict) and "state_dict" in checkpoint:
        state_dict = checkpoint["state_dict"]
    else:
        state_dict = checkpoint

    return state_dict, checkpoint


def build_model(num_classes):
    model = models.mobilenet_v3_small(weights=None)
    model.classifier[3] = nn.Linear(
        model.classifier[3].in_features, num_classes
    )
    return model


def evaluate(model, loader, criterion, device):
    model.eval()
    total_loss = 0.0
    true_labels, predicted_labels = [], []

    with torch.no_grad():
        for images, labels in loader:
            images = images.to(device)
            labels = labels.to(device)

            logits = model(images)
            loss = criterion(logits, labels)

            total_loss += loss.item() * labels.size(0)
            predictions = logits.argmax(dim=1)

            true_labels.extend(labels.cpu().tolist())
            predicted_labels.extend(predictions.cpu().tolist())

    return {
        "loss": total_loss / len(loader.dataset),
        "accuracy": accuracy_score(true_labels, predicted_labels),
        "macro_f1": f1_score(
            true_labels,
            predicted_labels,
            average="macro",
            zero_division=0,
        ),
    }


def main():
    seed_everything(SEED)

    if not BASELINE_PATH.exists():
        raise FileNotFoundError(
            f"Baseline checkpoint not found: {BASELINE_PATH}"
        )

    with open(CONFIG_PATH, encoding="utf-8") as file:
        config = yaml.safe_load(file)

    with open(LABEL_MAP_PATH, encoding="utf-8-sig") as file:
        label_map = json.load(file)

    class_names = [
        label_map["classes"][str(i)]
        for i in range(len(label_map["classes"]))
    ]
    class_to_id = {name: i for i, name in enumerate(class_names)}

    manifest_path = ROOT / config["dataset"]["manifest"]
    frame = pd.read_csv(manifest_path)

    required_columns = {"path", "label", "split"}
    if not required_columns.issubset(frame.columns):
        raise ValueError(
            f"Manifest must contain columns: {sorted(required_columns)}"
        )

    train_frame = frame[frame["split"] == "train"].copy()
    val_frame = frame[frame["split"] == "validation"].copy()

    if train_frame.empty or val_frame.empty:
        raise ValueError("Training or validation split is empty.")

    for label in frame["label"].unique():
        if str(label) not in class_to_id:
            raise ValueError(f"Unknown class in manifest: {label}")

    image_size = config["model"]["image_size"]
    mean = config["inference"]["normalization"]["mean"]
    std = config["inference"]["normalization"]["std"]

    train_transform = transforms.Compose([
        transforms.Resize((image_size, image_size)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(10),
        transforms.ColorJitter(
            brightness=0.15, contrast=0.15, saturation=0.10
        ),
        transforms.ToTensor(),
        transforms.Normalize(mean=mean, std=std),
    ])

    val_transform = transforms.Compose([
        transforms.Resize((image_size, image_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=mean, std=std),
    ])

    train_dataset = PackagingDataset(
        train_frame, class_to_id, train_transform
    )
    val_dataset = PackagingDataset(
        val_frame, class_to_id, val_transform
    )

    batch_size = config["training"]["batch_size"]
    num_workers = config["training"].get("num_workers", 0)

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=torch.cuda.is_available(),
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=torch.cuda.is_available(),
    )

    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )
    print(f"Device: {device}")
    print(f"Training images: {len(train_dataset)}")
    print(f"Validation images: {len(val_dataset)}")
    print(f"Classes: {class_names}")

    model = build_model(len(class_names))
    state_dict, _ = load_checkpoint(BASELINE_PATH, device)
    model.load_state_dict(state_dict, strict=True)

    # Freeze the early features; fine-tune the later feature blocks.
    for parameter in model.features.parameters():
        parameter.requires_grad = False

    for layer in list(model.features.children())[-4:]:
        for parameter in layer.parameters():
            parameter.requires_grad = True

    for parameter in model.classifier.parameters():
        parameter.requires_grad = True

    model = model.to(device)

    counts = (
        train_frame["label"]
        .astype(str)
        .value_counts()
        .reindex(class_names, fill_value=0)
    )

    if (counts == 0).any():
        raise ValueError(
            f"Missing classes in training split: {counts[counts == 0].index.tolist()}"
        )

    # Inverse-frequency weights, normalized to mean 1.
    class_weights = 1.0 / torch.tensor(
        counts.to_numpy(), dtype=torch.float32
    )
    class_weights = class_weights / class_weights.mean()
    criterion = nn.CrossEntropyLoss(
        weight=class_weights.to(device)
    )

    optimizer = torch.optim.AdamW([
        {
            "params": [
                p for p in model.features.parameters()
                if p.requires_grad
            ],
            "lr": BACKBONE_LR,
        },
        {
            "params": [
                p for p in model.classifier.parameters()
                if p.requires_grad
            ],
            "lr": CLASSIFIER_LR,
        },
    ], weight_decay=1e-4)

    best_macro_f1 = -1.0
    best_epoch = 0
    epochs_without_improvement = 0
    history = []

    for epoch in range(1, MAX_EPOCHS + 1):
        model.train()
        total_loss = 0.0

        for images, labels in train_loader:
            images = images.to(device)
            labels = labels.to(device)

            optimizer.zero_grad(set_to_none=True)
            logits = model(images)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()

            total_loss += loss.item() * labels.size(0)

        train_loss = total_loss / len(train_dataset)
        val_metrics = evaluate(model, val_loader, criterion, device)

        record = {
            "epoch": epoch,
            "train_loss": train_loss,
            "val_loss": val_metrics["loss"],
            "val_accuracy": val_metrics["accuracy"],
            "val_macro_f1": val_metrics["macro_f1"],
        }
        history.append(record)

        print(
            f"Epoch {epoch}/{MAX_EPOCHS} | "
            f"train_loss={train_loss:.4f} | "
            f"val_loss={val_metrics['loss']:.4f} | "
            f"val_accuracy={val_metrics['accuracy']:.4f} | "
            f"val_macro_f1={val_metrics['macro_f1']:.4f}"
        )

        if val_metrics["macro_f1"] > best_macro_f1 + 1e-4:
            best_macro_f1 = val_metrics["macro_f1"]
            best_epoch = epoch
            epochs_without_improvement = 0

            torch.save({
                "model_state_dict": model.state_dict(),
                "epoch": epoch,
                "val_macro_f1": best_macro_f1,
                "class_names": class_names,
                "model_version": "mobilenetv3-v1-finetuned",
            }, CANDIDATE_PATH)

            print(f"  Saved best candidate: {CANDIDATE_PATH}")
        else:
            epochs_without_improvement += 1

        if epochs_without_improvement >= PATIENCE:
            print("Early stopping: validation macro F1 did not improve.")
            break

    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_PATH, "w", encoding="utf-8") as file:
        json.dump(history, file, indent=2)

    print("\nFine-tuning complete.")
    print(f"Best epoch: {best_epoch}")
    print(f"Best validation macro F1: {best_macro_f1:.4f}")
    print(f"Candidate checkpoint: {CANDIDATE_PATH}")
    print(f"Training history: {HISTORY_PATH}")


if __name__ == "__main__":
    main()
