#!/usr/bin/env bash
# IAM role for the Amplify-hosted Next.js SERVER code (SSR compute role): no access keys needed.
# Same narrow permissions as the local frontend user: invoke the ${PREFIX}-* Lambdas and presign PutObject on uploads/*.
source "$(dirname "$0")/config.sh"
ROLE="${PREFIX}-amplify-ssr"
mkdir -p "${BUILD_DIR:?}"
aws iam get-role --role-name "$ROLE" >/dev/null 2>&1 || aws iam create-role --role-name "$ROLE" --assume-role-policy-document "file://$REPO_ROOT/infrastructure/iam/amplify-trust.json" --tags Key=Project,Value=EPRLens >/dev/null
sed -e "s|__REGION__|$AWS_REGION|g" -e "s|__ACCOUNT__|$ACCOUNT_ID|g" -e "s|__PREFIX__|$PREFIX|g" -e "s|__UPLOADS_BUCKET__|$UPLOADS_BUCKET|g" "$REPO_ROOT/infrastructure/iam/frontend-invoker.json" > "$BUILD_DIR/amplify-ssr-policy.json"
aws iam put-role-policy --role-name "$ROLE" --policy-name "${PREFIX}-amplify-ssr-access" --policy-document "file://$BUILD_DIR/amplify-ssr-policy.json"
echo "role arn: arn:aws:iam::$ACCOUNT_ID:role/$ROLE"
