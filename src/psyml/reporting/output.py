"""Write consistent, explicit experiment outputs."""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

from psyml.config import ExperimentConfig


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
    serialized: dict[str, Any] = asdict(config)
    serialized["input_path"] = str(config.input_path) if config.input_path else None
    serialized["output_dir"] = str(config.output_dir)
    (output_dir / "config.json").write_text(
        json.dumps(serialized, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
