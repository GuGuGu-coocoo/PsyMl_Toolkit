"""Reproducible classification and regression experiment runner."""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from sklearn.pipeline import Pipeline

from psyml.config import ExperimentConfig
from psyml.data.io import load_dataframe, validate_dataset
from psyml.evaluation.metrics import (
    classification_confusion_matrix,
    classification_metrics,
    regression_metrics,
)
from psyml.models.factory import build_model
from psyml.preprocessing.pipeline import build_preprocessor
from psyml.reporting.output import write_result_summary, write_results
from psyml.reporting.research import write_research_outputs
from psyml.validation.split import make_validation_splits


@dataclass
class ExperimentResult:
    """In-memory evaluation result and final fitted model."""

    metrics: dict[str, float]
    predictions: pd.DataFrame
    model: Pipeline
    fold_metrics: pd.DataFrame
    metric_summary: pd.DataFrame
    warnings: list[str]
    confusion_matrix: pd.DataFrame | None = None


def _build_pipeline(config: ExperimentConfig, training_features: pd.DataFrame) -> Pipeline:
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
            (
                "model",
                build_model(
                    config.task,
                    config.model_name,
                    config.random_seed,
                    config.model_params,
                ),
            ),
        ]
    )


def _risk_warnings(
    config: ExperimentConfig, target: pd.Series, groups: pd.Series | None, dropped_rows: int
) -> list[str]:
    warnings = []
    if dropped_rows:
        warnings.append(f"Dropped {dropped_rows} rows because missing_strategy='drop'.")
    if groups is not None and config.validation_strategy in {"k_fold", "stratified_k_fold"}:
        warnings.append(
            "A group column was supplied but the selected validation strategy does not isolate groups."
        )
    if config.task == "classification":
        counts = target.value_counts()
        if counts.max() >= 4 * counts.min():
            warnings.append(
                "The target classes are imbalanced; inspect balanced and macro metrics."
            )
        if config.validation_strategy == "stratified_k_fold" and counts.min() < config.n_splits:
            raise ValueError("Each class needs at least n_splits rows for stratified_k_fold")
    return warnings


def run_experiment(config: ExperimentConfig, frame: pd.DataFrame | None = None) -> ExperimentResult:
    """Run leakage-safe holdout or cross-validated evaluation."""
    if frame is None:
        if config.input_path is None:
            raise ValueError("input_path is required when frame is not supplied")
        frame = load_dataframe(config.input_path)
    validate_dataset(frame, config.target_column, config.group_column)

    working = frame.dropna(subset=[config.target_column]).copy()
    before_missing_drop = len(working)
    if config.missing_strategy == "drop":
        working = working.dropna()
    dropped_rows = before_missing_drop - len(working)
    if working.empty:
        raise ValueError("No rows remain after missing-data handling")

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

    warnings = _risk_warnings(config, target, groups, dropped_rows)
    splits = make_validation_splits(
        working,
        target,
        config.task,
        config.validation_strategy,
        config.n_splits,
        config.test_size,
        config.random_seed,
        groups,
    )

    fold_rows: list[dict[str, float | int]] = []
    prediction_frames = []
    last_model: Pipeline | None = None
    for fold_number, (train_index, test_index) in enumerate(splits, start=1):
        train_x = working.iloc[train_index]
        test_x = working.iloc[test_index]
        train_y = target.iloc[train_index]
        test_y = target.iloc[test_index]
        model = _build_pipeline(config, train_x)
        model.fit(train_x, train_y)
        predicted = model.predict(test_x)
        if config.task == "classification":
            fold_result = classification_metrics(model, test_x, test_y, predicted)
        else:
            fold_result = regression_metrics(test_y, predicted)
        fold_rows.append({"fold": fold_number, **fold_result})
        prediction_frames.append(
            pd.DataFrame(
                {
                    "row_index": test_y.index,
                    "fold": fold_number,
                    "observed": test_y.to_numpy(),
                    "predicted": predicted,
                }
            )
        )
        last_model = model

    fold_metrics = pd.DataFrame(fold_rows)
    metric_columns = [column for column in fold_metrics.columns if column != "fold"]
    metrics = {column: float(fold_metrics[column].mean()) for column in metric_columns}
    metric_summary = pd.DataFrame(
        [
            {
                "metric": column,
                "mean": float(fold_metrics[column].mean()),
                "std": float(fold_metrics[column].std(ddof=0)),
                "min": float(fold_metrics[column].min()),
                "max": float(fold_metrics[column].max()),
                "n_folds": len(fold_metrics),
            }
            for column in metric_columns
        ]
    )
    predictions = pd.concat(prediction_frames, ignore_index=True)
    confusion = None
    if config.task == "classification":
        confusion = classification_confusion_matrix(
            predictions["observed"], predictions["predicted"]
        )

    if config.validation_strategy == "holdout":
        assert last_model is not None
        final_model = last_model
    else:
        final_model = _build_pipeline(config, working)
        final_model.fit(working, target)

    write_results(
        Path(config.output_dir),
        config,
        metrics,
        predictions,
        fold_metrics=fold_metrics,
        metric_summary=metric_summary,
        warnings=warnings,
        confusion=confusion,
    )
    write_research_outputs(
        Path(config.output_dir),
        config,
        frame,
        analyzed_rows=len(working),
        feature_columns=len(working.columns),
        fold_metrics=fold_metrics,
        predictions=predictions,
        warnings=warnings,
        confusion=confusion,
    )
    write_result_summary(Path(config.output_dir), config, metrics, warnings)
    return ExperimentResult(
        metrics=metrics,
        predictions=predictions,
        model=final_model,
        fold_metrics=fold_metrics,
        metric_summary=metric_summary,
        warnings=warnings,
        confusion_matrix=confusion,
    )
