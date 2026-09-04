"""Research-facing, privacy-conscious reproducibility artefacts."""

from __future__ import annotations

import hashlib
import json
import platform
from dataclasses import asdict
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import matplotlib
import pandas as pd

from psyml.config import ExperimentConfig

matplotlib.use("Agg")
from matplotlib import pyplot as plt


def _package_version(distribution: str) -> str:
    try:
        return version(distribution)
    except PackageNotFoundError:
        return "unknown"


def _sha256(config: ExperimentConfig, frame: pd.DataFrame) -> tuple[str, str] | None:
    if not config.include_data_hash:
        return None
    digest = hashlib.sha256()
    if config.input_path is not None and Path(config.input_path).is_file():
        with Path(config.input_path).open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest(), "source_file_bytes"
    digest.update(frame.to_csv(index=False, lineterminator="\n").encode("utf-8"))
    return digest.hexdigest(), "canonical_in_memory_csv"


def _loader_dependency(config: ExperimentConfig) -> tuple[str, str] | None:
    if config.input_path is None:
        return None
    suffix = Path(config.input_path).suffix.lower()
    distribution = {
        ".xlsx": "openpyxl",
        ".xls": "xlrd",
        ".sav": "pyreadstat",
        ".dta": "pyreadstat",
        ".sas7bdat": "pyreadstat",
        ".xpt": "pyreadstat",
        ".parquet": "pyarrow",
    }.get(suffix)
    if distribution is None:
        return None
    return distribution, _package_version(distribution)


def _manifest(
    config: ExperimentConfig,
    frame: pd.DataFrame,
    analyzed_rows: int,
    feature_columns: int,
) -> dict[str, Any]:
    dependencies = {
        "matplotlib": _package_version("matplotlib"),
        "numpy": _package_version("numpy"),
        "pandas": _package_version("pandas"),
        "scikit-learn": _package_version("scikit-learn"),
    }
    loader_dependency = _loader_dependency(config)
    if loader_dependency is not None:
        dependencies[loader_dependency[0]] = loader_dependency[1]
    fingerprint = _sha256(config, frame)
    return {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "psyml_version": _package_version("psyml-toolkit"),
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
        },
        "operating_system": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "dependencies": dependencies,
        "data": {
            "source_kind": "file" if config.input_path is not None else "in_memory",
            "input_rows": len(frame),
            "input_columns": len(frame.columns),
            "analyzed_rows": analyzed_rows,
            "feature_columns": feature_columns,
            "sha256": fingerprint[0] if fingerprint else None,
            "hash_basis": fingerprint[1] if fingerprint else None,
        },
    }


def _display(value: str | None) -> str:
    if value is None:
        return "not used"
    return value.replace("|", "\\|").replace("\n", " ")


def _validation_description(config: ExperimentConfig) -> str:
    if config.validation_strategy == "holdout":
        return f"a holdout split with {config.test_size:.0%} assigned to evaluation"
    if config.validation_strategy == "leave_one_group_out":
        return "leave-one-group-out cross-validation"
    labels = {
        "k_fold": "cross-validation",
        "stratified_k_fold": "stratified cross-validation",
        "group_k_fold": "group cross-validation",
    }
    return f"{config.n_splits}-fold {labels[config.validation_strategy]}"


def _methods_summary(
    config: ExperimentConfig,
    analyzed_rows: int,
    feature_columns: int,
    metric_names: list[str],
) -> str:
    group_sentence = (
        f"The grouping variable `{_display(config.group_column)}` was excluded from predictors and "
        "used by the configured split."
        if config.group_column
        else "No grouping variable was configured."
    )
    parameters = json.dumps(config.model_params, ensure_ascii=False, sort_keys=True)
    metrics = ", ".join(metric_names)
    return f"""# Methods Summary

PsyML analyzed {analyzed_rows} rows with {feature_columns} predictor columns for a {config.task} task. The outcome column was `{_display(config.target_column)}`. {group_sentence}

Missing predictor values used the `{config.missing_strategy}` strategy. Numeric scaling was `{config.scaling}`, and categorical predictors were one-hot encoded. All learned preprocessing steps were fitted within each training partition only.

The `{config.model_name}` model was evaluated using {_validation_description(config)} with random seed {config.random_seed}. Explicit model parameters were `{parameters}`. Performance was calculated only from held-out predictions using: {metrics}.

This text describes the executed configuration and is intended as a starting point for a manuscript Methods section; researchers remain responsible for study-specific justification and reporting.
"""


def _markdown_table(frame: pd.DataFrame) -> str:
    columns = [str(column) for column in frame.columns]
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    rows = []
    for values in frame.itertuples(index=False, name=None):
        cells = []
        for value in values:
            if isinstance(value, float):
                cells.append(f"{value:.6g}")
            else:
                cells.append(_display(str(value)))
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join([header, separator, *rows])


def _safe_configuration(config: ExperimentConfig) -> dict[str, Any]:
    serialized = asdict(config)
    serialized["input_path"] = "<redacted-local-path>" if config.input_path else None
    serialized["output_dir"] = "<redacted-local-path>"
    return serialized


def _reproducibility_report(
    config: ExperimentConfig,
    manifest: dict[str, Any],
    fold_metrics: pd.DataFrame,
    warnings: list[str],
) -> str:
    environment = manifest["operating_system"]
    data = manifest["data"]
    warning_lines = "\n".join(f"- {warning}" for warning in warnings) or "- None recorded."
    fingerprint = data["sha256"] or "disabled"
    rerun_note = (
        "The saved `config.json` contains the source path required for a CLI rerun."
        if config.input_path is not None
        else "This run used an in-memory dataframe; attach an input path before a CLI rerun."
    )
    safe_config = json.dumps(
        _safe_configuration(config), indent=2, ensure_ascii=False, sort_keys=True, default=str
    )
    group_safeguard = (
        "- The configured group column was removed from predictors before fitting."
        if config.group_column
        else "- No group column was configured for this run."
    )
    return f"""# Reproducibility Report

## Run and environment

- PsyML: {manifest["psyml_version"]}
- Python: {manifest["python"]["version"]} ({manifest["python"]["implementation"]})
- OS: {environment["system"]} {environment["release"]} ({environment["machine"]})
- Data shape: {data["input_rows"]} input rows × {data["input_columns"]} columns; {data["analyzed_rows"]} analyzed rows and {data["feature_columns"]} predictors
- Data SHA-256: `{fingerprint}`

## Executed configuration

```json
{safe_config}
```

## Fold metrics

{_markdown_table(fold_metrics)}

## Warnings

{warning_lines}

## Leakage safeguards

- The target column was removed before preprocessing and model fitting.
{group_safeguard}
- Imputation, scaling and one-hot encoding were fitted inside each training partition.
- Reported metrics use only predictions from held-out partitions.

## Re-running and artefacts

{rerun_note} The result directory contains the executed configuration, fold and summary metrics, predictions, warnings, this report, a Methods summary, the analysis manifest and task-specific figures. Local paths are intentionally redacted from this report to reduce disclosure risk.
"""


def _write_figure(
    figures_dir: Path,
    config: ExperimentConfig,
    predictions: pd.DataFrame,
    confusion: pd.DataFrame | None,
) -> None:
    figures_dir.mkdir(parents=True, exist_ok=True)
    if config.task == "regression":
        figure, axis = plt.subplots(figsize=(6.4, 5.2))
        axis.scatter(predictions["observed"], predictions["predicted"], alpha=0.7)
        lower = min(predictions["observed"].min(), predictions["predicted"].min())
        upper = max(predictions["observed"].max(), predictions["predicted"].max())
        axis.plot([lower, upper], [lower, upper], linestyle="--", color="black", linewidth=1)
        axis.set(xlabel="Observed", ylabel="Predicted", title="Observed vs predicted")
        figure.tight_layout()
        figure.savefig(figures_dir / "observed_vs_predicted.png", dpi=160)
        plt.close(figure)
        return

    if confusion is None:
        return
    values = confusion.to_numpy()
    figure, axis = plt.subplots(figsize=(6.0, 5.2))
    image = axis.imshow(values, cmap="Blues")
    labels = [f"Class {index + 1}" for index in range(len(values))]
    axis.set_xticks(range(len(labels)), labels=labels, rotation=30, ha="right")
    axis.set_yticks(range(len(labels)), labels=labels)
    axis.set(xlabel="Predicted", ylabel="Observed", title="Confusion matrix")
    for row in range(values.shape[0]):
        for column in range(values.shape[1]):
            text_color = "white" if values[row, column] > values.max() / 2 else "black"
            axis.text(
                column,
                row,
                str(values[row, column]),
                ha="center",
                va="center",
                color=text_color,
            )
    figure.colorbar(image, ax=axis)
    figure.tight_layout()
    figure.savefig(figures_dir / "confusion_matrix.png", dpi=160)
    plt.close(figure)


def write_research_outputs(
    output_dir: Path,
    config: ExperimentConfig,
    source_frame: pd.DataFrame,
    analyzed_rows: int,
    feature_columns: int,
    fold_metrics: pd.DataFrame,
    predictions: pd.DataFrame,
    warnings: list[str],
    confusion: pd.DataFrame | None,
) -> None:
    """Write manifest, faithful narrative reports, and privacy-conscious figures."""
    manifest = _manifest(config, source_frame, analyzed_rows, feature_columns)
    (output_dir / "analysis_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    metric_names = [column for column in fold_metrics.columns if column != "fold"]
    (output_dir / "methods_summary.md").write_text(
        _methods_summary(config, analyzed_rows, feature_columns, metric_names),
        encoding="utf-8",
    )
    (output_dir / "reproducibility_report.md").write_text(
        _reproducibility_report(config, manifest, fold_metrics, warnings),
        encoding="utf-8",
    )
    _write_figure(output_dir / "figures", config, predictions, confusion)
