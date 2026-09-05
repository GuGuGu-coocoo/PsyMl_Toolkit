"""Protect the separation between family selection and outer evaluation."""

import json
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest
from sklearn.dummy import DummyClassifier

from psyml import ExperimentConfig, run_experiment, runner


def design(tmp_path):
    return ExperimentConfig(
        task="classification",
        target_column="target",
        group_column="group",
        feature_columns=["signal"],
        model_name="decision_tree",
        model_names=["decision_tree", "dummy"],
        output_dir=tmp_path / "run",
        validation_strategy="group_k_fold",
        n_splits=3,
        inner_splits=2,
    )


def data():
    # Every participant has both classes and the same deterministic signal.
    return pd.DataFrame(
        {
            "signal": [-1.0, 1.0] * 24,
            "target": [0, 1] * 24,
            "group": np.repeat(np.arange(12), 4),
        }
    )


def test_outer_leaderboard_cannot_select_family_or_parameters(tmp_path, monkeypatch):
    original = runner._fold_result

    def misleading_outer_scores(config, model, features, observed, predicted):
        values = original(config, model, features, observed, predicted)
        # Deliberately make the useless baseline top the outer leaderboard.
        values["balanced_accuracy"] = float(isinstance(model["model"], DummyClassifier))
        return values

    monkeypatch.setattr(runner, "_fold_result", misleading_outer_scores)
    result = run_experiment(design(tmp_path), data())
    assert result.leaderboard.iloc[0]["model"] == "dummy"
    assert result.best_model_name == "decision_tree"
    assert set(result.selection_trace.model) == {"decision_tree"}
    assert set(result.predictions.model) == {"decision_tree"}
    assert (result.predictions.observed == result.predictions.predicted).all()
    # Main results describe the selected pipeline, even if its reported outer metric loses.
    assert result.metrics["balanced_accuracy"] == 0.0


def test_no_parameter_search_still_selects_family_inside_grouped_inner_folds(tmp_path):
    config = design(tmp_path)
    features, target, groups, _ = runner._prepare_data(config, data())
    work_items, _ = runner._make_work_items(config, features, target, groups)
    for work in work_items:
        assert len(work.inner_splits) == 2
        train_groups = groups.iloc[work.train_index]
        for train, test in work.inner_splits:
            assert not set(train_groups.iloc[train]) & set(train_groups.iloc[test])
        assert not set(groups.iloc[work.train_index]) & set(groups.iloc[work.test_index])
    progress = []
    result = run_experiment(config, data(), progress_callback=progress.append)
    assert len(result.tuning_results) == 8  # 2 families × (3 outer choices + final choice)
    assert set(result.tuning_results.query("outer_fold == 0").model) == {"dummy", "decision_tree"}
    assert len(result.selection_trace) == 4
    assert result.predictions.row_index.nunique() == 48
    assert progress[-1]["completed_tasks"] == progress[-1]["total_tasks"]
    assert progress[-1]["progress"] == 1.0
    summary = json.loads((config.output_dir / "result.json").read_text())
    assert summary["evaluation_scope"] == "nested_selection_procedure"
    assert summary["selection_protocol"] == "nested_family_v1"


def test_selected_outer_failure_does_not_fall_back_to_successful_baseline(tmp_path, monkeypatch):
    original = runner._fold_result

    def fail_selected(config, model, features, observed, predicted):
        if not isinstance(model["model"], DummyClassifier):
            raise ValueError("Injected outer evaluation failure")  # noqa: TRY004
        return original(config, model, features, observed, predicted)

    monkeypatch.setattr(runner, "_fold_result", fail_selected)
    config = design(tmp_path)
    with pytest.raises(ValueError, match="Primary validation failed.*substitute"):
        run_experiment(config, data())
    assert not (config.output_dir / "result.json").exists()


def test_family_selection_cannot_run_with_one_inner_group(tmp_path):
    config = replace(design(tmp_path), n_splits=2)
    frame = data().iloc[:8]
    with pytest.raises(ValueError, match="Primary validation failed.*inner selection"):
        run_experiment(config, frame)


def test_sensitivity_results_do_not_change_primary_predictions_or_final_choice(tmp_path):
    config = design(tmp_path)
    primary = run_experiment(config, data())
    sensitivity = run_experiment(
        replace(
            config,
            output_dir=tmp_path / "sensitivity",
            validation_strategies=["group_k_fold", "holdout"],
        ),
        data(),
    )
    pd.testing.assert_frame_equal(primary.predictions, sensitivity.predictions)
    assert primary.best_model_name == sensitivity.best_model_name
    assert primary.best_params == sensitivity.best_params
    assert list(sensitivity.validation_summary.role) == ["primary", "sensitivity"]


def test_outer_holdout_targets_cannot_change_that_folds_inner_choice(tmp_path):
    config = replace(design(tmp_path), validation_strategy="holdout")
    original = data()
    first = run_experiment(config, original)
    changed = original.copy()
    # Only flip held-out outcomes; full-data final selection legitimately sees those later.
    changed.loc[first.predictions.row_index, "target"] = (
        1 - changed.loc[first.predictions.row_index, "target"]
    )
    second = run_experiment(replace(config, output_dir=tmp_path / "flipped"), changed)
    pd.testing.assert_frame_equal(
        first.selection_trace.query("outer_fold > 0"),
        second.selection_trace.query("outer_fold > 0"),
    )
    assert first.metrics["accuracy"] == 1.0
    assert second.metrics["accuracy"] == 0.0
