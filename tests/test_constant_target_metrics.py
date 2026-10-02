"""Audit F02/F04/F05/F07/F08/F11: executable scientific contracts."""


import numpy as np
import pandas as pd
import pytest

from psyml import ExperimentConfig, run_experiment
from psyml.evaluation.metrics import ConstantTargetWarning, finite_r2_score


def config(tmp_path, **updates):
    values = {"task": "classification", "target_column": "target", "model_name": "decision_tree",
              "output_dir": tmp_path / "out", "validation_strategy": "stratified_k_fold",
              "n_splits": 3, "save_best_model": False, "figure_types": []}
    values.update(updates)
    return ExperimentConfig(**values)


def frame():
    return pd.DataFrame({"x": np.arange(24), "target": ["A", "B"] * 12})


@pytest.mark.parametrize("prediction,expected", [([1, 1], 1), ([0, 0], 0)])
def test_constant_target_r2_convention_is_explicit(prediction, expected):
    with pytest.warns(ConstantTargetWarning, match="force_finite=True"):
        assert finite_r2_score([1, 1], prediction) == expected


def test_constant_target_warning_persists_inner_outer_and_reports(tmp_path):
    data = pd.DataFrame({"x": range(24), "target": [1.] * 24})
    cfg = config(tmp_path, task="regression", model_name="dummy", validation_strategy="k_fold",
                 tuning_mode="custom", selection_metric="r2",
                 parameter_grids={"dummy": {"strategy": ["mean", "median"]}})
    result = run_experiment(cfg, data)
    records = [r for r in result.fit_warnings if r["category"] == "ConstantTargetWarning"]
    assert {r["scope"] for r in records} == {"inner", "outer"}
    assert result.metrics["r2"] == 1
    for filename in ["warnings.json", "result.json", "reproducibility_report.md"]:
        assert "ConstantTargetWarning" in (cfg.output_dir / filename).read_text()
