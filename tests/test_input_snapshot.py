"""Audit F02/F04/F05/F07/F08/F11: executable scientific contracts."""

import hashlib
import json
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from psyml import ExperimentConfig, run_experiment
from psyml.data.provenance import SNAPSHOT_KEY, bind_input_snapshot


def config(tmp_path, **updates):
    values = {"task": "classification", "target_column": "target", "model_name": "decision_tree",
              "output_dir": tmp_path / "out", "validation_strategy": "stratified_k_fold",
              "n_splits": 3, "save_best_model": False, "figure_types": []}
    values.update(updates)
    return ExperimentConfig(**values)


def frame():
    return pd.DataFrame({"x": np.arange(24), "target": ["A", "B"] * 12})


@pytest.mark.parametrize("change", ["modify", "delete", "none"])
@pytest.mark.parametrize("independent", [False, True])
def test_file_hash_describes_parsed_snapshot_after_source_change(tmp_path, change, independent):
    path = tmp_path / "input.csv"
    frame().to_csv(path, index=False)
    expected = hashlib.sha256(path.read_bytes()).hexdigest()
    cfg = config(tmp_path, input_path=path)
    if independent:
        cfg = replace(cfg, validation_strategies=["stratified_k_fold", "holdout"],
                      primary_validation=None)
    changed = False

    def progress(event):
        nonlocal changed
        if changed or event.get("phase") != "finalizing":
            return
        changed = True
        if change == "modify":
            pd.DataFrame({"x": [0], "target": [9]}).to_csv(path, index=False)
        elif change == "delete":
            path.unlink()

    result = run_experiment(cfg, progress_callback=progress)
    manifests = list(cfg.output_dir.rglob("analysis_manifest.json"))
    assert len(manifests) == (2 if independent else 1)
    for path in manifests:
        manifest = json.loads(path.read_text())
        assert manifest["data"]["sha256"] == expected
        assert manifest["data"]["hash_basis"] == "source_file_bytes"
        assert manifest["input_snapshot"]["source_status_at_export"] == {
            "modify": "changed", "delete": "unavailable", "none": "unchanged"}[change]
    results = result.validation_results.values() if independent else [result]
    for entry in results:
        assert set(entry.predictions.observed) == {"A", "B"}
        assert any("input source file" in warning for warning in entry.warnings) == (change != "none")


def test_loader_reads_exact_hashed_bytes_even_if_original_changes(tmp_path):
    source = tmp_path / "input.csv"
    frame().to_csv(source, index=False)
    expected = hashlib.sha256(source.read_bytes()).hexdigest()
    snapshot_path = None

    def loader(path):
        nonlocal snapshot_path
        snapshot_path = path
        source.write_text("x,target\n99,Z\n")
        return pd.read_csv(path)

    snap = bind_input_snapshot(config(tmp_path, input_path=source), None, loader=loader)
    assert snap.attrs[SNAPSHOT_KEY]["sha256"] == expected
    assert snap.target.tolist() == frame().target.tolist()
    assert not snapshot_path.exists()


@pytest.mark.parametrize("file_kind", ["dataframe", "parquet", "csv"])
@pytest.mark.parametrize("indexes", [[100] * 24, list(range(90, 138, 2))])
def test_row_positions_survive_nonunique_named_indexes_and_dropped_rows(tmp_path, file_kind, indexes):
    data = frame()
    data.index = pd.Index(indexes, name="participant_index")
    data.loc[data.index[0], "x"] = np.nan if len(set(indexes)) > 1 else 0
    data.iloc[3, data.columns.get_loc("x")] = np.nan
    data.iloc[7, data.columns.get_loc("target")] = None
    cfg = config(tmp_path, missing_strategy="drop")
    if file_kind == "dataframe":
        result = run_experiment(cfg, data)
    else:
        path = tmp_path / f"input.{file_kind}"
        if file_kind == "parquet":
            data.to_parquet(path)
        else:
            data.to_csv(path, index=False)
        result = run_experiment(replace(cfg, input_path=path))
    expected = np.flatnonzero(data.notna().all(axis=1)).tolist()
    assert sorted(result.predictions.row_index) == expected
    assert result.predictions.row_index.is_unique
    assert data.index.name == "participant_index"  # caller's frame remains intact
