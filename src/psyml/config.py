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
    "leave_one_group_out",
]
MissingStrategy = Literal["drop", "mean", "median", "mode"]
ScalingStrategy = Literal["none", "standard", "minmax"]


@dataclass(frozen=True)
class ExperimentConfig:
    """Explicit, serializable settings for a reproducible experiment."""

    task: TaskKind
    target_column: str
    model_name: str
    input_path: Path | None = None
    output_dir: Path = Path("results/run")
    group_column: str | None = None
    test_size: float = 0.2
    random_seed: int = 42
    validation_strategy: ValidationKind = "holdout"
    n_splits: int = 5
    missing_strategy: MissingStrategy = "median"
    scaling: ScalingStrategy = "standard"
    model_params: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.task not in {"classification", "regression"}:
            raise ValueError("task must be 'classification' or 'regression'")
        if not self.target_column.strip():
            raise ValueError("target_column cannot be empty")
        if not self.model_name.strip():
            raise ValueError("model_name cannot be empty")
        if not 0 < self.test_size < 1:
            raise ValueError("test_size must be between 0 and 1")
        if self.n_splits < 2:
            raise ValueError("n_splits must be at least 2")
        if self.group_column == self.target_column:
            raise ValueError("group_column cannot be the target_column")
        if self.validation_strategy not in {
            "holdout",
            "k_fold",
            "stratified_k_fold",
            "group_k_fold",
            "leave_one_group_out",
        }:
            raise ValueError(f"Unsupported validation_strategy: {self.validation_strategy}")
        if self.validation_strategy == "stratified_k_fold" and self.task != "classification":
            raise ValueError("stratified_k_fold is only valid for classification")
        if (
            self.validation_strategy in {"group_k_fold", "leave_one_group_out"}
            and not self.group_column
        ):
            raise ValueError(f"{self.validation_strategy} requires group_column")
        if self.missing_strategy not in {"drop", "mean", "median", "mode"}:
            raise ValueError(f"Unsupported missing_strategy: {self.missing_strategy}")
        if self.scaling not in {"none", "standard", "minmax"}:
            raise ValueError(f"Unsupported scaling: {self.scaling}")
