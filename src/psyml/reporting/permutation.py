"""Export per-validation permutation-importance artefacts.

The runner computes permutation importances per outer fold and keeps them
isolated per validation. This module turns those in-memory records into
auditable files: raw per-repeat values, a per-fold table (repeat mean and
descriptive repeat SD), an equal-weight cross-fold summary (between-fold SD),
a JSON metadata document and a signed ranking figure.

Design rules enforced here:

* Repeat variation (``repeat_std``) is never mixed with cross-fold variation
  (``between_fold_std``); the latter is ``null`` for a single successful fold.
* Negative importances are kept, never normalised to percentages, and no
  confidence interval is implied.
* Partial or failed status is always written; a validation with no successful
  fold never receives a success ranking table or a blank figure.
* Group identifiers are kept out of these files; only row counts and optional
  held-out row indices travel from the runner metadata.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

INTERPRETATIONS_DIRNAME = "interpretations"
RAW_FILENAME = "permutation_raw.csv"
FOLD_FILENAME = "permutation_folds.csv"
SUMMARY_FILENAME = "permutation_summary.csv"
METADATA_FILENAME = "permutation.json"
FIGURE_FILENAME = "permutation_importance.png"

_RAW_COLUMNS = [
    "validation",
    "fold",
    "model_family",
    "variable",
    "repeat",
    "metric",
    "importance",
    "direction",
    "baseline_score",
    "n_rows",
]
_FOLD_COLUMNS = [
    "validation",
    "fold",
    "model_family",
    "variable",
    "metric",
    "direction",
    "baseline_score",
    "repeats",
    "mean",
    "repeat_std",
    "n_rows",
    "status",
    "error",
]
_SUMMARY_COLUMNS = [
    "validation",
    "variable",
    "metric",
    "direction",
    "n_folds_successful",
    "n_folds_planned",
    "status",
    "fold_mean_equal_weight",
    "between_fold_std",
]


def _finite_or_none(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _fold_variable_rows(
    validation: str, record: dict[str, Any]
) -> list[dict[str, Any]]:
    fold = record.get("fold")
    family = record.get("model_family")
    metric = record.get("metric")
    direction = record.get("direction")
    baseline = _finite_or_none(record.get("baseline_score"))
    n_rows = record.get("n_rows")
    repeats = record.get("repeats")
    rows: list[dict[str, Any]] = []
    for variable in record.get("variables", []):
        rows.append(
            {
                "variable": str(variable.get("name")),
                "mean": _finite_or_none(variable.get("mean")),
                "repeat_std": _finite_or_none(variable.get("std")),
                "n_repeats": len(variable.get("importances", [])),
                "metric": metric,
                "direction": direction,
                "baseline_score": baseline,
                "repeats": repeats,
                "n_rows": n_rows,
                "fold": fold,
                "model_family": family,
                "validation": validation,
                "status": "completed",
                "error": "",
            }
        )
    return rows


def _build_frames(
    permutation_results: dict[str, list[dict[str, Any]]],
    planned_folds: dict[str, dict[int, dict[str, Any]]] | None = None,
) -> tuple[dict[str, pd.DataFrame], dict[str, pd.DataFrame], dict[str, pd.DataFrame]]:
    raw_by_validation: dict[str, pd.DataFrame] = {}
    folds_by_validation: dict[str, pd.DataFrame] = {}
    summary_by_validation: dict[str, pd.DataFrame] = {}
    plan = planned_folds or {}

    for validation, records in permutation_results.items():
        raw_rows: list[dict[str, Any]] = []
        fold_rows: list[dict[str, Any]] = []
        for record in records:
            if record.get("status") == "completed":
                family = record.get("model_family")
                for variable in record.get("variables", []):
                    name = str(variable.get("name"))
                    importances = list(variable.get("importances", []))
                    for repeat, importance in enumerate(importances):
                        raw_rows.append(
                            {
                                "validation": validation,
                                "fold": record.get("fold"),
                                "model_family": family,
                                "variable": name,
                                "repeat": repeat,
                                "metric": record.get("metric"),
                                "importance": _finite_or_none(importance),
                                "direction": record.get("direction"),
                                "baseline_score": _finite_or_none(
                                    record.get("baseline_score")
                                ),
                                "n_rows": record.get("n_rows"),
                            }
                        )
                fold_rows.extend(_fold_variable_rows(validation, record))
            else:
                fold_rows.append(
                    {
                        "validation": validation,
                        "fold": record.get("fold"),
                        "model_family": record.get("model_family"),
                        "variable": "",
                        "metric": "",
                        "direction": "",
                        "baseline_score": None,
                        "repeats": None,
                        "mean": None,
                        "repeat_std": None,
                        "n_rows": None,
                        "status": "failed",
                        "error": record.get("error", ""),
                    }
                )

        # Planned folds come from the runner's work plan when available, so a
        # fold whose interpretation never produced a record still counts.
        planned_ids = set(plan.get(validation, {})) | {row["fold"] for row in fold_rows}
        planned_folds_count = len(planned_ids)
        successful_folds = len(
            {row["fold"] for row in fold_rows if row["status"] == "completed"}
        )

        summary_rows: list[dict[str, Any]] = []
        if successful_folds > 0:
            completed = [row for row in fold_rows if row["status"] == "completed"]
            for variable in sorted({row["variable"] for row in completed}):
                variable_rows = [row for row in completed if row["variable"] == variable]
                means = [
                    row["mean"] for row in variable_rows if row["mean"] is not None
                ]
                between = (
                    float(np.std(np.asarray(means, dtype=float), ddof=1))
                    if len(means) >= 2
                    else None
                )
                summary_rows.append(
                    {
                        "validation": validation,
                        "variable": variable,
                        "metric": variable_rows[0]["metric"],
                        "direction": variable_rows[0]["direction"],
                        "n_folds_successful": len(variable_rows),
                        "n_folds_planned": planned_folds_count,
                        "status": (
                            "completed"
                            if len(variable_rows) == planned_folds_count
                            else "partial"
                        ),
                        "fold_mean_equal_weight": (
                            float(np.mean(np.asarray(means, dtype=float)))
                            if means
                            else None
                        ),
                        "between_fold_std": between,
                    }
                )

        raw_by_validation[validation] = pd.DataFrame(raw_rows, columns=_RAW_COLUMNS)
        folds_by_validation[validation] = pd.DataFrame(fold_rows, columns=_FOLD_COLUMNS)
        summary_by_validation[validation] = pd.DataFrame(
            summary_rows, columns=_SUMMARY_COLUMNS
        )

    return raw_by_validation, folds_by_validation, summary_by_validation


def _direction_axis_label(metric: str | None, direction: str | None) -> str:
    name = metric or "selection metric"
    if direction == "lower_is_better":
        return f"{name} increase after permutation (importance)"
    return f"{name} decrease after permutation (importance)"


_CJK_FONT_CANDIDATES = [
    "Arial Unicode MS",
    "PingFang SC",
    "Heiti SC",
    "Songti SC",
    "STHeiti",
    "Microsoft YaHei",
    "SimHei",
    "Noto Sans CJK SC",
    "WenQuanYi Zen Hei",
]


def _cjk_font_families(font_manager: Any) -> list[str]:
    """Return installed CJK-capable families, in preference order."""
    available = {font.name for font in font_manager.fontManager.ttflist}
    return [name for name in _CJK_FONT_CANDIDATES if name in available]


def figure_caption(
    *,
    validation: str,
    metric: str | None,
    direction: str | None,
    status: str,
    successful_folds: int,
    planned_folds: int,
    between_fold_std_available: bool,
) -> dict[str, str]:
    """Build the title, axis label and error-note for a ranking figure.

    Factored out of plotting so tests can assert the exact wording without
    rendering or comparing pixels. Every standalone PNG must be readable on its
    own: it names the validation, the successful/planned fold counts, whether
    the run was complete or partial, and what the error bars mean.
    """
    status_label = {
        "completed": "completed",
        "partial": "partial",
        "failed": "failed",
        "not_run": "not run",
    }.get(status, status)
    title = (
        f"Permutation importance — {validation} "
        f"({successful_folds}/{planned_folds} folds successful, {status_label})"
    )
    xlabel = _direction_axis_label(metric, direction)
    if between_fold_std_available:
        error_note = (
            "Error bars: between-fold SD of fold means (ddof=1); descriptive spread "
            "across folds, not a confidence interval."
        )
    else:
        error_note = (
            "Between-fold SD unavailable (fewer than two successful folds); "
            "no error bars drawn."
        )
    return {"title": title, "xlabel": xlabel, "error_note": error_note}


def _write_figure(
    path: Path,
    validation: str,
    summary: pd.DataFrame,
    *,
    status: str,
    successful_folds: int,
    planned_folds: int,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import font_manager
    from matplotlib import pyplot as plt

    frame = summary.dropna(subset=["fold_mean_equal_weight"]).copy()
    if frame.empty:
        return
    frame = frame.sort_values("fold_mean_equal_weight", ascending=True)
    values = frame["fold_mean_equal_weight"].to_numpy(dtype=float)
    positions = np.arange(len(frame))
    errors = frame["between_fold_std"].to_numpy(dtype=float)
    # Error bars only make sense when at least two folds contribute; a single
    # fold has no between-fold spread and must not imply one.
    draw_errors = len(values) >= 2 and np.all(np.isfinite(errors))
    height = max(4.0, 0.45 * len(frame) + 1.6)
    # Prefer a CJK-capable family so Unicode variable names stay readable; keep
    # the DejaVu fallback for Latin and symbols.
    families = _cjk_font_families(font_manager)
    settings: dict[str, Any] = {"axes.unicode_minus": False}
    if families:
        settings["font.family"] = [*families, "DejaVu Sans"]
    metric = str(frame["metric"].iloc[0]) if frame["metric"].notna().any() else None
    direction = (
        str(frame["direction"].iloc[0]) if frame["direction"].notna().any() else None
    )
    caption = figure_caption(
        validation=validation,
        metric=metric,
        direction=direction,
        status=status,
        successful_folds=successful_folds,
        planned_folds=planned_folds,
        between_fold_std_available=draw_errors,
    )
    with matplotlib.rc_context(settings):
        figure, axis = plt.subplots(figsize=(9.0, height))
        left = np.where(values >= 0, 0.0, values)
        width = np.abs(values)
        axis.barh(positions, width, left=left, color="#5261c9", alpha=0.9)
        if draw_errors:
            axis.errorbar(
                values,
                positions,
                xerr=errors,
                fmt="none",
                ecolor="#20232b",
                elinewidth=1.0,
                capsize=3,
            )
        axis.axvline(0.0, color="#20232b", linewidth=1.0, linestyle="--")
        labels = [str(name) for name in frame["variable"]]
        axis.set_yticks(positions, labels=labels)
        axis.set_xlabel(caption["xlabel"])
        axis.set_title(caption["title"])
        axis.grid(axis="x", alpha=0.25)
        figure.tight_layout()
        figure.text(
            0.01,
            0.01,
            caption["error_note"],
            ha="left",
            va="bottom",
            fontsize=8,
            color="#444444",
        )
        figure.savefig(path, dpi=160, bbox_inches="tight")
        plt.close(figure)


def permutation_status(
    records: list[dict[str, Any]], hint: str | None = None
) -> tuple[str, int, int]:
    """Return ``(status, successful_folds, failed_folds)`` for one validation."""
    return _validation_status(records, hint)


def _validation_status(
    records: list[dict[str, Any]], hint: str | None
) -> tuple[str, int, int]:
    planned = len(records)
    successful = sum(1 for record in records if record.get("status") == "completed")
    failed = planned - successful
    if planned == 0:
        return "not_run", 0, 0
    if successful == 0:
        return "failed", successful, failed
    if failed:
        return "partial", successful, failed
    return "completed", successful, failed


def _metadata_payload(
    validation: str,
    records: list[dict[str, Any]],
    summary: pd.DataFrame,
    status: str,
    status_hint: str | None,
    request_context: dict[str, Any] | None = None,
    planned_folds: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    context = request_context or {}
    plan = planned_folds or {}
    completed = [record for record in records if record.get("status") == "completed"]
    failed = [record for record in records if record.get("status") != "completed"]
    first = completed[0] if completed else {}
    baselines: dict[str, Any] = {}
    heldout: dict[str, Any] = {}
    encodings: dict[str, Any] = {}
    notes: list[str] = []
    for record in records:
        if record.get("status") != "completed":
            continue
        fold = str(record.get("fold"))
        baselines[fold] = {
            "model_family": record.get("model_family"),
            "baseline_score": _finite_or_none(record.get("baseline_score")),
            "n_rows": record.get("n_rows"),
        }
        heldout[fold] = {
            "n_rows": record.get("n_rows"),
            "row_indices": record.get("heldout_row_indices"),
        }
        encodings[fold] = record.get("feature_encoding", {"status": "unavailable"})
        for note in record.get("metadata", {}).get("notes", []):
            if note not in notes:
                notes.append(note)
    variables = []
    for row in summary.itertuples(index=False):
        variables.append(
            {
                "name": row.variable,
                "n_folds_successful": int(row.n_folds_successful),
                "n_folds_planned": int(row.n_folds_planned),
                "equal_weight_fold_mean": _finite_or_none(row.fold_mean_equal_weight),
                "between_fold_std": _finite_or_none(row.between_fold_std),
                "between_fold_std_ddof": 1,
                "between_fold_std_available": _finite_or_none(row.between_fold_std)
                is not None,
            }
        )
    # Requested settings must survive even when every fold interpretation fails
    # or the selection procedure never ran. Fall back to the runner's known work
    # plan, never fabricate a successful score.
    def _setting(key: str) -> Any:
        value = first.get(key)
        return value if value is not None else context.get(key)

    planned_ids = set(plan) | {
        record.get("fold") for record in records if record.get("fold") is not None
    }
    planned_entries = []
    for fold in sorted(planned_ids):
        entry = plan.get(fold, {})
        planned_entries.append(
            {
                "fold": fold,
                "model_family": entry.get("model_family"),
                "n_rows": entry.get("n_rows"),
            }
        )
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "validation": validation,
        "status": status,
        "selection_procedure_status": status_hint,
        "metric": _setting("metric"),
        "direction": _setting("direction"),
        "selection_metric": _setting("metric"),
        "data_scope": "outer_test",
        "model_scope": "outer_fold_model",
        "permutation_scheme": "rowwise_marginal",
        "seed": _setting("seed"),
        "repeats": _setting("repeats"),
        "n_folds_planned": len(planned_ids),
        "n_folds_successful": len(completed),
        "n_folds_failed": len(failed),
        "planned_folds": planned_entries,
        "baseline_by_fold": baselines,
        "heldout_by_fold": heldout,
        "feature_encoding_by_fold": encodings,
        "model_families": sorted(
            {
                str(record.get("model_family"))
                for record in records
                if record.get("model_family")
            }
        ),
        "models_vary_by_fold": len(
            {
                record.get("model_family")
                for record in completed
                if record.get("model_family")
            }
        )
        > 1,
        "variables": variables,
        "limitations": notes,
        "notes": [
            (
                "Between-fold standard deviation uses ddof=1 and is null for a single "
                "successful fold; it is descriptive, not a confidence interval."
            ),
            (
                "Repeat standard deviation describes variation across repeats inside one "
                "fold and is kept separate from between-fold variation."
            ),
            (
                "Importances are row-wise marginal; correlated variables share or mask "
                "attribution. Values are signed and not normalised."
            ),
        ],
    }
    if failed:
        payload["failed_folds"] = [
            {
                "fold": record.get("fold"),
                "model_family": record.get("model_family")
                or plan.get(record.get("fold"), {}).get("model_family"),
                "n_rows": record.get("n_rows")
                if record.get("n_rows") is not None
                else plan.get(record.get("fold"), {}).get("n_rows"),
                "error_type": record.get("error_type"),
                "error": record.get("error"),
            }
            for record in failed
        ]
    return payload


def _artifact_paths(validation: str, written: dict[str, bool]) -> dict[str, str]:
    base = f"{INTERPRETATIONS_DIRNAME}/{validation}"
    mapping = {
        "raw": (RAW_FILENAME, written.get("raw", False)),
        "folds": (FOLD_FILENAME, written.get("folds", False)),
        "summary": (SUMMARY_FILENAME, written.get("summary", False)),
        "metadata": (METADATA_FILENAME, written.get("metadata", False)),
        "figure": (FIGURE_FILENAME, written.get("figure", False)),
    }
    return {
        f"permutation_{validation}_{key}": f"{base}/{name}"
        for key, (name, present) in mapping.items()
        if present
    }


def write_permutation_outputs(
    output_dir: Path,
    permutation_results: dict[str, list[dict[str, Any]]],
    *,
    validation_status: dict[str, str] | None = None,
    request_context: dict[str, Any] | None = None,
    planned_folds: dict[str, dict[int, dict[str, Any]]] | None = None,
) -> dict[str, str]:
    """Write interpretation artefacts for each validation and return their index.

    ``validation_status`` optionally maps a validation to the status of its
    selection procedure (``"completed"``/``"failed"``). It only clarifies a
    validation that produced no per-fold records at all.

    ``request_context`` carries the requested metric/direction/seed/repeats so
    they survive even when every interpretation fails. ``planned_folds`` maps a
    validation to its known per-fold model family and held-out row count.
    """
    output_dir = Path(output_dir)
    artifacts: dict[str, str] = {}
    raw_by_validation, folds_by_validation, summary_by_validation = _build_frames(
        permutation_results, planned_folds
    )
    hints = validation_status or {}
    plan = planned_folds or {}

    for validation, records in permutation_results.items():
        status, successful, _failed = _validation_status(
            records, hints.get(validation)
        )
        written = {
            "raw": False,
            "folds": False,
            "summary": False,
            "metadata": True,
            "figure": False,
        }
        directory = output_dir / INTERPRETATIONS_DIRNAME / validation
        directory.mkdir(parents=True, exist_ok=True)

        raw = raw_by_validation[validation]
        folds = folds_by_validation[validation]
        summary = summary_by_validation[validation]
        if not raw.empty:
            raw.to_csv(directory / RAW_FILENAME, index=False)
            written["raw"] = True
        if not folds.empty:
            folds.to_csv(directory / FOLD_FILENAME, index=False)
            written["folds"] = True
        if not summary.empty:
            summary.to_csv(directory / SUMMARY_FILENAME, index=False)
            written["summary"] = True

        payload = _metadata_payload(
            validation,
            records,
            summary,
            status,
            hints.get(validation),
            request_context,
            plan.get(validation),
        )
        (directory / METADATA_FILENAME).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if not summary.empty:
            planned_count = len(plan.get(validation, {})) or len(
                {record.get("fold") for record in records}
            )
            _write_figure(
                directory / FIGURE_FILENAME,
                validation,
                summary,
                status=status,
                successful_folds=successful,
                planned_folds=planned_count,
            )
            written["figure"] = (directory / FIGURE_FILENAME).exists()
        artifacts.update(_artifact_paths(validation, written))

    return artifacts


def existing_permutation_artifacts(
    output_dir: Path, validation: str, *, prefix: str = ""
) -> dict[str, str]:
    """Index interpretation files that actually exist for one validation."""
    directory = Path(output_dir) / INTERPRETATIONS_DIRNAME / validation
    if not directory.is_dir():
        return {}
    result: dict[str, str] = {}
    for key, name in [
        ("raw", RAW_FILENAME),
        ("folds", FOLD_FILENAME),
        ("summary", SUMMARY_FILENAME),
        ("metadata", METADATA_FILENAME),
        ("figure", FIGURE_FILENAME),
    ]:
        if (directory / name).is_file():
            result[f"permutation_{validation}_{key}"] = (
                f"{prefix}{INTERPRETATIONS_DIRNAME}/{validation}/{name}"
            )
    return result


def read_permutation_summary(
    output_dir: Path, validation: str
) -> pd.DataFrame | None:
    """Read a written per-validation summary table, if it exists."""
    path = Path(output_dir) / INTERPRETATIONS_DIRNAME / validation / SUMMARY_FILENAME
    if not path.is_file():
        return None
    return pd.read_csv(path)
