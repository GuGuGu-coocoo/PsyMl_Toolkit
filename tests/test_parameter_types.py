"""Numeric parameter types must survive every configuration path.

JSON ``1`` is an integer count while ``1.0`` is a decimal fraction. For
scikit-learn parameters such as ``max_features``, ``max_samples`` or
``min_samples_leaf`` the two forms can select different models, so PsyML must
preserve the type the user wrote and must report invalid values instead of
silently substituting a different valid model.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from psyml import ExperimentConfig, run_experiment
from psyml.models.catalog import validate_model_parameters
from psyml.runner import _parameter_candidates


def _classification_frame(rows: int = 24) -> pd.DataFrame:
    rng = np.random.RandomState(7)
    features = rng.rand(rows, 4)
    return pd.DataFrame(
        {
            "f1": features[:, 0],
            "f2": features[:, 1],
            "f3": features[:, 2],
            "f4": features[:, 3],
            "target": [0, 1] * (rows // 2),
        }
    )


def _config(tmp_path, **overrides) -> ExperimentConfig:
    settings = {
        "task": "classification",
        "target_column": "target",
        "model_name": "random_forest",
        "output_dir": tmp_path / "run",
        "random_seed": 3,
    }
    settings.update(overrides)
    return ExperimentConfig(**settings)


def test_config_preserves_json_number_types(tmp_path):
    config = _config(
        tmp_path,
        model_params={"max_features": 1, "max_samples": 1.0, "verbose": 0, "n_jobs": 1},
        parameter_grids={"random_forest": {"min_samples_leaf": [1, 0.25]}},
    )
    assert type(config.model_params["max_features"]) is int
    assert type(config.model_params["max_samples"]) is float
    assert type(config.model_params["verbose"]) is int
    assert config.model_params["verbose"] == 0
    assert type(config.model_params["n_jobs"]) is int
    leaves = config.parameter_grids["random_forest"]["min_samples_leaf"]
    assert type(leaves[0]) is int
    assert type(leaves[1]) is float


def test_fixed_parameter_types_reach_the_fitted_estimator(tmp_path):
    frame = _classification_frame()
    integer_run = run_experiment(
        _config(
            tmp_path / "integer",
            model_params={"max_features": 1, "n_estimators": 2, "n_jobs": 1, "verbose": 0},
        ),
        frame,
    )
    float_run = run_experiment(
        _config(
            tmp_path / "float",
            model_params={"max_features": 1.0, "n_estimators": 2, "n_jobs": 1},
        ),
        frame,
    )
    integer_forest = integer_run.model.named_steps["model"]
    float_forest = float_run.model.named_steps["model"]
    assert type(integer_forest.get_params()["max_features"]) is int
    assert type(float_forest.get_params()["max_features"]) is float
    assert type(integer_forest.get_params()["verbose"]) is int
    assert integer_forest.get_params()["verbose"] == 0
    assert type(integer_forest.get_params()["n_jobs"]) is int
    # Effective behaviour: an int selects one feature, a float selects all four.
    assert integer_forest.estimators_[0].max_features_ == 1
    assert float_forest.estimators_[0].max_features_ == frame.shape[1] - 1


def test_max_samples_integer_and_fraction_reach_the_fitted_estimator(tmp_path):
    frame = _classification_frame()
    integer_run = run_experiment(
        _config(tmp_path / "integer", model_params={"max_samples": 1, "n_estimators": 1}),
        frame,
    )
    fraction_run = run_experiment(
        _config(tmp_path / "fraction", model_params={"max_samples": 1.0, "n_estimators": 1}),
        frame,
    )
    integer_tree = integer_run.model.named_steps["model"].estimators_[0].tree_
    fraction_tree = fraction_run.model.named_steps["model"].estimators_[0].tree_
    assert type(integer_run.model.named_steps["model"].get_params()["max_samples"]) is int
    assert type(fraction_run.model.named_steps["model"].get_params()["max_samples"]) is float
    # Effective bootstrap size: one row for the integer count, all rows for the fraction.
    assert integer_tree.weighted_n_node_samples[0] == 1
    assert fraction_tree.weighted_n_node_samples[0] == len(frame)


def test_custom_grid_candidates_preserve_number_types(tmp_path):
    config = _config(
        tmp_path,
        tuning_mode="custom",
        parameter_grids={
            "random_forest": {"max_features": [1, 1.0], "min_samples_leaf": [1, 0.25]}
        },
    )
    candidates = _parameter_candidates(config, "random_forest")
    max_features_types = {(type(c["max_features"]), c["max_features"]) for c in candidates}
    min_samples_types = {(type(c["min_samples_leaf"]), c["min_samples_leaf"]) for c in candidates}
    assert (int, 1) in max_features_types
    assert (float, 1.0) in max_features_types
    assert (int, 1) in min_samples_types
    assert (float, 0.25) in min_samples_types


def test_validate_model_parameters_accepts_counts_and_legal_fractions():
    validate_model_parameters(
        "classification",
        "random_forest",
        {
            "max_features": 1,
            "max_samples": 1.0,
            "verbose": 0,
            "n_jobs": 1,
            "min_samples_leaf": 0.25,
        },
        source="fixed parameter",
    )
    validate_model_parameters(
        "classification", "random_forest", {"max_features": 1.0}, source="fixed parameter"
    )
    validate_model_parameters(
        "classification", "random_forest", {"min_samples_leaf": 1}, source="fixed parameter"
    )


def test_unknown_fixed_parameter_names_are_reported():
    with pytest.raises(ValueError, match="max_features_typo"):
        validate_model_parameters(
            "classification",
            "random_forest",
            {"max_features_typo": 1},
            source="fixed parameter",
        )


@pytest.mark.parametrize(
    ("model_name", "params"),
    [
        ("decision_tree", {"max_depth": 3.0}),
        ("mlp", {"max_iter": 30.0}),
    ],
)
def test_whole_number_decimal_counts_are_rejected_with_guidance(model_name, params):
    parameter = next(iter(params))
    with pytest.raises(ValueError) as error:
        validate_model_parameters(
            "classification", model_name, params, source="fixed parameter"
        )
    message = str(error.value)
    assert parameter in message
    assert "write" in message


def test_invalid_fixed_decimal_count_fails_before_any_output(tmp_path):
    frame = _classification_frame()
    config = _config(tmp_path, model_params={"min_samples_leaf": 1.0})
    with pytest.raises(ValueError, match="min_samples_leaf") as error:
        run_experiment(config, frame)
    message = str(error.value)
    assert "1.0" in message
    assert "write 1" in message
    assert not config.output_dir.exists()


def test_invalid_grid_decimal_count_fails_before_any_output(tmp_path):
    frame = _classification_frame()
    config = _config(
        tmp_path,
        tuning_mode="custom",
        parameter_grids={"random_forest": {"min_samples_leaf": [1.0]}},
    )
    with pytest.raises(ValueError, match="min_samples_leaf"):
        run_experiment(config, frame)
    assert not config.output_dir.exists()
