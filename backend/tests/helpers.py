import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LAMBDAS = ROOT / "backend" / "lambdas"
GEN = ROOT / "syntheticml" / "data" / "generated" / "invoices"
SAMPLES = ROOT / "frontend" / "public" / "samples"
MOCKS = ROOT / "frontend" / "src" / "lib" / "mocks"


def load_handler(name: str):
    spec = importlib.util.spec_from_file_location(f"handler_{name.replace('-', '_')}", LAMBDAS / name / "handler.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.handler
