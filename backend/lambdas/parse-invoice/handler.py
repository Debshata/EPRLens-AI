"""parse-invoice: digital PDF in S3 -> Invoice (fields + line items, original value/unit and kg). No OCR."""
import hashlib
import sys
from pathlib import Path

_here = Path(__file__).resolve()
for _c in (_here.parent, _here.parents[2] / "shared"):  # zip layout / repo layout
    if (_c / "eprlens_shared").is_dir():
        sys.path.insert(0, str(_c))
        break

from eprlens_shared.invoice_parse import extract_text, parse_invoice_text
from eprlens_shared.lambda_utils import run
from eprlens_shared.storage import read_bytes
from eprlens_shared.store import try_put

MAX_BYTES = 10 * 1024 * 1024


def _handle(ev: dict) -> dict:
    content, name = read_bytes(ev)
    if len(content) > MAX_BYTES:
        raise ValueError("The PDF is larger than 10 MB. Split or compress it and upload again.")
    if not content.startswith(b"%PDF"):
        raise ValueError("The file is not a PDF. Upload a text-based (digital) invoice PDF.")
    sha = hashlib.sha256(content).hexdigest()
    stem = name.rsplit(".", 1)[0]
    doc_id = stem if stem.startswith("DOC_") else f"DOC_{sha[:10]}"
    text, pages = extract_text(content)
    if len(text.strip()) < 40:
        raise ValueError("No readable text was found. Scanned images are not supported yet; upload a digital PDF.")
    invoice = parse_invoice_text(text, pages, doc_id, name, sha)
    if ev.get("company_id"):
        try_put(ev["company_id"], f"INVOICE#{doc_id}", {"invoice": invoice, "s3_key": (ev.get("s3") or {}).get("key", "")}, kind="invoice")
    return invoice


def handler(event, context=None):
    return run(event, _handle)
