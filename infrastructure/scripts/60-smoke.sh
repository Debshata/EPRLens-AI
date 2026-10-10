#!/usr/bin/env bash
# Uploads the bundled samples and invokes every function once. Prints a one-line verdict per function; exits non-zero on failure.
source "$(dirname "$0")/config.sh"
SAMPLES="$REPO_ROOT/frontend/public/samples"
K=uploads/COMP_0001
aws s3 cp "$SAMPLES/sample-carton.png" "s3://$UPLOADS_BUCKET/$K/images/sample-carton.png" --only-show-errors
aws s3 cp "$SAMPLES/DOC_000832.pdf" "s3://$UPLOADS_BUCKET/$K/invoices/DOC_000832.pdf" --only-show-errors
aws s3 cp "$SAMPLES/transactions_demo.csv" "s3://$UPLOADS_BUCKET/$K/csv/transactions_demo.csv" --only-show-errors

OUT="$BUILD_DIR/smoke"; mkdir -p "$OUT"
FAIL=0
invoke() { # function  json-event  python-expression-on-"r"
  local f="$1" ev="$2" check="$3" out="$OUT/$1.json"
  aws lambda invoke --function-name "$(fn_name "$f")" --cli-binary-format raw-in-base64-out --payload "$ev" "$out" >"$OUT/$f.meta.json"
  python3 - "$out" "$OUT/$f.meta.json" "$f" "$check" <<'PY' || FAIL=1
import json, sys
out, meta, f, check = sys.argv[1:5]
m = json.load(open(meta)); r = json.load(open(out))
ok = "FunctionError" not in m and not (isinstance(r, dict) and "statusCode" in r) and bool(eval(check))
print(("PASS " if ok else "FAIL ") + f, "" if ok else json.dumps(r)[:300])
sys.exit(0 if ok else 1)
PY
}
S3I="\"s3\":{\"bucket\":\"$UPLOADS_BUCKET\",\"key\":\"$K"
invoke scenario-engine '{"action":"what_if","units":100000,"current_g_per_unit":25,"proposed_g_per_unit":20}' 'r["reduction_kg"]==500'
invoke classify-image "{\"company_id\":\"COMP_0001\",$S3I/images/sample-carton.png\"}}" 'r["predicted_class"]=="cardboard"'
invoke parse-invoice "{\"company_id\":\"COMP_0001\",$S3I/invoices/DOC_000832.pdf\"}}" 'r["invoice_number"]=="SYEC/2526/00004" and r["lines"][0]["normalized_quantity_kg"]==500'
invoke reconcile "{\"action\":\"validate_transactions\",\"company_id\":\"COMP_0001\",$S3I/csv/transactions_demo.csv\"}}" 'r["row_count"]==15'
invoke reconcile "{\"action\":\"reconcile\",\"company_id\":\"COMP_0001\",\"document_id\":\"DOC_000832\",\"csv\":{\"bucket\":\"$UPLOADS_BUCKET\",\"key\":\"$K/csv/transactions_demo.csv\"}}" 'r["findings"][0]["difference_kg"]==499500'
invoke company-data '{"action":"dashboard_summary","company_id":"COMP_0001"}' 'len(r["monthly_placed_on_market"])==36'
invoke forecast '{"action":"forecast","company_id":"COMP_0001"}' 'r["forecast"]["points"][0]["month"]=="2026-04" and r["forecast"]["interval"] is None'
invoke detect-anomaly '{"use_sample":true}' 'r["is_anomaly"] is True'
[ "$FAIL" = 0 ] && echo "ALL PASSED" || { echo "SOME FAILED (see $OUT)"; exit 1; }
