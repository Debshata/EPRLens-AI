"""Anomaly features: fixed order, finite, deterministic, label-free."""
import math

from conftest import ADIR, load, needs_artifacts
from eprlens_ml import anomaly_features as af


def test_feature_names_fixed_and_label_free():
    assert len(af.FEATURES) == len(set(af.FEATURES)) == 19
    af.assert_no_label_fields(af.FEATURES)


@needs_artifacts
def test_sample_record_features_finite_and_deterministic():
    rec = load(ADIR / "sample_input.json")
    a, b = af.anomaly_features(rec), af.anomaly_features(rec)
    assert a == b and list(a) == af.FEATURES
    assert all(math.isfinite(v) for v in af.vector(a))


def test_missing_context_is_handled():
    rec = {"invoice": {"invoice_type": "FG_SALES", "total": 100.0},
           "lines": [{"line_no": 1, "normalized_quantity_kg": 5.0}]}
    f = af.anomaly_features(rec)
    assert f["item_spike"] == 0.0 and f["type_FG_SALES"] == 1.0
