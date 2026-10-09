"""Shared helpers: paths, logging, seeds, versions, hashing, experiment log, run state.
SYNTHETIC — EPRLens Demo."""
import csv
import hashlib
import json
import logging
import os
import platform
import random
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ML_DIR = Path(__file__).resolve().parents[1]
ROOT = ML_DIR.parent
LOG_FIELDS = ["experiment_id", "timestamp", "task", "algorithm", "parameters", "train_metric", "validation_metric",
              "test_metric_if_final", "duration_seconds", "selected", "notes"]
LIBS = ["numpy", "pandas", "scipy", "scikit-learn", "xgboost", "joblib", "onnx", "onnxruntime", "onnxmltools",
        "skl2onnx", "matplotlib"]


def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def seed_everything(seed):
    random.seed(seed)
    np.random.seed(seed % (2**32))
    os.environ["PYTHONHASHSEED"] = str(seed)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_commit():
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10)
        return out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def library_versions():
    from importlib.metadata import PackageNotFoundError, version
    out = {"python": platform.python_version()}
    for lib in LIBS:
        try:
            out[lib] = version(lib)
        except PackageNotFoundError:
            out[lib] = None
    return out


def to_jsonable(o):
    """Convert numpy / pandas scalars and containers into plain JSON types."""
    if isinstance(o, dict):
        return {str(k): to_jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [to_jsonable(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        v = float(o)
        return None if v != v else v
    if isinstance(o, float) and o != o:
        return None
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return to_jsonable(o.tolist())
    return o


def write_json(obj, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(obj), indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def get_logger(log_paths):
    logger = logging.getLogger("eprlens_ml")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    for p in log_paths:
        Path(p).parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(p, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    return logger


class ExperimentLog:
    """Append-only CSV of every experiment; survives restarts."""

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            with self.path.open("w", encoding="utf-8", newline="") as fh:
                csv.writer(fh, lineterminator="\n").writerow(LOG_FIELDS)

    def rows(self):
        with self.path.open(encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))

    def next_id(self, task):
        n = sum(1 for r in self.rows() if r["task"] == task)
        return f"{task[:4].upper()}-{n + 1:03d}"

    def add(self, task, algorithm, parameters, train_metric=None, validation_metric=None, test_metric=None,
            duration=0.0, selected=False, notes=""):
        eid = self.next_id(task)
        row = [eid, now(), task, algorithm, json.dumps(to_jsonable(parameters), sort_keys=True),
               json.dumps(to_jsonable(train_metric)) if train_metric is not None else "",
               json.dumps(to_jsonable(validation_metric)) if validation_metric is not None else "",
               json.dumps(to_jsonable(test_metric)) if test_metric is not None else "",
               f"{duration:.2f}", "true" if selected else "false", notes]
        with self.path.open("a", encoding="utf-8", newline="") as fh:
            csv.writer(fh, lineterminator="\n").writerow(row)
        return eid

    def mark_selected(self, experiment_ids, test_metrics=None):
        rows = self.rows()
        for r in rows:
            if r["experiment_id"] in experiment_ids:
                r["selected"] = "true"
                if test_metrics and r["experiment_id"] in test_metrics:
                    r["test_metric_if_final"] = json.dumps(to_jsonable(test_metrics[r["experiment_id"]]))
        with self.path.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=LOG_FIELDS, lineterminator="\n")
            w.writeheader()
            w.writerows(rows)


class RunState:
    """status.json with completed stages; lets the overnight run resume."""

    def __init__(self, run_dir):
        self.path = Path(run_dir) / "status.json"
        self.data = read_json(self.path) if self.path.exists() else {"stages": {}, "created_at": now()}

    def done(self, stage):
        return self.data["stages"].get(stage, {}).get("status") == "completed"

    def mark(self, stage, status, **info):
        self.data["stages"][stage] = {"status": status, "at": now(), **info}
        self.data["updated_at"] = now()
        write_json(self.data, self.path)


class Timer:
    def __enter__(self):
        self.t0 = time.perf_counter()
        return self

    def __exit__(self, *a):
        self.seconds = time.perf_counter() - self.t0
