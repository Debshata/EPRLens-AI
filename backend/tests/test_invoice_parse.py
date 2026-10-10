import json

import pytest

from eprlens_shared.invoice_parse import extract_text, parse_invoice_text
from tests.helpers import GEN, SAMPLES


def parse(doc_id: str) -> tuple[dict, dict]:
    raw = (GEN / "pdf" / f"{doc_id}.pdf").read_bytes()
    text, pages = extract_text(raw)
    gt = json.loads((GEN / "json" / f"{doc_id}.json").read_text(encoding="utf-8"))["expected_fields"]
    return parse_invoice_text(text, pages, doc_id, f"{doc_id}.pdf", "0" * 64), gt


def test_demo_invoice_0_5_mt():
    raw = (SAMPLES / "DOC_000832.pdf").read_bytes()
    text, pages = extract_text(raw)
    inv = parse_invoice_text(text, pages, "DOC_000832", "DOC_000832.pdf", "x")
    assert inv["invoice_number"] == "SYEC/2526/00004" and inv["invoice_date"] == "2025-11-17"
    assert inv["vendor"]["name"] == "Ecoglow PET Bottles Pvt Ltd"
    line = inv["lines"][0]
    assert (line["quantity"], line["printed_unit"], line["normalized_quantity_kg"]) == (0.5, "Tonne", 500.0)
    assert inv["total_amount"] == 124524.33
    assert inv["extraction"]["status"] == "success"


# one document per layout (L01..L12) plus the tricky ones: credit note, blank quantity, multi-page, missing date
DOCS = ["DOC_000002", "DOC_000003", "DOC_000045", "DOC_000053", "DOC_000022", "DOC_000004", "DOC_000005", "DOC_000008", "DOC_000016", "DOC_000266", "DOC_000001", "DOC_000025", "DOC_000035", "DOC_000014", "DOC_000012"]


@pytest.mark.parametrize("doc", DOCS)
def test_matches_ground_truth(doc):
    got, gt = parse(doc)
    assert got["invoice_number"] == gt["invoice_number"]
    assert (got["invoice_date"] or None) == (gt.get("invoice_date") or None)
    assert got["vendor"]["name"] == gt["vendor"]
    assert len(got["lines"]) == len(gt["lines"])
    for g, e in zip(got["lines"], gt["lines"]):
        if e["quantity"] is None:
            assert g["quantity"] is None  # missing in the document: never zero
        else:
            assert g["quantity"] == pytest.approx(float(e["quantity"]))
        if g["normalized_quantity_kg"] is not None and e["normalized_quantity_kg"] is not None:
            assert g["normalized_quantity_kg"] == pytest.approx(e["normalized_quantity_kg"], rel=1e-4, abs=0.01)
        if g["normalized_quantity_kg"] is None:
            assert e.get("normalization_requires_master") or e["normalized_quantity_kg"] is None


def test_missing_values_are_flagged_not_invented():
    got, _ = parse("DOC_000014")  # a blank quantity cell in the PDF
    assert got["lines"][0]["quantity"] is None and got["lines"][0]["normalized_quantity_kg"] is None
    assert got["extraction"]["status"] == "needs_review"
    f = next(x for x in got["fields"] if x["field"] == "line1.quantity")
    assert f["status"] == "unknown" and f["review_state"] == "needs_review"
