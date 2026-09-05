import json

import numpy as np
import pandas as pd
import pytest

from psyml import ExperimentConfig, run_experiment
from psyml.validation import split_train_test


def _classification_frame() -> pd.DataFrame:
    values = np.arange(40, dtype=float)
    return pd.DataFrame(
        {
            "continuous": values,
            "category": ["a", "b"] * 20,
            "target": [0, 1] * 20,
        }
    )


def test_classification_pipeline_fits_scaler_to_training_partition_only(tmp_path, monkeypatch):
    frame = _classification_frame()
    config = ExperimentConfig(
        task="classification",
        target_column="target",
        model_name="svm",
        output_dir=tmp_path / "classification",
        random_seed=7,
    )

    from sklearn.preprocessing import StandardScaler

    fitted_means = []
    original_fit = StandardScaler.fit

    def record_fit(self, X, y=None, sample_weight=None):
        fitted_means.append(
            float(X.iloc[:, 0].mean()) if hasattr(X, "iloc") else float(X[:, 0].mean())
        )
        return original_fit(self, X, y, sample_weight)

    monkeypatch.setattr(StandardScaler, "fit", record_fit)
    result = run_experiment(config, frame)

    train_x, _, _, _ = split_train_test(
        frame[["continuous", "category"]],
        frame["target"],
        "classification",
        config.test_size,
        config.random_seed,
    )
    scaler = (
        result.model.named_steps["preprocess"].named_transformers_["numeric"].named_steps["scale"]
    )
    assert fitted_means[0] == train_x["continuous"].mean()
    assert fitted_means[0] != frame["continuous"].mean()
    assert scaler.mean_[0] == frame["continuous"].mean()
    assert {"accuracy", "balanced_accuracy", "f1_weighted", "roc_auc"} <= result.metrics.keys()
    assert (config.output_dir / "metrics.csv").is_file()
    assert (config.output_dir / "predictions.csv").is_file()
    saved_config = json.loads((config.output_dir / "config.json").read_text(encoding="utf-8"))
    assert saved_config["random_seed"] == 7


def test_regression_outputs_holdout_metrics(tmp_path):
    features = np.linspace(0, 10, 48)
    frame = pd.DataFrame({"feature": features, "target": 2 * features + 1})
    config = ExperimentConfig(
        task="regression",
        target_column="target",
        model_name="lasso",
        output_dir=tmp_path / "regression",
        random_seed=3,
        model_params={"alpha": 0.001},
    )

    result = run_experiment(config, frame)

    assert {"r2", "mae", "rmse"} == result.metrics.keys()
    assert result.metrics["r2"] > 0.99
    assert len(result.predictions) > 0


def test_cross_validation_exports_fold_metrics_and_confusion_matrix(tmp_path):
    frame = _classification_frame()
    config = ExperimentConfig(
        task="classification",
        target_column="target",
        model_name="logistic_regression",
        output_dir=tmp_path / "cross validation 中文",
        validation_strategy="stratified_k_fold",
        n_splits=4,
        scaling="minmax",
    )

    result = run_experiment(config, frame)

    assert len(result.fold_metrics) == 4
    assert set(result.metric_summary.columns) == {
        "metric",
        "mean",
        "std",
        "min",
        "max",
        "n_folds",
    }
    assert set(result.metric_summary["n_folds"]) == {4}
    assert set(result.predictions["fold"]) == {1, 2, 3, 4}
    assert (config.output_dir / "fold_metrics.csv").is_file()
    assert (config.output_dir / "metrics_summary.csv").is_file()
    assert (config.output_dir / "confusion_matrix.csv").is_file()
    assert (config.output_dir / "warnings.json").is_file()


def test_drop_missing_strategy_reports_removed_rows(tmp_path):
    frame = _classification_frame()
    frame.loc[0, "continuous"] = np.nan
    config = ExperimentConfig(
        task="classification",
        target_column="target",
        model_name="dummy",
        output_dir=tmp_path / "drop",
        missing_strategy="drop",
        scaling="none",
    )

    result = run_experiment(config, frame)

    assert result.warnings == ["Dropped 1 rows because missing_strategy='drop'."]


@pytest.mark.parametrize("missing_strategy", ["mean", "median", "mode"])
@pytest.mark.parametrize("scaling", ["none", "standard", "minmax"])
def test_preprocessing_options_handle_mixed_missing_data(missing_strategy, scaling, tmp_path):
    frame = _classification_frame()
    frame.loc[0, "continuous"] = np.nan
    frame.loc[1, "category"] = None
    config = ExperimentConfig(
        task="classification",
        target_column="target",
        model_name="dummy",
        output_dir=tmp_path / f"{missing_strategy}-{scaling}",
        missing_strategy=missing_strategy,
        scaling=scaling,
    )

    result = run_experiment(config, frame)

    assert len(result.predictions) > 0


def test_regression_k_fold_evaluates_every_row_once(tmp_path):
    features = np.linspace(0, 10, 30)
    frame = pd.DataFrame({"feature": features, "target": 2 * features + 1})
    config = ExperimentConfig(
        task="regression",
        target_column="target",
        model_name="linear_regression",
        output_dir=tmp_path / "k-fold",
        validation_strategy="k_fold",
        n_splits=3,
    )

    result = run_experiment(config, frame)

    assert len(result.fold_metrics) == 3
    assert sorted(result.predictions["row_index"]) == list(range(len(frame)))


def test_target_and_group_columns_never_enter_model_features(tmp_path):
    frame = _classification_frame().assign(
        participant=[f"participant-{index // 2}" for index in range(40)]
    )
    config = ExperimentConfig(
        task="classification",
        target_column="target",
        group_column="participant",
        model_name="dummy",
        output_dir=tmp_path / "group isolation",
        validation_strategy="group_k_fold",
        n_splits=4,
    )

    result = run_experiment(config, frame)

    feature_names = set(result.model.named_steps["preprocess"].feature_names_in_)
    assert feature_names == {"continuous", "category"}


def test_explicit_feature_selection_excludes_unselected_columns(tmp_path):
    frame = _classification_frame().assign(unselected=np.arange(40) * 100)
    config = ExperimentConfig(
        task="classification",
        target_column="target",
        feature_columns=["continuous"],
        model_name="dummy",
        output_dir=tmp_path / "feature selection",
    )

    result = run_experiment(config, frame)

    feature_names = list(result.model.named_steps["preprocess"].feature_names_in_)
    assert feature_names == ["continuous"]


def test_non_group_validation_warns_when_group_column_is_supplied(tmp_path):
    frame = _classification_frame().assign(
        participant=[f"participant-{index // 2}" for index in range(40)]
    )
    config = ExperimentConfig(
        task="classification",
        target_column="target",
        group_column="participant",
        model_name="dummy",
        output_dir=tmp_path / "group warning",
        validation_strategy="stratified_k_fold",
        n_splits=4,
    )

    result = run_experiment(config, frame)

    assert result.warnings == [
        "A group column was supplied but the selected validation strategy does not isolate groups."
    ]


def test_multi_model_multi_validation_nested_search_and_progress(tmp_path):
    rng = np.random.default_rng(91)
    signal = rng.normal(size=60)
    frame = pd.DataFrame(
        {
            "signal": signal,
            "noise": rng.normal(size=60),
            "target": (signal > 0).astype(int),
        }
    )
    progress = []
    config = ExperimentConfig(
        task="classification",
        target_column="target",
        model_name="decision_tree",
        model_names=["decision_tree", "dummy"],
        output_dir=tmp_path / "comparative study",
        validation_strategy="stratified_k_fold",
        validation_strategies=["stratified_k_fold", "holdout"],
        n_splits=3,
        tuning_mode="custom",
        parameter_grids={
            "decision_tree": {"max_depth": [1, None]},
            "dummy": {"strategy": ["prior", "stratified"]},
        },
        inner_splits=2,
        max_candidates=4,
        selection_metric="balanced_accuracy",
    )

    result = run_experiment(config, frame, progress_callback=progress.append)

    assert result.best_model_name == "decision_tree"
    assert result.best_validation_strategy == "stratified_k_fold"
    assert len(result.leaderboard) == 4
    assert set(result.leaderboard["validation"]) == {"stratified_k_fold", "holdout"}
    assert set(result.leaderboard.groupby("validation")["rank"].min()) == {1}
    assert not result.tuning_results.empty
    assert set(result.tuning_results["status"]) == {"completed"}
    assert set(result.tuning_results["selection_scope"]) == {
        "outer_training_fold",
        "final_full_data",
    }
    assert set(result.tuning_results.loc[result.tuning_results["outer_fold"] == 0, "model"]) == {
        "decision_tree",
        "dummy",
    }
    assert (
        json.loads((config.output_dir / "best_parameters.json").read_text(encoding="utf-8"))
        == result.best_params
    )
    assert progress[0]["progress"] == 0.0
    assert progress[0]["estimated_remaining_seconds"] is None
    assert progress[-1]["progress"] == 1.0
    assert progress[-1]["remaining_tasks"] == 0
    assert [item["progress"] for item in progress] == sorted(item["progress"] for item in progress)
    for artifact in [
        "model_comparison.csv",
        "parameter_search.csv",
        "best_parameters.json",
        "study_config.json",
    ]:
        assert (config.output_dir / artifact).is_file()
