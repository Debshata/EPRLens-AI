"""company-data: seeded demo company profile, dashboard summary and simulator catalogue; creates a company record."""
import time
import sys
from pathlib import Path

_here = Path(__file__).resolve()
for _c in (_here.parent, _here.parents[2] / "shared"):  # zip layout / repo layout
    if (_c / "eprlens_shared").is_dir():
        sys.path.insert(0, str(_c))
        break

from eprlens_shared.lambda_utils import run
from eprlens_shared.storage import StorageError, read_seed_json
from eprlens_shared.store import try_put

DEMO = "COMP_0001"
RULES_VERSION = "applicability-demo-v0"


def _seed(company_id: str, name: str) -> dict:
    if company_id != DEMO:
        raise StorageError("no_data", "This company has no processed data yet.", "Upload a transaction CSV and an invoice on the Workspace page first.")
    return read_seed_json(f"{company_id}/{name}.json")


def _create(company: dict) -> dict:
    name = (company.get("company_name") or "").strip()
    roles = company.get("roles") or []
    if len(name) < 2:
        raise ValueError("Enter the registered business name (at least 2 characters).")
    cid = f"COMP_LOCAL_{int(time.time()):X}"
    bundle = {
        "_meta": {"synthetic": True, "watermark": "SYNTHETIC — EPRLens Demo", "note": "Company created through the API. It has no uploaded data yet."},
        "company": {
            "company_id": cid, "company_name": name, "industry": company.get("industry", ""), "turnover_cr": company.get("turnover_cr"),
            "manufacturer": "manufacturer" in roles, "importer": "importer" in roles, "brand_owner": "brand_owner" in roles,
            "states_operated": company.get("states_operated") or [], "registration_status": company.get("registration_status", "unknown"),
            "business_description": company.get("business_description", ""), "synthetic_flag": False,
        },
        "roles": {"producer": "producer" in roles, "importer": "importer" in roles, "brand_owner": "brand_owner" in roles, "manufacturer": "manufacturer" in roles},
        "rules_version": RULES_VERSION,
    }
    try_put(cid, "COMPANY#profile", bundle, kind="company")
    return bundle


def _handle(ev: dict) -> dict:
    action, cid = ev.get("action"), ev.get("company_id") or DEMO
    if action == "get_company_profile":
        return _seed(cid, "company")
    if action == "dashboard_summary":
        return _seed(cid, "dashboard")
    if action == "simulator_catalog":
        return _seed(cid, "simulator")
    if action == "create_company":
        return _create(ev.get("company") or {})
    raise ValueError(f"Unknown action: {action}")


def handler(event, context=None):
    return run(event, _handle)
