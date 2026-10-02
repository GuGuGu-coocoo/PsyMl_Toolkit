"""Audit F02/F04/F05/F07/F08/F11: executable scientific contracts."""

import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from psyml import ExperimentConfig, run_experiment


def config(tmp_path, **updates):
    values = {"task": "classification", "target_column": "target", "model_name": "decision_tree",
              "output_dir": tmp_path / "out", "validation_strategy": "stratified_k_fold",
              "n_splits": 3, "save_best_model": False, "figure_types": []}
    values.update(updates)
    return ExperimentConfig(**values)


def frame():
    return pd.DataFrame({"x": np.arange(24), "target": ["A", "B"] * 12})


def test_runtime_identity_records_code_dependencies_backend_and_row_contract(tmp_path):
    cfg = config(tmp_path)
    run_experiment(cfg, frame())
    manifest = json.loads((cfg.output_dir / "analysis_manifest.json").read_text())
    assert {"scipy", "joblib", "threadpoolctl"} <= manifest["dependencies"].keys()
    code = manifest["code_identity"]
    assert code["kind"] == "source_checkout"
    assert len(code["commit"]) == len(code["lock_sha256"]) - 24 == 40
    assert isinstance(code["working_tree_modified"], bool)
    backend = manifest["numerical_environment"]
    assert "OPENBLAS_NUM_THREADS" in backend["thread_environment"]
    assert backend["threadpools"]
    assert all("filepath" not in pool for pool in backend["threadpools"])
    assert manifest["input_snapshot"]["row_identity"] == "zero_based_input_position_before_filtering"


def test_source_identity_does_not_claim_enclosing_repository(tmp_path, monkeypatch):
    import subprocess

    from psyml.reporting import environment

    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com",
         "commit", "--allow-empty", "-qm", "parent"],
        cwd=tmp_path, check=True, capture_output=True,
    )
    root = tmp_path / "vendor" / "psyml"
    source = root / "src" / "psyml"
    (source / "reporting").mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\nname='psyml-toolkit'\n")
    (source / "runner.py").write_text("")
    (root / "uv.lock").write_text("lock identity")
    monkeypatch.setattr(environment, "__file__", str(source / "reporting" / "environment.py"))
    identity = environment.source_identity()
    assert identity["commit"] == "unknown"
    assert identity["working_tree_modified"] == "unknown"
    assert identity["lock_sha256"] == hashlib.sha256(b"lock identity").hexdigest()


@pytest.mark.parametrize("build_json", ["[]", "null", "4", '"text"', "not json"])
def test_frozen_invalid_build_metadata_is_optional(tmp_path, monkeypatch, build_json):
    from psyml.reporting import environment

    executable = tmp_path / "core" / "psyml-core"
    executable.parent.mkdir()
    executable.write_text("")
    (tmp_path / "BUILD.json").write_text(build_json)
    monkeypatch.setattr(environment.sys, "frozen", True, raising=False)
    monkeypatch.setattr(environment.sys, "executable", str(executable))
    monkeypatch.setattr(environment, "__file__", str(tmp_path / "a/b/c/d/environment.py"))
    identity = environment.source_identity()
    assert identity["kind"] == "frozen_build"
    assert identity["build_manifest_sha256"] == "unknown"


def test_optional_digest_unavailable_is_unknown(tmp_path):
    from psyml.reporting.environment import _digest

    assert _digest(tmp_path / "missing.lock") == "unknown"
