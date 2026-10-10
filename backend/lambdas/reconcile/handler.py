"""reconcile: parsed invoice + CSV transactions -> findings (rules-v1). Also validates an uploaded transaction CSV."""
import time
import sys
from pathlib import Path

_here = Path(__file__).resolve()
for _c in (_here.parent, _here.parents[2] / "shared"):  # zip layout / repo layout
    if (_c / "eprlens_shared").is_dir():
        sys.path.insert(0, str(_c))
        break

from eprlens_shared.csvio import summarize_transaction_csv
from eprlens_shared.lambda_utils import run
from eprlens_shared.reconcile import RULES_VERSION, TOLERANCES, find_index_entry, reconcile_invoice
from eprlens_shared.storage import StorageError, read_bytes, read_seed_json
from eprlens_shared.store import get_store, try_put


def _validate(ev: dict) -> dict:
    content, name = read_bytes(ev)
    if len(content) > 5 * 1024 * 1024:
        raise ValueError("The CSV is larger than 5 MB. Split it by month and upload again.")
    return summarize_transaction_csv(name, content.decode("utf-8-sig", errors="replace"))


def _reconcile(ev: dict) -> dict:
    company, doc = ev.get("company_id"), ev.get("document_id")
    if not company or not doc:
        raise ValueError("company_id and document_id are required.")
    saved = get_store().get(company, f"INVOICE#{doc}")
    if not saved:
        raise StorageError("invoice_not_found", "That invoice has not been analysed yet.", "Upload the invoice PDF first, then run reconciliation.")
    csv = _validate({"s3": ev.get("csv"), "local_path": ev.get("csv_local_path")})  # csv_local_path: local runs/tests only
    if csv["missing_required_columns"]:
        raise ValueError(f"The CSV is missing required columns: {', '.join(csv['missing_required_columns'])}. Add them and upload again.")
    invoice = saved["invoice"]
    entry = find_index_entry(read_seed_json("invoice_index.json"), invoice)
    findings = reconcile_invoice(invoice, entry, csv["rows"])
    result = {
        "analysis_id": f"run-{int(time.time())}",
        "schema_version": "0.4-proposal",
        "company_id": company,
        "rules_version": RULES_VERSION,
        "tolerances": TOLERANCES,
        "findings": findings,
    }
    try_put(company, f"RUN#{result['analysis_id']}", result, kind="reconciliation", document_id=doc)
    return result


def _handle(ev: dict) -> dict:
    action = ev.get("action", "reconcile")
    if action == "validate_transactions":
        return _validate(ev)
    if action == "reconcile":
        return _reconcile(ev)
    raise ValueError(f"Unknown action: {action}")


def handler(event, context=None):
    return run(event, _handle)
