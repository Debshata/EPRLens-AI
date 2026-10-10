"""Result store: DynamoDB on AWS, a JSON file when running locally.

Item shape (one table, PAY_PER_REQUEST):  pk = company_id,  sk = "<KIND>#<id>",
  payload = JSON string (avoids DynamoDB float/Decimal issues), plus small queryable attributes.
Raw files are never stored here — only their S3 keys.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path


class Store:
    def put(self, company_id: str, sk: str, payload: dict, **attrs) -> None: ...
    def get(self, company_id: str, sk: str) -> dict | None: ...


class LocalStore(Store):
    def __init__(self, path: str):
        self.path = Path(path)

    def _load(self) -> dict:
        return json.loads(self.path.read_text()) if self.path.is_file() else {}

    def put(self, company_id, sk, payload, **attrs):
        data = self._load()
        data[f"{company_id}|{sk}"] = {"payload": payload, **attrs}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data))

    def get(self, company_id, sk):
        item = self._load().get(f"{company_id}|{sk}")
        return item["payload"] if item else None


class DynamoStore(Store):
    def __init__(self, table: str):
        import boto3

        self.table = boto3.resource("dynamodb").Table(table)

    def put(self, company_id, sk, payload, **attrs):
        item = {"pk": company_id, "sk": sk, "payload": json.dumps(payload), "updated_at": int(time.time())}
        item.update({k: v for k, v in attrs.items() if isinstance(v, (str, int, bool))})
        self.table.put_item(Item=item)

    def get(self, company_id, sk):
        r = self.table.get_item(Key={"pk": company_id, "sk": sk}).get("Item")
        return json.loads(r["payload"]) if r else None


def get_store() -> Store:
    local = os.environ.get("LOCAL_STORE_FILE")
    if local:
        return LocalStore(local)
    table = os.environ.get("ANALYSIS_TABLE")
    if not table:
        raise RuntimeError("ANALYSIS_TABLE is not configured")
    return DynamoStore(table)


def try_put(company_id: str, sk: str, payload: dict, **attrs) -> bool:
    """Best-effort save of an analysis result. Never fails the request: results are also returned to the caller."""
    try:
        get_store().put(company_id, sk, payload, **attrs)
        return True
    except Exception:  # noqa: BLE001 - store not configured (local run) or throttled
        return False
