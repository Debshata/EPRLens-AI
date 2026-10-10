"""Handler plumbing: uniform success/error shapes. Success = bare JSON; user-facing failure = {statusCode, body:{code,message,next_step}}."""
from __future__ import annotations

import json
import logging
from typing import Callable

from .scenario import ScenarioInputError
from .storage import StorageError

_NOT_FOUND = {"file_not_found", "object_not_found", "invoice_not_found", "no_data", "no_history", "seed_missing"}
log = logging.getLogger("eprlens")
log.setLevel(logging.INFO)


def user_error(status: int, code: str, message: str, next_step: str) -> dict:
    return {"statusCode": status, "body": {"code": code, "message": message, "next_step": next_step}}


def unwrap_event(event):
    """Accept a direct invoke payload or an API-style {"body": "<json>"} envelope."""
    if isinstance(event, dict) and "body" in event and isinstance(event["body"], (str, dict)) and "action" not in event:
        body = event["body"]
        return json.loads(body) if isinstance(body, str) else body
    return event


def run(event, fn: Callable[[dict], dict]) -> dict:
    try:
        return fn(unwrap_event(event))
    except StorageError as e:
        return user_error(404 if e.code in _NOT_FOUND else 400, e.code, str(e), e.next_step)
    except ScenarioInputError as e:
        return user_error(400, "invalid_input", str(e), e.next_step)
    except ValueError as e:
        return user_error(400, "invalid_input", str(e), "Check the request values and try again.")
    except Exception:  # noqa: BLE001 - never leak internals to callers
        log.exception("unhandled error")
        return user_error(500, "unexpected", "The function could not complete the request.", "Retry; if it keeps failing, check the Lambda logs.")
