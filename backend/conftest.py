import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE / "shared"))
sys.path.insert(0, str(ROOT / "syntheticml" / "ml" / "aws_examples"))
os.environ["LOCAL_SEED_DIR"] = str(HERE / "seed" / "reference")
os.environ["LOCAL_STORE_FILE"] = str(Path(tempfile.mkdtemp()) / "store.json")
os.environ.pop("ANALYSIS_TABLE", None)
os.environ.pop("MODEL_BUCKET", None)
os.environ.pop("MODELS_BUCKET", None)
