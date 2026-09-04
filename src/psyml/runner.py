"""One reproducible experiment runner for classification and regression."""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from sklearn.pipeline import Pipeline

from psyml.config import ExperimentConfig
from psyml.data.io import load_dataframe, validate_dataset
from psyml.evaluation.metrics import classification_metrics, regression_metrics
from psyml.models.factory import build_model
from psyml.preprocessing.pipeline import build_preprocessor
from psyml.reporting.output import write_results
from psyml.validation.split import split_train_test


@dataclass
class ExperimentResult:
    """In-memory result returned after held-out evaluation."""

    metrics: dict[str, float]
    predictions: pd.DataFrame
    model: Pipeline


def run_experiment(config: ExperimentConfig, frame: pd.DataFrame | None = None) -> ExperimentResult:
    """Run a holdout experiment without fitting transformations on test data."""
    if frame is None:
        if config.input_path is None:
            raise ValueError("input_path is required when frame is not supplied")
        frame = load_dataframe(config.input_path)
    validate_dataset(frame, config.target_column, config.group_column)
    working = frame.dropna(subset=[config.target_column]).copy()
    target = working.pop(config.target_column)
    groups = working.pop(config.group_column) if config.group_column else None
    if working.empty:
        raise ValueError("No feature columns remain after selecting target and group columns")
    if config.task == "classification" and target.nunique() < 2:
        raise ValueError("Classification requires at least two target classes")

    train_x, test_x, train_y, test_y = split_train_test(
        working,
        target,
        config.task,
        config.test_size,
        config.random_seed,
        groups,
    )
    model = Pipeline(
        [
            ("preprocess", build_preprocessor(train_x)),
            ("model", build_model(config.task, config.model_name, config.random_seed, config.model_params)),
        ]
    )
    model.fit(train_x, train_y)
    predicted = model.predict(test_x)
    if config.task == "classification":
        metrics = classification_metrics(model, test_x, test_y, predicted)
    else:
        metrics = regression_metrics(test_y, predicted)
    predictions = pd.DataFrame({"observed": test_y.to_numpy(), "predicted": predicted}, index=test_y.index)
    predictions.index.name = "row_index"
    write_results(Path(config.output_dir), config, metrics, predictions)
    return ExperimentResult(metrics=metrics, predictions=predictions, model=model)
