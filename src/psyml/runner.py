"""Reproducible, leakage-safe single-model and comparative study runner."""

from __future__ import annotations

import json
import math
import time
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import ParameterGrid, ParameterSampler
from sklearn.pipeline import Pipeline

from psyml.config import ExperimentConfig
from psyml.data.io import load_dataframe, validate_dataset
from psyml.evaluation.metrics import (
    classification_confusion_matrix,
    classification_metrics,
    regression_metrics,
)
from psyml.models.catalog import quick_parameter_grid, supported_models
from psyml.models.factory import build_model
from psyml.preprocessing.pipeline import build_preprocessor
from psyml.reporting.output import write_result_summary, write_results, write_study_outputs
from psyml.reporting.research import write_research_outputs
from psyml.validation.split import make_validation_splits

ProgressCallback = Callable[[dict[str, Any]], None]


@dataclass
class ExperimentResult:
    """In-memory evaluation result and final fitted model."""

    metrics: dict[str, float]
    predictions: pd.DataFrame
    model: Pipeline | None
    fold_metrics: pd.DataFrame
    metric_summary: pd.DataFrame
    warnings: list[str]
    confusion_matrix: pd.DataFrame | None = None
    leaderboard: pd.DataFrame = field(default_factory=pd.DataFrame)
    tuning_results: pd.DataFrame = field(default_factory=pd.DataFrame)
    best_model_name: str = ""
    best_validation_strategy: str = ""
    best_params: dict[str, Any] = field(default_factory=dict)
    selection_trace: pd.DataFrame = field(default_factory=pd.DataFrame)
    validation_summary: pd.DataFrame = field(default_factory=pd.DataFrame)
    validation_results: dict[str, ExperimentResult] = field(default_factory=dict)


@dataclass
class _WorkItem:
    validation: str
    model_name: str
    fold_number: int
    train_index: list[int]
    test_index: list[int]
    inner_splits: list[tuple[list[int], list[int]]]
    candidates: list[dict[str, Any]]


class _ProgressTracker:
    def __init__(self, total_tasks: int, callback: ProgressCallback | None) -> None:
        self.total_tasks = max(total_tasks, 1)
        self.completed_tasks = 0
        self.callback = callback
        self.started = time.monotonic()

    def announce(self) -> None:
        if self.callback is not None:
            self.callback(
                {
                    "progress": 0.0,
                    "completed_tasks": 0,
                    "total_tasks": self.total_tasks,
                    "remaining_tasks": self.total_tasks,
                    "elapsed_seconds": 0.0,
                    "estimated_remaining_seconds": None,
                    "phase": "planning",
                    "message": "Execution plan ready",
                    "current_model": "",
                    "current_validation": "",
                    "current_fold": 1,
                }
            )

    def advance(self, **details: Any) -> None:
        self.completed_tasks += 1
        elapsed = time.monotonic() - self.started
        remaining = max(self.total_tasks - self.completed_tasks, 0)
        eta = elapsed / self.completed_tasks * remaining if remaining else 0.0
        if self.callback is not None:
            self.callback(
                {
                    "progress": self.completed_tasks / self.total_tasks,
                    "completed_tasks": self.completed_tasks,
                    "total_tasks": self.total_tasks,
                    "remaining_tasks": remaining,
                    "elapsed_seconds": elapsed,
                    "estimated_remaining_seconds": eta,
                    **details,
                }
            )

    def skip(self, tasks: int) -> None:
        """Account for planned upper-bound work that the winning model did not need."""
        self.completed_tasks += max(tasks, 0)


def _build_pipeline(
    config: ExperimentConfig,
    training_features: pd.DataFrame,
    model_name: str,
    model_params: dict[str, Any],
    training_target: pd.Series | None = None,
    training_groups: pd.Series | None = None,
) -> Pipeline:
    if model_name == "stacking":
        return _build_stacking_pipeline(
            config, training_features, training_target, training_groups, model_params
        )
    return Pipeline(
        [
            (
                "preprocess",
                build_preprocessor(
                    training_features,
                    missing_strategy=config.missing_strategy,
                    scaling=config.scaling,
                ),
            ),
            ("model", build_model(config.task, model_name, config.random_seed, model_params)),
        ]
    )


def _build_stacking_pipeline(config, features, target, groups, params) -> Pipeline:
    """Cross-fit whole base pipelines, retaining group isolation at the stacking layer."""
    model = build_model(config.task, "stacking", config.random_seed, params)
    requested_cv = 5 if model.cv is None else model.cv
    if not isinstance(requested_cv, int) or requested_cv < 2:
        raise ValueError("Stacking cv must be an integer >= 2; prefit stacking is not supported")
    model.cv = _inner_splits(
        replace(config, inner_splits=requested_cv), features, target, groups, 0
    )
    if not model.cv:
        raise ValueError("Insufficient rows/classes/groups for stacking inner validation")
    if any(set(target.iloc[train].unique()) != set(target.unique()) for train, _ in model.cv):
        raise ValueError("Stacking inner training folds must contain all target classes")
    model.estimators = [
        (
            name,
            Pipeline(
                [
                    (
                        "preprocess",
                        build_preprocessor(features, config.missing_strategy, config.scaling),
                    ),
                    ("model", estimator),
                ]
            ),
        )
        for name, estimator in model.estimators
    ]
    if model.passthrough:
        # Stacking concatenates numeric out-of-fold predictions with the original columns.
        # Fit this meta-level preprocessor only when fitting the meta-estimator.
        n_classes = target.nunique()
        # predict emits one label column even for multiclass targets; auto uses
        # probabilities/decision scores from the built-in base estimators.
        outputs_per_estimator = 1 if model.stack_method == "predict" or n_classes == 2 else n_classes
        n_outputs = len(model.estimators) * outputs_per_estimator
        template = pd.concat(
            [
                pd.DataFrame(
                    0.0, index=features.index, columns=[f"__stack_{i}" for i in range(n_outputs)]
                ),
                features,
            ],
            axis=1,
        )
        template.columns = [f"column_{i}" for i in range(len(template.columns))]
        preprocessor = build_preprocessor(template, config.missing_strategy, config.scaling)
        preprocessor.transformers = [
            (name, transform, [template.columns.get_loc(c) for c in columns])
            for name, transform, columns in preprocessor.transformers
        ]
        model.final_estimator = Pipeline(
            [("preprocess", preprocessor), ("model", model.final_estimator)]
        )
    return Pipeline([("model", model)])


def _risk_warnings(
    config: ExperimentConfig, target: pd.Series, groups: pd.Series | None, dropped_rows: int
) -> list[str]:
    warnings = []
    if dropped_rows:
        warnings.append(f"Dropped {dropped_rows} rows because missing_strategy='drop'.")
    if groups is not None and any(
        strategy in {"k_fold", "stratified_k_fold"} for strategy in config.selected_validations()
    ):
        if len(config.selected_validations()) == 1:
            warnings.append(
                "A group column was supplied but the selected validation strategy does not "
                "isolate groups."
            )
        else:
            warnings.append(
                "A group column was supplied but at least one selected validation strategy does "
                "not isolate groups."
            )
    if config.task == "classification":
        counts = target.value_counts()
        if counts.max() >= 4 * counts.min():
            warnings.append(
                "The target classes are imbalanced; inspect balanced and macro metrics."
            )
        if "stratified_k_fold" in config.selected_validations() and counts.min() < config.n_splits:
            raise ValueError("Each class needs at least n_splits rows for stratified_k_fold")
    return warnings


def _prepare_data(
    config: ExperimentConfig, frame: pd.DataFrame
) -> tuple[pd.DataFrame, pd.Series, pd.Series | None, int]:
    validate_dataset(frame, config.target_column, config.group_column)
    columns = config.feature_columns
    if columns is None:
        columns = [c for c in frame.columns if c not in {config.target_column, config.group_column}]
    required = [*columns, config.target_column]
    if config.group_column:
        required.append(config.group_column)
    working = frame.loc[:, required].dropna(subset=[config.target_column]).copy()
    before_missing_drop = len(working)
    if config.missing_strategy == "drop":
        working = working.dropna()
    dropped_rows = before_missing_drop - len(working)
    if working.empty:
        raise ValueError("No rows remain after missing-data handling")
    if config.group_column and working[config.group_column].isna().any():
        raise ValueError("Missing group identifiers: resolve group membership before analysis")
    target = working.pop(config.target_column)
    groups = working.pop(config.group_column) if config.group_column else None
    if config.feature_columns is not None:
        missing_features = set(config.feature_columns) - set(working.columns)
        if missing_features:
            missing = ", ".join(sorted(missing_features))
            raise KeyError(f"Feature columns were not found: {missing}")
        working = working.loc[:, config.feature_columns]
    if working.empty:
        raise ValueError("No feature columns remain after selecting target and group columns")
    if config.task == "classification" and target.nunique() < 2:
        raise ValueError("Classification requires at least two target classes")
    return working, target, groups, dropped_rows


def _parameter_candidates(config: ExperimentConfig, model_name: str) -> list[dict[str, Any]]:
    base = dict(config.model_params) if len(config.selected_models()) == 1 else {}
    if config.tuning_mode == "none":
        return [base]
    grid = (
        quick_parameter_grid(config.task, model_name)
        if config.tuning_mode == "quick"
        else config.parameter_grids.get(model_name, {})
    )
    if not grid:
        return [base]
    allowed = set(build_model(config.task, model_name, config.random_seed, {}).get_params())
    unknown = set(grid) - allowed
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ValueError(f"Unknown parameters for {model_name}: {names}")
    parameter_grid = ParameterGrid(grid)
    if len(parameter_grid) > config.max_candidates:
        combinations = list(
            ParameterSampler(
                grid,
                n_iter=config.max_candidates,
                random_state=config.random_seed,
            )
        )
    else:
        combinations = list(parameter_grid)
    return [{**base, **candidate} for candidate in combinations]


def _inner_splits(
    config: ExperimentConfig,
    features: pd.DataFrame,
    target: pd.Series,
    groups: pd.Series | None,
    fold_number: int,
) -> list[tuple[list[int], list[int]]]:
    if groups is not None:
        n_splits = min(config.inner_splits, int(groups.nunique()))
        strategy = "stratified_group_k_fold" if config.task == "classification" else "group_k_fold"
    elif config.task == "classification":
        n_splits = min(config.inner_splits, int(target.value_counts().min()))
        strategy = "stratified_k_fold"
    else:
        n_splits = min(config.inner_splits, len(features))
        strategy = "k_fold"
    if n_splits < 2:
        return []
    return make_validation_splits(
        features,
        target,
        config.task,
        strategy,
        n_splits,
        config.test_size,
        config.random_seed + fold_number,
        groups,
    )


def _selection_score(metric: str, observed: pd.Series, predicted: Any) -> float:
    if metric == "balanced_accuracy":
        return float(balanced_accuracy_score(observed, predicted))
    if metric == "f1_macro":
        return float(f1_score(observed, predicted, average="macro", zero_division=0))
    if metric == "accuracy":
        return float(accuracy_score(observed, predicted))
    if metric == "r2":
        return float(r2_score(observed, predicted))
    if metric == "mae":
        return float(mean_absolute_error(observed, predicted))
    return float(math.sqrt(mean_squared_error(observed, predicted)))


def _objective(metric: str, score: float) -> float:
    return -score if metric in {"rmse", "mae"} else score


def _fold_result(
    config: ExperimentConfig,
    model: Pipeline,
    features: pd.DataFrame,
    observed: pd.Series,
    predicted: Any,
) -> dict[str, float]:
    if config.task == "classification":
        return classification_metrics(model, features, observed, predicted)
    return regression_metrics(observed, predicted)


def _summaries(fold_metrics: pd.DataFrame) -> tuple[dict[str, float], pd.DataFrame]:
    excluded = {"fold", "model", "validation"}
    metric_columns = [column for column in fold_metrics.columns if column not in excluded]
    metrics = {
        column: float(fold_metrics[column].mean())
        for column in metric_columns
        if not fold_metrics[column].isna().all()
    }
    summary = pd.DataFrame(
        [
            {
                "metric": column,
                "mean": float(fold_metrics[column].mean()),
                "std": float(fold_metrics[column].std(ddof=0)),
                "min": float(fold_metrics[column].min()),
                "max": float(fold_metrics[column].max()),
                "n_folds": int(fold_metrics[column].count()),
            }
            for column in metric_columns
            if not fold_metrics[column].isna().all()
        ]
    )
    return metrics, summary


def _make_work_items(
    config: ExperimentConfig,
    features: pd.DataFrame,
    target: pd.Series,
    groups: pd.Series | None,
) -> tuple[list[_WorkItem], int]:
    work_items: list[_WorkItem] = []
    total_tasks = 1
    family_search = len(config.selected_models()) > 1
    needs_search = family_search or any(
        len(_parameter_candidates(config, name)) > 1 for name in config.selected_models()
    )
    final_inner = _inner_splits(config, features, target, groups, 0) if needs_search else []
    final_tuning_budget = 0
    for validation in config.selected_validations():
        outer_splits = make_validation_splits(
            features,
            target,
            config.task,
            validation,
            config.n_splits,
            config.test_size,
            config.random_seed,
            groups,
        )
        for model_name in config.selected_models():
            if model_name not in supported_models(config.task):
                raise ValueError(f"Unsupported {config.task} model: {model_name}")
            candidates = _parameter_candidates(config, model_name)
            if validation == config.selected_validations()[0] and (
                family_search or len(candidates) > 1
            ):
                final_tuning_budget += len(candidates) * len(final_inner)
            for fold_number, (train_index, test_index) in enumerate(outer_splits, start=1):
                train_groups = groups.iloc[train_index] if groups is not None else None
                inner = (
                    _inner_splits(
                        config,
                        features.iloc[train_index],
                        target.iloc[train_index],
                        train_groups,
                        fold_number,
                    )
                    if family_search or len(candidates) > 1
                    else []
                )
                work_items.append(
                    _WorkItem(
                        validation=validation,
                        model_name=model_name,
                        fold_number=fold_number,
                        train_index=train_index,
                        test_index=test_index,
                        inner_splits=inner,
                        candidates=candidates,
                    )
                )
                total_tasks += 1 + len(candidates) * len(inner)
    return work_items, total_tasks + final_tuning_budget


def _choose_parameters(
    config: ExperimentConfig,
    work: _WorkItem,
    train_x: pd.DataFrame,
    train_y: pd.Series,
    tracker: _ProgressTracker,
    tuning_rows: list[dict[str, Any]],
    train_groups: pd.Series | None = None,
) -> dict[str, Any]:
    metric = config.resolved_selection_metric()
    if len(work.candidates) == 1 and len(config.selected_models()) == 1:
        return work.candidates[0]
    if not work.inner_splits:
        raise ValueError("Insufficient rows/classes/groups for inner parameter selection")
    best_params: dict[str, Any] | None = None
    best_objective = -math.inf
    for candidate_index, candidate in enumerate(work.candidates, start=1):
        scores: list[float] = []
        error_text = ""
        for inner_fold, (inner_train, inner_test) in enumerate(work.inner_splits, start=1):
            try:
                model = _build_pipeline(
                    config,
                    train_x.iloc[inner_train],
                    work.model_name,
                    candidate,
                    train_y.iloc[inner_train],
                    train_groups.iloc[inner_train] if train_groups is not None else None,
                )
                model.fit(train_x.iloc[inner_train], train_y.iloc[inner_train])
                predicted = model.predict(train_x.iloc[inner_test])
                score = _selection_score(metric, train_y.iloc[inner_test], predicted)
                if not math.isfinite(score):
                    raise ValueError(f"Non-finite inner selection metric: {metric}")
                scores.append(score)
            except Exception as error:  # noqa: BLE001
                error_text = f"{type(error).__name__}: {error}"
            tracker.advance(
                phase="tuning",
                message=f"Candidate {candidate_index}/{len(work.candidates)}, inner fold {inner_fold}",
                current_model=work.model_name,
                current_validation=work.validation,
                current_fold=max(work.fold_number, 1),
            )
        score = float(pd.Series(scores).mean()) if scores and not error_text else math.nan
        tuning_rows.append(
            {
                "model": work.model_name,
                "validation": work.validation,
                "outer_fold": work.fold_number,
                "selection_scope": (
                    "final_full_data" if work.fold_number == 0 else "outer_training_fold"
                ),
                "candidate": candidate_index,
                "selection_metric": metric,
                "score": score,
                "parameters": json.dumps(candidate, ensure_ascii=False, sort_keys=True),
                "status": "failed" if error_text else "completed",
                "error": error_text,
            }
        )
        if not math.isnan(score) and _objective(metric, score) > best_objective:
            best_objective = _objective(metric, score)
            best_params = candidate
    if best_params is None:
        raise ValueError(
            f"All parameter candidates failed for {work.model_name} in {work.validation} "
            f"outer fold {work.fold_number}. Cause / 具体原因: {error_text}"
        )
    return best_params


def _inner_winner(rows: list[dict[str, Any]], metric: str) -> dict[str, Any]:
    """Choose using training-only evidence; stable ties preserve candidate order."""
    eligible = [row for row in rows if row["status"] == "completed" and math.isfinite(row["score"])]
    if not eligible:
        raise ValueError("All model/parameter candidates failed during inner selection")
    return max(eligible, key=lambda row: _objective(metric, row["score"]))


def _selection_record(winner: dict[str, Any]) -> dict[str, Any]:
    return {
        key: winner[key]
        for key in ["validation", "outer_fold", "selection_scope", "model", "parameters", "score"]
    }


def run_experiment(
    config: ExperimentConfig,
    frame: pd.DataFrame | None = None,
    progress_callback: ProgressCallback | None = None,
) -> ExperimentResult:
    """Run one or more models and validations with optional nested parameter search."""
    if frame is not None and config.input_path is not None:
        raise ValueError(
            "Supply either frame or input_path, not both; source provenance must be unambiguous"
        )
    if config.resolved_primary_validation() is None:
        return _run_independent_validations(config, frame, progress_callback)
    return _run_prioritized(config, frame, progress_callback)


def _run_prioritized(
    config: ExperimentConfig,
    frame: pd.DataFrame | None,
    progress_callback: ProgressCallback | None,
) -> ExperimentResult:
    """Execute the existing nested procedure; internal callers may supply a file snapshot."""
    output_dir = Path(config.output_dir)
    if output_dir.exists() and (not output_dir.is_dir() or any(output_dir.iterdir())):
        raise FileExistsError("Output directory must be new or empty; existing output is preserved")
    output_dir.mkdir(parents=True, exist_ok=True)
    if frame is None:
        if config.input_path is None:
            raise ValueError("input_path is required when frame is not supplied")
        frame = load_dataframe(config.input_path)
    source_frame = frame
    features, target, groups, dropped_rows = _prepare_data(config, frame)
    warnings = _risk_warnings(config, target, groups, dropped_rows)
    missing_targets = int(frame[config.target_column].isna().sum())
    if missing_targets:
        warnings.append(f"Dropped {missing_targets} rows with missing target values.")
    if len(config.selected_models()) > 1:
        warnings.append(
            "Primary metrics evaluate the nested model-family and parameter selection procedure, "
            "not the final full-data model. Family leaderboard ranks are exploratory; choosing "
            "from their outer scores introduces selection bias. External validity requires "
            "appropriate independent data."
        )
    work_items, total_tasks = _make_work_items(config, features, target, groups)
    tracker = _ProgressTracker(total_tasks, progress_callback)
    tracker.announce()
    tuning_rows: list[dict[str, Any]] = []
    combo_folds: dict[tuple[str, str], list[dict[str, Any]]] = {}
    combo_predictions: dict[tuple[str, str], list[pd.DataFrame]] = {}
    combo_errors: dict[tuple[str, str], list[str]] = {}
    outer_results: dict[tuple[str, int, str], tuple[dict, pd.DataFrame]] = {}

    for work in work_items:
        key = (work.validation, work.model_name)
        train_x = features.iloc[work.train_index]
        test_x = features.iloc[work.test_index]
        train_y = target.iloc[work.train_index]
        test_y = target.iloc[work.test_index]
        try:
            selected_params = _choose_parameters(
                config,
                work,
                train_x,
                train_y,
                tracker,
                tuning_rows,
                groups.iloc[work.train_index] if groups is not None else None,
            )
            model = _build_pipeline(
                config,
                train_x,
                work.model_name,
                selected_params,
                train_y,
                groups.iloc[work.train_index] if groups is not None else None,
            )
            model.fit(train_x, train_y)
            predicted = model.predict(test_x)
            metrics = _fold_result(config, model, test_x, test_y, predicted)
            selection_value = metrics.get(config.resolved_selection_metric(), math.nan)
            if not math.isfinite(selection_value):
                raise ValueError(
                    "Non-finite outer selection metric; this combination cannot be ranked"
                )
            if config.task == "classification" and (
                set(train_y.unique()) != set(target.unique())
                or set(test_y.unique()) != set(target.unique())
            ):
                warnings.append(
                    f"{work.validation}/{work.model_name}/fold {work.fold_number}: missing classes "
                    "in training or evaluation; macro/balanced metrics use the labels present, "
                    "and AUC is omitted when class sets differ."
                )
            if any(not math.isfinite(value) for value in metrics.values()):
                warnings.append(
                    f"{work.validation}/{work.model_name}/fold {work.fold_number}: undefined "
                    "secondary metrics are omitted from means; inspect n_folds."
                )
            combo_folds.setdefault(key, []).append(
                {
                    "fold": work.fold_number,
                    "model": work.model_name,
                    "validation": work.validation,
                    **metrics,
                }
            )
            combo_predictions.setdefault(key, []).append(
                pd.DataFrame(
                    {
                        "row_index": test_y.index,
                        "fold": work.fold_number,
                        "observed": test_y.to_numpy(),
                        "predicted": predicted,
                    }
                )
            )
            outer_results[(work.validation, work.fold_number, work.model_name)] = (
                combo_folds[key][-1],
                combo_predictions[key][-1],
            )
        except Exception as error:  # noqa: BLE001
            combo_errors.setdefault(key, []).append(f"{type(error).__name__}: {error}")
        tracker.advance(
            phase="evaluating",
            message="Outer evaluation fold completed",
            current_model=work.model_name,
            current_validation=work.validation,
            current_fold=work.fold_number,
        )

    leaderboard_rows: list[dict[str, Any]] = []
    combo_results: dict[tuple[str, str], tuple[dict[str, float], pd.DataFrame, pd.DataFrame]] = {}
    for validation in config.selected_validations():
        for model_name in config.selected_models():
            key = (validation, model_name)
            fold_rows = combo_folds.get(key, [])
            if not fold_rows or key in combo_errors:
                leaderboard_rows.append(
                    {
                        "rank": None,
                        "model": model_name,
                        "validation": validation,
                        "selection_metric": config.resolved_selection_metric(),
                        "selection_score": math.nan,
                        "status": "failed",
                        "error": " | ".join(combo_errors.get(key, ["No completed folds"])),
                    }
                )
                continue
            fold_frame = pd.DataFrame(fold_rows)
            metrics, _ = _summaries(fold_frame)
            predictions = pd.concat(combo_predictions[key], ignore_index=True)
            selection_score = metrics[config.resolved_selection_metric()]
            leaderboard_rows.append(
                {
                    "rank": None,
                    "model": model_name,
                    "validation": validation,
                    "selection_metric": config.resolved_selection_metric(),
                    "selection_score": selection_score,
                    "status": "completed",
                    "error": "",
                    **metrics,
                }
            )
            combo_results[key] = (metrics, fold_frame, predictions)

    for row in leaderboard_rows:
        if row["status"] == "failed":
            warnings.append(
                f"Failed combination {row['validation']}/{row['model']}: {row['error']}"
            )
    completed_rows = [row for row in leaderboard_rows if row["status"] == "completed"]
    if not completed_rows and len(config.selected_models()) == 1:
        details = " | ".join(row["error"] for row in leaderboard_rows)
        raise ValueError(f"Every selected model/validation run failed: {details}")
    metric = config.resolved_selection_metric()
    ranked_rows: list[dict[str, Any]] = []
    for validation in config.selected_validations():
        validation_rows = [row for row in completed_rows if row["validation"] == validation]
        validation_rows.sort(
            key=lambda row: _objective(metric, row["selection_score"]), reverse=True
        )
        for rank, row in enumerate(validation_rows, start=1):
            row["rank"] = rank
        ranked_rows.extend(validation_rows)
    leaderboard_rows = ranked_rows + [
        row for row in leaderboard_rows if row["status"] != "completed"
    ]
    leaderboard = pd.DataFrame(leaderboard_rows)
    primary_validation = config.resolved_primary_validation()
    family_search = len(config.selected_models()) > 1
    selection_rows: list[dict[str, Any]] = []
    validation_rows: list[dict[str, Any]] = []
    procedure_results = {}
    for validation in config.selected_validations():
        selected_folds, selected_predictions = [], []
        try:
            if family_search:
                fold_numbers = sorted(
                    {w.fold_number for w in work_items if w.validation == validation}
                )
                for fold_number in fold_numbers:
                    winner = _inner_winner(
                        [
                            r
                            for r in tuning_rows
                            if r["validation"] == validation and r["outer_fold"] == fold_number
                        ],
                        metric,
                    )
                    selection_rows.append(_selection_record(winner))
                    selected_key = (validation, fold_number, winner["model"])
                    if selected_key not in outer_results:
                        raise ValueError(
                            f"Inner-selected model {winner['model']} failed in outer fold {fold_number}; "
                            "outer scores cannot be used to substitute another family"
                        )
                    fold_row, fold_predictions = outer_results[selected_key]
                    selected_folds.append(fold_row)
                    selected_predictions.append(fold_predictions.assign(model=winner["model"]))
                validation_folds = pd.DataFrame(selected_folds)
                validation_predictions = pd.concat(selected_predictions, ignore_index=True)
                validation_metrics, _ = _summaries(validation_folds)
            else:
                key = (validation, config.selected_models()[0])
                if key not in combo_results:
                    raise ValueError("The prespecified model did not complete all outer folds")
                validation_metrics, validation_folds, validation_predictions = combo_results[key]
            procedure_results[validation] = (
                validation_metrics,
                validation_folds,
                validation_predictions,
            )
            validation_rows.append(
                {
                    "validation": validation,
                    "role": "primary" if validation == primary_validation else "sensitivity",
                    "status": "completed",
                    "error": "",
                    "n_folds": len(validation_folds),
                    **validation_metrics,
                }
            )
        except ValueError as error:
            if validation == primary_validation:
                raise ValueError(f"Primary validation failed ({validation}): {error}") from error
            warnings.append(
                f"Selection procedure failed for sensitivity validation {validation}: {error}"
            )
            validation_rows.append(
                {
                    "validation": validation,
                    "role": "sensitivity",
                    "status": "failed",
                    "error": str(error),
                    "n_folds": 0,
                }
            )
    metrics, fold_metrics, predictions = procedure_results[primary_validation]
    _, metric_summary = _summaries(fold_metrics)

    # Final family/parameters are selected afresh using only full-data inner CV.
    # Neither outer leaderboard ranks nor sensitivity results enter this decision.
    needs_search = family_search or any(
        len(_parameter_candidates(config, name)) > 1 for name in config.selected_models()
    )
    final_inner = _inner_splits(config, features, target, groups, 0) if needs_search else []
    final_parameters = {}
    for model_name in config.selected_models():
        final_work = _WorkItem(
            validation=primary_validation,
            model_name=model_name,
            fold_number=0,
            train_index=list(range(len(features))),
            test_index=[],
            inner_splits=final_inner,
            candidates=_parameter_candidates(config, model_name),
        )
        try:
            final_parameters[model_name] = _choose_parameters(
                config, final_work, features, target, tracker, tuning_rows, groups
            )
        except ValueError as error:
            if not family_search:
                raise
            warnings.append(f"Final inner selection failed for {model_name}: {error}")
    if family_search:
        winner = _inner_winner([r for r in tuning_rows if r["outer_fold"] == 0], metric)
        selection_rows.append(_selection_record(winner))
        best = {"model": winner["model"], "validation": primary_validation}
    else:
        best = {"model": config.selected_models()[0], "validation": primary_validation}
    best_params = final_parameters[best["model"]]
    selection_trace = pd.DataFrame(
        selection_rows,
        columns=[
            "validation",
            "outer_fold",
            "selection_scope",
            "model",
            "parameters",
            "score",
        ],
    )
    validation_summary = pd.DataFrame(validation_rows)
    final_model = _build_pipeline(config, features, best["model"], best_params, target, groups)
    final_model.fit(features, target)
    tracker.advance(
        phase="finalizing",
        message="Best model fitted on all analyzed rows",
        current_model=best["model"],
        current_validation=best["validation"],
        current_fold=1,
    )
    confusion = None
    if config.task == "classification":
        confusion = classification_confusion_matrix(
            predictions["observed"], predictions["predicted"]
        )

    executed_config = replace(
        config,
        model_name=best["model"],
        validation_strategy=best["validation"],
        model_params=best_params,
    )
    output_dir = Path(config.output_dir)
    write_results(
        output_dir,
        config,
        metrics,
        predictions,
        fold_metrics=fold_metrics,
        metric_summary=metric_summary,
        warnings=warnings,
        confusion=confusion,
    )
    tuning_results = pd.DataFrame(
        tuning_rows,
        columns=[
            "model",
            "validation",
            "outer_fold",
            "selection_scope",
            "candidate",
            "selection_metric",
            "score",
            "parameters",
            "status",
            "error",
        ],
    )
    write_study_outputs(output_dir, config, leaderboard, tuning_results, best_params)
    selection_trace.to_csv(output_dir / "selection_trace.csv", index=False)
    validation_summary.to_csv(output_dir / "validation_summary.csv", index=False)
    write_research_outputs(
        output_dir,
        executed_config,
        source_frame,
        analyzed_rows=len(features),
        feature_columns=len(features.columns),
        fold_metrics=fold_metrics,
        predictions=predictions,
        warnings=warnings,
        confusion=confusion,
    )
    write_result_summary(
        output_dir,
        executed_config,
        metrics,
        warnings,
        study_summary={
            "evaluation_scope": "nested_selection_procedure"
            if family_search
            else "prespecified_family",
            "selection_protocol": "nested_family_v1",
            "best_model": best["model"],
            "best_validation": best["validation"],
            "selection_metric": metric,
            "best_parameters": best_params,
            "evaluated_combinations": len(ranked_rows),
        },
    )
    return ExperimentResult(
        metrics=metrics,
        predictions=predictions,
        model=final_model,
        fold_metrics=fold_metrics,
        metric_summary=metric_summary,
        warnings=warnings,
        confusion_matrix=confusion,
        leaderboard=leaderboard,
        tuning_results=tuning_results,
        best_model_name=best["model"],
        best_validation_strategy=best["validation"],
        best_params=best_params,
        selection_trace=selection_trace,
        validation_summary=validation_summary,
    )



def _run_independent_validations(
    config: ExperimentConfig,
    frame: pd.DataFrame | None,
    progress_callback: ProgressCallback | None,
) -> ExperimentResult:
    """Run the same nested procedure for each validation without selecting a global winner."""
    from psyml.protocol import error_payload
    from psyml.reporting.output import write_independent_outputs

    output_dir = Path(config.output_dir)
    if output_dir.exists() and (not output_dir.is_dir() or any(output_dir.iterdir())):
        raise FileExistsError("Output directory must be new or empty; existing output is preserved")
    output_dir.mkdir(parents=True, exist_ok=True)
    if frame is None:
        if config.input_path is None:
            raise ValueError("input_path is required when frame is not supplied")
        frame = load_dataframe(config.input_path)
    validations = config.selected_validations()
    results: dict[str, ExperimentResult] = {}
    entries: dict[str, dict[str, Any]] = {}
    summaries, warnings = [], []
    started = time.monotonic()

    for index, validation in enumerate(validations):
        def report(
            details: dict[str, Any], index: int = index, validation: str = validation
        ) -> None:
            if progress_callback is None:
                return
            fraction = (index + details.get("progress", 0.0)) / len(validations)
            elapsed = time.monotonic() - started
            completed = index + int(details.get("progress", 0.0) >= 1.0)
            progress_callback({
                **details, "progress": fraction, "current_validation": validation,
                "completed_tasks": completed, "total_tasks": len(validations),
                "remaining_tasks": len(validations) - completed,
                "elapsed_seconds": elapsed,
                "estimated_remaining_seconds": elapsed * (1 - fraction) / fraction
                if fraction > 0 else None,
            })

        child_dir = output_dir / "validations" / validation
        child_config = replace(
            config, output_dir=child_dir, validation_strategy=validation,
            validation_strategies=[validation], primary_validation=validation,
        )
        try:
            child = _run_prioritized(child_config, frame, report)
        except (ValueError, TypeError, KeyError) as error:
            # Scientific/data failures remain explicit; cancellation and IO failures propagate.
            details = error_payload(error)
            entries[validation] = {"status": "failed", "error": details}
            summaries.append({
                "validation": validation, "role": "independent", "status": "failed",
                "error": str(error), "n_folds": 0,
            })
            warnings.append(f"Validation {validation} failed: {error}")
        else:
            results[validation] = child
            entries[validation] = {
                "status": "completed", "result_path": f"validations/{validation}/result.json",
                "metrics": child.metrics,
            }
            summaries.append({
                "validation": validation, "role": "independent", "status": "completed",
                "error": "", "n_folds": len(child.fold_metrics), **child.metrics,
            })
            warnings.extend(f"[{validation}] {warning}" for warning in child.warnings)
        report({"progress": 1.0, "phase": "finalizing", "current_fold": 1})

    summary = pd.DataFrame(summaries)
    write_independent_outputs(output_dir, config, summary, entries, warnings, results)
    if not results:
        raise ValueError("Every independent validation failed; see validation_summary.csv: "
                         + " | ".join(warnings))
    if progress_callback is not None:
        progress_callback({
            "progress": 1.0, "phase": "finalizing", "completed_tasks": len(validations),
            "total_tasks": len(validations), "remaining_tasks": 0,
            "elapsed_seconds": time.monotonic() - started, "estimated_remaining_seconds": 0.0,
            "current_validation": "", "current_fold": 1,
        })
    # Empty headline fields are deliberate: callers must choose an entry explicitly.
    return ExperimentResult(
        metrics={}, predictions=pd.DataFrame(), model=None, fold_metrics=pd.DataFrame(),
        metric_summary=pd.DataFrame(), warnings=warnings, validation_summary=summary,
        validation_results=results,
    )
