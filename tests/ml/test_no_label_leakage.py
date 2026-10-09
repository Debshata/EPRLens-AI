"""Label columns can never become model inputs."""
import pytest

from conftest import ADIR, FDIR, ROOT, load, needs_artifacts, needs_data
from eprlens_ml import anomaly_features as af
from eprlens_ml import forecast_features as ff

LEAK = ["is_anomaly", "anomaly_type", "expected_detection", "ground_truth", "bad_value", "test_case_type"]


@pytest.mark.parametrize("col", LEAK)
def test_guard_rejects_label_columns(col):
    with pytest.raises(ValueError):
        af.assert_no_label_fields(af.FEATURES + [col])


def test_feature_lists_contain_no_labels_or_target():
    for col in LEAK + ["next_month_packaging_kg", "anomaly_types", "split"]:
        assert col not in af.FEATURES and col not in ff.FEATURES


@needs_data
def test_loader_drops_labels_before_records_are_built():
    import yaml
    from eprlens_ml import data
    cfg = yaml.safe_load((ROOT / "ml/configs/synthetic_ml.yaml").read_text())
    inv, *_ = data.load_observed(cfg)
    assert not set(inv.columns) & data.LABEL_COLUMNS


@needs_artifacts
def test_exported_schema_and_handler_reject_labels():
    import lambda_anomaly_handler as h
    assert set(LEAK) <= set(load(ADIR / "feature_schema.json")["forbidden_inputs"])
    rec = load(ADIR / "sample_input.json")
    rec["lines"][0]["anomaly_type"] = "AN01"
    assert h.handler(rec)["status"] == "error"


@needs_artifacts
def test_model_metadata_features_are_clean():
    for d in (FDIR, ADIR):
        assert not set(load(d / "model_metadata.json")["features"]) & set(LEAK)
