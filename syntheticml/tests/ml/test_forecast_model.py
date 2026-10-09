"""Exported forecast model: loads, deterministic, sensible output, metrics recorded honestly."""
import json

from conftest import FDIR, ROOT, load, needs_artifacts


@needs_artifacts
def test_model_loads_and_reproduces_sample_output():
    import lambda_forecast_handler as h
    h._STATE.clear()
    req, exp = load(FDIR / "sample_input.json"), load(FDIR / "sample_output.json")
    a, b = h.handler(req), h.handler(req)
    assert a == b == exp
    assert a["forecast_kg"] > 0


@needs_artifacts
def test_scaling_history_scales_forecast():
    import lambda_forecast_handler as h
    req = load(FDIR / "sample_input.json")
    big = dict(req, history=[dict(x, packaging_kg=x["packaging_kg"] * 10) for x in req["history"]])
    a, b = h.handler(req)["forecast_kg"], h.handler(big)["forecast_kg"]
    assert 5 < b / a < 20   # scale-free model: about 10x (the log-size feature allows small differences)


@needs_artifacts
def test_metrics_are_recorded_and_test_is_separate_from_validation():
    meta = load(FDIR / "model_metadata.json")
    m = meta["metrics"]
    assert set(m["test"]) >= {"mae_kg", "rmse_kg", "r2"} and set(m["validation"]) >= {"mae_kg", "rmse_kg", "r2"}
    assert m["test"]["rows"] == meta["test_rows"] and m["validation"]["rows"] == meta["validation_rows"]
    metrics = json.loads((ROOT / "ml/evaluation/forecast/metrics.json").read_text())
    assert metrics["target_met"] == (metrics["winner"]["test"]["r2"] >= metrics["target_r2"])
