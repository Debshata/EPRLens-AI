#!/usr/bin/env bash
# Uploads model artifacts (S3 layout from the runbook) and the small reference/demo data the Lambdas read.
source "$(dirname "$0")/config.sh"
ML="$REPO_ROOT/syntheticml/ml/artifacts"
up() { aws s3 cp "$1" "s3://$MODELS_BUCKET/$2" --only-show-errors; echo "  $2"; }

log "image classifier (models/material-classifier/v1/)"
up "$REPO_ROOT/ml/models/mobilenetv3-v1.onnx" models/material-classifier/v1/mobilenetv3-v1.onnx
up "$REPO_ROOT/ml/models/model_manifest.json" models/material-classifier/v1/model_manifest.json

log "forecast (models/forecast/v1/)"
for f in model.onnx preprocessor.joblib features.py model_metadata.json feature_schema.json; do up "$ML/forecast/v1/$f" "models/forecast/v1/$f"; done

log "anomaly (models/anomaly/v1/)"
for f in isolation_forest.joblib preprocessor.joblib features.py rules.py rules_config.json threshold.json model_metadata.json feature_schema.json sample_input.json; do up "$ML/anomaly/v1/$f" "models/anomaly/v1/$f"; done

log "reference/demo data (reference/)"
[ -d "$REPO_ROOT/backend/seed/reference" ] || python3 "$REPO_ROOT/backend/seed/build_seed.py"
aws s3 sync "$REPO_ROOT/backend/seed/reference" "s3://$MODELS_BUCKET/reference" --delete --only-show-errors
echo done
