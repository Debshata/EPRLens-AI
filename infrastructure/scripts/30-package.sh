#!/usr/bin/env bash
# Builds one zip per Lambda in infrastructure/build/ (Linux x86_64, Python 3.12 wheels; no Docker needed).
source "$(dirname "$0")/config.sh"
command -v zip >/dev/null || { echo "zip is required"; exit 1; }
PY="${PYTHON:-python3}"
mkdir -p "$BUILD_DIR"

# dependencies come from backend/lambdas/<fn>/requirements.txt (comments and blank lines ignored)
reqs_of() { grep -vE '^\s*(#|$)' "$REPO_ROOT/backend/lambdas/$1/requirements.txt" 2>/dev/null | tr '\n' ' ' || true; }

for f in $FUNCTIONS; do
  log "package $f"
  d="$BUILD_DIR/pkg-$f"; rm -rf "$d"; mkdir -p "$d"
  REQ="$(reqs_of "$f")"
  if [ -n "$REQ" ]; then
    # shellcheck disable=SC2086
    "$PY" -m pip install --quiet --no-compile --target "$d" --platform manylinux_2_28_x86_64 --platform manylinux_2_27_x86_64 --platform manylinux2014_x86_64 --implementation cp --python-version 3.12 --only-binary=:all: $REQ
  fi
  cp "$REPO_ROOT/backend/lambdas/$f/handler.py" "$d/handler.py"
  cp -R "$REPO_ROOT/backend/shared/eprlens_shared" "$d/eprlens_shared"
  case "$f" in
    forecast)       cp "$REPO_ROOT/syntheticml/ml/aws_examples/lambda_forecast_handler.py" "$d/" ;;
    detect-anomaly) cp "$REPO_ROOT/syntheticml/ml/aws_examples/lambda_anomaly_handler.py" "$d/" ;;
  esac
  find "$d" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
  find "$d" -name '*.dist-info' -type d -prune -exec rm -rf {} + 2>/dev/null || true
  rm -f "$BUILD_DIR/$f.zip"; (cd "$d" && zip -qr9 "$BUILD_DIR/$f.zip" .)
  echo "$f.zip  $(du -h "$BUILD_DIR/$f.zip" | cut -f1) zipped, $(du -sh "$d" | cut -f1) unzipped (limit 250 MB unzipped)"
done
