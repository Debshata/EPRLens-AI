# EPRLens AI - Packaging Image Classifier

## Overview

This module classifies packaging and waste images into seven categories using MobileNetV3-Small. It supports model training, evaluation, ONNX export, and image-level inference.

### Supported classes

1. `plastic`
2. `paper`
3. `cardboard`
4. `metal`
5. `glass`
6. `battery`
7. `trash_other`

## Model Performance

The fine-tuned MobileNetV3-Small model was selected after comparison with the original baseline on the same held-out test set.

| Metric | Baseline | Fine-tuned |
|---|---:|---:|
| Test accuracy | 91.01% | 93.76% |
| Test macro F1 | 85.42% | 89.59% |
| Test weighted F1 | 91.11% | 93.84% |

The test set contains 2,325 images. These results measure performance on the selected public dataset and do not guarantee equivalent performance on real-world images.

## Project Structure

```text
ml/
â”œâ”€â”€ configs/
â”‚   â””â”€â”€ image_classifier.yaml
â”œâ”€â”€ datasets/
â”‚   â”œâ”€â”€ DATASET_REGISTER.md
â”‚   â”œâ”€â”€ LICENSES.md
â”‚   â”œâ”€â”€ download.md
â”‚   â””â”€â”€ label_map.json
â”œâ”€â”€ evaluation/
â”‚   â”œâ”€â”€ metrics.json
â”‚   â”œâ”€â”€ metrics_finetuned.json
â”‚   â”œâ”€â”€ model_comparison.json
â”‚   â”œâ”€â”€ training_history.json
â”‚   â”œâ”€â”€ finetuning_history.json
â”‚   â”œâ”€â”€ confusion_matrix.png
â”‚   â”œâ”€â”€ confusion_matrix_baseline.png
â”‚   â””â”€â”€ confusion_matrix_finetuned.png
â”œâ”€â”€ models/
â”‚   â”œâ”€â”€ mobilenetv3-v1.onnx
â”‚   â””â”€â”€ model_manifest.json
â”œâ”€â”€ scripts/
â”‚   â”œâ”€â”€ prepare_images.py
â”‚   â”œâ”€â”€ train_image_classifier.py
â”‚   â”œâ”€â”€ evaluate_image_classifier.py
â”‚   â”œâ”€â”€ fine_tune_image_classifier.py
â”‚   â”œâ”€â”€ compare_image_classifiers.py
â”‚   â”œâ”€â”€ export_onnx.py
â”‚   â””â”€â”€ predict_image.py
â””â”€â”€ requirements.txt
```

Local `.pth` checkpoints and the generated image manifest may also exist but are excluded from Git by the repository's ignore rules.

## Setup

Run commands from the repository root.

Activate the existing virtual environment:

```powershell
.\syntheticml\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r ml/requirements.txt
```

## Dataset

The current dataset is the Garbage Classification dataset from Kaggle:

https://www.kaggle.com/datasets/mostafaabla/garbage-classification

Follow `datasets/download.md` for download instructions and `datasets/DATASET_REGISTER.md` for source-category mappings.

Place the extracted dataset under:

```text
data/raw/packaging_images/garbage_classification/
```

The preparation script validates images, removes exact duplicate files, and creates stratified training, validation, and test splits with an approximate 70/15/15 ratio.

Generate the manifest:

```powershell
python ml\scripts\prepare_images.py
```

The generated manifest is stored at `ml/datasets/image_manifest.csv` and is intentionally excluded from Git.

## Training

Train the baseline:

```powershell
python ml\scripts\train_image_classifier.py
```

Fine-tune the baseline:

```powershell
python ml\scripts\fine_tune_image_classifier.py
```

The fine-tuning script selects its best checkpoint using validation macro F1. The current selected checkpoint was saved at epoch 7.

## Evaluation

Evaluate the baseline:

```powershell
python ml\scripts\evaluate_image_classifier.py
```

Compare the baseline and fine-tuned models on the same test split:

```powershell
python ml\scripts\compare_image_classifiers.py
```

Metrics, classification reports, confusion matrices, and training histories are saved under `ml/evaluation/`.

## ONNX Export

Export the selected fine-tuned checkpoint:

```powershell
python ml\scripts\export_onnx.py
```

The exported model is:

```text
ml/models/mobilenetv3-v1.onnx
```

The export script validates the ONNX graph and checks numerical parity between PyTorch and ONNX Runtime.

The current export passed the parity check, with a maximum absolute difference of approximately `0.00000411` on the verification input.

## Image Inference

Classify an image:

```powershell
python ml\scripts\predict_image.py "path\to\image.jpg"
```

The inference script resizes the image, applies the configured ImageNet normalization, and reports the top three predicted classes and their model confidence scores.

Confidence is not a guarantee of correctness.

## Automated Tests

Run the ONNX inference tests:

```powershell
python -m pytest tests/ml/test_onnx_inference.py -v
```

The current test suite contains four tests covering model artifacts, class metadata, preprocessing, and ONNX prediction outputs.

## Reproducibility and Limitations

- The dataset and model artifacts should be used according to their applicable licences.
- The current split is stratified, and exact duplicate images are removed before splitting. Near-duplicate detection has not been implemented.
- The public dataset may differ from packaging images captured in real-world environments.
- Validate on independently collected images before relying on the model in production.
- The `trash_other` category combines several source categories and may contain visually diverse items.
- Do not interpret classification predictions as regulatory or recycling-compliance decisions without additional validation.

## Main Artifacts

- `models/mobilenetv3-v1.onnx` â€” exported inference model.
- `models/model_manifest.json` â€” input, output, class, and export metadata.
- `evaluation/metrics.json` â€” baseline evaluation.
- `evaluation/metrics_finetuned.json` â€” fine-tuned evaluation.
- `evaluation/model_comparison.json` â€” side-by-side evaluation results.

