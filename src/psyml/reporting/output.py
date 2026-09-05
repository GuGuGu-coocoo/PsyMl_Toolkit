"""Write consistent, explicit experiment outputs."""

import json
from pathlib import Path

import pandas as pd

from psyml.config import ExperimentConfig
from psyml.protocol import config_to_dict, result_payload


def write_results(
    output_dir: Path,
    config: ExperimentConfig,
    metrics: dict[str, float],
    predictions: pd.DataFrame,
    fold_metrics: pd.DataFrame | None = None,
    metric_summary: pd.DataFrame | None = None,
    warnings: list[str] | None = None,
    confusion: pd.DataFrame | None = None,
) -> None:
    """Persist evaluation, warnings, and configuration in one output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([metrics]).to_csv(output_dir / "metrics.csv", index=False)
    predictions.to_csv(output_dir / "predictions.csv", index=False)
    if fold_metrics is not None:
        fold_metrics.to_csv(output_dir / "fold_metrics.csv", index=False)
    if metric_summary is not None:
        metric_summary.to_csv(output_dir / "metrics_summary.csv", index=False)
    if confusion is not None:
        confusion.to_csv(output_dir / "confusion_matrix.csv", index=True)
    (output_dir / "warnings.json").write_text(
        json.dumps(warnings or [], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    serialized = (
        json.dumps(
            config_to_dict(config), indent=2, ensure_ascii=False, sort_keys=True, default=str
        )
        + "\n"
    )
    (output_dir / "analysis_config.json").write_text(serialized, encoding="utf-8")
    (output_dir / "config.json").write_text(serialized, encoding="utf-8")


def write_result_summary(
    output_dir: Path,
    config: ExperimentConfig,
    metrics: dict[str, float],
    warnings: list[str],
    study_summary: dict | None = None,
) -> None:
    """Write the stable result summary after every other artefact succeeds."""
    (output_dir / ".result.json.tmp").write_text(
        json.dumps(
            result_payload(config, metrics, warnings, study_summary=study_summary),
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    (output_dir / ".result.json.tmp").replace(output_dir / "result.json")


def write_study_outputs(
    output_dir: Path,
    config: ExperimentConfig,
    leaderboard: pd.DataFrame,
    tuning_results: pd.DataFrame,
    best_parameters: dict,
) -> None:
    """Persist the complete comparison and parameter-selection evidence."""
    leaderboard.to_csv(output_dir / "model_comparison.csv", index=False)
    tuning_results.to_csv(output_dir / "parameter_search.csv", index=False)
    (output_dir / "best_parameters.json").write_text(
        json.dumps(best_parameters, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "study_config.json").write_text(
        json.dumps(
            config_to_dict(config), indent=2, ensure_ascii=False, sort_keys=True, default=str
        )
        + "\n",
        encoding="utf-8",
    )
