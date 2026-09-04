"""Configuration objects for a single PsyML experiment."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

TaskKind = Literal["classification", "regression"]


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
        if self.group_column == self.target_column:
            raise ValueError("group_column cannot be the target_column")
