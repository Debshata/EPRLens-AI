
"""Validate, deduplicate and split the packaging image dataset."""

from __future__ import annotations
from tqdm import tqdm

import argparse
import hashlib
import json
from pathlib import Path


import pandas as pd
from PIL import Image, UnidentifiedImageError
from sklearn.model_selection import train_test_split


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA = ROOT / "data" / "raw" / "packaging_images" / "garbage_classification"
DEFAULT_OUTPUT = ROOT / "ml" / "datasets" / "image_manifest.csv"
LABEL_MAP = ROOT / "ml" / "datasets" / "label_map.json"

SOURCE_TO_TARGET = {
    "plastic": "plastic",
    "paper": "paper",
    "cardboard": "cardboard",
    "metal": "metal",
    "battery": "battery",
    "brown-glass": "glass",
    "green-glass": "glass",
    "white-glass": "glass",
    "biological": "trash_other",
    "clothes": "trash_other",
    "shoes": "trash_other",
    "trash": "trash_other",
}

SEED = 42


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_image(path: Path) -> bool:
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            image.convert("RGB")
        return True
    except (OSError, ValueError, UnidentifiedImageError):
        return False


def collect_images(data_dir: Path) -> pd.DataFrame:
    rows = []
    seen_hashes = set()
    skipped = 0

    if not data_dir.is_dir():
        raise FileNotFoundError(
            f"Dataset folder not found: {data_dir}\n"
            "Download and extract the dataset, then retry."
        )

    image_paths = sorted(
        path for path in data_dir.rglob("*")
        if path.is_file()
        and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    )

    for path in tqdm(image_paths, desc="Validating images"):
        if not path.is_file() or path.suffix.lower() not in {
            ".jpg", ".jpeg", ".png", ".bmp", ".webp"
        }:
            continue

        source_label = path.parent.name.lower()
        target_label = SOURCE_TO_TARGET.get(source_label)

        if target_label is None or not validate_image(path):
            skipped += 1
            continue

        file_hash = sha256_file(path)
        if file_hash in seen_hashes:
            skipped += 1
            continue
        seen_hashes.add(file_hash)

        rows.append({
            "path": str(path.resolve()),
            "source_label": source_label,
            "label": target_label,
            "sha256": file_hash,
        })

    frame = pd.DataFrame(rows)
    if frame.empty:
        raise ValueError(f"No valid supported images found in {data_dir}")

    print(f"Valid unique images: {len(frame)}")
    print(f"Skipped unsupported, invalid or exact duplicate files: {skipped}")
    print("\nCounts by target class:")
    print(frame["label"].value_counts().sort_index().to_string())

    return frame


def split_dataset(frame: pd.DataFrame) -> pd.DataFrame:
    counts = frame["label"].value_counts()
    too_small = counts[counts < 3]
    if not too_small.empty:
        raise ValueError(
            "At least 3 unique images per class are required for a "
            f"stratified split. Insufficient classes:\n{too_small}"
        )

    train, remainder = train_test_split(
        frame,
        test_size=0.30,
        random_state=SEED,
        stratify=frame["label"],
    )

    validation, test = train_test_split(
        remainder,
        test_size=0.50,
        random_state=SEED,
        stratify=remainder["label"],
    )

    train = train.copy()
    validation = validation.copy()
    test = test.copy()

    train["split"] = "train"
    validation["split"] = "validation"
    test["split"] = "test"

    result = pd.concat([train, validation, test], ignore_index=True)
    result = result.sort_values(["split", "label", "path"]).reset_index(drop=True)

    # Explicitly verify that no image hash crosses splits.
    split_counts = result.groupby("sha256")["split"].nunique()
    if (split_counts > 1).any():
        raise RuntimeError("Data leakage detected: duplicate hashes cross splits.")

    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    with LABEL_MAP.open("r", encoding="utf-8-sig") as file:
        label_config = json.load(file)

    expected = set(label_config["classes"].values())
    if expected != set(SOURCE_TO_TARGET.values()):
        raise ValueError("Source mapping and label_map.json classes do not match.")

    frame = collect_images(args.data_dir)
    result = split_dataset(frame)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)

    print("\nSplit counts:")
    print(pd.crosstab(result["label"], result["split"]).to_string())
    print(f"\nManifest written to: {args.output}")
    print("Note: splits are stratified; near-duplicate detection is not yet implemented.")


if __name__ == "__main__":
    main()
