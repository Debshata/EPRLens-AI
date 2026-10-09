"""Anomaly system: model + threshold load, rule contract, sample behaviour."""
import joblib

from conftest import ADIR, load, needs_artifacts
from eprlens_ml import anomaly_features as af
from rules import anomaly_rules as ar


@needs_artifacts
def test_model_and_threshold_load():
    m = joblib.load(ADIR / "isolation_forest.joblib")
    thr = load(ADIR / "threshold.json")
    assert m.n_features_in_ == len(af.FEATURES)
    assert 0 < thr["threshold"] <= 1 and thr["chosen_on"].startswith("validation")


@needs_artifacts
def test_scores_deterministic():
    m = joblib.load(ADIR / "isolation_forest.joblib")
    ref = joblib.load(ADIR / "preprocessor.joblib")["rate_reference_per_kg"]
    x = [af.vector(af.anomaly_features(load(ADIR / "sample_input.json"), ref))]
    assert (m.score_samples(x) == m.score_samples(x)).all()


def test_every_rule_returns_contract_fields():
    inv = {"record_type": "invoice",
           "invoice": {"invoice_type": "PKG_PURCHASE", "invoice_date": "2026-01-02", "total": 118.0,
                       "total_taxable_value": 100.0, "gst": 18.0, "supplier_id": "SUP_0001"},
           "lines": [{"line_no": 1, "raw_quantity": 10, "raw_unit": "kg", "hsn_code": "3923",
                      "normalized_quantity_kg": 10.0, "taxable_value": 100.0,
                      "transaction": {"raw_unit": "kg", "normalized_quantity_kg": 100.0, "status": "posted"}}],
           "master": {}, "context": {}}
    out = ar.run_rules(inv)
    assert {r["rule_id"] for r in out} <= set(ar.RULE_CATALOGUE)
    for r in out:
        assert set(r) == {"rule_id", "triggered", "severity", "reason"}
    fired = {r["rule_id"] for r in out if r["triggered"]}
    assert {"QTY_MATCH_TOL", "QTY_RATIO_POW10"} <= fired


def test_recycling_rules():
    rec = {"record_type": "recycling",
           "recycling": {"waste_generated_kg": 100, "waste_collected_kg": 120, "waste_recycled_kg": 130,
                         "recycler_id": "REC_X"},
           "master": {"recycler_registered": False}}
    fired = {r["rule_id"] for r in ar.run_rules(rec) if r["triggered"]}
    assert fired == {"RECYCLED_LE_COLLECTED", "COLLECTED_LE_GENERATED", "RECYCLER_REGISTERED"}


@needs_artifacts
def test_demo_sample_is_flagged():
    import lambda_anomaly_handler as h
    h._STATE.clear()
    out = h.handler(load(ADIR / "sample_input.json"))
    assert out["status"] == "success" and out["is_anomaly"] is True and out["rule_findings"]
