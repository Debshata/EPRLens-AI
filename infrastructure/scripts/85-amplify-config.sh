#!/usr/bin/env bash
# After the Amplify app exists (created in the console by connecting GitHub), configure it from the CLI and start a build.
#   ./85-amplify-config.sh <app-id> [branch-name]
source "$(dirname "$0")/config.sh"
APP_ID="${1:?usage: 85-amplify-config.sh <app-id> [branch]}"
BRANCH="${2:-feat/synthetic-entity-master}"
ROLE_ARN="arn:aws:iam::$ACCOUNT_ID:role/${PREFIX}-amplify-ssr"
# names only: no secrets of any kind go into Amplify
ENV_JSON="$(python3 - <<PY
import json
print(json.dumps({
  "AMPLIFY_MONOREPO_APP_ROOT": "frontend",
  "NEXT_PUBLIC_API_MODE": "live",
  "UPLOADS_BUCKET": "$UPLOADS_BUCKET",
  "LAMBDA_PARSE_INVOICE": "$(fn_name parse-invoice)",
  "LAMBDA_RECONCILE": "$(fn_name reconcile)",
  "LAMBDA_CLASSIFY_IMAGE": "$(fn_name classify-image)",
  "LAMBDA_FORECAST": "$(fn_name forecast)",
  "LAMBDA_DETECT_ANOMALY": "$(fn_name detect-anomaly)",
  "LAMBDA_SCENARIO_ENGINE": "$(fn_name scenario-engine)",
  "LAMBDA_COMPANY_DATA": "$(fn_name company-data)",
}))
PY
)"
log "configure app $APP_ID (WEB_COMPUTE, compute role, env vars)"
aws amplify update-app --app-id "$APP_ID" --platform WEB_COMPUTE --compute-role-arn "$ROLE_ARN" --environment-variables "$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); print(','.join(f'{k}={v}' for k,v in d.items()))" "$ENV_JSON")" >/dev/null
log "start build for branch $BRANCH"
JOB="$(aws amplify start-job --app-id "$APP_ID" --branch-name "$BRANCH" --job-type RELEASE --query 'jobSummary.jobId' --output text)"
echo "job $JOB started. Watch: aws amplify get-job --app-id $APP_ID --branch-name $BRANCH --job-id $JOB --query 'job.summary.status'"
DOMAIN="$(aws amplify get-app --app-id "$APP_ID" --query 'app.defaultDomain' --output text)"
echo "default domain: $DOMAIN  ->  https://${BRANCH//\//-}.$DOMAIN"
