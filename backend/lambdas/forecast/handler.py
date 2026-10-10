"""forecast: company history -> next-month packaging kg per company (+ labelled projected months). Model: forecast-v1 (XGBoost→ONNX)."""
import sys
from pathlib import Path

_here = Path(__file__).resolve()
for _c in (_here.parent, _here.parents[2] / "shared"):  # zip layout / repo layout
    if (_c / "eprlens_shared").is_dir():
        sys.path.insert(0, str(_c))
        break

for _c in (_here.parent, _here.parents[3] / "syntheticml" / "ml" / "aws_examples"):  # zip layout / repo layout
    if (_c / "lambda_forecast_handler.py").is_file():
        sys.path.insert(0, str(_c))
        break
import lambda_forecast_handler as ml  # reference handler from the ML team (loads model.onnx + preprocessor from S3/MODEL_BUCKET)

from eprlens_shared.forecast_company import build_forecast
from eprlens_shared.lambda_utils import run
from eprlens_shared.storage import StorageError, read_seed_json
from eprlens_shared.store import try_put


def _handle(ev: dict) -> dict:
    cid = ev.get("company_id")
    if not cid:
        raise ValueError("company_id is required.")
    if cid != "COMP_0001":
        raise StorageError("no_history", "There is no packaging history for this company yet.", "Upload at least 12 months of transaction data to enable a forecast.")
    result = build_forecast(read_seed_json(f"{cid}/forecast_history.json"), ml.handler)
    try_put(cid, f"FORECAST#{result['forecast']['points'][0]['month']}", result, kind="forecast")
    return result


def handler(event, context=None):
    return run(event, _handle)
