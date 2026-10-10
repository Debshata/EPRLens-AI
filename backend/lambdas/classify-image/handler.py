"""classify-image: S3 image key -> {predicted_class, confidence, uncertain, model_version}. Probable material only."""
import sys
from pathlib import Path

_here = Path(__file__).resolve()
for _c in (_here.parent, _here.parents[2] / "shared"):  # zip layout / repo layout
    if (_c / "eprlens_shared").is_dir():
        sys.path.insert(0, str(_c))
        break

from eprlens_shared.classify import classify
from eprlens_shared.lambda_utils import run
from eprlens_shared.storage import read_bytes
from eprlens_shared.store import try_put


def _handle(ev: dict) -> dict:
    content, name = read_bytes(ev)
    if len(content) > 8 * 1024 * 1024:
        raise ValueError("The image is larger than 8 MB. Reduce its size and upload it again.")
    result = classify(content)
    if ev.get("company_id"):
        try_put(ev["company_id"], f"IMAGE#{name}", result, kind="image", s3_key=(ev.get("s3") or {}).get("key", ""))
    return result


def handler(event, context=None):
    return run(event, _handle)
