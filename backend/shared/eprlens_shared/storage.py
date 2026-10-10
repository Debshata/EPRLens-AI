"""Object access that works the same locally and on AWS.

Event shapes accepted by every Lambda that reads a file:
  {"s3": {"bucket": "...", "key": "uploads/<company>/..."}}   -> S3 (boto3, available in the Lambda runtime)
  {"local_path": "/abs/or/relative/file"}                     -> local file (tests, `run_local.py`)
No credentials are read here; Lambda uses its execution role.
"""
from __future__ import annotations

import os
from pathlib import Path

_client = None


class StorageError(Exception):
    def __init__(self, code: str, message: str, next_step: str):
        super().__init__(message)
        self.code, self.next_step = code, next_step


def _s3():
    global _client
    if _client is None:
        import boto3

        _client = boto3.client("s3")
    return _client


def read_bytes(event: dict) -> tuple[bytes, str]:
    """Returns (content, file_name)."""
    if event.get("local_path"):
        p = Path(event["local_path"])
        if not p.is_absolute() and not p.is_file():  # allow repo-root-relative paths in test events
            p = Path(__file__).resolve().parents[3] / p
        if not p.is_file():
            raise StorageError("file_not_found", f"File not found: {p.name}", "Check the path or upload the file again.")
        return p.read_bytes(), p.name
    s3 = event.get("s3") or {}
    bucket, key = s3.get("bucket") or os.environ.get("UPLOADS_BUCKET"), s3.get("key")
    if not bucket or not key:
        raise StorageError("bad_request", "The request needs s3.bucket and s3.key (or local_path).", "Upload the file first, then retry with its S3 key.")
    try:
        body = _s3().get_object(Bucket=bucket, Key=key)["Body"].read()
    except Exception as e:  # noqa: BLE001 - surface a friendly message, never raw AWS internals
        name = type(e).__name__
        if "NoSuchKey" in name or "404" in str(e):
            raise StorageError("object_not_found", "The uploaded file was not found.", "Upload the file again and retry.") from e
        raise StorageError("storage_error", "The file could not be read from storage.", "Retry; if it persists check the Lambda role's s3:GetObject permission.") from e
    return body, key.rsplit("/", 1)[-1]


def read_seed_json(rel_path: str) -> dict:
    """Seeded demo/reference JSON: S3 `reference/<rel_path>` on AWS, or $LOCAL_SEED_DIR/<rel_path> locally."""
    import json

    local = os.environ.get("LOCAL_SEED_DIR")
    if local:
        p = Path(local) / rel_path
        if not p.is_file():
            raise StorageError("seed_missing", f"Seed data not found: {rel_path}", "Run the seed script (infrastructure/scripts/50-seed.sh) or set LOCAL_SEED_DIR.")
        return json.loads(p.read_text(encoding="utf-8"))
    bucket = os.environ.get("REFERENCE_BUCKET") or os.environ.get("MODELS_BUCKET")
    if not bucket:
        raise StorageError("config_missing", "REFERENCE_BUCKET is not configured.", "Set the Lambda environment variable or LOCAL_SEED_DIR for local runs.")
    try:
        return json.loads(_s3().get_object(Bucket=bucket, Key=f"reference/{rel_path}")["Body"].read())
    except Exception as e:  # noqa: BLE001
        raise StorageError("seed_missing", f"Seed data not found: {rel_path}", "Run the seed script (infrastructure/scripts/50-seed.sh).") from e
