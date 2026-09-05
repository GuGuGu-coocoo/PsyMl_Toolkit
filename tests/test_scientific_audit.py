"""Regression cases found in the September 2026 scientific audit."""

import json
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest
from sklearn.dummy import DummyClassifier
from sklearn.metrics import roc_auc_score

from psyml import ExperimentConfig, run_experiment
from psyml.evaluation.metrics import classification_metrics
from psyml.models import build_model
from psyml.runner import _prepare_data


def config(tmp_path, **kwargs):
    return ExperimentConfig(
        task="classification",
        target_column="y",
        model_name="dummy",
        output_dir=tmp_path / "run",
        **kwargs,
    )


def frame():
    return pd.DataFrame(
        {"x": np.arange(48.0), "y": [0, 1] * 24, "group": np.repeat(np.arange(12), 4)},
        index=np.arange(100, 148),
    )


def test_unselected_missing_admin_does_not_exclude_rows(tmp_path):
    data = frame().assign(admin=np.nan)
    x, y, groups, dropped = _prepare_data(
        config(tmp_path, feature_columns=["x"], group_column="group", missing_strategy="drop"), data
    )
    assert len(x) == 48 and dropped == 0
    assert x.index.equals(y.index) and x.index.equals(groups.index)


def test_missing_target_is_counted_and_prediction_indices_survive(tmp_path):
    data = frame()
    data.loc[101, "y"] = np.nan
    data.loc[105, "x"] = np.nan
    result = run_experiment(
        config(
            tmp_path,
            feature_columns=["x"],
            group_column="group",
            missing_strategy="drop",
            validation_strategy="group_k_fold",
            n_splits=3,
        ),
        data,
    )
    assert set(result.predictions.row_index) == set(data.index) - {101, 105}
    assert (
        result.predictions.observed.tolist() == data.loc[result.predictions.row_index, "y"].tolist()
    )
    assert any("target" in w and "1" in w for w in result.warnings)


def test_holdout_final_model_uses_all_rows_without_changing_oos(tmp_path):
    result = run_experiment(config(tmp_path, feature_columns=["x"]), frame())
    scaler = result.model.named_steps["preprocess"].named_transformers_["numeric"]["scale"]
    assert scaler.n_samples_seen_ == 48
    assert len(result.predictions) == 10


def test_multiclass_training_binary_test_does_not_invent_binary_auc():
    x = pd.DataFrame({"x": range(9)})
    model = DummyClassifier(strategy="prior").fit(x, [0, 1, 2] * 3)
    metrics = classification_metrics(model, x.iloc[:4], [0, 2, 0, 2], [0] * 4)
    assert "roc_auc" not in metrics


def test_binary_auc_uses_estimator_class_order():
    class Reversed:
        classes_ = np.array(["yes", "no"])

        def predict_proba(self, x):
            return np.array([[0.9, 0.1], [0.2, 0.8], [0.8, 0.2], [0.1, 0.9]])

    observed = np.array(["yes", "no", "yes", "no"])
    m = classification_metrics(Reversed(), None, observed, observed)
    assert m["roc_auc"] == roc_auc_score(observed == "no", [0.1, 0.8, 0.2, 0.9])


def test_dummy_respects_seed():
    x = np.zeros((100, 1))
    y = [0, 1] * 50
    a = build_model("classification", "dummy", 19, {"strategy": "stratified"}).fit(x, y)
    b = build_model("classification", "dummy", 19, {"strategy": "stratified"}).fit(x, y)
    np.testing.assert_array_equal(a.predict(x), b.predict(x))


def test_default_parameter_can_be_overridden():
    assert build_model("classification", "mlp", 19, {"max_iter": 12}).max_iter == 12


def test_no_inner_splits_cannot_silently_choose_first_candidate(tmp_path):
    data = frame().iloc[:8].copy()
    data["group"] = [0] * 4 + [1] * 4
    cfg = config(
        tmp_path,
        feature_columns=["x"],
        group_column="group",
        validation_strategy="group_k_fold",
        n_splits=2,
        tuning_mode="custom",
        parameter_grids={"dummy": {"strategy": ["prior", "stratified"]}},
    )
    with pytest.raises(ValueError, match="inner|parameter candidates"):
        run_experiment(cfg, data)


def test_replay_config_retains_original_search_base(tmp_path):
    cfg = config(
        tmp_path,
        feature_columns=["x"],
        tuning_mode="custom",
        parameter_grids={"dummy": {"strategy": ["prior", "stratified"]}},
        inner_splits=2,
    )
    run_experiment(cfg, frame())
    payload = json.loads((cfg.output_dir / "config.json").read_text())
    assert payload["model_params"] == {}


def test_existing_output_is_preserved_on_retry(tmp_path):
    cfg = config(tmp_path, feature_columns=["x"])
    run_experiment(cfg, frame())
    before = (cfg.output_dir / "result.json").read_bytes()
    with pytest.raises((ValueError, FileExistsError), match="output|Output"):
        run_experiment(cfg, frame())
    assert (cfg.output_dir / "result.json").read_bytes() == before


def test_tiny_r2_primary_has_clear_failure(tmp_path):
    cfg = ExperimentConfig(
        task="regression",
        target_column="y",
        model_name="dummy",
        feature_columns=["x"],
        output_dir=tmp_path / "tiny",
        validation_strategy="k_fold",
        n_splits=3,
        selection_metric="r2",
    )
    with pytest.raises(ValueError, match="selection|finite"):
        run_experiment(cfg, pd.DataFrame({"x": [1, 2, 3], "y": [2, 4, 9]}))


def test_family_selection_warning_and_report(tmp_path):
    cfg = replace(config(tmp_path, feature_columns=["x"]), model_names=["dummy", "decision_tree"])
    result = run_experiment(cfg, frame())
    assert any("selection" in w and "independent" in w for w in result.warnings)
    methods = (cfg.output_dir / "methods_summary.md").read_text().lower()
    assert "model-family selection and parameter selection were jointly nested" in methods


def test_inner_tuning_preserves_outer_group_isolation(tmp_path):
    from psyml.runner import _make_work_items

    cfg = config(
        tmp_path,
        feature_columns=["x"],
        group_column="group",
        validation_strategy="group_k_fold",
        n_splits=3,
        tuning_mode="quick",
        inner_splits=3,
    )
    x, y, groups, _ = _prepare_data(cfg, frame())
    work, _ = _make_work_items(cfg, x, y, groups)
    for item in work:
        train_groups = groups.iloc[item.train_index]
        assert set(train_groups).isdisjoint(groups.iloc[item.test_index])
        for train, test in item.inner_splits:
            assert set(train_groups.iloc[train]).isdisjoint(train_groups.iloc[test])


@pytest.mark.parametrize("passthrough", [False, True])
def test_stacking_crossfits_preprocessing_and_groups(tmp_path, passthrough, monkeypatch):
    from sklearn.preprocessing import StandardScaler

    from psyml.runner import _build_pipeline

    data = frame().assign(category=["a", "b", "c", "d"] * 12)
    cfg = replace(
        config(tmp_path, feature_columns=["x", "category"], group_column="group"),
        model_name="stacking",
    )
    x, y, groups, _ = _prepare_data(cfg, data)
    model = _build_pipeline(cfg, x, "stacking", {"cv": 3, "passthrough": passthrough}, y, groups)
    for train, test in model["model"].cv:
        assert set(groups.iloc[train]).isdisjoint(groups.iloc[test])
    fit_rows = []
    original = StandardScaler.fit

    def record(self, X, y=None, sample_weight=None):
        fit_rows.append(len(X))
        return original(self, X, y, sample_weight)

    monkeypatch.setattr(StandardScaler, "fit", record)
    model.fit(x, y)
    assert 32 in fit_rows  # each base preprocess learns only two of the three folds
    assert len(model.predict(x)) == len(x)


def test_failed_outer_fold_excludes_whole_combination(tmp_path):
    cfg = replace(
        config(tmp_path, feature_columns=["x"], validation_strategy="k_fold", n_splits=3),
        model_names=["knn", "dummy"],
        tuning_mode="custom",
        parameter_grids={"knn": {"n_neighbors": [1000]}},
    )
    result = run_experiment(cfg, frame())
    assert result.best_model_name == "dummy"
    row = result.leaderboard.set_index("model").loc["knn"]
    assert row.status == "failed" and pd.isna(row["rank"])
    assert any("Failed combination" in w for w in result.warnings)


def test_export_failure_never_leaves_success_marker(tmp_path, monkeypatch):
    from psyml import runner

    def fail(*args, **kwargs):
        raise OSError("simulated disk failure")

    monkeypatch.setattr(runner, "write_research_outputs", fail)
    cfg = config(tmp_path, feature_columns=["x"])
    with pytest.raises(OSError, match="disk failure"):
        run_experiment(cfg, frame())
    assert not (cfg.output_dir / "result.json").exists()


def test_missing_groups_require_resolution_without_silent_exclusion(tmp_path):
    data = frame()
    data.loc[101, "group"] = np.nan
    with pytest.raises(ValueError, match="Missing group"):
        _prepare_data(config(tmp_path, feature_columns=["x"], group_column="group"), data)


def test_cancellation_inside_estimator_is_not_treated_as_failed_fold(tmp_path, monkeypatch):
    from psyml.cli import CancellationRequested

    calls = []

    def cancel(*args, **kwargs):
        calls.append(1)
        raise CancellationRequested("stop during fitting")

    monkeypatch.setattr(DummyClassifier, "fit", cancel)
    cfg = config(tmp_path, feature_columns=["x"], validation_strategy="k_fold", n_splits=3)
    with pytest.raises(CancellationRequested):
        run_experiment(cfg, frame())
    assert calls == [1]
    assert not (cfg.output_dir / "result.json").exists()


def test_primary_failure_cannot_be_replaced_by_successful_sensitivity(tmp_path):
    cfg = replace(
        config(
            tmp_path,
            feature_columns=["x"],
            test_size=0.9,
            validation_strategies=["holdout", "k_fold"],
            n_splits=3,
        ),
        model_name="knn",
        model_params={"n_neighbors": 5},
    )
    with pytest.raises(ValueError, match="[Pp]rimary validation"):
        run_experiment(cfg, frame())
    assert not (cfg.output_dir / "result.json").exists()


def test_ambiguous_input_sources_are_rejected(tmp_path):
    input_path = tmp_path / "different.csv"
    frame().iloc[:8].to_csv(input_path, index=False)
    cfg = config(tmp_path, feature_columns=["x"], input_path=input_path)
    with pytest.raises(ValueError, match="either frame or input_path"):
        run_experiment(cfg, frame())
    assert not (cfg.output_dir / "analysis_manifest.json").exists()
