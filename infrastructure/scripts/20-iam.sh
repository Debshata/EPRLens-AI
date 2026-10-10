#!/usr/bin/env bash
# Least-privilege execution role per Lambda + a narrow IAM user for the local frontend (invoke + presign only). Idempotent.
source "$(dirname "$0")/config.sh"
IAM_DIR="$REPO_ROOT/infrastructure/iam"

S3_GET_UPLOADS='{"Effect":"Allow","Action":"s3:GetObject","Resource":"arn:aws:s3:::'"$UPLOADS_BUCKET"'/uploads/*"}'
S3_GET_MODELS='{"Effect":"Allow","Action":"s3:GetObject","Resource":"arn:aws:s3:::'"$MODELS_BUCKET"'/models/*"}'
S3_GET_REF='{"Effect":"Allow","Action":"s3:GetObject","Resource":"arn:aws:s3:::'"$MODELS_BUCKET"'/reference/*"}'
DDB_PUT='{"Effect":"Allow","Action":["dynamodb:PutItem"],"Resource":"arn:aws:dynamodb:'"$AWS_REGION:$ACCOUNT_ID"':table/'"$TABLE"'"}'
DDB_RW='{"Effect":"Allow","Action":["dynamodb:PutItem","dynamodb:GetItem"],"Resource":"arn:aws:dynamodb:'"$AWS_REGION:$ACCOUNT_ID"':table/'"$TABLE"'"}'

statements_for() {
  case "$1" in
    classify-image) echo "$S3_GET_UPLOADS,$S3_GET_MODELS,$DDB_PUT" ;;
    parse-invoice)  echo "$S3_GET_UPLOADS,$DDB_PUT" ;;
    reconcile)      echo "$S3_GET_UPLOADS,$S3_GET_REF,$DDB_RW" ;;
    forecast)       echo "$S3_GET_MODELS,$S3_GET_REF,$DDB_PUT" ;;
    detect-anomaly) echo "$S3_GET_MODELS" ;;
    company-data)   echo "$S3_GET_REF,$DDB_PUT" ;;
    scenario-engine) echo "" ;;
  esac
}

for f in $FUNCTIONS; do
  role="$(role_name "$f")"
  log "role $role"
  if ! aws iam get-role --role-name "$role" >/dev/null 2>&1; then
    aws iam create-role --role-name "$role" --assume-role-policy-document "file://$IAM_DIR/lambda-trust.json" --tags Key=Project,Value=EPRLens >/dev/null
  fi
  # CloudWatch Logs write only (implicit Lambda requirement; retention is set at deploy)
  aws iam attach-role-policy --role-name "$role" --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
  st="$(statements_for "$f")"
  if [ -n "$st" ]; then
    echo "{\"Version\":\"2012-10-17\",\"Statement\":[$st]}" > "$BUILD_DIR/policy-$f.json" 2>/dev/null || { mkdir -p "$BUILD_DIR"; echo "{\"Version\":\"2012-10-17\",\"Statement\":[$st]}" > "$BUILD_DIR/policy-$f.json"; }
    aws iam put-role-policy --role-name "$role" --policy-name "${PREFIX}-$f-access" --policy-document "file://$BUILD_DIR/policy-$f.json"
  fi
done

log "IAM user $FRONTEND_USER (invoke the ${PREFIX}-* functions, PutObject to uploads/* for presigned URLs)"
aws iam get-user --user-name "$FRONTEND_USER" >/dev/null 2>&1 || aws iam create-user --user-name "$FRONTEND_USER" --tags Key=Project,Value=EPRLens >/dev/null
mkdir -p "$BUILD_DIR"
sed -e "s|__REGION__|$AWS_REGION|g" -e "s|__ACCOUNT__|$ACCOUNT_ID|g" -e "s|__PREFIX__|$PREFIX|g" -e "s|__UPLOADS_BUCKET__|$UPLOADS_BUCKET|g" "$IAM_DIR/frontend-invoker.json" > "$BUILD_DIR/frontend-invoker.json"
aws iam put-user-policy --user-name "$FRONTEND_USER" --policy-name "${PREFIX}-frontend-invoker" --policy-document "file://$BUILD_DIR/frontend-invoker.json"
echo "waiting 10s for IAM propagation"; sleep 10
echo done
