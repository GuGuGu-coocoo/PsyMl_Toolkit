"""Versioned JSON protocol shared by the CLI and future GUI."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from psyml.config import ExperimentConfig
from psyml.data.formats import SUPPORTED_SUFFIXES
from psyml.models.catalog import quick_parameter_grid, supported_models

SCHEMA_VERSION = "1.0"
SCHEMA_NAMES = {"analysis_config", "event", "result"}


def config_to_dict(config: ExperimentConfig) -> dict[str, Any]:
    """Serialize a configuration using the stable public schema."""
    serialized = asdict(config)
    serialized["schema_version"] = SCHEMA_VERSION
    serialized["input_path"] = str(config.input_path) if config.input_path else None
    serialized["output_dir"] = str(config.output_dir)
    return {"schema_version": serialized.pop("schema_version"), **serialized}


def config_from_dict(payload: dict[str, Any]) -> ExperimentConfig:
    """Validate protocol-level fields and construct an experiment configuration."""
    if not isinstance(payload, dict):
        raise TypeError("Analysis configuration must be a JSON object")
    version = payload.get("schema_version")
    if version != SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported analysis configuration schema_version: {version!r}; "
            f"expected {SCHEMA_VERSION!r}"
        )
    required = {"task", "target_column", "model_name", "input_path", "output_dir"}
    missing = required - set(payload)
    if missing:
        raise ValueError(f"Missing analysis configuration fields: {', '.join(sorted(missing))}")
    fields = set(ExperimentConfig.__dataclass_fields__)
    unknown = set(payload) - fields - {"schema_version"}
    if unknown:
        raise ValueError(f"Unknown analysis configuration fields: {', '.join(sorted(unknown))}")
    values = {key: value for key, value in payload.items() if key != "schema_version"}
    if "input_path" in values and values["input_path"] is not None:
        values["input_path"] = Path(values["input_path"])
    if "output_dir" in values:
        values["output_dir"] = Path(values["output_dir"])
    try:
        return ExperimentConfig(**values)
    except TypeError as error:
        raise ValueError(f"Invalid analysis configuration fields: {error}") from error


def load_config(path: Path | str) -> ExperimentConfig:
    """Read a UTF-8 analysis configuration file."""
    config_path = Path(path)
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file does not exist: {config_path}") from None
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Configuration file is not valid JSON at line {error.lineno}, column {error.colno}"
        ) from error
    return config_from_dict(payload)


def result_payload(
    config: ExperimentConfig,
    metrics: dict[str, float],
    warnings: list[str],
    *,
    study_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a stable machine-readable result summary."""
    artifacts = {
        "analysis_config": "analysis_config.json",
        "analysis_manifest": "analysis_manifest.json",
        "fold_metrics": "fold_metrics.csv",
        "methods_summary": "methods_summary.md",
        "metrics": "metrics.csv",
        "metrics_summary": "metrics_summary.csv",
        "predictions": "predictions.csv",
        "reproducibility_report": "reproducibility_report.md",
        "result": "result.json",
        "warnings": "warnings.json",
        "model_comparison": "model_comparison.csv",
        "parameter_search": "parameter_search.csv",
        "best_parameters": "best_parameters.json",
        "study_config": "study_config.json",
        "selection_trace": "selection_trace.csv",
        "validation_summary": "validation_summary.csv",
    }
    if config.task == "classification":
        artifacts["confusion_matrix"] = "confusion_matrix.csv"
        artifacts["figure"] = "figures/confusion_matrix.png"
    else:
        artifacts["figure"] = "figures/observed_vs_predicted.png"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": "completed",
        "task": config.task,
        "metrics": metrics,
        "warnings": warnings,
        "artifacts": artifacts,
    }
    if study_summary:
        payload.update(study_summary)
    return payload


def event_payload(
    event: str,
    progress: float,
    *,
    result_path: str | None = None,
    error: dict[str, str] | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one versioned subprocess status event."""
    if event not in {"started", "progress", "completed", "failed", "cancelled"}:
        raise ValueError(f"Unsupported event: {event}")
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "event": event,
        "progress": progress,
    }
    if result_path is not None:
        payload["result_path"] = result_path
    if error is not None:
        payload["error"] = error
    if details:
        payload.update(details)
    return payload


def error_payload(error: Exception) -> dict[str, str]:
    """Convert expected user-facing failures to a stable, traceback-free structure."""
    if isinstance(error, FileNotFoundError):
        code = "file_not_found"
    elif isinstance(error, KeyError):
        code = "column_not_found"
    elif isinstance(error, (ValueError, TypeError)):
        code = "invalid_input"
    else:
        code = "analysis_failed"
    return {"code": code, "type": type(error).__name__, "message": str(error)}


def capabilities_payload() -> dict[str, Any]:
    """Describe selectable core capabilities without importing GUI logic."""
    return {
        "schema_version": SCHEMA_VERSION,
        "tasks": ["classification", "regression"],
        "models": {
            "classification": list(supported_models("classification")),
            "regression": list(supported_models("regression")),
        },
        "parameter_grids": {
            task: {model: quick_parameter_grid(task, model) for model in supported_models(task)}
            for task in ["classification", "regression"]
        },
        "selection_metrics": {
            "classification": ["balanced_accuracy", "f1_macro", "accuracy"],
            "regression": ["rmse", "mae", "r2"],
        },
        "input_formats": sorted(SUPPORTED_SUFFIXES),
        "validation_strategies": [
            "holdout",
            "k_fold",
            "stratified_k_fold",
            "group_k_fold",
            "stratified_group_k_fold",
            "leave_one_group_out",
        ],
        "missing_strategies": ["drop", "mean", "median", "mode"],
        "scaling_strategies": ["none", "standard", "minmax"],
        "schemas": {name: SCHEMA_VERSION for name in sorted(SCHEMA_NAMES)},
    }


def _json_value(value: Any) -> Any:
    import pandas as pd

    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def preview_payload(
    path: Path | str,
    *,
    rows: int = 5,
    include_sample: bool = False,
) -> dict[str, Any]:
    """Return local-only column metadata and an optional small sample."""
    if rows < 1 or rows > 100:
        raise ValueError("Preview rows must be between 1 and 100")
    from psyml.data import load_dataframe

    frame = load_dataframe(path)
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "row_count": len(frame),
        "column_count": len(frame.columns),
        "columns": [],
    }
    for position, column in enumerate(frame.columns):
        series = frame.iloc[:, position]
        payload["columns"].append(
            {
                "name": str(column),
                "dtype": str(series.dtype),
                "missing_count": int(series.isna().sum()),
            }
        )
    if include_sample:
        payload["sample"] = [
            {str(column): _json_value(value) for column, value in row.items()}
            for row in frame.head(rows).to_dict(orient="records")
        ]
    return payload


def schema_text(name: str) -> str:
    """Read one bundled JSON schema."""
    if name not in SCHEMA_NAMES:
        raise ValueError(f"Unknown schema: {name}")
    from importlib.resources import files

    return files("psyml.schemas").joinpath(f"{name}.schema.json").read_text(encoding="utf-8")
