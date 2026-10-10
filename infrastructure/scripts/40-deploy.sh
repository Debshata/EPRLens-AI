#!/usr/bin/env bash
# Uploads the zips (via S3, so >50 MB works) and creates/updates the Lambda functions. Idempotent.
source "$(dirname "$0")/config.sh"

for f in $FUNCTIONS; do
  [ -f "$BUILD_DIR/$f.zip" ] || { echo "missing $BUILD_DIR/$f.zip — run 30-package.sh first"; exit 1; }
done

ENV_COMMON="ANALYSIS_TABLE=$TABLE,UPLOADS_BUCKET=$UPLOADS_BUCKET,MODELS_BUCKET=$MODELS_BUCKET,MODEL_BUCKET=$MODELS_BUCKET,REFERENCE_BUCKET=$MODELS_BUCKET,UNCERTAIN_THRESHOLD=0.60"

for f in $FUNCTIONS; do
  name="$(fn_name "$f")"; role_arn="arn:aws:iam::$ACCOUNT_ID:role/$(role_name "$f")"
  log "deploy $name"
  aws s3 cp "$BUILD_DIR/$f.zip" "s3://$MODELS_BUCKET/deploy/$f.zip" --only-show-errors
  aws logs create-log-group --log-group-name "/aws/lambda/$name" 2>/dev/null || true
  aws logs put-retention-policy --log-group-name "/aws/lambda/$name" --retention-in-days "$LOG_RETENTION_DAYS"
  if aws lambda get-function --function-name "$name" >/dev/null 2>&1; then
    aws lambda update-function-code --function-name "$name" --s3-bucket "$MODELS_BUCKET" --s3-key "deploy/$f.zip" >/dev/null
    aws lambda wait function-updated --function-name "$name"
    aws lambda update-function-configuration --function-name "$name" --memory-size "$(memory_of "$f")" --timeout "$(timeout_of "$f")" --environment "Variables={$ENV_COMMON}" >/dev/null
  else
    aws lambda create-function --function-name "$name" --runtime "$RUNTIME" --architectures "$ARCH" --handler handler.handler \
      --role "$role_arn" --code "S3Bucket=$MODELS_BUCKET,S3Key=deploy/$f.zip" --memory-size "$(memory_of "$f")" --timeout "$(timeout_of "$f")" \
      --environment "Variables={$ENV_COMMON}" --tags "$TAGS" >/dev/null
  fi
  aws lambda wait function-active-v2 --function-name "$name" 2>/dev/null || aws lambda wait function-active --function-name "$name"
  echo "ok: $name"
done
