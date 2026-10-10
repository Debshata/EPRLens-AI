#!/usr/bin/env bash
# Deploys the Next.js app to AWS Lambda behind a public Function URL (Lambda Web Adapter). Idempotent.
#   needs: build/web.zip (35-package-web.sh) and the 7 backend functions (40-deploy.sh)
# The web function uses its own IAM role (invoke eprlens-demo-* + presign uploads): NO access keys are stored anywhere.
source "$(dirname "$0")/config.sh"
[ -f "${BUILD_DIR:?}/web.zip" ] || { echo "run 35-package-web.sh first"; exit 1; }

WEB="${PREFIX}-web"
ROLE="${PREFIX}-lambda-web"
LWA_LAYER="arn:aws:lambda:${AWS_REGION}:753240598075:layer:LambdaAdapterLayerX86:30"
IAM_DIR="$REPO_ROOT/infrastructure/iam"

log "IAM role $ROLE"
aws iam get-role --role-name "$ROLE" >/dev/null 2>&1 || aws iam create-role --role-name "$ROLE" --assume-role-policy-document "file://$IAM_DIR/lambda-trust.json" --tags Key=Project,Value=EPRLens >/dev/null
aws iam attach-role-policy --role-name "$ROLE" --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
sed -e "s|__REGION__|$AWS_REGION|g" -e "s|__ACCOUNT__|$ACCOUNT_ID|g" -e "s|__PREFIX__|$PREFIX|g" -e "s|__UPLOADS_BUCKET__|$UPLOADS_BUCKET|g" "$IAM_DIR/frontend-invoker.json" > "$BUILD_DIR/web-role-policy.json"
aws iam put-role-policy --role-name "$ROLE" --policy-name "${PREFIX}-web-access" --policy-document "file://$BUILD_DIR/web-role-policy.json"
sleep 10

ENV="NEXT_PUBLIC_API_MODE=live,UPLOADS_BUCKET=$UPLOADS_BUCKET,LAMBDA_PARSE_INVOICE=$(fn_name parse-invoice),LAMBDA_RECONCILE=$(fn_name reconcile),LAMBDA_CLASSIFY_IMAGE=$(fn_name classify-image),LAMBDA_FORECAST=$(fn_name forecast),LAMBDA_DETECT_ANOMALY=$(fn_name detect-anomaly),LAMBDA_SCENARIO_ENGINE=$(fn_name scenario-engine),LAMBDA_COMPANY_DATA=$(fn_name company-data),AWS_LAMBDA_EXEC_WRAPPER=/opt/bootstrap,PORT=8080,HOSTNAME=0.0.0.0"

log "function $WEB"
aws s3 cp "$BUILD_DIR/web.zip" "s3://$MODELS_BUCKET/deploy/web.zip" --only-show-errors
aws logs create-log-group --log-group-name "/aws/lambda/$WEB" 2>/dev/null || true
aws logs put-retention-policy --log-group-name "/aws/lambda/$WEB" --retention-in-days "$LOG_RETENTION_DAYS"
if aws lambda get-function --function-name "$WEB" >/dev/null 2>&1; then
  aws lambda update-function-code --function-name "$WEB" --s3-bucket "$MODELS_BUCKET" --s3-key deploy/web.zip >/dev/null
  aws lambda wait function-updated --function-name "$WEB"
  aws lambda update-function-configuration --function-name "$WEB" --memory-size 1024 --timeout 60 --layers "$LWA_LAYER" --environment "Variables={$ENV}" >/dev/null
else
  aws lambda create-function --function-name "$WEB" --runtime nodejs22.x --architectures "$ARCH" --handler run.sh \
    --role "arn:aws:iam::$ACCOUNT_ID:role/$ROLE" --code "S3Bucket=$MODELS_BUCKET,S3Key=deploy/web.zip" --memory-size 1024 --timeout 60 \
    --layers "$LWA_LAYER" --environment "Variables={$ENV}" --tags "$TAGS" >/dev/null
fi
aws lambda wait function-active-v2 --function-name "$WEB" 2>/dev/null || aws lambda wait function-active --function-name "$WEB"

log "public Function URL (AuthType NONE) — the app itself is the public entry point"
aws lambda get-function-url-config --function-name "$WEB" >/dev/null 2>&1 || aws lambda create-function-url-config --function-name "$WEB" --auth-type NONE --invoke-mode BUFFERED >/dev/null
aws lambda add-permission --function-name "$WEB" --statement-id FunctionURLAllowPublicAccess --action lambda:InvokeFunctionUrl --principal '*' --function-url-auth-type NONE >/dev/null 2>&1 || true
aws lambda add-permission --function-name "$WEB" --statement-id FunctionURLInvokeViaUrl --action lambda:InvokeFunction --principal '*' --invoked-via-function-url >/dev/null 2>&1 || true
URL="$(aws lambda get-function-url-config --function-name "$WEB" --query FunctionUrl --output text)"
ORIGIN="${URL%/}"

log "S3 uploads CORS: allow the site origin for presigned browser uploads"
aws s3api put-bucket-cors --bucket "$UPLOADS_BUCKET" --cors-configuration "{\"CORSRules\":[{\"AllowedOrigins\":[\"http://localhost:3000\",\"http://localhost:3100\",\"$ORIGIN\"],\"AllowedMethods\":[\"PUT\"],\"AllowedHeaders\":[\"*\"],\"MaxAgeSeconds\":300}]}"
echo "$URL" > "$BUILD_DIR/web-url.txt"
echo "DEPLOYED: $URL"
