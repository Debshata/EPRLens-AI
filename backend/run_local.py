"""Run any Lambda handler locally against a JSON event, with no AWS credentials.

    python backend/run_local.py parse-invoice backend/test-events/parse-invoice.json

Sets LOCAL_SEED_DIR (backend/seed/reference) and a throw-away LOCAL_STORE_FILE unless already set.
"""
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ.setdefault("LOCAL_SEED_DIR", str(HERE / "seed" / "reference"))
os.environ.setdefault("LOCAL_STORE_FILE", str(Path(tempfile.gettempdir()) / "eprlens-local-store.json"))

name, event_path = sys.argv[1], sys.argv[2]
spec = importlib.util.spec_from_file_location("handler", HERE / "lambdas" / name / "handler.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
print(json.dumps(mod.handler(json.loads(Path(event_path).read_text())), indent=2, ensure_ascii=False))
