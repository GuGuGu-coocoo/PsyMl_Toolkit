"""Audit F02/F04/F05/F07/F08/F11: executable scientific contracts."""

from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from psyml import ExperimentConfig, run_experiment
from psyml.runner import _inner_splits
from psyml.validation.split import split_train_test


def config(tmp_path, **updates):
    values = {"task": "classification", "target_column": "target", "model_name": "decision_tree",
              "output_dir": tmp_path / "out", "validation_strategy": "stratified_k_fold",
              "n_splits": 3, "save_best_model": False, "figure_types": []}
    values.update(updates)
    return ExperimentConfig(**values)


def frame():
    return pd.DataFrame({"x": np.arange(24), "target": ["A", "B"] * 12})


@pytest.mark.parametrize("parquet", [False, True])
def test_unused_categorical_levels_do_not_change_splits_or_results(tmp_path, parquet):
    ordinary = frame()
    categorical = ordinary.copy()
    categorical.target = pd.Categorical(categorical.target, categories=["A", "B", "unused"])
    cfg = config(tmp_path)
    assert _inner_splits(cfg, categorical[["x"]], categorical.target, None, 1) == _inner_splits(
        cfg, ordinary[["x"]], ordinary.target, None, 1)
    for target in [ordinary.target, categorical.target]:
        _, _, train, test = split_train_test(ordinary[["x"]], target, "classification", .25, 42)
        assert set(train) == set(test) == {"A", "B"}
    expected = run_experiment(cfg, ordinary)
    cfg = replace(cfg, output_dir=tmp_path / "categorical")
    if parquet:
        path = tmp_path / "input.parquet"
        categorical.to_parquet(path)
        actual = run_experiment(replace(cfg, input_path=path))
    else:
        actual = run_experiment(cfg, categorical)
    assert expected.metrics == actual.metrics
    assert expected.predictions.predicted.tolist() == actual.predictions.predicted.tolist()
    assert not any("imbalanced" in item for item in actual.warnings)
