"""FR-009: concise, evidence-based result interpretation."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd
import pytest

from psyml import ExperimentConfig, run_experiment
from psyml.reporting.interpretation import (
    build_interpretation,
    metric_direction,
)


def _config(tmp_path, **overrides):
    values = {
        "task": "classification",
        "target_column": "target",
        "model_name": "decision_tree",
        "model_names": ["decision_tree", "dummy"],
        "input_path": tmp_path / "data.csv",
        "output_dir": tmp_path / "run",
        "validation_strategy": "stratified_k_fold",
        "validation_strategies": ["stratified_k_fold"],
        "selection_metric": "balanced_accuracy",
        "n_splits": 3,
        "inner_splits": 2,
    }
    values.update(overrides)
    return ExperimentConfig(**values)


def _procedure_folds(metric="balanced_accuracy", values=(0.9, 0.8, 0.7), validation="stratified_k_fold"):
    return pd.DataFrame(
        {
            "fold": [1, 2, 3][: len(values)],
            "model": ["decision_tree"] * len(values),
            "validation": [validation] * len(values),
            metric: list(values),
        }
    )


def _dummy_folds(metric="balanced_accuracy", values=(0.5, 0.5, 0.5), validation="stratified_k_fold"):
    return [
        {
            "fold": fold,
            "model": "dummy",
            "validation": validation,
            metric: value,
        }
        for fold, value in zip([1, 2, 3][: len(values)], values)
    ]


def _validation_summary(status="completed", n_folds=3, error="", validation="stratified_k_fold"):
    return pd.DataFrame(
        [
            {
                "validation": validation,
                "role": "primary",
                "status": status,
                "error": error,
                "n_folds": n_folds,
            }
        ]
    )


def _leaderboard(dummy_status="completed", validation="stratified_k_fold"):
    return pd.DataFrame(
        [
            {
                "rank": 1,
                "model": "decision_tree",
                "validation": validation,
                "selection_metric": "balanced_accuracy",
                "selection_score": 0.8,
                "status": "completed",
                "error": "",
            },
            {
                "rank": 2,
                "model": "dummy",
                "validation": validation,
                "selection_metric": "balanced_accuracy",
                "selection_score": 0.5,
                "status": dummy_status,
                "error": "" if dummy_status == "completed" else "dummy failed",
            },
        ]
    )


def _build(tmp_path, **overrides):
    metric = overrides.pop("metric", "balanced_accuracy")
    validation = overrides.pop("validation", "stratified_k_fold")
    procedure_folds = overrides.pop("procedure_folds", _procedure_folds(metric))
    dummy_folds = overrides.pop("dummy_folds", _dummy_folds(metric))
    leaderboard = overrides.pop("leaderboard", _leaderboard())
    validation_summary = overrides.pop("validation_summary", _validation_summary())
    config = overrides.pop("config", _config(tmp_path))
    procedure_results = overrides.pop(
        "procedure_results",
        {validation: ({}, procedure_folds, pd.DataFrame())},
    ) or {}
    combo_folds = {(validation, "dummy"): dummy_folds}
    return build_interpretation(
        config=config,
        procedure_results=procedure_results,
        combo_folds=combo_folds,
        tuning_rows=overrides.pop("tuning_rows", []),
        leaderboard=leaderboard,
        validation_summary=validation_summary,
    )


def test_metric_direction_known_and_unknown():
    assert metric_direction("balanced_accuracy") == "higher_is_better"
    assert metric_direction("r2") == "higher_is_better"
    assert metric_direction("rmse") == "lower_is_better"
    assert metric_direction("mae") == "lower_is_better"
    assert metric_direction("mystery") is None


def test_comparable_higher_is_better_mean_difference_is_procedure_minus_baseline(tmp_path):
    interpretation = _build(tmp_path)
    comparison = interpretation["validations"]["stratified_k_fold"]["baseline_comparison"]
    assert comparison["status"] == "comparable"
    assert comparison["positive_means"] == "procedure_better_than_baseline"
    assert comparison["n_paired_folds"] == 3
    assert math.isclose(comparison["mean_difference"], (0.4 + 0.3 + 0.2) / 3)
    assert comparison["per_fold"][0]["difference"] == pytest.approx(0.4)


def test_lower_is_better_metric_flips_the_sign(tmp_path):
    procedure = _procedure_folds("rmse", (1.0, 1.0, 1.0), validation="k_fold")
    dummy = _dummy_folds("rmse", (2.0, 2.0, 2.0), validation="k_fold")
    interpretation = _build(
        tmp_path,
        metric="rmse",
        validation="k_fold",
        procedure_folds=procedure,
        dummy_folds=dummy,
        leaderboard=_leaderboard(validation="k_fold"),
        validation_summary=_validation_summary(validation="k_fold"),
        config=_config(
            tmp_path,
            selection_metric="rmse",
            task="regression",
            validation_strategy="k_fold",
            validation_strategies=["k_fold"],
        ),
    )
    comparison = interpretation["validations"]["k_fold"]["baseline_comparison"]
    assert comparison["direction"] == "lower_is_better"
    # Baseline has higher error, so the procedure is better and the value is positive.
    assert comparison["mean_difference"] == pytest.approx(1.0)


def test_baseline_not_selected_reports_clear_reason(tmp_path):
    config = _config(tmp_path, model_names=["decision_tree"], model_name="decision_tree")
    interpretation = _build(tmp_path, config=config)
    comparison = interpretation["validations"]["stratified_k_fold"]["baseline_comparison"]
    assert comparison["status"] == "not_comparable"
    assert comparison["reason"] == "baseline_not_selected"
    assert comparison["mean_difference"] is None


def test_failed_baseline_is_not_fabricated(tmp_path):
    interpretation = _build(tmp_path, leaderboard=_leaderboard(dummy_status="failed"))
    comparison = interpretation["validations"]["stratified_k_fold"]["baseline_comparison"]
    assert comparison["status"] == "not_comparable"
    assert comparison["reason"] == "baseline_not_run_or_failed"
    assert comparison["mean_difference"] is None


def test_different_fold_sets_are_not_comparable(tmp_path):
    interpretation = _build(
        tmp_path,
        dummy_folds=[
            {"fold": 1, "model": "dummy", "validation": "stratified_k_fold", "balanced_accuracy": 0.5},
            {"fold": 2, "model": "dummy", "validation": "stratified_k_fold", "balanced_accuracy": 0.5},
        ],
    )
    comparison = interpretation["validations"]["stratified_k_fold"]["baseline_comparison"]
    assert comparison["status"] == "not_comparable"
    assert comparison["reason"] == "fold_sets_differ"
    assert comparison["fold_count_match"] is False


def test_non_finite_matched_score_blocks_comparison(tmp_path):
    interpretation = _build(
        tmp_path,
        procedure_folds=pd.DataFrame(
            {
                "fold": [1, 2, 3],
                "model": ["decision_tree"] * 3,
                "validation": ["stratified_k_fold"] * 3,
                "balanced_accuracy": [0.9, float("nan"), 0.7],
            }
        ),
    )
    comparison = interpretation["validations"]["stratified_k_fold"]["baseline_comparison"]
    assert comparison["status"] == "not_comparable"
    assert comparison["reason"] == "non_finite_matched_scores"
    assert comparison["mean_difference"] is None


def test_procedure_selecting_dummy_gives_zero_difference_with_label(tmp_path):
    procedure = _procedure_folds(values=(0.5, 0.9, 0.7))
    procedure.loc[0, "model"] = "dummy"
    interpretation = _build(tmp_path, procedure_folds=procedure)
    comparison = interpretation["validations"]["stratified_k_fold"]["baseline_comparison"]
    first = comparison["per_fold"][0]
    assert first["procedure_selected_baseline"] is True
    assert first["procedure_model"] == "dummy"
    assert first["difference"] == 0.0


def test_single_fold_reports_no_std_and_stability_not_assessable(tmp_path):
    interpretation = _build(
        tmp_path,
        procedure_folds=_procedure_folds(values=(0.9,)),
        dummy_folds=_dummy_folds(values=(0.5,)),
        validation_summary=_validation_summary(n_folds=1),
    )
    summaries = interpretation["validations"]["stratified_k_fold"]["metric_summaries"]
    assert summaries["balanced_accuracy"]["n_folds"] == 1
    assert summaries["balanced_accuracy"]["std"] is None
    assert summaries["balanced_accuracy"]["stability"] == "not_assessable"


def test_failure_counts_are_separated_by_level(tmp_path):
    tuning_rows = [
        {
            "validation": "stratified_k_fold",
            "outer_fold": 1,
            "selection_scope": "outer_training_fold",
            "model": "decision_tree",
            "candidate": 2,
            "status": "failed",
            "error": "ValueError: bad candidate",
        }
    ]
    leaderboard = pd.concat(
        [
            _leaderboard(),
            pd.DataFrame(
                [
                    {
                        "rank": None,
                        "model": "random_forest",
                        "validation": "stratified_k_fold",
                        "selection_metric": "balanced_accuracy",
                        "selection_score": math.nan,
                        "status": "failed",
                        "error": "outer failure",
                    }
                ]
            ),
        ],
        ignore_index=True,
    )
    interpretation = _build(
        tmp_path,
        tuning_rows=tuning_rows,
        leaderboard=leaderboard,
        validation_summary=_validation_summary(status="failed", n_folds=0, error="procedure failed"),
    )
    failures = interpretation["validations"]["stratified_k_fold"]["failures"]
    assert failures["inner_candidate"]["count"] == 1
    assert failures["outer_model_validation"]["count"] == 1
    assert failures["validation_procedure"]["count"] == 1
    # Every level points at the full file that records its failures.
    assert failures["inner_candidate"]["evidence"] == "parameter_search.csv"
    assert failures["outer_model_validation"]["evidence"] == "model_comparison.csv"
    assert failures["validation_procedure"]["evidence"] == "validation_summary.csv"
    assert interpretation["failures"] == {
        "inner_candidate": 1,
        "outer_model_validation": 1,
        "validation_procedure": 1,
    }


def test_failed_procedure_has_no_metric_summaries_or_difference(tmp_path):
    interpretation = _build(
        tmp_path,
        procedure_results=None,
        validation_summary=_validation_summary(status="failed", n_folds=0, error="boom"),
    )
    entry = interpretation["validations"]["stratified_k_fold"]
    assert entry["status"] == "failed"
    assert entry["metric_summaries"] == {}
    assert entry["baseline_comparison"]["status"] == "not_comparable"
    assert entry["baseline_comparison"]["reason"] == "procedure_failed"


def test_runner_writes_interpretation_artifacts_and_matches_fold_values(tmp_path):
    frame = pd.DataFrame(
        {
            "signal": [-1.0, 1.0] * 24,
            "target": [0, 1] * 24,
        }
    )
    config = ExperimentConfig(
        task="classification",
        target_column="target",
        feature_columns=["signal"],
        model_name="decision_tree",
        model_names=["decision_tree", "dummy"],
        output_dir=tmp_path / "run",
        validation_strategy="stratified_k_fold",
        n_splits=3,
        inner_splits=2,
        random_seed=7,
    )
    result = run_experiment(config, frame)
    output_dir = config.output_dir
    assert result.interpretation
    payload = json.loads((output_dir / "result_interpretation.json").read_text())
    summary = json.loads((output_dir / "result.json").read_text())
    for artifact in summary["artifacts"].values():
        assert (output_dir / artifact).is_file()
    assert summary["artifacts"]["result_interpretation"] == "result_interpretation.json"

    entry = payload["validations"]["stratified_k_fold"]
    comparison = entry["baseline_comparison"]
    assert comparison["status"] == "comparable"
    # Recompute the difference from the raw fold evidence and compare.
    procedure = result.fold_metrics.set_index("fold")["balanced_accuracy"]
    expected = []
    for fold in comparison["per_fold"]:
        baseline = fold["baseline_value"]
        expected.append(fold["procedure_value"] - baseline)
    assert comparison["mean_difference"] == pytest.approx(sum(expected) / len(expected))
    assert procedure.index.tolist() == [fold["fold"] for fold in comparison["per_fold"]]
    assert (output_dir / "interpretation_baseline_differences.csv").is_file()
    assert (output_dir / "result_interpretation.md").is_file()
    # The interpretation must not add model fits or change the selected family.
    assert result.best_model_name == "decision_tree"


def test_partial_independent_root_interpretation_keeps_error_and_counts(tmp_path):
    """A failed peer validation must keep its error, count 1 whole-procedure
    failure and mark unknown inner/outer counts unavailable (not zero)."""
    root = Path(__file__).resolve().parents[1]
    config = ExperimentConfig(
        task="classification",
        target_column="target",
        model_name="decision_tree",
        model_names=["decision_tree", "dummy"],
        input_path=root / "examples/synthetic/classification.csv",
        output_dir=tmp_path / "partial",
        feature_columns=["score", "category"],
        group_column="participant",
        validation_strategies=["holdout", "group_k_fold"],
        primary_validation=None,
        n_splits=20,
        inner_splits=2,
    )
    result = run_experiment(config)
    assert set(result.validation_results) == {"holdout"}

    root_payload = json.loads((config.output_dir / "result.json").read_text())
    failed_entry = root_payload["validation_results"]["group_k_fold"]
    assert failed_entry["status"] == "failed"

    interpretation = json.loads(
        (config.output_dir / "result_interpretation.json").read_text()
    )
    failed = interpretation["validations"]["group_k_fold"]
    assert failed["status"] == "failed"
    assert failed["error"] == failed_entry["error"]
    assert failed["failures"]["validation_procedure"] == 1
    assert failed["failures"]["inner_candidate"] is None
    assert failed["failures"]["outer_model_validation"] is None
    assert failed["baseline_comparison"]["status"] == "not_comparable"
    assert failed["baseline_comparison"]["reason"] == "procedure_failed"
    assert failed["evidence"]["validation_procedure"] == "validation_summary.csv"
    assert failed["evidence"]["error"] == "validations/group_k_fold/error.json"
    # Evidence paths are real files, never invented.
    for path in failed["evidence"].values():
        assert (config.output_dir / path).is_file()

    # A successful child stays isolated with its own comparable evidence.
    finished = interpretation["validations"]["holdout"]
    assert finished["status"] == "completed"
    assert finished["failures"]["validation_procedure"] == 0
    assert finished["baseline_comparison"]["reason"] != "procedure_failed"
    assert finished["error"] is None
    for path in finished["evidence"].values():
        assert (config.output_dir / path).is_file()

    # Root aggregate: inner/outer unknown because a child is missing evidence.
    assert interpretation["failures"]["inner_candidate"] is None
    assert interpretation["failures"]["outer_model_validation"] is None
    assert interpretation["failures"]["validation_procedure"] == 1
