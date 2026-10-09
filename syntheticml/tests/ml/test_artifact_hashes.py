"""Artifacts match their SHA256SUMS and metadata."""
import hashlib

import pytest

from conftest import ADIR, FDIR, load, needs_artifacts

REQUIRED_META = {"model_name", "model_version", "algorithm", "training_timestamp", "git_commit", "dataset_sha256", "seed",
                 "features", "target", "training_rows", "validation_rows", "test_rows", "metrics", "python_version",
                 "library_versions", "artifact_sha256"}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


@needs_artifacts
@pytest.mark.parametrize("folder", [FDIR, ADIR], ids=["forecast", "anomaly"])
def test_sha256sums(folder):
    listed = {}
    for line in (folder / "SHA256SUMS.txt").read_text().splitlines():
        digest, name = line.split("  ", 1)
        listed[name] = digest
    files = {p.name for p in folder.iterdir() if p.is_file() and p.name != "SHA256SUMS.txt"}
    assert set(listed) == files
    for name, digest in listed.items():
        assert sha(folder / name) == digest, name


@needs_artifacts
@pytest.mark.parametrize("folder,model", [(FDIR, None), (ADIR, "isolation_forest.joblib")], ids=["forecast", "anomaly"])
def test_metadata(folder, model):
    meta = load(folder / "model_metadata.json")
    assert REQUIRED_META <= set(meta)
    assert meta["artifact_sha256"] == sha(folder / (model or meta["model_file"]))
    assert meta["seed"] == 20261009 and meta["synthetic_only"] is True
