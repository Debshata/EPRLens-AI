"""Run only the forecasting stages of the overnight pipeline (validate, features, baselines, search, final)."""
import subprocess, sys
from pathlib import Path
ML = Path(__file__).resolve().parents[1]
sys.exit(subprocess.call([sys.executable, str(ML / "run_overnight.py"), "--until", "forecast_final", *sys.argv[1:]]))
