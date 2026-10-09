"""Serialization: preprocessors and models reload to identical predictions; shipped code equals source."""
import joblib
import numpy as np

from conftest import ADIR, FDIR, load, needs_artifacts
from eprlens_ml import anomaly_features as af
from eprlens_ml import forecast_features as ff


def _src(module):
    return open(module.__file__, encoding="utf-8").read()


@needs_artifacts
def test_forecast_preprocessor_matches_feature_code():
    prep = joblib.load(FDIR / "preprocessor.joblib")
    assert prep["feature_order"] == ff.FEATURES == load(FDIR / "feature_schema.json")["feature_order"]
    assert (FDIR / prep["model_file"]).exists()
    assert (FDIR / "features.py").read_text(encoding="utf-8") == _src(ff)


@needs_artifacts
def test_forecast_model_file_round_trip():
    prep = joblib.load(FDIR / "preprocessor.joblib")
    req = load(FDIR / "sample_input.json")
    f, raw, *_ = ff.build_features(req["history"], req["industry"], prep["season_table"])
    X = np.asarray([ff.vector(f)])
    if prep["model_file"] == "model.onnx":
        import onnxruntime as ort

        def run():
            s = ort.InferenceSession(str(FDIR / "model.onnx"), providers=["CPUExecutionProvider"])
            return s.run(None, {"features": X.astype("float32")})[0].ravel()[0]
    else:
        def run():
            return joblib.load(FDIR / prep["model_file"]).predict(X)[0]
    p1, p2 = run(), run()
    assert p1 == p2
    assert abs(ff.to_kg(p1, raw["packaging_kg"]) - load(FDIR / "sample_output.json")["forecast_kg"]) < 1e-3


@needs_artifacts
def test_anomaly_artifacts_round_trip():
    prep = joblib.load(ADIR / "preprocessor.joblib")
    assert prep["feature_order"] == af.FEATURES
    m1, m2 = joblib.load(ADIR / "isolation_forest.joblib"), joblib.load(ADIR / "isolation_forest.joblib")
    x = np.random.default_rng(0).normal(size=(20, len(af.FEATURES)))
    assert np.array_equal(m1.score_samples(x), m2.score_samples(x))
    assert (ADIR / "features.py").read_text(encoding="utf-8") == _src(af)
