#!/usr/bin/env bash
# Fast redeploy of ONE function after a code change (reuses the dependencies already in build/pkg-<fn>).
#   ./45-redeploy.sh forecast
source "$(dirname "$0")/config.sh"
f="${1:?usage: 45-redeploy.sh <function-dir-name>}"
d="${BUILD_DIR:?}/pkg-${f:?}"
[ -d "$d" ] || { echo "run 30-package.sh first (no $d)"; exit 1; }
cp "$REPO_ROOT/backend/lambdas/$f/handler.py" "$d/handler.py"
rm -rf "${d:?}/eprlens_shared" && cp -R "$REPO_ROOT/backend/shared/eprlens_shared" "$d/eprlens_shared"
find "$d/eprlens_shared" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
rm -f "${BUILD_DIR:?}/${f:?}.zip"; (cd "$d" && zip -qr9 "${BUILD_DIR:?}/${f:?}.zip" .)
aws s3 cp "$BUILD_DIR/$f.zip" "s3://$MODELS_BUCKET/deploy/$f.zip" --only-show-errors
aws lambda update-function-code --function-name "$(fn_name "$f")" --s3-bucket "$MODELS_BUCKET" --s3-key "deploy/$f.zip" >/dev/null
aws lambda wait function-updated --function-name "$(fn_name "$f")"
echo "redeployed $(fn_name "$f")"
