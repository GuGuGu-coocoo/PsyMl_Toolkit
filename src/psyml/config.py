"""Configuration objects for a single PsyML experiment."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

TaskKind = Literal["classification", "regression"]
ValidationKind = Literal[
    "holdout",
    "k_fold",
    "stratified_k_fold",
    "group_k_fold",
    "stratified_group_k_fold",
    "leave_one_group_out",
]
MissingStrategy = Literal["drop", "mean", "median", "mode"]
ScalingStrategy = Literal["none", "standard", "minmax"]
TuningMode = Literal["none", "quick", "custom"]

CLASSIFICATION_SELECTION_METRICS = {"balanced_accuracy", "f1_macro", "accuracy"}
REGRESSION_SELECTION_METRICS = {"rmse", "mae", "r2"}


@dataclass(frozen=True)
class ExperimentConfig:
    """Explicit, serializable settings for a reproducible experiment."""

    task: TaskKind
    target_column: str
    model_name: str
    input_path: Path | None = None
    output_dir: Path = Path("results/run")
    group_column: str | None = None
    feature_columns: list[str] | None = None
    test_size: float = 0.2
    random_seed: int = 42
    validation_strategy: ValidationKind = "holdout"
    n_splits: int = 5
    missing_strategy: MissingStrategy = "median"
    scaling: ScalingStrategy = "standard"
    include_data_hash: bool = True
    model_params: dict[str, Any] = field(default_factory=dict)
    model_names: list[str] | None = None
    validation_strategies: list[ValidationKind] | None = None
    tuning_mode: TuningMode = "none"
    parameter_grids: dict[str, dict[str, list[Any]]] = field(default_factory=dict)
    selection_metric: str | None = None
    inner_splits: int = 3
    max_candidates: int = 20

    def __post_init__(self) -> None:
        if self.task not in {"classification", "regression"}:
            raise ValueError("task must be 'classification' or 'regression'")
        if not self.target_column.strip():
            raise ValueError("target_column cannot be empty")
        if not self.model_name.strip():
            raise ValueError("model_name cannot be empty")
        if self.model_names is not None:
            if not self.model_names or any(not name.strip() for name in self.model_names):
                raise ValueError("model_names cannot be empty")
            if len(self.model_names) != len(set(self.model_names)):
                raise ValueError("model_names cannot contain duplicates")
        if not 0 < self.test_size < 1:
            raise ValueError("test_size must be between 0 and 1")
        if self.n_splits < 2:
            raise ValueError("n_splits must be at least 2")
        if self.group_column == self.target_column:
            raise ValueError("group_column cannot be the target_column")
        if self.feature_columns is not None:
            if not self.feature_columns:
                raise ValueError("feature_columns cannot be empty")
            if len(self.feature_columns) != len(set(self.feature_columns)):
                raise ValueError("feature_columns cannot contain duplicates")
            excluded = {self.target_column, self.group_column} & set(self.feature_columns)
            if excluded:
                raise ValueError("feature_columns cannot include the target or group column")
        if self.validation_strategy not in {
            "holdout",
            "k_fold",
            "stratified_k_fold",
            "group_k_fold",
            "stratified_group_k_fold",
            "leave_one_group_out",
        }:
            raise ValueError(f"Unsupported validation_strategy: {self.validation_strategy}")
        selected_validations = self.selected_validations()
        if not selected_validations:
            raise ValueError("validation_strategies cannot be empty")
        if len(selected_validations) != len(set(selected_validations)):
            raise ValueError("validation_strategies cannot contain duplicates")
        for strategy in selected_validations:
            if strategy not in {
                "holdout",
                "k_fold",
                "stratified_k_fold",
                "group_k_fold",
                "stratified_group_k_fold",
                "leave_one_group_out",
            }:
                raise ValueError(f"Unsupported validation strategy: {strategy}")
            if (
                strategy in {"stratified_k_fold", "stratified_group_k_fold"}
                and self.task != "classification"
            ):
                raise ValueError(f"{strategy} is only valid for classification")
            if (
                strategy in {"group_k_fold", "stratified_group_k_fold", "leave_one_group_out"}
                and not self.group_column
            ):
                raise ValueError(f"{strategy} requires group_column")
        if self.missing_strategy not in {"drop", "mean", "median", "mode"}:
            raise ValueError(f"Unsupported missing_strategy: {self.missing_strategy}")
        if self.scaling not in {"none", "standard", "minmax"}:
            raise ValueError(f"Unsupported scaling: {self.scaling}")
        if self.tuning_mode not in {"none", "quick", "custom"}:
            raise ValueError("tuning_mode must be 'none', 'quick', or 'custom'")
        if self.inner_splits < 2:
            raise ValueError("inner_splits must be at least 2")
        if not 1 <= self.max_candidates <= 200:
            raise ValueError("max_candidates must be between 1 and 200")
        allowed_metrics = (
            CLASSIFICATION_SELECTION_METRICS
            if self.task == "classification"
            else REGRESSION_SELECTION_METRICS
        )
        if self.selection_metric is not None and self.selection_metric not in allowed_metrics:
            raise ValueError(
                f"Unsupported selection_metric for {self.task}: {self.selection_metric}"
            )
        for model, grid in self.parameter_grids.items():
            if model not in self.selected_models():
                raise ValueError(f"parameter_grids contains an unselected model: {model}")
            if not isinstance(grid, dict):
                raise TypeError(f"parameter grid for {model} must be an object")
            for parameter, values in grid.items():
                if not parameter or not isinstance(values, list) or not values:
                    raise ValueError(
                        f"parameter grid value for {model}.{parameter} must be a non-empty list"
                    )

    def selected_models(self) -> list[str]:
        """Return the ordered model selection while preserving old configurations."""
        return list(self.model_names) if self.model_names is not None else [self.model_name]

    def selected_validations(self) -> list[ValidationKind]:
        """Return the ordered validation selection while preserving old configurations."""
        if self.validation_strategies is not None:
            return list(self.validation_strategies)
        return [self.validation_strategy]

    def resolved_selection_metric(self) -> str:
        """Return the research-oriented default used to compare candidates."""
        if self.selection_metric is not None:
            return self.selection_metric
        return "balanced_accuracy" if self.task == "classification" else "rmse"
