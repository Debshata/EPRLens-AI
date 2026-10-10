"""detect-anomaly: invoice/recycling record features -> is_anomaly, score and rule findings (rules + Isolation Forest, anomaly-v1)."""
import sys
from pathlib import Path

_here = Path(__file__).resolve()
for _c in (_here.parent, _here.parents[2] / "shared"):  # zip layout / repo layout
    if (_c / "eprlens_shared").is_dir():
        sys.path.insert(0, str(_c))
        break

for _c in (_here.parent, *([_here.parents[3] / "syntheticml" / "ml" / "aws_examples"] if len(_here.parents) > 3 else [])):  # zip layout / repo layout
    if (_c / "lambda_anomaly_handler.py").is_file():
        sys.path.insert(0, str(_c))
        break
import lambda_anomaly_handler as ml  # reference handler from the ML team

from eprlens_shared.lambda_utils import run


def _handle(ev: dict) -> dict:
    if ev.get("use_sample"):  # smoke test: score the ML team's bundled sample record (seeded reference data)
        from eprlens_shared.storage import read_seed_json

        ev = read_seed_json("anomaly_sample_input.json")
    out = ml.handler(ev)
    if out.get("status") != "success":
        raise ValueError(out.get("message") or "The anomaly model could not score this record.")
    return out


def handler(event, context=None):
    return run(event, _handle)
