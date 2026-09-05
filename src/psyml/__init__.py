"""PsyML's reproducible, leakage-safe machine-learning core."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from psyml.config import ExperimentConfig
    from psyml.runner import ExperimentResult

__all__ = ["ExperimentConfig", "ExperimentResult", "run_experiment"]
__version__ = "0.1.1"


def __getattr__(name: str) -> Any:
    """Load the scientific runtime only when its public API is requested."""
    if name == "ExperimentConfig":
        from psyml.config import ExperimentConfig

        return ExperimentConfig
    if name in {"ExperimentResult", "run_experiment"}:
        from psyml.runner import ExperimentResult, run_experiment

        return {"ExperimentResult": ExperimentResult, "run_experiment": run_experiment}[name]
    raise AttributeError(f"module 'psyml' has no attribute {name!r}")
