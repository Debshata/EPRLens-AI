"""Run the exported anomaly artifact locally exactly as Lambda would — no retraining.

    python ml/aws_examples/test_anomaly_local.py
SYNTHETIC — EPRLens Demo."""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lambda_anomaly_handler as h  # noqa: E402

ART = h._artifact_dir()
REQUIRED = {"is_anomaly", "anomaly_score", "threshold", "ml_flag", "rule_findings", "model_version", "status"}


def main():
    req = json.loads((ART / "sample_input.json").read_text(encoding="utf-8"))
    t0 = time.perf_counter()
    out = h.handler(req)
    ms = (time.perf_counter() - t0) * 1000
    print(json.dumps(out, indent=2))
    assert out["status"] == "success", out
    assert REQUIRED <= set(out), set(out)
    json.dumps(out)
    expected = json.loads((ART / "sample_output.json").read_text(encoding="utf-8"))
    assert out == expected, (out, expected)
    leak = dict(req, is_anomaly=True)
    assert h.handler(leak)["status"] == "error", "label fields must be rejected"
    rec = {"record_type": "recycling", "record_id": "RCY_TEST", "recycling": {
        "recycling_record_id": "RCY_TEST", "company_id": "COMP_0001", "month": "2026-01", "synthetic_category": "CAT_I",
        "waste_generated_kg": 100.0, "waste_collected_kg": 60.0, "waste_recycled_kg": 75.0, "recycler_id": "REC_0004",
        "recycler_registered": True, "credits_documented_kg": 50.0, "basis": "synthetic_proxy_v1"},
        "master": {"recycler_registered": True}}
    r2 = h.handler(rec)
    assert r2["status"] == "success" and r2["is_anomaly"] and r2["anomaly_score"] is None, r2
    print(f"OK — matches sample_output.json; first call incl. model load {ms:.1f} ms (LOCAL machine timing)")


if __name__ == "__main__":
    main()
