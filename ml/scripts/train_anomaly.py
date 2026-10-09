"""Run the pipeline up to the anomaly stages (forecast stages are skipped if already completed)."""
import subprocess, sys
from pathlib import Path
ML = Path(__file__).resolve().parents[1]
sys.exit(subprocess.call([sys.executable, str(ML / "run_overnight.py"), "--until", "anomaly_final", *sys.argv[1:]]))
