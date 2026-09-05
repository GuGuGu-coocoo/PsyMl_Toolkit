"""Regression coverage for the researcher feedback of 2026-09-05."""
import json
from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

from psyml import ExperimentConfig, run_experiment
from psyml.protocol import config_from_dict, config_to_dict, load_config

ROOT = Path(__file__).resolve().parents[1]


def test_reported_godot_float_grid_and_fixed_parameter_recipe(tmp_path):
    config = ExperimentConfig(
        task="classification", target_column="target", model_name="decision_tree",
        model_names=["decision_tree"], input_path=ROOT / "examples/synthetic/classification.csv",
        output_dir=tmp_path / "search", feature_columns=["score", "category"],
        group_column="participant", validation_strategy="k_fold", n_splits=5,
        inner_splits=3, max_candidates=20, tuning_mode="custom", selection_metric="f1_macro",
        parameter_grids={"decision_tree": {
            "max_depth": [None, 5.0, 10.0], "min_samples_leaf": [1.0, 3.0, 5.0],
        }}, figure_types=["confusion_matrix", "class_distribution"],
    )
    run_experiment(config)
    result = json.loads((config.output_dir / "result.json").read_text(encoding="utf-8"))
    recipe = load_config(config.output_dir / "best_parameters_configure.json")
    assert recipe.model_params == result["best_parameters"]
    assert recipe.model_names == [result["best_model"]]
    assert recipe.tuning_mode == "none" and recipe.parameter_grids == {}
    assert recipe.selected_validations() == [result["best_validation"]]
    assert recipe.output_dir == config.output_dir / "best_parameters_run"
    run_experiment(recipe)
    assert (recipe.output_dir / "result.json").is_file()
    for key, value in result["artifacts"].items():
        assert (config.output_dir / value).is_file(), key
    assert "best_parameters" in (config.output_dir / "reproducibility_report.md").read_text(encoding="utf-8")
    assert "不保证绝对正确" in (config.output_dir / "methods_summary_zh.md").read_text(encoding="utf-8")
    assert config.parameter_grids["decision_tree"]["min_samples_leaf"][0] == 1.0
    assert isinstance(config.parameter_grids["decision_tree"]["min_samples_leaf"][0], float)
    assert isinstance(config.parameter_grids["decision_tree"]["min_samples_leaf"][1], int)


def test_plot_selection_and_empty_selection(tmp_path):
    config = load_config(ROOT / "examples/synthetic/regression_config.json")
    config = replace(config, input_path=ROOT / config.input_path, output_dir=tmp_path / "plots")
    run_experiment(config)
    assert {p.stem for p in (config.output_dir / "figures").glob("*.png")} == set(config.figure_types)
    config = replace(config, output_dir=tmp_path / "no_plots", figure_types=[])
    run_experiment(config)
    assert not list((config.output_dir / "figures").glob("*.png"))
    result = json.loads((config.output_dir / "result.json").read_text(encoding="utf-8"))
    assert "figure" not in result["artifacts"]
    assert config_from_dict(config_to_dict(config)) == config
    with pytest.raises(ValueError, match="figure_types"):
        replace(config, figure_types=["confusion_matrix"])


def test_candidate_failure_keeps_specific_parameter_cause(tmp_path):
    config = ExperimentConfig(
        task="regression", target_column="y", model_name="decision_tree", output_dir=tmp_path,
        tuning_mode="custom", parameter_grids={"decision_tree": {"max_depth": [-2, -1]}},
        inner_splits=2,
    )
    with pytest.raises(ValueError, match="max_depth"):
        run_experiment(config, pd.DataFrame({"x": range(30), "y": range(30)}))
