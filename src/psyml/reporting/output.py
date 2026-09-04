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
) -> None:
    """Persist metrics, predictions, and configuration in one output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([metrics]).to_csv(output_dir / "metrics.csv", index=False)
    predictions.to_csv(output_dir / "predictions.csv", index=False)
    serialized: dict[str, Any] = asdict(config)
    serialized["input_path"] = str(config.input_path) if config.input_path else None
    serialized["output_dir"] = str(config.output_dir)
    (output_dir / "config.json").write_text(
        json.dumps(serialized, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
