#!/usr/bin/env bash
# Deletes EVERYTHING this project created (functions, roles, user, table, buckets, log groups). Requires --yes.
source "$(dirname "$0")/config.sh"
[ "${1:-}" = "--yes" ] || { echo "This deletes all EPRLens AWS resources in $AWS_REGION for account $ACCOUNT_ID. Re-run with --yes."; exit 1; }

for f in $FUNCTIONS; do
  n="$(fn_name "$f")"; r="$(role_name "$f")"
  aws lambda delete-function --function-name "$n" 2>/dev/null && echo "deleted function $n" || true
  aws logs delete-log-group --log-group-name "/aws/lambda/$n" 2>/dev/null || true
  for p in $(aws iam list-attached-role-policies --role-name "$r" --query 'AttachedPolicies[].PolicyArn' --output text 2>/dev/null); do aws iam detach-role-policy --role-name "$r" --policy-arn "$p"; done
  for p in $(aws iam list-role-policies --role-name "$r" --query 'PolicyNames[]' --output text 2>/dev/null); do aws iam delete-role-policy --role-name "$r" --policy-name "$p"; done
  aws iam delete-role --role-name "$r" 2>/dev/null && echo "deleted role $r" || true
done
WEB="${PREFIX}-web"; WROLE="${PREFIX}-lambda-web"
aws lambda delete-function-url-config --function-name "$WEB" 2>/dev/null || true
aws lambda delete-function --function-name "$WEB" 2>/dev/null && echo "deleted function $WEB" || true
aws logs delete-log-group --log-group-name "/aws/lambda/$WEB" 2>/dev/null || true
for p in $(aws iam list-attached-role-policies --role-name "$WROLE" --query 'AttachedPolicies[].PolicyArn' --output text 2>/dev/null); do aws iam detach-role-policy --role-name "$WROLE" --policy-arn "$p"; done
for p in $(aws iam list-role-policies --role-name "$WROLE" --query 'PolicyNames[]' --output text 2>/dev/null); do aws iam delete-role-policy --role-name "$WROLE" --policy-name "$p"; done
aws iam delete-role --role-name "$WROLE" 2>/dev/null && echo "deleted role $WROLE" || true
for k in $(aws iam list-access-keys --user-name "$FRONTEND_USER" --query 'AccessKeyMetadata[].AccessKeyId' --output text 2>/dev/null); do aws iam delete-access-key --user-name "$FRONTEND_USER" --access-key-id "$k"; done
for p in $(aws iam list-user-policies --user-name "$FRONTEND_USER" --query 'PolicyNames[]' --output text 2>/dev/null); do aws iam delete-user-policy --user-name "$FRONTEND_USER" --policy-name "$p"; done
aws iam delete-user --user-name "$FRONTEND_USER" 2>/dev/null && echo "deleted user $FRONTEND_USER" || true
aws dynamodb delete-table --table-name "$TABLE" >/dev/null 2>&1 && echo "deleted table $TABLE" || true
for b in "$UPLOADS_BUCKET" "$MODELS_BUCKET"; do
  aws s3 rm "s3://$b" --recursive --only-show-errors 2>/dev/null || true
  aws s3api delete-bucket --bucket "$b" 2>/dev/null && echo "deleted bucket $b" || true
done
rm -f "$REPO_ROOT/frontend/.env.local"
echo "teardown complete. Also review Billing to confirm nothing is running."
