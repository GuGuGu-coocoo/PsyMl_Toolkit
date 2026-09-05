"""Bounded real-fit coverage; no mocked estimators or large research datasets."""

import hashlib
import json
import runpy
import shutil
from dataclasses import replace
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.model_selection import ParameterGrid

from psyml import ExperimentConfig, run_experiment
from psyml.data import load_dataframe
from psyml.gui_config import import_configuration
from psyml.models import supported_models
from psyml.models.catalog import quick_parameter_grid
from psyml.runner import _build_pipeline, _prepare_data

DATA = runpy.run_path(str(Path(__file__).parents[1] / "tools/generate_matrix_data.py"))
SAS_FIXTURES = Path(__file__).parents[1] / "examples/synthetic/matrix"
MODELS = [(task, model) for task in ["classification", "regression"]
          for model in supported_models(task)]
PREPROCESSING = list(product(["drop", "mean", "median", "mode"],
                             ["none", "standard", "minmax"]))
VALIDATIONS = {
    "classification": ["holdout", "k_fold", "stratified_k_fold", "group_k_fold",
                       "stratified_group_k_fold", "leave_one_group_out"],
    "regression": ["holdout", "k_fold", "group_k_fold", "leave_one_group_out"],
}


def config(task, model, **kwargs):
    return ExperimentConfig(task=task, model_name=model, target_column="target",
                            group_column="participant", feature_columns=DATA["FEATURES"],
                            figure_types=[], n_splits=2, inner_splits=2, **kwargs)


def fast_params(model):
    # Only reduce training effort outside the exact recommended-grid checks.
    if model == "mlp":
        return {"hidden_layer_sizes": [8], "max_iter": 60}
    if model in {"random_forest", "gradient_boosting"}:
        return {"n_estimators": 5}
    if model == "stacking":
        return {"cv": 2}
    if model == "qda":
        # Full one-hot columns are collinear; QDA needs explicit regularization.
        return {"reg_param": 0.1}
    return {}


def assert_predictions(task, prediction, target):
    assert len(prediction) == len(target)
    assert pd.notna(prediction).all()
    if task == "classification":
        assert set(prediction) <= set(target)
    else:
        assert np.isfinite(np.asarray(prediction, dtype=float)).all()


@pytest.mark.parametrize("task,model", MODELS)
@pytest.mark.parametrize("missing,scaling", PREPROCESSING)
@pytest.mark.filterwarnings("ignore::sklearn.exceptions.ConvergenceWarning")
def test_every_model_preprocessing_pair(task, model, missing, scaling):
    cfg = config(task, model, missing_strategy=missing, scaling=scaling)
    x, y, groups, dropped = _prepare_data(cfg, DATA["make_frame"](task))
    assert dropped == (4 if missing == "drop" else 0)
    train, test = np.arange(32), np.arange(32, len(x))
    pipeline = _build_pipeline(cfg, x.iloc[train], model, fast_params(model),
                               y.iloc[train], groups.iloc[train])
    pipeline.fit(x.iloc[train], y.iloc[train])
    unseen = x.iloc[test].copy()
    unseen["category"] = "unseen_site"
    assert_predictions(task, pipeline.predict(unseen), y.iloc[test])


GRID_CASES = [
    pytest.param(task, model, params, classes,
                 id=f"{task}-{model}-classes{classes}-{index}")
    for task, model in MODELS
    for index, params in enumerate(ParameterGrid(quick_parameter_grid(task, model)))
    for classes in ([2, 3] if task == "classification" else [2])
]


@pytest.mark.parametrize("task,model,params,classes", GRID_CASES)
@pytest.mark.filterwarnings("ignore::sklearn.exceptions.ConvergenceWarning")
def test_every_recommended_candidate_actually_fits(task, model, params, classes):
    cfg = config(task, model)
    if model == "qda" and params.get("reg_param") == 0:
        cfg = replace(cfg, feature_columns=["signal", "noise"])
    x, y, groups, _ = _prepare_data(cfg, DATA["make_frame"](task, classes))
    train, test = np.arange(36), np.arange(36, 48)
    pipeline = _build_pipeline(cfg, x.iloc[train], model, params,
                               y.iloc[train], groups.iloc[train])
    pipeline.fit(x.iloc[train], y.iloc[train])
    assert_predictions(task, pipeline.predict(x.iloc[test]), y.iloc[test])


@pytest.mark.parametrize("task,model,validation", [
    (task, model, validation) for task, model in MODELS for validation in VALIDATIONS[task]
])
@pytest.mark.filterwarnings("ignore::sklearn.exceptions.ConvergenceWarning")
def test_every_model_validation_exports_real_results(task, model, validation, tmp_path):
    cfg = config(task, model, validation_strategy=validation, output_dir=tmp_path / "run",
                 model_params=fast_params(model))
    result = run_experiment(cfg, DATA["make_frame"](task))
    assert set(result.leaderboard.status) == {"completed"}
    assert all(np.isfinite(value) for value in result.metrics.values())
    # A grouped holdout rounds up to two whole groups, each with six rows.
    assert result.predictions.row_index.nunique() == (12 if validation == "holdout" else 48)
    assert result.best_model_name == model
    for name in ["result.json", "predictions.csv", "metrics.csv", "config.json"]:
        assert (cfg.output_dir / name).is_file()


@pytest.fixture(scope="module")
def format_data(tmp_path_factory):
    root = tmp_path_factory.mktemp("小数据 中文路径")
    DATA["generate"](root)
    # Exercise committed real binaries on every platform without loading the
    # optional private writer interface in normal tests.
    for path in SAS_FIXTURES.glob("*.sas7bdat"):
        shutil.copy2(path, root / path.name)
    for path in SAS_FIXTURES.glob("*_sas7bdat_config.json"):
        shutil.copy2(path, root / path.name)
    return root


@pytest.mark.parametrize("suffix", [*DATA["FORMATS"], "sas7bdat"])
@pytest.mark.parametrize("name,task,classes", [
    ("binary", "classification", 2), ("multiclass", "classification", 3),
    ("regression", "regression", 2),
])
def test_each_format_roundtrip_and_analysis(format_data, suffix, name, task, classes, tmp_path):
    path = format_data / f"{name}.{suffix}"
    loaded = load_dataframe(path)
    expected = DATA["make_frame"](task, classes)
    assert loaded.shape == expected.shape
    for column in ["signal", "noise", "target", "admin_note"]:
        np.testing.assert_allclose(loaded[column], expected[column], equal_nan=True)
    assert loaded.participant.tolist() == expected.participant.tolist()
    # SAV/DTA/XPT use empty strings for missing categorical cells.
    assert loaded.category.fillna("").tolist() == expected.category.fillna("").tolist()
    imported = import_configuration(format_data / f"{name}_{suffix}_config.json")
    assert not imported["needs_data"]
    assert imported["preview"]["row_count"] == 48
    assert imported["config"]["feature_columns"] == DATA["FEATURES"]
    cfg = config(task, "decision_tree", input_path=path, output_dir=tmp_path / "run",
                 validation_strategy="group_k_fold", model_params={"max_depth": 3})
    result = run_experiment(cfg)
    assert result.predictions.row_index.nunique() == 48
    assert all(np.isfinite(value) for value in result.metrics.values())
    saved = json.loads((cfg.output_dir / "result.json").read_text())
    assert saved
    x, _, _, dropped = _prepare_data(replace(cfg, missing_strategy="drop"), loaded)
    assert dropped == 4
    assert len(x) == 44


@pytest.mark.parametrize("task,model", MODELS)
@pytest.mark.parametrize("mode", ["quick", "custom"])
@pytest.mark.filterwarnings("ignore::sklearn.exceptions.ConvergenceWarning")
def test_each_model_nested_parameter_search(task, model, mode, tmp_path):
    cfg = config(task, model, output_dir=tmp_path / "run", model_params=fast_params(model),
                 tuning_mode=mode, max_candidates=2,
                 parameter_grids={model: quick_parameter_grid(task, model)} if mode == "custom"
                 else {})
    if model == "qda":
        cfg = replace(cfg, feature_columns=["signal", "noise"])
    result = run_experiment(cfg, DATA["make_frame"](task))
    assert set(result.tuning_results.status) == {"completed"}
    assert set(result.tuning_results.selection_scope) == {"outer_training_fold", "final_full_data"}
    assert len(result.tuning_results) == 4  # two candidates × (outer training + final refit)
    assert all(np.isfinite(value) for value in result.metrics.values())


@pytest.mark.parametrize("classes", [2, 3])
@pytest.mark.parametrize("passthrough", [False, True])
@pytest.mark.parametrize("method", ["auto", "predict"])
def test_stacking_method_passthrough_interaction(classes, passthrough, method, tmp_path):
    cfg = config("classification", "stacking", output_dir=tmp_path / "run",
                 model_params={"cv": 2, "passthrough": passthrough, "stack_method": method})
    frame = DATA["make_frame"]("classification", classes)
    result = run_experiment(cfg, frame)
    assert result.predictions.row_index.nunique() == 12
    assert set(result.leaderboard.status) == {"completed"}
    assert_predictions("classification", result.model.predict(frame[DATA["FEATURES"]]),
                       frame.target)


# Deliberately incompatible choices must remain explicit failures, never silently
# substituted parameters or a successful result marker.
@pytest.mark.parametrize("task,model,params,reason", [
    ("classification", "knn", {"n_neighbors": 1000}, "n_neighbors"),
    ("classification", "svm", {"C": -1}, "C"),
    ("classification", "lda", {"solver": "svd", "shrinkage": "auto"}, "shrinkage"),
    ("classification", "stacking", {"cv": "prefit"}, "prefit"),
    ("classification", "stacking", {"stack_method": "decision_function"}, "decision_function"),
    ("classification", "stacking", {"stack_method": "predict_proba"}, "predict_proba"),
    ("classification", "qda", {"reg_param": 0}, "rank|covariance|finite"),
    ("regression", "decision_tree", {"criterion": "poisson"}, "negative|Poisson|poisson"),
    ("regression", "elastic_net", {"l1_ratio": 2}, "l1_ratio"),
    ("regression", "ridge", {"not_a_parameter": 1}, "not_a_parameter"),
])
def test_incompatible_parameters_fail_with_reason(task, model, params, reason, tmp_path):
    cfg = config(task, model, model_params=params, output_dir=tmp_path / "run")
    with pytest.raises((ValueError, TypeError), match=reason):
        run_experiment(cfg, DATA["make_frame"](task))
    assert not (cfg.output_dir / "result.json").exists()


@pytest.mark.parametrize("task,metric", [
    ("classification", "accuracy"), ("classification", "balanced_accuracy"),
    ("classification", "f1_macro"), ("regression", "r2"),
    ("regression", "mae"), ("regression", "rmse"),
])
@pytest.mark.parametrize("validation", ["holdout", "group_k_fold"])
def test_failed_candidate_does_not_hide_valid_candidate(task, metric, validation, tmp_path):
    cfg = config(task, "knn", output_dir=tmp_path / "run", validation_strategy=validation,
                 tuning_mode="custom", parameter_grids={"knn": {"n_neighbors": [1000, 3]}},
                 selection_metric=metric)
    result = run_experiment(cfg, DATA["make_frame"](task))
    assert set(result.tuning_results.status) == {"failed", "completed"}
    assert result.best_params["n_neighbors"] == 3
    assert (cfg.output_dir / "result.json").is_file()
    assert all(np.isfinite(value) for value in result.metrics.values())


@pytest.mark.parametrize("missing,scaling", PREPROCESSING)
@pytest.mark.parametrize("kind", ["nullable_boolean", "nullable_number", "categorical_only",
                                  "string_target", "empty_numeric"])
def test_small_data_schema_variations(missing, scaling, kind, tmp_path):
    frame = DATA["make_frame"]()
    if kind == "nullable_boolean":
        frame["noise"] = pd.Series([True, False, pd.NA] * 16, dtype="boolean")
    elif kind == "nullable_number":
        frame["signal"] = frame.signal.astype("Float64")
    elif kind == "categorical_only":
        frame["signal"] = frame.category
        frame["noise"] = frame.category
    elif kind == "string_target":
        frame["target"] = frame.target.map({0: "对照", 1: "试验"})
    else:
        frame["signal"] = np.nan
    cfg = config("classification", "logistic_regression", missing_strategy=missing,
                 scaling=scaling, output_dir=tmp_path / "run")
    if kind == "empty_numeric" and missing == "drop":
        with pytest.raises(ValueError, match="No rows remain"):
            run_experiment(cfg, frame)
        assert not (cfg.output_dir / "result.json").exists()
        return
    result = run_experiment(cfg, frame)
    assert result.metrics and all(np.isfinite(value) for value in result.metrics.values())
    assert set(result.leaderboard.status) == {"completed"}


CUSTOM_CASES = [
    ("classification", "svm", {"kernel": kernel, "probability": probability, "C": 0.3})
    for kernel, probability in product(["linear", "rbf", "poly", "sigmoid"], [False, True])
] + [
    (task, "knn", {"algorithm": algorithm, "p": p, "weights": "distance", "n_neighbors": 3})
    for task, algorithm, p in product(["classification", "regression"],
                                      ["auto", "ball_tree", "kd_tree", "brute"], [1, 2])
] + [
    ("classification", "lda", {"solver": solver, "shrinkage": shrinkage})
    for solver, shrinkage in product(["lsqr", "eigen"], ["auto", 0.2])
] + [
    (task, "decision_tree", {"max_depth": 3.0, "min_samples_leaf": 0.1,
                              "min_samples_split": 0.2, "max_features": features})
    for task, features in product(["classification", "regression"], [None, "sqrt", 0.5])
] + [
    (task, "mlp", {"solver": solver, "activation": "tanh", "hidden_layer_sizes": [6.0, 3.0],
                   "max_iter": 30.0, "early_stopping": early})
    for task, solver, early in product(["classification", "regression"],
                                       ["adam", "sgd", "lbfgs"], [False, True])
] + [
    ("regression", "ridge", {"solver": "lbfgs", "positive": True, "alpha": 0.1}),
    ("regression", "linear_regression", {"positive": True, "fit_intercept": False}),
    ("regression", "gradient_boosting", {"loss": "huber", "n_estimators": 5}),
    ("regression", "gradient_boosting", {"loss": "quantile", "alpha": 0.9, "n_estimators": 5}),
]


@pytest.mark.parametrize("task,model,params", CUSTOM_CASES)
@pytest.mark.filterwarnings("ignore::sklearn.exceptions.ConvergenceWarning")
def test_additional_custom_parameter_interactions(task, model, params, tmp_path):
    cfg = config(task, model, model_params=params, output_dir=tmp_path / "run")
    result = run_experiment(cfg, DATA["make_frame"](task))
    assert set(result.leaderboard.status) == {"completed"}
    assert all(np.isfinite(value) for value in result.metrics.values())


@pytest.mark.parametrize("name,task,classes", [
    ("binary", "classification", 2), ("multiclass", "classification", 3),
    ("regression", "regression", 2),
])
def test_sas7bdat_independent_reader(name, task, classes):
    path = SAS_FIXTURES / f"{name}.sas7bdat"
    records = json.loads((SAS_FIXTURES / "sas7bdat_manifest.json").read_text())["files"]
    record = next(record for record in records if record["file"] == path.name)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"]
    assert path.stat().st_size == record["bytes"]
    # pandas has its own SAS parser, independent of pyreadstat/ReadStat.
    loaded = pd.read_sas(path, encoding="utf-8").replace("", float("nan"))
    expected = DATA["make_frame"](task, classes)
    pd.testing.assert_frame_equal(loaded, expected, check_dtype=False, atol=1e-12, rtol=1e-12)


@pytest.mark.parametrize("name", ["binary", "multiclass", "regression"])
def test_sas7bdat_cli_events_and_exports(name, format_data, tmp_path, capsys):
    from psyml.cli import main

    payload = json.loads((format_data / f"{name}_sas7bdat_config.json").read_text())
    payload.update(input_path=str(format_data / f"{name}.sas7bdat"),
                   output_dir=str(tmp_path / "run"), missing_strategy="drop",
                   tuning_mode="custom", parameter_grids={"decision_tree": {"max_depth": [1, 3]}})
    path = tmp_path / "配置.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert main(["run", "--config", str(path), "--events"]) == 0
    events = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert events[-1]["event"] == "completed"
    output = tmp_path / "run"
    predictions = pd.read_csv(output / "predictions.csv")
    assert len(predictions) == predictions.row_index.nunique() == 44
    assert pd.read_csv(output / "parameter_search.csv").status.eq("completed").all()
    assert (output / "result.json").is_file()


def test_truncated_real_sas7bdat_reports_filename_and_format(tmp_path):
    path = tmp_path / "损坏样例.sas7bdat"
    path.write_bytes((SAS_FIXTURES / "binary.sas7bdat").read_bytes()[:64])
    with pytest.raises(ValueError, match=r"Failed to read '\.sas7bdat'.*损坏样例"):
        load_dataframe(path)
