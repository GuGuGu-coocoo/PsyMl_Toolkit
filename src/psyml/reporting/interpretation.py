"""Concise, evidence-based interpretation of already-computed results.

This module only aggregates evidence that the runner already produced
(``procedure_results``, per-combination ``combo_folds``, ``tuning_rows``,
``leaderboard`` and ``validation_summary``). It never fits a model, never
re-selects a family or parameter, and never lets a descriptive comparison flow
back into selection.

Scientific boundaries enforced here:

* A baseline comparison is only reported for the user-selected ``dummy`` when it
  ran successfully on the same validation, the same fold set and the same
  metric, and every matched fold score is finite. Otherwise an explicit
  ``not_comparable`` reason is returned and no difference is invented.
* Differences are signed so that a positive value always means the procedure
  performed better than the baseline (higher-is-better metrics: procedure minus
  baseline; MAE/RMSE: baseline minus procedure).
* Fold variability is descriptive. Single-fold standard deviations are reported
  as ``null`` with stability ``not_assessable``; no significance threshold or
  "reliable/unstable" label is fabricated.
* Failure counts are separated into inner-search candidate failures, outer
  model+validation failures and whole validation/procedure failures.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

LOWER_IS_BETTER = {"mae", "rmse"}
HIGHER_IS_BETTER = {"accuracy", "balanced_accuracy", "f1_macro", "r2"}
BASELINE_MODEL = "dummy"
POSITIVE_MEANS = "procedure_better_than_baseline"
METRIC_COLUMNS_EXCLUDED = {"fold", "model", "validation"}


def metric_direction(metric: str) -> str | None:
    """Return the scoring direction for a metric, or None when unknown."""
    if metric in LOWER_IS_BETTER:
        return "lower_is_better"
    if metric in HIGHER_IS_BETTER:
        return "higher_is_better"
    return None


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _number(value: Any) -> float | None:
    return float(value) if _finite(value) else None


def _metric_summaries(fold_metrics: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """Reuse the runner's fold-mean/std definition, with ddof made explicit."""
    summaries: dict[str, dict[str, Any]] = {}
    if fold_metrics is None or fold_metrics.empty:
        return summaries
    for column in fold_metrics.columns:
        if column in METRIC_COLUMNS_EXCLUDED:
            continue
        series = fold_metrics[column].dropna()
        if series.empty:
            continue
        count = int(series.count())
        summaries[str(column)] = {
            "mean": float(series.mean()),
            "std": float(series.std(ddof=0)) if count >= 2 else None,
            "std_ddof": 0,
            "n_folds": count,
            "min": float(series.min()),
            "max": float(series.max()),
            "stability": "not_assessable" if count < 2 else "descriptive",
        }
    return summaries


def _not_comparable(reason: str, metric: str, direction: str | None) -> dict[str, Any]:
    return {
        "status": "not_comparable",
        "reason": reason,
        "baseline_model": BASELINE_MODEL,
        "metric": metric,
        "direction": direction,
        "positive_means": POSITIVE_MEANS,
        "per_fold": [],
        "mean_difference": None,
        "n_paired_folds": 0,
        "n_folds_procedure": 0,
        "n_folds_baseline": 0,
        "fold_count_match": None,
    }


def _baseline_comparison(
    validation: str,
    metric: str,
    direction: str | None,
    baseline_selected: bool,
    procedure_folds: pd.DataFrame,
    combo_folds: dict[tuple[str, str], list[dict[str, Any]]],
    leaderboard_by_key: dict[tuple[str, str], dict[str, Any]],
    procedure_status: str,
) -> dict[str, Any]:
    if procedure_status != "completed":
        return _not_comparable("procedure_failed", metric, direction)
    if not baseline_selected:
        return _not_comparable("baseline_not_selected", metric, direction)
    if direction is None:
        return _not_comparable("unknown_metric_direction", metric, direction)
    baseline_row = leaderboard_by_key.get((validation, BASELINE_MODEL))
    if baseline_row is None or baseline_row.get("status") != "completed":
        return _not_comparable("baseline_not_run_or_failed", metric, direction)
    dummy_folds = combo_folds.get((validation, BASELINE_MODEL), [])
    if not dummy_folds:
        return _not_comparable("baseline_not_run_or_failed", metric, direction)
    if metric not in procedure_folds.columns:
        return _not_comparable("metric_missing_from_procedure", metric, direction)
    if metric not in dummy_folds[0]:
        return _not_comparable("metric_missing_from_baseline", metric, direction)

    procedure_by_fold = {int(row["fold"]): row for row in procedure_folds.to_dict("records")}
    baseline_by_fold = {int(row["fold"]): row for row in dummy_folds}
    fold_count_match = set(procedure_by_fold) == set(baseline_by_fold)

    per_fold: list[dict[str, Any]] = []
    differences: list[float] = []
    for fold in sorted(set(procedure_by_fold) | set(baseline_by_fold)):
        procedure_row = procedure_by_fold.get(fold)
        baseline_fold_row = baseline_by_fold.get(fold)
        procedure_value = _number(procedure_row.get(metric)) if procedure_row else None
        baseline_value = _number(baseline_fold_row.get(metric)) if baseline_fold_row else None
        difference = None
        if procedure_value is not None and baseline_value is not None:
            difference = (
                procedure_value - baseline_value
                if direction == "higher_is_better"
                else baseline_value - procedure_value
            )
            differences.append(difference)
        procedure_model = procedure_row.get("model") if procedure_row else None
        per_fold.append(
            {
                "fold": fold,
                "procedure_model": procedure_model,
                "procedure_selected_baseline": procedure_model == BASELINE_MODEL,
                "procedure_value": procedure_value,
                "baseline_value": baseline_value,
                "difference": difference,
            }
        )

    result = {
        "status": "comparable",
        "reason": "",
        "baseline_model": BASELINE_MODEL,
        "metric": metric,
        "direction": direction,
        "positive_means": POSITIVE_MEANS,
        "per_fold": per_fold,
        "mean_difference": (sum(differences) / len(differences)) if differences else None,
        "n_paired_folds": len(differences),
        "n_folds_procedure": len(procedure_by_fold),
        "n_folds_baseline": len(baseline_by_fold),
        "fold_count_match": fold_count_match,
    }
    if not fold_count_match:
        result["status"] = "not_comparable"
        result["reason"] = "fold_sets_differ"
        # A mean over an unmatched subset would misrepresent the comparison.
        result["mean_difference"] = None
    elif len(differences) != len(procedure_by_fold):
        result["status"] = "not_comparable"
        result["reason"] = "non_finite_matched_scores"
        result["mean_difference"] = None
    return result


def _failure_summary(
    validation: str,
    tuning_rows: list[dict[str, Any]],
    leaderboard_by_key: dict[tuple[str, str], dict[str, Any]],
    validation_summary_by: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    inner = [
        {
            "outer_fold": row.get("outer_fold"),
            "selection_scope": row.get("selection_scope"),
            "model": row.get("model"),
            "candidate": row.get("candidate"),
            "error": row.get("error"),
        }
        for row in tuning_rows
        if row.get("validation") == validation and row.get("status") == "failed"
    ]
    outer = [
        {"model": row.get("model"), "error": row.get("error")}
        for (candidate_validation, _model), row in leaderboard_by_key.items()
        if candidate_validation == validation and row.get("status") == "failed"
    ]
    procedure_entry = validation_summary_by.get(validation, {})
    validation_failed = procedure_entry.get("status") == "failed"
    procedure = (
        [{"error": procedure_entry.get("error", "")}] if validation_failed else []
    )
    return {
        "inner_candidate": {
            "count": len(inner),
            "examples": inner[:5],
            "evidence": "parameter_search.csv",
            "note": "Inner-search candidate failures, not whole-model failures.",
        },
        "outer_model_validation": {
            "count": len(outer),
            "examples": outer[:5],
            "evidence": "model_comparison.csv",
            "note": "A selected model family failed on this validation at outer evaluation.",
        },
        "validation_procedure": {
            "count": len(procedure),
            "examples": procedure,
            "evidence": "validation_summary.csv",
            "note": "The whole validation/selection procedure failed.",
        },
    }


def build_interpretation(
    *,
    config,
    procedure_results: dict[str, tuple[dict[str, float], pd.DataFrame, pd.DataFrame]],
    combo_folds: dict[tuple[str, str], list[dict[str, Any]]],
    tuning_rows: list[dict[str, Any]],
    leaderboard: pd.DataFrame,
    validation_summary: pd.DataFrame,
) -> dict[str, Any]:
    """Aggregate already-computed evidence into per-validation summaries."""
    metric = config.resolved_selection_metric()
    direction = metric_direction(metric)
    selected_models = list(config.selected_models())
    baseline_selected = BASELINE_MODEL in selected_models
    validation_rows = validation_summary.to_dict("records") if not validation_summary.empty else []
    validation_summary_by = {str(row["validation"]): row for row in validation_rows}
    leaderboard_records = leaderboard.to_dict("records") if not leaderboard.empty else []
    leaderboard_by_key = {
        (str(row["validation"]), str(row["model"])): row for row in leaderboard_records
    }

    validations: dict[str, dict[str, Any]] = {}
    for validation in config.selected_validations():
        result = procedure_results.get(validation)
        procedure_status = "completed" if result is not None else "failed"
        if result is not None:
            _metrics, folds, _predictions = result
            metric_summaries = _metric_summaries(folds)
            baseline = _baseline_comparison(
                validation,
                metric,
                direction,
                baseline_selected,
                folds,
                combo_folds,
                leaderboard_by_key,
                procedure_status,
            )
        else:
            metric_summaries = {}
            baseline = _not_comparable("procedure_failed", metric, direction)
        summary_row = validation_summary_by.get(validation, {})
        validations[validation] = {
            "validation": validation,
            "role": str(summary_row.get("role", "")),
            "status": procedure_status,
            "n_folds": int(summary_row.get("n_folds", 0) or 0)
            if procedure_status == "completed"
            else 0,
            "metric_summaries": metric_summaries,
            "baseline_comparison": baseline,
            "failures": _failure_summary(
                validation, tuning_rows, leaderboard_by_key, validation_summary_by
            ),
        }

    completed = [name for name, entry in validations.items() if entry["status"] == "completed"]
    failed = [name for name, entry in validations.items() if entry["status"] != "completed"]
    total_inner = sum(entry["failures"]["inner_candidate"]["count"] for entry in validations.values())
    total_outer = sum(
        entry["failures"]["outer_model_validation"]["count"] for entry in validations.values()
    )
    total_procedure = sum(
        entry["failures"]["validation_procedure"]["count"] for entry in validations.values()
    )
    return {
        "schema_version": "1.0",
        "selection_metric": metric,
        "metric_direction": direction,
        "positive_means": POSITIVE_MEANS,
        "baseline_model": BASELINE_MODEL if baseline_selected else None,
        "primary_validation": config.resolved_primary_validation(),
        "overview": {
            "n_validations": len(validations),
            "n_completed": len(completed),
            "n_failed": len(failed),
            "completed_validations": completed,
            "failed_validations": failed,
        },
        "failures": {
            "inner_candidate": total_inner,
            "outer_model_validation": total_outer,
            "validation_procedure": total_procedure,
        },
        "validations": validations,
        "notes": [
            (
                "Interpretations describe already-selected fold evaluations, not the final "
                "full-data model's training score."
            ),
            "A positive difference means the procedure did better than the dummy baseline.",
            (
                "Fold standard deviations use ddof=0 and are descriptive, not confidence "
                "intervals or significance tests."
            ),
            (
                "Failures are separated into inner candidate, outer model+validation and whole "
                "validation levels and are traceable to the full result files."
            ),
        ],
    }


def _baseline_rows(interpretation: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for validation, entry in interpretation["validations"].items():
        comparison = entry["baseline_comparison"]
        if not comparison["per_fold"]:
            rows.append(
                {
                    "validation": validation,
                    "fold": None,
                    "procedure_model": None,
                    "metric": comparison["metric"],
                    "procedure_value": None,
                    "baseline_value": None,
                    "difference": None,
                    "direction": comparison["direction"],
                    "baseline_model": comparison["baseline_model"],
                    "status": comparison["status"],
                    "reason": comparison["reason"],
                }
            )
            continue
        for fold in comparison["per_fold"]:
            rows.append(
                {
                    "validation": validation,
                    "fold": fold["fold"],
                    "procedure_model": fold["procedure_model"],
                    "metric": comparison["metric"],
                    "procedure_value": fold["procedure_value"],
                    "baseline_value": fold["baseline_value"],
                    "difference": fold["difference"],
                    "direction": comparison["direction"],
                    "baseline_model": comparison["baseline_model"],
                    "status": comparison["status"],
                    "reason": comparison["reason"],
                }
            )
    return rows


def _number_text(value: Any) -> str:
    return "—" if value is None else f"{value:.6g}"


def _markdown(interpretation: dict[str, Any]) -> str:
    lines = ["# Result interpretation / 结果解读", ""]
    lines.append(
        "Descriptive summary of already-selected fold evaluations. "
        "Positive difference = procedure better than the dummy baseline. "
        "Descriptive fold SD (ddof=0); not a significance test. / "
        "已选折评估的描述性汇总；差值正值表示优于 dummy 基线；折间标准差（ddof=0）为描述性，不作显著性。"
    )
    lines.append("")
    overview = interpretation["overview"]
    lines.append(
        f"- Validations: {overview['n_completed']}/{overview['n_validations']} completed "
        f"(failed: {', '.join(overview['failed_validations']) or 'none'})"
    )
    lines.append(
        f"- Failures: inner candidates {interpretation['failures']['inner_candidate']}, "
        f"outer model+validation {interpretation['failures']['outer_model_validation']}, "
        f"validation procedures {interpretation['failures']['validation_procedure']}"
    )
    lines.append("")
    for validation, entry in interpretation["validations"].items():
        lines.append(f"## {validation} ({entry['status']})")
        lines.append("")
        if entry["status"] != "completed":
            lines.append("- Selection procedure failed for this validation.")
            lines.append("")
            continue
        selection = entry["metric_summaries"].get(interpretation["selection_metric"])
        if selection is not None:
            lines.append(
                f"- Selection metric `{interpretation['selection_metric']}`: "
                f"mean {_number_text(selection['mean'])}, "
                f"std {_number_text(selection['std'])} (ddof=0), "
                f"n_folds {selection['n_folds']}, stability {selection['stability']}"
            )
        comparison = entry["baseline_comparison"]
        if comparison["status"] == "comparable":
            lines.append(
                f"- Baseline (`{comparison['baseline_model']}`): "
                f"mean difference {_number_text(comparison['mean_difference'])}, "
                f"paired folds {comparison['n_paired_folds']}/{comparison['n_folds_procedure']}"
            )
        else:
            lines.append(
                f"- Baseline comparison unavailable: {comparison['reason']}"
            )
        failures = entry["failures"]
        lines.append(
            f"- Failures: inner {failures['inner_candidate']['count']}, "
            f"outer {failures['outer_model_validation']['count']}, "
            f"validation {failures['validation_procedure']['count']}"
        )
        lines.append("")
    lines.append(
        "Full machine-readable details: `result_interpretation.json`; per-fold baseline "
        "values: `interpretation_baseline_differences.csv`."
    )
    return "\n".join(lines) + "\n"


INDEPENDENT_ARTIFACTS = {
    "result_interpretation": "result_interpretation.json",
    "interpretation_baseline_differences": "interpretation_baseline_differences.csv",
    "interpretation_summary": "result_interpretation.md",
}

# Full files that back each failure level, used as explicit evidence pointers.
INDEPENDENT_FAILURE_EVIDENCE = {
    "inner_candidate": "parameter_search.csv",
    "outer_model_validation": "model_comparison.csv",
    "validation_procedure": "validation_summary.csv",
}


def _failure_count(failures: Any, level: str) -> int | None:
    """Return a known count, or None (unavailable) when child evidence is absent."""
    entry = failures.get(level) if isinstance(failures, dict) else None
    if isinstance(entry, dict) and isinstance(entry.get("count"), (int, float)):
        return int(entry["count"])
    return None


def _aggregate_failure(validations: dict[str, dict[str, Any]], level: str) -> int | None:
    """Sum one failure level across children; None if any child's count is unknown."""
    values = [item["failures"].get(level) for item in validations.values()]
    if any(value is None for value in values):
        return None
    return int(sum(values))


def _independent_evidence(
    output_dir: Path | None, validation: str, status: Any
) -> dict[str, str]:
    """Return only evidence files that really exist; never invent a missing path."""
    if output_dir is None:
        return {}
    root = Path(output_dir)
    child = root / "validations" / validation
    evidence: dict[str, str] = {}
    for level, name in INDEPENDENT_FAILURE_EVIDENCE.items():
        if (child / name).is_file():
            evidence[level] = f"validations/{validation}/{name}"
    if status != "completed":
        if (root / "validation_summary.csv").is_file():
            evidence.setdefault("validation_procedure", "validation_summary.csv")
        if (child / "error.json").is_file():
            evidence["error"] = f"validations/{validation}/error.json"
    return evidence


def build_independent_interpretation(
    entries: dict[str, dict[str, Any]],
    results: dict[str, Any],
    output_dir: Path | None = None,
) -> dict[str, Any]:
    """Overview/index of peer validations. Never compares validations globally."""
    validations: dict[str, dict[str, Any]] = {}
    for validation, entry in entries.items():
        status = entry.get("status")
        child = results.get(validation)
        child_interpretation = getattr(child, "interpretation", None) or {}
        per_validation = (child_interpretation.get("validations") or {}).get(validation, {})
        baseline = per_validation.get("baseline_comparison", {})
        child_failures = per_validation.get("failures", {})
        completed = status == "completed" and bool(child_interpretation)
        artifacts: dict[str, str] = {}
        if completed and output_dir is not None:
            child_dir = Path(output_dir) / "validations" / validation
            artifacts = {
                key: f"validations/{validation}/{name}"
                for key, name in INDEPENDENT_ARTIFACTS.items()
                if (child_dir / name).is_file()
            }
        if completed:
            comparison = {
                "status": baseline.get("status", "not_available"),
                "reason": baseline.get("reason", ""),
                "mean_difference": baseline.get("mean_difference"),
                "n_paired_folds": int(baseline.get("n_paired_folds", 0) or 0),
            }
            failures = {
                "inner_candidate": _failure_count(child_failures, "inner_candidate"),
                "outer_model_validation": _failure_count(
                    child_failures, "outer_model_validation"
                ),
                "validation_procedure": _failure_count(
                    child_failures, "validation_procedure"
                ),
            }
            error = None
        else:
            # The child never produced evidence: keep its known error, count the
            # whole-procedure failure, and mark unknown levels unavailable (None).
            comparison = {
                "status": "not_comparable",
                "reason": "procedure_failed",
                "mean_difference": None,
                "n_paired_folds": 0,
            }
            failures = {
                "inner_candidate": None,
                "outer_model_validation": None,
                "validation_procedure": 1,
            }
            error = entry.get("error")
        validations[validation] = {
            "status": status,
            "role": "independent",
            "selection_metric": child_interpretation.get("selection_metric"),
            "n_folds": int(per_validation.get("n_folds", 0) or 0) if completed else 0,
            "error": error,
            "baseline_comparison": comparison,
            "failures": failures,
            "evidence": _independent_evidence(output_dir, validation, status),
            "artifacts": artifacts,
        }
    completed_names = [name for name, item in validations.items() if item["status"] == "completed"]
    failed_names = [name for name, item in validations.items() if item["status"] != "completed"]
    return {
        "schema_version": "1.0",
        "evaluation_scope": "independent_validations",
        "primary_validation": None,
        "overview": {
            "n_validations": len(validations),
            "n_completed": len(completed_names),
            "n_failed": len(failed_names),
            "completed_validations": completed_names,
            "failed_validations": failed_names,
        },
        "failures": {
            "inner_candidate": _aggregate_failure(validations, "inner_candidate"),
            "outer_model_validation": _aggregate_failure(
                validations, "outer_model_validation"
            ),
            "validation_procedure": _aggregate_failure(
                validations, "validation_procedure"
            ),
        },
        "validations": validations,
        "notes": [
            (
                "Each validation is summarised separately from its own folder; no global score, "
                "ranking or winner is produced."
            ),
            (
                "A failed validation keeps its recorded error; unknown inner/outer failure "
                "counts are null (unavailable), not zero."
            ),
        ],
    }


def write_independent_interpretation(
    output_dir: Path, interpretation: dict[str, Any]
) -> dict[str, str]:
    """Write the root overview/index for independent validations."""
    name = INDEPENDENT_ARTIFACTS["result_interpretation"]
    (Path(output_dir) / name).write_text(
        json.dumps(interpretation, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {"result_interpretation": name}


def write_interpretation_outputs(
    output_dir: Path, interpretation: dict[str, Any]
) -> dict[str, str]:
    """Persist the interpretation JSON, a per-fold CSV and a concise Markdown note."""
    output_dir = Path(output_dir)
    json_name = "result_interpretation.json"
    csv_name = "interpretation_baseline_differences.csv"
    md_name = "result_interpretation.md"
    (output_dir / json_name).write_text(
        json.dumps(interpretation, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    rows = _baseline_rows(interpretation)
    fieldnames = [
        "validation",
        "fold",
        "procedure_model",
        "metric",
        "procedure_value",
        "baseline_value",
        "difference",
        "direction",
        "baseline_model",
        "status",
        "reason",
    ]
    with (output_dir / csv_name).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    (output_dir / md_name).write_text(_markdown(interpretation), encoding="utf-8")
    return {
        "result_interpretation": json_name,
        "interpretation_baseline_differences": csv_name,
        "interpretation_summary": md_name,
    }
