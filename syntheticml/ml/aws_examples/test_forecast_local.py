"""Run the exported forecast artifact locally exactly as Lambda would — no retraining.

    python ml/aws_examples/test_forecast_local.py
SYNTHETIC — EPRLens Demo."""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lambda_forecast_handler as h  # noqa: E402

ART = h._artifact_dir()
REQUIRED = {"company_id", "product_id", "target_month", "forecast_kg", "model_version", "model_name", "status"}


def main():
    req = json.loads((ART / "sample_input.json").read_text(encoding="utf-8"))
    t0 = time.perf_counter()
    out = h.handler(req)
    ms = (time.perf_counter() - t0) * 1000
    print(json.dumps(out, indent=2))
    assert out["status"] == "success", out
    assert REQUIRED <= set(out), set(out)
    json.dumps(out)  # must be plain JSON
    expected = json.loads((ART / "sample_output.json").read_text(encoding="utf-8"))
    assert abs(out["forecast_kg"] - expected["forecast_kg"]) <= 1e-6 * max(1.0, expected["forecast_kg"]), (out, expected)
    bad = h.handler({"company_id": "C", "product_id": "P", "industry": "Beverages", "history": []})
    assert bad["status"] == "error", bad
    print(f"OK — matches sample_output.json; first call incl. model load {ms:.1f} ms (LOCAL machine timing)")


if __name__ == "__main__":
    main()
