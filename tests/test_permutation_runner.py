"""Integration tests: permutation importance inside the nested runner.

These tests prove the runner hands the engine only the inner-selected outer-fold
pipeline and its held-out rows, that enabling the switch cannot change model
selection, and that interpretation failures/cancellation stay observable.
"""

import json

import numpy as np
import pandas as pd
import pytest
from sklearn.dummy import DummyClassifier
from sklearn.pipeline import Pipeline

from psyml import ExperimentConfig, run_experiment, runner
from psyml.evaluation.permutation import NonFiniteScoreError
from psyml.validation import make_validation_splits


def grouped_classification() -> pd.DataFrame:
    """12 participants x 4 rows with a deterministic signal and a raw category."""
    return pd.DataFrame(
        {
            "signal": [-1.0, 1.0] * 24,
            "category": ["x", "y"] * 24,
            "target": [0, 1] * 24,
            "group": np.repeat(np.arange(12), 4),
        }
    )


def grouped_regression() -> pd.DataFrame:
    signal = np.tile([-1.0, 1.0], 24)
    offset = np.repeat(np.linspace(-0.1, 0.1, 12), 4)
    return pd.DataFrame(
        {
            "signal": signal,
            "category": np.tile(["x", "y"], 24),
            "target": 2.0 * signal + offset,
            "group": np.repeat(np.arange(12), 4),
        }
    )


def config_at(path, **kwargs) -> ExperimentConfig:
    settings = {
        "task": "classification",
        "target_column": "target",
        "group_column": "group",
        "feature_columns": ["signal", "category"],
        "model_name": "decision_tree",
        "output_dir": path / "run",
        "validation_strategy": "group_k_fold",
        "n_splits": 3,
        "inner_splits": 2,
        "permutation_importance": True,
        "permutation_repeats": 2,
    }
    settings.update(kwargs)
    return ExperimentConfig(**settings)


def all_records(result) -> list[dict]:
    return [record for records in result.permutation_results.values() for record in records]


def _outer_expected_folds(config, frame):
    features, target, groups, _ = runner._prepare_data(config, frame)
    splits = make_validation_splits(
        features,
        target,
        config.task,
        config.validation_strategy,
        config.n_splits,
        config.test_size,
        config.random_seed,
        groups,
    )
    return features, {
        fold: set(features.index[test_index])
        for fold, (_, test_index) in enumerate(splits, start=1)
    }


@pytest.mark.parametrize("task", ["classification", "regression"])
def test_engine_receives_only_outer_test_rows_and_the_fold_pipeline(tmp_path, monkeypatch, task):
    frame = grouped_classification() if task == "classification" else grouped_regression()
    config = config_at(
        tmp_path,
        task=task,
        model_name="decision_tree" if task == "classification" else "linear_regression",
        model_names=["decision_tree", "dummy"] if task == "classification" else None,
    )
    calls = []
    real_engine = runner.permutation_importance

    def spy(model, features, target, **kwargs):
        calls.append(
            {
                "model": model,
                "index": list(features.index),
                "columns": list(features.columns),
                "target_index": list(target.index),
                "metric": kwargs["metric"],
                "seed": kwargs["seed"],
                "repeats": kwargs["repeats"],
                "context": kwargs["context"],
            }
        )
        return real_engine(model, features, target, **kwargs)

    monkeypatch.setattr(runner, "permutation_importance", spy)
    result = run_experiment(config, frame)

    features, expected = _outer_expected_folds(config, frame)
    assert calls, "the engine must be called once per completed outer fold"
    matched_folds = set()
    for call in calls:
        rows = set(call["index"])
        fold_matches = [fold for fold, held_out in expected.items() if held_out == rows]
        assert len(fold_matches) == 1, "each explanation must target exactly one outer fold"
        matched_folds.add(fold_matches[0])
        assert call["columns"] == ["signal", "category"]
        assert call["target_index"] == call["index"], "target rows must mirror feature rows"
        assert call["seed"] == config.random_seed
        assert call["repeats"] == config.permutation_repeats
        assert call["context"]["model_scope"] == "outer_fold_model"
        assert set(call["context"]["heldout_row_indices"]) == {int(row) for row in rows}
        assert "heldout_groups" in call["context"]
    assert matched_folds == set(expected)

    records = all_records(result)
    for call, record in zip(calls, records):
        fold_rows = result.predictions[result.predictions["fold"] == record["fold"]]
        expected_map = dict(zip(fold_rows["row_index"], fold_rows["predicted"]))
        predicted = call["model"].predict(features.loc[call["index"]])
        assert [expected_map[row] for row in call["index"]] == list(predicted)
        assert record["status"] == "completed"
    assert not any(isinstance(call["model"]["model"], DummyClassifier) for call in calls)


def test_multi_family_uses_inner_winner_even_when_outer_score_favours_another(tmp_path, monkeypatch):
    original = runner._fold_result

    def misleading(config, model, features, observed, predicted):
        values = original(config, model, features, observed, predicted)
        values["balanced_accuracy"] = float(isinstance(model["model"], DummyClassifier))
        return values

    monkeypatch.setattr(runner, "_fold_result", misleading)
    config = config_at(tmp_path, model_names=["decision_tree", "dummy"])
    result = run_experiment(config, grouped_classification())

    assert result.leaderboard.iloc[0]["model"] == "dummy"
    winners = dict(
        zip(result.selection_trace["outer_fold"], result.selection_trace["model"])
    )
    assert {record["model_family"] for record in all_records(result)} == {"decision_tree"}
    for record in all_records(result):
        assert record["model_family"] == winners[record["fold"]]
        assert record["fold"] in {1, 2, 3}


def test_inner_winner_outer_failure_is_not_substituted_by_another_family(tmp_path, monkeypatch):
    original = runner._fold_result

    def fail_selected(config, model, features, observed, predicted):
        if not isinstance(model["model"], DummyClassifier):
            raise ValueError("Injected outer evaluation failure")  # noqa: TRY004
        return original(config, model, features, observed, predicted)

    monkeypatch.setattr(runner, "_fold_result", fail_selected)
    config = config_at(tmp_path, model_names=["decision_tree", "dummy"])
    calls = []
    monkeypatch.setattr(
        runner,
        "permutation_importance",
        lambda *args, **kwargs: calls.append(args),
    )
    with pytest.raises(ValueError, match="Primary validation failed.*substitute"):
        run_experiment(config, grouped_classification())
    assert calls == []
    assert not (config.output_dir / "result.json").exists()


def test_disabled_switch_calls_no_helpers_and_adds_no_fit(tmp_path, monkeypatch):
    config = config_at(tmp_path, permutation_importance=False)
    engine_calls = {"n": 0}
    build_calls = {"n": 0}
    real_build = runner._build_pipeline

    def counting_build(*args, **kwargs):
        build_calls["n"] += 1
        return real_build(*args, **kwargs)

    def boom(*args, **kwargs):
        engine_calls["n"] += 1
        raise AssertionError("permutation helpers must not run when the switch is off")

    monkeypatch.setattr(runner, "_build_pipeline", counting_build)
    monkeypatch.setattr(runner, "permutation_importance", boom)
    monkeypatch.setattr(runner, "extract_feature_encoding", boom)

    result = run_experiment(config, grouped_classification())
    assert result.permutation_results == {}
    assert engine_calls["n"] == 0
    assert build_calls["n"] > 0


def test_enabled_switch_preserves_evaluation_selection_and_fit_count(tmp_path, monkeypatch):
    frame = grouped_classification()
    off_config = config_at(tmp_path / "off", permutation_importance=False)
    on_config = config_at(tmp_path / "on", permutation_importance=True)
    counts = {"off": 0, "on": 0}
    real_fit = Pipeline.fit

    def make_counter(label):
        def counter(self, *args, **kwargs):
            counts[label] += 1
            return real_fit(self, *args, **kwargs)

        return counter

    monkeypatch.setattr(Pipeline, "fit", make_counter("off"))
    off = run_experiment(off_config, frame)
    monkeypatch.setattr(Pipeline, "fit", make_counter("on"))
    on = run_experiment(on_config, frame)

    assert counts["off"] > 0
    assert counts["off"] == counts["on"]
    assert off.permutation_results == {}
    assert on.permutation_results
    assert off.metrics == on.metrics
    assert off.best_params == on.best_params
    assert off.best_model_name == on.best_model_name
    assert off.effective_params == on.effective_params
    assert off.validation_summary.equals(on.validation_summary)
    pd.testing.assert_frame_equal(off.predictions, on.predictions)
    pd.testing.assert_frame_equal(off.selection_trace, on.selection_trace)


def test_same_seed_reproduces_permutation_results(tmp_path):
    frame = grouped_classification()
    first = run_experiment(config_at(tmp_path / "first"), frame)
    second = run_experiment(config_at(tmp_path / "second"), frame)
    assert first.permutation_results == second.permutation_results


def test_independent_mode_isolates_results_per_validation(tmp_path):
    config = config_at(
        tmp_path,
        model_names=["decision_tree", "dummy"],
        validation_strategies=["holdout", "group_k_fold"],
        primary_validation=None,
    )
    result = run_experiment(config, grouped_classification())
    assert result.permutation_results == {}
    assert set(result.validation_results) == {"holdout", "group_k_fold"}
    for validation, child in result.validation_results.items():
        assert set(child.permutation_results) == {validation}
        for record in child.permutation_results[validation]:
            assert record["validation"] == validation
            assert record["model_family"] == child.best_model_name


def test_primary_plus_sensitivity_keeps_validations_isolated(tmp_path):
    config = config_at(
        tmp_path,
        model_names=["decision_tree", "dummy"],
        validation_strategies=["group_k_fold", "holdout"],
    )
    result = run_experiment(config, grouped_classification())
    assert set(result.permutation_results) == {"group_k_fold", "holdout"}
    for validation, records in result.permutation_results.items():
        assert records
        assert {record["validation"] for record in records} == {validation}


def test_interpretation_failure_is_recorded_without_zero_fill_or_pollution(tmp_path, monkeypatch):
    frame = grouped_classification()
    baseline = run_experiment(
        config_at(tmp_path / "baseline", permutation_importance=False), frame
    )

    def failing_engine(*args, **kwargs):
        raise NonFiniteScoreError("injected non-finite score")

    monkeypatch.setattr(runner, "permutation_importance", failing_engine)
    result = run_experiment(config_at(tmp_path / "failing"), frame)

    records = all_records(result)
    assert records
    assert all(record["status"] == "failed" for record in records)
    assert all(record["error_type"] == "NonFiniteScoreError" for record in records)
    assert all("variables" not in record for record in records)
    assert any("Permutation importance failed" in warning for warning in result.warnings)
    assert result.metrics == baseline.metrics
    pd.testing.assert_frame_equal(result.predictions, baseline.predictions)


def test_progress_reports_every_permutation_and_reaches_one(tmp_path):
    frame = grouped_classification()
    events = []
    config = config_at(tmp_path, model_names=["decision_tree", "dummy"])
    run_experiment(config, frame, progress_callback=events.append)

    permutation_events = [
        event for event in events if event.get("phase") == "permutation_importance"
    ]
    n_features = len(config.feature_columns)
    expected = config.n_splits * n_features * config.permutation_repeats
    assert len(permutation_events) == expected
    for event in permutation_events:
        assert event["current_validation"] == "group_k_fold"
        assert event["current_model"] in {"decision_tree", "dummy"}
        assert event["current_fold"] in {1, 2, 3}
        assert "variable" in event and "repeat" in event
    assert [event["progress"] for event in events] == sorted(
        event["progress"] for event in events
    )
    assert events[-1]["progress"] == 1.0
    assert events[-1]["remaining_tasks"] == 0
    assert events[-1]["completed_tasks"] == events[-1]["total_tasks"]

    off_events = []
    off_config = config_at(tmp_path / "off", model_names=["decision_tree", "dummy"],
                           permutation_importance=False)
    run_experiment(off_config, frame, progress_callback=off_events.append)
    assert not [e for e in off_events if e.get("phase") == "permutation_importance"]
    assert events[0]["total_tasks"] - off_events[0]["total_tasks"] == expected


def test_failed_sensitivity_is_skipped_without_fake_interpretation(tmp_path, monkeypatch):
    real_winner = runner._inner_winner

    def failing_sensitivity(rows, metric):
        if rows and rows[0]["validation"] == "holdout":
            raise ValueError("injected sensitivity selection failure")
        return real_winner(rows, metric)

    monkeypatch.setattr(runner, "_inner_winner", failing_sensitivity)
    events = []
    config = config_at(
        tmp_path,
        model_names=["decision_tree", "dummy"],
        validation_strategies=["group_k_fold", "holdout"],
    )
    result = run_experiment(config, grouped_classification(), progress_callback=events.append)

    assert set(result.permutation_results) == {"group_k_fold", "holdout"}
    assert result.permutation_results["holdout"] == []
    assert result.permutation_results["group_k_fold"]
    assert result.metrics
    assert any("Selection procedure failed for sensitivity validation holdout" in w
               for w in result.warnings)
    # The failed sensitivity still writes reproducible request context, with a
    # status that separates a failed selection procedure from a failed
    # interpretation, and no fabricated ranking files.
    holdout_dir = config.output_dir / "interpretations" / "holdout"
    assert (holdout_dir / "permutation.json").is_file()
    metadata = json.loads((holdout_dir / "permutation.json").read_text(encoding="utf-8"))
    assert metadata["status"] == "not_run"
    assert metadata["selection_procedure_status"] == "failed"
    assert metadata["metric"] == config.resolved_selection_metric()
    assert metadata["seed"] == config.random_seed
    assert metadata["repeats"] == config.permutation_repeats
    assert metadata["n_folds_planned"] >= 1
    assert metadata["n_folds_successful"] == 0
    assert metadata["variables"] == []
    assert not (holdout_dir / "permutation_summary.csv").exists()
    assert not (holdout_dir / "permutation_importance.png").exists()
    assert [event["progress"] for event in events] == sorted(
        event["progress"] for event in events
    )
    assert events[-1]["progress"] == 1.0


def test_callback_cancellation_propagates_in_prioritized_and_independent_modes(tmp_path):
    def canceller(event):
        if event.get("phase") == "permutation_importance":
            raise RuntimeError("cancelled")

    config = config_at(tmp_path / "prioritized", model_names=["decision_tree", "dummy"])
    with pytest.raises(runner._PermutationCallbackError, match="cancelled"):
        run_experiment(config, grouped_classification(), progress_callback=canceller)

    independent = config_at(
        tmp_path / "independent",
        model_names=["decision_tree", "dummy"],
        validation_strategies=["holdout", "group_k_fold"],
        primary_validation=None,
    )
    with pytest.raises(runner._PermutationCallbackError, match="cancelled"):
        run_experiment(independent, grouped_classification(), progress_callback=canceller)
