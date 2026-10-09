"""Reproducibility of the full-dataset generator on a small pilot (5 companies, 20 PDFs)."""
from pathlib import Path

import generate as gen

SD = Path(__file__).resolve().parents[1]


def _run(out):
    return gen.run(SD / "config.yaml", out, company_limit=5, pdf_total=20)["manifest"]


def test_same_seed_reproduces_every_file(tmp_path):
    a, b = _run(tmp_path / "a"), _run(tmp_path / "b")
    assert a["file_hashes"] == b["file_hashes"]
    assert a["document_hashes"] == b["document_hashes"]
    assert a["dataset_sha256"] == b["dataset_sha256"]
    assert a["counts"]["invoice_pdfs"] == len([k for k in a["document_hashes"] if k.endswith(".pdf")])
