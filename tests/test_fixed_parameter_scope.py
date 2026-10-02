"""Audit F02/F04/F05/F07/F08/F11: executable scientific contracts."""

from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from psyml import ExperimentConfig, run_experiment
from psyml.runner import _parameter_candidates


def config(tmp_path, **updates):
    values = {"task": "classification", "target_column": "target", "model_name": "decision_tree",
              "output_dir": tmp_path / "out", "validation_strategy": "stratified_k_fold",
              "n_splits": 3, "save_best_model": False, "figure_types": []}
    values.update(updates)
    return ExperimentConfig(**values)


def frame():
    return pd.DataFrame({"x": np.arange(24), "target": ["A", "B"] * 12})


@pytest.mark.parametrize("mode", ["none", "quick", "custom"])
@pytest.mark.parametrize("models", [["decision_tree", "random_forest"],
                                    ["decision_tree", "logistic_regression"]])
def test_multi_model_fixed_parameters_rejected_before_output(tmp_path, mode, models):
    cfg = config(tmp_path, model_names=models, model_params={"max_depth": 1}, tuning_mode=mode)
    with pytest.raises(ValueError, match="exactly one selected model"):
        run_experiment(cfg, frame())
    assert not cfg.output_dir.exists()
    with pytest.raises(ValueError, match="exactly one selected model"):
        _parameter_candidates(cfg, models[0])


@pytest.mark.parametrize("mode", ["none", "quick", "custom"])
def test_single_model_fixed_parameters_reach_effective_estimator(tmp_path, mode):
    cfg = config(tmp_path, tuning_mode=mode, model_params={"max_depth": 1},
                 parameter_grids={"decision_tree": {"min_samples_leaf": [1, 2]}},
                 max_candidates=2)
    # Quick search overrides max_depth by design; pin a parameter absent from its grid.
    if mode == "quick":
        cfg = replace(cfg, model_params={"min_impurity_decrease": 0.123})
    result = run_experiment(cfg, frame())
    for key, value in cfg.model_params.items():
        assert result.effective_params[key] == value
