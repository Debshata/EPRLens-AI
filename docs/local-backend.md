# Running the backend locally (no AWS credentials)

```bash
python3 -m venv .venv && . .venv/bin/activate && pip install -r backend/requirements-dev.txt
python backend/seed/build_seed.py                     # regenerate backend/seed/reference (committed; optional)
pytest backend -q                                       # 37 tests: parser vs ground truth, handlers, contract parity
python backend/tools/evaluate_invoice_parser.py 1000    # parser accuracy on the 1,000 synthetic invoices
python backend/run_local.py parse-invoice   backend/test-events/parse-invoice.json
python backend/run_local.py reconcile       backend/test-events/validate-transactions.json
python backend/run_local.py reconcile       backend/test-events/reconcile.json      # run parse-invoice first
python backend/run_local.py classify-image  backend/test-events/classify-image-carton.json
python backend/run_local.py forecast        backend/test-events/forecast.json
python backend/run_local.py detect-anomaly  backend/test-events/detect-anomaly.json
python backend/run_local.py scenario-engine backend/test-events/scenario-engine.json
python backend/run_local.py company-data    backend/test-events/company-data.json
```
Locally the handlers read files via `local_path` and keep results in a temp JSON file (`LOCAL_STORE_FILE`) instead of DynamoDB. Python 3.11+ works locally; Lambda runs Python 3.12.

Measured on the 1,000 synthetic invoices (`backend/evaluation/invoice_parser_metrics.json`): invoice number, date, vendor, line count and total 100%; line quantity 3,839/3,846; kg value 3,846/3,846 (unknown where the PDF gives no weight). Synthetic layouts only — not real-world accuracy.
