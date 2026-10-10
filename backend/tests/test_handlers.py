import json

import pytest

from tests.helpers import MOCKS, SAMPLES, load_handler

EVENTS = {n: json.loads((__import__("pathlib").Path(__file__).resolve().parents[1] / "test-events" / f"{n}.json").read_text()) for n in ("parse-invoice", "reconcile", "scenario-engine", "validate-transactions", "classify-image", "classify-image-carton")}
CTX = None


def test_scenario_handler():
    out = load_handler("scenario-engine")(EVENTS["scenario-engine"], CTX)
    assert out["reduction_kg"] == 500 and out["hypothetical"] is True


def test_scenario_handler_error_shape_has_next_step():
    out = load_handler("scenario-engine")({"units": -5, "current_g_per_unit": 25, "proposed_g_per_unit": 20}, CTX)
    assert out["statusCode"] == 400 and out["body"]["next_step"] and out["body"]["code"] == "invalid_input"


def test_classify_cardboard_and_shape():
    out = load_handler("classify-image")(EVENTS["classify-image-carton"], CTX)
    assert set(out) == {"predicted_class", "confidence", "uncertain", "model_version"}
    assert out["predicted_class"] == "cardboard" and 0 <= out["confidence"] <= 1


def test_classify_rejects_non_image_with_next_step(tmp_path):
    bad = tmp_path / "x.png"
    bad.write_bytes(b"not an image")
    out = load_handler("classify-image")({"local_path": str(bad)}, CTX)
    assert out["statusCode"] == 400 and "image" in out["body"]["message"].lower()


def test_parse_rejects_non_pdf(tmp_path):
    bad = tmp_path / "x.pdf"
    bad.write_bytes(b"hello")
    out = load_handler("parse-invoice")({"local_path": str(bad)}, CTX)
    assert out["statusCode"] == 400 and out["body"]["next_step"]


def test_missing_file_is_a_friendly_404():
    out = load_handler("parse-invoice")({"local_path": "/nope/missing.pdf"}, CTX)
    assert out["statusCode"] == 404 and out["body"]["code"] == "file_not_found"


def test_demo_flow_parse_validate_reconcile_matches_frontend_fixture():
    inv = load_handler("parse-invoice")(EVENTS["parse-invoice"], CTX)
    assert inv["document_id"] == "DOC_000832"
    csv = load_handler("reconcile")(EVENTS["validate-transactions"], CTX)
    assert csv["row_count"] == 15 and csv["missing_required_columns"] == []
    res = load_handler("reconcile")(EVENTS["reconcile"], CTX)
    assert len(res["findings"]) == 1
    f = res["findings"][0]
    fixture = next(x for x in json.loads((MOCKS / "reconciliation.json").read_text())["findings"] if x["invoice_id"] == "INV_00017685")
    assert f["difference_kg"] == fixture["difference_kg"] == 499500
    assert f["expected"]["value_kg"] == fixture["expected"]["value_kg"] == 500
    assert f["observed"]["value_kg"] == fixture["observed"]["value_kg"] == 500000
    assert f["rule_ids"] == fixture["rule_ids"] and f["severity"] == fixture["severity"]
    assert f["legal_determination"] is False and f["observed"]["source_ref"] == "TXN_00121740"


def test_reconcile_before_parse_asks_to_upload_first():
    out = load_handler("reconcile")({"action": "reconcile", "company_id": "COMP_NEW", "document_id": "DOC_999999", "csv_local_path": str(SAMPLES / "transactions_demo.csv")}, CTX)
    assert out["statusCode"] == 404 and "upload" in out["body"]["next_step"].lower()


def test_csv_missing_columns_is_reported(tmp_path):
    f = tmp_path / "t.csv"
    f.write_text("transaction_id,date\nT1,2026-03-01\n")
    out = load_handler("reconcile")({"action": "validate_transactions", "local_path": str(f)}, CTX)
    assert out["missing_required_columns"] == ["company_id", "raw_quantity", "raw_unit"]


def test_forecast_matches_frontend_fixture():
    out = load_handler("forecast")({"action": "forecast", "company_id": "COMP_0001"}, CTX)
    fx = json.loads((MOCKS / "forecast.json").read_text())["forecast"]
    got = out["forecast"]
    assert got["interval"] is None and got["synthetic_only"] is True
    assert [p["month"] for p in got["points"]] == [p["month"] for p in fx["points"]] == ["2026-04", "2026-05", "2026-06"]
    for a, b in zip(got["points"], fx["points"]):
        assert a["packaging_kg"] == pytest.approx(b["packaging_kg"], rel=1e-4)
    assert [p["kind"] for p in got["points"]] == ["model", "projected", "projected"]


def test_forecast_unknown_company_has_next_step():
    out = load_handler("forecast")({"company_id": "COMP_X"}, CTX)
    assert out["statusCode"] == 404 and out["body"]["next_step"]


def test_company_data_actions():
    h = load_handler("company-data")
    assert h({"action": "get_company_profile", "company_id": "COMP_0001"}, CTX)["company"]["company_name"].startswith("EcoFizz")
    assert "monthly_placed_on_market" in h({"action": "dashboard_summary", "company_id": "COMP_0001"}, CTX)
    assert h({"action": "simulator_catalog", "company_id": "COMP_0001"}, CTX)["products"]
    assert h({"action": "dashboard_summary", "company_id": "COMP_LOCAL_1"}, CTX)["statusCode"] == 404
    made = h({"action": "create_company", "company": {"company_name": "Test Co", "roles": ["importer"], "industry": "FMCG"}}, CTX)
    assert made["roles"]["importer"] is True and made["company"]["company_id"].startswith("COMP_LOCAL_")


def test_detect_anomaly_sample_matches_ml_output():
    out = load_handler("detect-anomaly")({"use_sample": True}, CTX)
    assert out["is_anomaly"] is True and out["anomaly_score"] == pytest.approx(0.599222, abs=1e-5)
    assert {r["rule_id"] for r in out["rule_findings"]} == {"QTY_MATCH_TOL", "QTY_RATIO_POW10"}
