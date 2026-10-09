import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT / "ml", ROOT, ROOT / "ml" / "aws_examples"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
FDIR = ROOT / "ml" / "artifacts" / "forecast" / "v1"
ADIR = ROOT / "ml" / "artifacts" / "anomaly" / "v1"
DATA = ROOT / "data" / "generated"
os.environ.setdefault("FORECAST_ARTIFACT_DIR", str(FDIR))
os.environ.setdefault("ANOMALY_ARTIFACT_DIR", str(ADIR))

needs_data = pytest.mark.skipif(not (DATA / "csv" / "forecast_panel.csv").exists(), reason="data/generated not present")
needs_artifacts = pytest.mark.skipif(not (FDIR / "model_metadata.json").exists(), reason="artifacts not exported")


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
