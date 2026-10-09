"""AWS JSON contracts: exact keys, plain JSON types, clean errors."""
import json

from conftest import ADIR, FDIR, load, needs_artifacts

FORECAST_KEYS = {"company_id", "product_id", "target_month", "forecast_kg", "model_version", "model_name", "status"}
ANOMALY_KEYS = {"record_id", "is_anomaly", "anomaly_score", "threshold", "ml_flag", "rule_findings", "model_version",
                "status"}


def _plain(o):
    if isinstance(o, dict):
        return all(isinstance(k, str) and _plain(v) for k, v in o.items())
    if isinstance(o, list):
        return all(_plain(v) for v in o)
    return o is None or type(o) in (str, int, float, bool)


@needs_artifacts
def test_forecast_contract():
    import lambda_forecast_handler as h
    out = h.handler(load(FDIR / "sample_input.json"))
    assert set(out) == FORECAST_KEYS and out["status"] == "success" and out["model_version"] == "forecast-v1"
    assert _plain(out) and json.loads(json.dumps(out)) == out
    assert h.handler({"body": json.dumps(load(FDIR / "sample_input.json"))}) == out   # API-style string body
    err = h.handler({"company_id": "C"})
    assert err["status"] == "error" and _plain(err)


@needs_artifacts
def test_anomaly_contract():
    import lambda_anomaly_handler as h
    out = h.handler(load(ADIR / "sample_input.json"))
    assert set(out) == ANOMALY_KEYS and out["model_version"] == "anomaly-v1" and _plain(out)
    for f in out["rule_findings"]:
        assert set(f) == {"rule_id", "severity", "reason"}
    assert h.handler({"record_type": "invoice"})["status"] == "error"


@needs_artifacts
def test_sample_outputs_follow_schema():
    assert set(load(FDIR / "sample_output.json")) == FORECAST_KEYS
    assert set(load(ADIR / "sample_output.json")) == ANOMALY_KEYS
