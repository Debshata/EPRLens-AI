"""scenario-engine: units, current g/unit, proposed g/unit -> baseline kg, proposed kg, reduction kg. No ML."""
import sys
from pathlib import Path

_here = Path(__file__).resolve()
for _c in (_here.parent, _here.parents[2] / "shared"):  # zip layout / repo layout
    if (_c / "eprlens_shared").is_dir():
        sys.path.insert(0, str(_c))
        break

from eprlens_shared.lambda_utils import run
from eprlens_shared.scenario import compute


def _handle(ev: dict) -> dict:
    return compute(ev.get("units"), ev.get("current_g_per_unit"), ev.get("proposed_g_per_unit"))


def handler(event, context=None):
    return run(event, _handle)
