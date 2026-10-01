"""Predeclared numerical and structural acceptance checks for the DSA case.

Compares the uninstrumented CLI result, the independent scikit-learn
recomputation and the observation-only supplemental run under the frozen
tolerances: exact split membership, exact winning family/parameters and hard
predictions, metrics within 1e-12, preprocessing statistics within
atol=rtol=1e-12 and probabilities within atol=1e-10/rtol=1e-8.

Balanced accuracy and macro-F1 are also recomputed from per-class TP/FN/FP
counts instead of trusting the exported metric columns. Differences are
retained in ``checks.json``; the process exits non-zero when any check fails.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import balanced_accuracy_score, confusion_matrix

if __package__ in {None, ""}:  # direct script execution
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from psyml.prediction import compatibility_check, load_model, predict_dataframe
from tools.cases import dsa_case

PROBABILITY_COLUMNS = tuple(f"probability_{label}" for label in range(1, 20))
REFERENCE_DIAGNOSTIC_COLUMNS = frozenset({"inner_scores"})
# Columns the reference-only inner_scores diagnostic actually reads. A missing
# entry fails the diagnostic explicitly instead of raising or passing vacuously.
DIAGNOSTIC_REQUIRED_COLUMNS = ("status", "score", "inner_scores")
# Production columns the direct confusion-count metric recomputation reads.
DIRECT_METRIC_DEPENDENCY_COLUMNS = ("fold", "accuracy", "balanced_accuracy", "f1_macro")
# Numeric columns that are legitimately empty when no problem occurred. Every
# other NaN (outside an explicitly failed candidate row) fails the comparison.
MAY_BE_EMPTY_NUMERIC_COLUMNS = frozenset({"error"})
# Fixed per-table column contracts from the frozen protocol and the expected
# artifact schemas. They deliberately do not depend on the production table's
# current columns: two tables missing the same critical column must still fail.
_REQUIRED_PREDICTION_COLUMNS = ("row_index", "fold", "observed", "predicted", "model")
REQUIRED_COLUMNS: dict[str, tuple[str, ...]] = {
    "predictions": _REQUIRED_PREDICTION_COLUMNS,
    "predictions_with_probabilities": (
        *_REQUIRED_PREDICTION_COLUMNS,
        *PROBABILITY_COLUMNS,
    ),
    "observed_oof_probabilities": (
        *_REQUIRED_PREDICTION_COLUMNS,
        *PROBABILITY_COLUMNS,
    ),
    "fold_metrics": (
        "fold",
        "model",
        "validation",
        "accuracy",
        "balanced_accuracy",
        "precision_weighted",
        "recall_weighted",
        "f1_weighted",
        "precision_macro",
        "recall_macro",
        "f1_macro",
        "roc_auc_ovr_weighted",
    ),
    "metrics": (
        "accuracy",
        "balanced_accuracy",
        "precision_weighted",
        "recall_weighted",
        "f1_weighted",
        "precision_macro",
        "recall_macro",
        "f1_macro",
        "roc_auc_ovr_weighted",
    ),
    "metrics_summary": ("metric", "mean", "std", "min", "max", "n_folds"),
    "selection_trace": (
        "validation",
        "outer_fold",
        "selection_scope",
        "model",
        "parameters",
        "score",
    ),
    "parameter_search": (
        "model",
        "validation",
        "outer_fold",
        "selection_scope",
        "candidate",
        "selection_metric",
        "score",
        "parameters",
        "status",
        "error",
    ),
}


def missing_required_columns(table: pd.DataFrame, table_name: str) -> list[str]:
    """Return the frozen required columns absent from ``table``.

    The contract is fixed per table name, so a framework-wide column loss that
    affects production and reference alike is still reported as a failure.
    """
    if table_name not in REQUIRED_COLUMNS:
        raise KeyError(f"No required-column contract is defined for table {table_name!r}")
    return [column for column in REQUIRED_COLUMNS[table_name] if column not in table.columns]


def max_abs_diff(left, right) -> float:
    """Maximum absolute difference over finite pairs; empty comparisons are 0."""
    first = np.asarray(left, dtype=float)
    second = np.asarray(right, dtype=float)
    finite = np.isfinite(first) & np.isfinite(second)
    if not finite.any():
        return 0.0
    return float(np.max(np.abs(first[finite] - second[finite])))


def compare_metric_tables(
    left: pd.DataFrame,
    right: pd.DataFrame,
    *,
    table_name: str,
    numeric_atol: float = dsa_case.METRIC_ATOL,
    reference_only_allowed: frozenset[str] = REFERENCE_DIAGNOSTIC_COLUMNS,
    may_be_empty_numeric: frozenset[str] = MAY_BE_EMPTY_NUMERIC_COLUMNS,
) -> dict[str, Any]:
    """Compare one production table against the reference without skipping anything.

    Required columns come from the fixed ``REQUIRED_COLUMNS`` contract for
    ``table_name``, checked on the production and the reference side
    separately, so a shared column loss fails too. Every production column must
    also exist in the reference and is actively compared; unregistered
    reference-only columns fail, as do row-count mismatches, one-sided NaN,
    NaN in a statistic that must be finite and any infinity. Values are
    compared within ``numeric_atol`` with ``rtol=0``.
    """
    production_missing = missing_required_columns(left, table_name)
    reference_missing = missing_required_columns(right, table_name)
    result: dict[str, Any] = {
        "table": table_name,
        "passed": True,
        "max_abs_numeric_difference": 0.0,
        "production_missing_required_columns": production_missing,
        "reference_missing_required_columns": reference_missing,
        "missing_reference_columns": [],
        "unexpected_reference_columns": [],
        "non_finite_problems": [],
    }
    if production_missing or reference_missing:
        result["passed"] = False
    missing = [column for column in left.columns if column not in right.columns]
    unexpected = [
        column
        for column in right.columns
        if column not in left.columns and column not in reference_only_allowed
    ]
    result["missing_reference_columns"] = missing
    result["unexpected_reference_columns"] = unexpected
    if missing or unexpected:
        result["passed"] = False
    if len(left) != len(right):
        result["passed"] = False
        result["row_counts"] = [len(left), len(right)]
        return result
    statuses = (
        right["status"].astype(str).to_numpy()
        if "status" in right.columns
        else np.full(len(right), "", dtype=object)
    )
    maximum = 0.0
    for column in left.columns:
        if column not in right.columns:
            continue
        left_column = left[column]
        right_column = right[column]
        left_numeric = pd.api.types.is_numeric_dtype(left_column)
        right_numeric = pd.api.types.is_numeric_dtype(right_column)
        if left_numeric != right_numeric:
            result["passed"] = False
            result["non_finite_problems"].append(
                f"{column}: dtype mismatch (production numeric={left_numeric}, "
                f"reference numeric={right_numeric})"
            )
            continue
        if not left_numeric:
            if left_column.fillna("").tolist() != right_column.fillna("").tolist():
                result["passed"] = False
            continue
        left_values = left_column.to_numpy(dtype=float)
        right_values = right_column.to_numpy(dtype=float)
        infinite = np.isinf(left_values) | np.isinf(right_values)
        if infinite.any():
            result["passed"] = False
            result["non_finite_problems"].append(
                f"{column}: infinite value at rows {np.flatnonzero(infinite).tolist()[:10]}"
            )
        left_nan = np.isnan(left_values)
        right_nan = np.isnan(right_values)
        one_sided = left_nan != right_nan
        if one_sided.any():
            result["passed"] = False
            result["non_finite_problems"].append(
                f"{column}: NaN on one side only at rows "
                f"{np.flatnonzero(one_sided).tolist()[:10]}"
            )
        both_nan = left_nan & right_nan
        if both_nan.any() and column not in may_be_empty_numeric:
            failed_rows = statuses == "failed"
            disallowed = both_nan & ~failed_rows
            if disallowed.any():
                result["passed"] = False
                result["non_finite_problems"].append(
                    f"{column}: NaN in a statistic that must be finite at rows "
                    f"{np.flatnonzero(disallowed).tolist()[:10]}"
                )
        finite = ~left_nan & ~right_nan
        if finite.any():
            differences = np.abs(left_values[finite] - right_values[finite])
            maximum = max(maximum, float(differences.max()))
            if bool((differences > numeric_atol).any()):
                result["passed"] = False
    result["max_abs_numeric_difference"] = maximum
    return result


def validate_reference_diagnostics(
    table: pd.DataFrame,
    *,
    expected_inner_folds: int,
    numeric_atol: float = dsa_case.METRIC_ATOL,
    table_name: str = "parameter_search",
) -> dict[str, Any]:
    """Validate the reference-only diagnostic column instead of skipping it.

    The function checks its actual dependency columns first; when any of them
    is absent it returns an explicit failure carrying the table name, the
    missing columns and the reason, and never fills defaults or returns a
    vacuous pass. Otherwise ``inner_scores`` must be a JSON list of
    ``expected_inner_folds`` finite numbers for every completed candidate, and
    its unweighted mean must equal the reported candidate score.
    """
    detail: dict[str, Any] = {"table": table_name, "checked_rows": 0, "problems": []}
    missing = [column for column in DIAGNOSTIC_REQUIRED_COLUMNS if column not in table.columns]
    if missing:
        detail["missing_required_columns"] = missing
        detail["reason"] = "diagnostic validation requires these reference columns"
        detail["problems"].append(f"missing required columns: {', '.join(missing)}")
        return {"passed": False, "detail": detail}
    for index, row in table.iterrows():
        if str(row.get("status")) != "completed":
            continue
        detail["checked_rows"] += 1
        try:
            values = json.loads(row["inner_scores"])
        except (TypeError, ValueError):
            detail["problems"].append(f"row {index}: inner_scores is not valid JSON")
            continue
        if not isinstance(values, list) or len(values) != expected_inner_folds:
            detail["problems"].append(
                f"row {index}: expected {expected_inner_folds} inner scores"
            )
            continue
        if not all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            for value in values
        ):
            detail["problems"].append(f"row {index}: non-finite inner score")
            continue
        mean = float(sum(values) / len(values))
        if abs(mean - float(row["score"])) > numeric_atol:
            detail["problems"].append(f"row {index}: mean {mean} != score {row['score']}")
    return {"passed": not detail["problems"], "detail": detail}


def direct_metrics(observed: Sequence, predicted: Sequence) -> dict[str, float]:
    """Recompute accuracy, balanced accuracy and macro-F1 from class counts."""
    observed = np.asarray(observed)
    predicted = np.asarray(predicted)
    recalls: list[float] = []
    f1_scores: list[float] = []
    for label in sorted(np.unique(observed)):
        true_positive = int(np.sum((observed == label) & (predicted == label)))
        false_negative = int(np.sum((observed == label) & (predicted != label)))
        false_positive = int(np.sum((observed != label) & (predicted == label)))
        recalls.append(true_positive / (true_positive + false_negative))
        denominator = 2 * true_positive + false_positive + false_negative
        f1_scores.append(2 * true_positive / denominator if denominator else 0.0)
    return {
        "accuracy": float(np.sum(observed == predicted)) / len(observed),
        "balanced_accuracy": float(np.mean(recalls)),
        "f1_macro": float(np.mean(f1_scores)),
    }


def _frames_equal_as_text(left: pd.DataFrame, right: pd.DataFrame) -> bool:
    if list(left.columns) != list(right.columns):
        return False
    if left.shape != right.shape:
        return False
    return left.fillna("").astype(str).equals(right.fillna("").astype(str))


def _sorted(frame: pd.DataFrame) -> pd.DataFrame:
    keys = [column for column in ("row_index", "fold") if column in frame.columns]
    if not keys:
        return frame.reset_index(drop=True)
    return frame.sort_values(keys).reset_index(drop=True)


def compare(
    config_path: str | Path,
    primary_dir: str | Path,
    reference_dir: str | Path,
    observed_dir: str | Path,
    output_dir: str | Path,
    *,
    golden_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Run every predeclared check and write ``checks.json``; return the payload."""
    config = dsa_case.load_case_config(config_path)
    primary = Path(primary_dir)
    reference = Path(reference_dir)
    observed = Path(observed_dir)
    golden = Path(golden_dir) if golden_dir is not None else None
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=False)

    numerical: list[dict[str, Any]] = []
    structural: list[dict[str, Any]] = []
    extended: list[dict[str, Any]] = []
    golden_checks: list[dict[str, Any]] = []

    def check(bucket: list[dict[str, Any]], name: str, passed: bool, detail=None) -> None:
        bucket.append({"name": name, "pass": bool(passed), "detail": detail})

    frame = pd.read_csv(config["input_path"])
    features = frame[config["feature_columns"]]

    for name in ("predictions", "fold_metrics", "selection_trace", "parameter_search", "metrics_summary"):
        left = pd.read_csv(primary / f"{name}.csv")
        right = pd.read_csv(observed / "run" / f"{name}.csv")
        primary_missing = missing_required_columns(left, name)
        observed_missing = missing_required_columns(right, name)
        check(
            numerical,
            f"observational_run_equals_primary_{name}",
            not primary_missing and not observed_missing and left.equals(right),
            {
                "table": name,
                "primary_missing_required_columns": primary_missing,
                "observed_missing_required_columns": observed_missing,
            },
        )

    reference_splits = dsa_case.read_json(reference / "fold_membership.json")
    observed_splits = dsa_case.read_json(observed / "fold_membership.json")
    check(
        numerical,
        "independent_fold_membership_exact",
        reference_splits == observed_splits,
        {"unique_plans": len(reference_splits)},
    )

    leaks = []
    for key, entry in observed_splits.items():
        for fold_index, fold in enumerate(entry["folds"], start=1):
            if set(fold["train_groups"]) & set(fold["test_groups"]):
                leaks.append([key, fold_index])
    check(numerical, "all_outer_inner_and_final_groups_disjoint", not leaks, leaks)

    reference_fits = dsa_case.read_json(reference / "fit_audit.json")
    observed_fits = dsa_case.read_json(observed / "fit_audit.json")
    check(
        numerical,
        "fit_count",
        len(reference_fits) == len(observed_fits) == 54,
        {"reference": len(reference_fits), "observed": len(observed_fits)},
    )
    stat_columns = ["imputer_statistics", "scaler_mean", "scaler_var", "scaler_scale"]
    parameter_columns = ["coef", "intercept"]
    metadata_columns = [
        "family",
        "overrides",
        "train_rows",
        "feature_names",
        "scaler_n_samples_seen",
        "classes",
        "effective_parameters",
        "n_iter",
    ]
    metadata_ok = True
    stats_ok = True
    parameters_ok = True
    max_stats = 0.0
    max_parameters = 0.0
    for left, right in zip(reference_fits, observed_fits):
        metadata_ok &= all(left[column] == right[column] for column in metadata_columns)
        for column in stat_columns:
            left_values = np.asarray(left[column])
            right_values = np.asarray(right[column])
            stats_ok &= np.allclose(
                left_values, right_values, rtol=dsa_case.PREPROCESS_RTOL, atol=dsa_case.PREPROCESS_ATOL
            )
            max_stats = max(max_stats, max_abs_diff(left_values, right_values))
        for column in parameter_columns:
            left_values = np.asarray(left[column])
            right_values = np.asarray(right[column])
            parameters_ok &= np.array_equal(left_values, right_values)
            max_parameters = max(max_parameters, max_abs_diff(left_values, right_values))
    check(numerical, "all_fit_row_ids_families_parameters_classes_exact", metadata_ok)
    check(
        numerical,
        "all_training_fold_preprocessing_statistics",
        stats_ok,
        {"max_abs_difference": max_stats, "atol": 1e-12, "rtol": 1e-12},
    )
    direct_stats_ok = True
    direct_max = 0.0
    for record in observed_fits:
        training = features.loc[record["train_rows"]].to_numpy()
        for column, expected in (
            ("imputer_statistics", np.median(training, axis=0)),
            ("scaler_mean", np.mean(training, axis=0)),
            ("scaler_var", np.var(training, axis=0, ddof=0)),
        ):
            actual = np.asarray(record[column])
            direct_stats_ok &= np.allclose(
                actual, expected, atol=dsa_case.PREPROCESS_ATOL, rtol=dsa_case.PREPROCESS_RTOL
            )
            direct_max = max(direct_max, max_abs_diff(actual, expected))
    check(
        numerical,
        "preprocessing_matches_direct_training_row_math",
        direct_stats_ok,
        {"max_abs_difference": direct_max, "atol": 1e-12, "rtol": 1e-12},
    )
    check(
        numerical,
        "all_fitted_coefficients_intercepts_exact",
        parameters_ok,
        {"max_abs_difference": max_parameters},
    )

    primary_predictions = _sorted(pd.read_csv(primary / "predictions.csv"))
    reference_predictions = _sorted(pd.read_csv(reference / "predictions_with_probabilities.csv"))
    observed_predictions = _sorted(pd.read_csv(observed / "observed_oof_probabilities.csv"))
    primary_predictions_missing = missing_required_columns(primary_predictions, "predictions")
    reference_predictions_missing = missing_required_columns(
        reference_predictions, "predictions_with_probabilities"
    )
    observed_predictions_missing = missing_required_columns(
        observed_predictions, "observed_oof_probabilities"
    )
    check(
        numerical,
        "each_original_row_has_exactly_one_oof_prediction",
        not primary_predictions_missing
        and len(primary_predictions) == len(frame)
        and primary_predictions["row_index"].nunique() == len(frame)
        and set(primary_predictions["row_index"]) == set(frame.index),
        {"table": "predictions", "production_missing_required_columns": primary_predictions_missing},
    )
    identity_columns = ["row_index", "fold", "observed", "predicted", "model"]
    check(
        numerical,
        "oof_predictions_fold_observed_family_exact",
        not primary_predictions_missing
        and not reference_predictions_missing
        and primary_predictions[identity_columns].equals(reference_predictions[identity_columns]),
        {
            "primary_missing_required_columns": primary_predictions_missing,
            "reference_missing_required_columns": reference_predictions_missing,
        },
    )
    probability_columns_missing = [
        column
        for column in PROBABILITY_COLUMNS
        if column not in reference_predictions.columns or column not in observed_predictions.columns
    ]
    reference_tail_ok = (
        len(reference_predictions.columns) == 5 + len(PROBABILITY_COLUMNS)
        and list(reference_predictions.columns)[5:] == list(PROBABILITY_COLUMNS)
    )
    observed_tail_ok = (
        len(observed_predictions.columns) == 5 + len(PROBABILITY_COLUMNS)
        and list(observed_predictions.columns)[5:] == list(PROBABILITY_COLUMNS)
    )
    probability_detail: dict[str, Any] = {
        "reference_missing_required_columns": reference_predictions_missing,
        "observed_missing_required_columns": observed_predictions_missing,
        "missing_probability_columns": probability_columns_missing,
        "reference_probability_order_ok": reference_tail_ok,
        "observed_probability_order_ok": observed_tail_ok,
    }
    probability_required_missing = bool(
        reference_predictions_missing or observed_predictions_missing
    )
    if (
        probability_columns_missing
        or probability_required_missing
        or not reference_tail_ok
        or not observed_tail_ok
    ):
        check(numerical, "oof_probabilities", False, probability_detail)
    else:
        check(
            numerical,
            "oof_probabilities",
            np.allclose(
                reference_predictions[list(PROBABILITY_COLUMNS)],
                observed_predictions[list(PROBABILITY_COLUMNS)],
                rtol=dsa_case.PROBABILITY_RTOL,
                atol=dsa_case.PROBABILITY_ATOL,
            ),
            {
                **probability_detail,
                "max_abs_difference": max_abs_diff(
                    reference_predictions[list(PROBABILITY_COLUMNS)].to_numpy(),
                    observed_predictions[list(PROBABILITY_COLUMNS)].to_numpy(),
                ),
                "atol": 1e-10,
                "rtol": 1e-8,
            },
        )

    for name in ("fold_metrics", "metrics_summary", "selection_trace", "parameter_search"):
        left = pd.read_csv(primary / f"{name}.csv")
        right = pd.read_csv(reference / f"{name}.csv")
        comparison = compare_metric_tables(left, right, table_name=name)
        detail: dict[str, Any] = {
            "table": name,
            "max_abs_numeric_difference": comparison["max_abs_numeric_difference"],
            "atol": dsa_case.METRIC_ATOL,
            "production_missing_required_columns": comparison[
                "production_missing_required_columns"
            ],
            "reference_missing_required_columns": comparison[
                "reference_missing_required_columns"
            ],
            "missing_reference_columns": comparison["missing_reference_columns"],
            "unexpected_reference_columns": comparison["unexpected_reference_columns"],
        }
        if comparison.get("row_counts"):
            detail["row_counts"] = comparison["row_counts"]
        passed = comparison["passed"]
        if name == "parameter_search":
            diagnostics = validate_reference_diagnostics(
                right,
                expected_inner_folds=int(config["inner_splits"]),
                table_name="parameter_search",
            )
            passed = passed and diagnostics["passed"]
            detail["reference_diagnostics"] = diagnostics
        check(
            numerical,
            f"independent_{name}_match",
            passed,
            detail,
        )

    # Structural checks: every partition is group-isolated, covers the source
    # rows exactly once per level, keeps all 19 classes, and inner scopes are
    # strict subsets of the corresponding outer training folds.
    partition_ok = True
    classes_ok = True
    inner_scope_ok = True
    accessed: set[int] = set()
    for key, entry in observed_splits.items():
        covered: set[int] = set()
        for fold in entry["folds"]:
            train_rows = set(fold["train_rows"])
            test_rows = set(fold["test_rows"])
            if train_rows & test_rows:
                partition_ok = False
            covered |= test_rows
            partition_ok &= set(fold["train_groups"]).isdisjoint(set(fold["test_groups"]))
            for rows in (fold["train_rows"], fold["test_rows"]):
                classes_ok &= set(frame.loc[rows, config["target_column"]].unique()) == set(
                    range(1, 20)
                )
        if entry["strategy"] == "group_k_fold":
            if covered != set(entry["input_rows"]):
                partition_ok = False
            accessed |= covered
        elif covered != set(entry["input_rows"]):
            partition_ok = False
    partition_ok &= accessed == set(frame.index)
    outer_entries = [entry for entry in observed_splits.values() if entry["strategy"] == "group_k_fold"]
    inner_entries = [
        entry for entry in observed_splits.values() if entry["strategy"] == "stratified_group_k_fold"
    ]
    outer_fold_rows = {
        fold_number: set(fold["train_rows"])
        for entry in outer_entries
        for fold_number, fold in enumerate(entry["folds"], start=1)
    }
    for entry in inner_entries:
        fold_number = entry["random_seed"] - int(config["random_seed"]) or 0
        if fold_number == 0:
            inner_scope_ok &= set(entry["input_rows"]) == set(frame.index)
        elif fold_number in outer_fold_rows:
            inner_scope_ok &= set(entry["input_rows"]) == outer_fold_rows[fold_number]
        else:
            inner_scope_ok = False
    role_columns = {"segment_id", config["target_column"], config["group_column"]}
    role_ok = not (set(config["feature_columns"]) & role_columns)
    role_ok &= list(features.columns) == list(config["feature_columns"])
    structural.append({"name": "all_partitions_disjoint_cover_source", "pass": bool(partition_ok), "detail": None})
    structural.append(
        {
            "name": "all_train_and_validation_partitions_have_19_classes",
            "pass": bool(classes_ok),
            "detail": None,
        }
    )
    structural.append(
        {
            "name": "every_inner_scope_is_corresponding_outer_training_rows",
            "pass": bool(inner_scope_ok),
            "detail": None,
        }
    )
    structural.append(
        {
            "name": "role_columns_excluded_from_features",
            "pass": bool(role_ok),
            "detail": None,
        }
    )

    result = json.loads((primary / "result.json").read_text(encoding="utf-8"))
    model_path = primary / result["model_export"]["model_path"]
    reference_model = joblib.load(reference / "final_model.joblib")
    loaded = load_model(model_path, trusted=True)
    replay, _added = predict_dataframe(loaded, frame)
    replay.to_csv(output / "saved_pipeline_replay.csv", index=False)
    reference_probabilities = [
        f"probability_{label}" for label in reference_model.classes_
    ]
    check(
        numerical,
        "saved_pipeline_replay_class_equality",
        np.array_equal(replay["predicted_class"], reference_model.predict(features)),
    )
    check(
        numerical,
        "saved_pipeline_replay_probabilities",
        np.allclose(
            replay[reference_probabilities],
            reference_model.predict_proba(features),
            atol=1e-10,
            rtol=1e-8,
        ),
        {
            "max_abs_difference": max_abs_diff(
                replay[reference_probabilities].to_numpy(),
                reference_model.predict_proba(features),
            ),
            "scope": "same input rows; persistence check only, not external validation",
        },
    )
    reversed_frame = frame[frame.columns[::-1]]
    reversed_replay, _added = predict_dataframe(loaded, reversed_frame)
    check(
        numerical,
        "saved_pipeline_column_reordering",
        np.array_equal(reversed_replay["predicted_class"], replay["predicted_class"]),
    )
    missing = compatibility_check(
        loaded, frame.drop(columns=[config["feature_columns"][0]])
    )
    check(numerical, "saved_pipeline_missing_feature_blocked", not missing["compatible"], missing)

    predictions_complete = not primary_predictions_missing
    if not predictions_complete:
        for blocked_name in (
            "metrics_match_direct_confusion_count_definitions",
            "pooled_oof_confusion_matrix_exact",
        ):
            check(
                numerical,
                blocked_name,
                False,
                {
                    "blocked_by_missing_required_columns": primary_predictions_missing,
                    "table": "predictions / fold_metrics",
                },
            )
    else:
        joined = primary_predictions.merge(
            frame.reset_index(names="row_index")[["row_index", "segment_id", "subject_id"]],
            on="row_index",
            validate="one_to_one",
        )
        joined.to_csv(output / "oof_predictions_by_segment.csv", index=False)
        per_subject = [
            {
                "subject_id": int(subject),
                "n_segments": len(rows),
                "balanced_accuracy": float(
                    balanced_accuracy_score(rows["observed"], rows["predicted"])
                ),
            }
            for subject, rows in joined.groupby("subject_id")
        ]
        pd.DataFrame(per_subject).to_csv(output / "per_subject_metrics.csv", index=False)
        dummy = pd.read_csv(reference / "dummy_oof.csv")
        differences = []
        for fold, rows in joined.groupby("fold"):
            fold_dummy = dummy[dummy["fold"] == fold]
            procedure_score = float(balanced_accuracy_score(rows["observed"], rows["predicted"]))
            dummy_score = float(
                balanced_accuracy_score(fold_dummy["observed"], fold_dummy["predicted"])
            )
            differences.append(
                {
                    "fold": int(fold),
                    "procedure_balanced_accuracy": procedure_score,
                    "dummy_balanced_accuracy": dummy_score,
                    "difference": procedure_score - dummy_score,
                }
            )
        pd.DataFrame(differences).to_csv(output / "paired_dummy_differences.csv", index=False)

        fold_metrics_frame = pd.read_csv(primary / "fold_metrics.csv")
        math_dependencies_missing = [
            column
            for column in DIRECT_METRIC_DEPENDENCY_COLUMNS
            if column not in fold_metrics_frame.columns
        ]
        if math_dependencies_missing:
            check(
                numerical,
                "metrics_match_direct_confusion_count_definitions",
                False,
                {
                    "table": "fold_metrics",
                    "missing_required_columns": math_dependencies_missing,
                    "reason": "direct metric recomputation requires these production columns",
                    "atol": 1e-12,
                },
            )
        else:
            math_ok = True
            for fold, rows in primary_predictions.groupby("fold"):
                direct = direct_metrics(
                    rows["observed"].to_numpy(), rows["predicted"].to_numpy()
                )
                expected = fold_metrics_frame[fold_metrics_frame["fold"] == fold].iloc[0]
                math_ok &= all(
                    abs(direct[name] - float(expected[name])) <= 1e-12 for name in direct
                )
            check(
                numerical,
                "metrics_match_direct_confusion_count_definitions",
                math_ok,
                {
                    "definitions": (
                        "BA=mean class TP/(TP+FN); macroF1=mean 2TP/(2TP+FP+FN); "
                        "accuracy=correct/N"
                    ),
                    "atol": 1e-12,
                },
            )
        primary_matrix = pd.read_csv(primary / "confusion_matrix.csv", index_col=0)
        check(
            numerical,
            "pooled_oof_confusion_matrix_exact",
            np.array_equal(
                primary_matrix.to_numpy(),
                confusion_matrix(
                    primary_predictions["observed"], primary_predictions["predicted"]
                ),
            ),
        )
    check(
        numerical,
        "source_input_csv_matches_frozen_hash",
        dsa_case.sha256_file(config["input_path"]) == dsa_case.DERIVED_CSV_SHA256,
    )

    # Extended checks: exported probability columns follow the fitted classes_,
    # and the saved pipeline metadata matches the independent final model.
    probability_ok = list(reference_predictions.columns)[5:] == list(PROBABILITY_COLUMNS)
    probability_ok &= loaded.metadata.get("n_features") == len(config["feature_columns"])
    metadata_classes = loaded.metadata.get("classes")
    metadata_ok = (
        metadata_classes is not None
        and list(metadata_classes) == list(reference_model.classes_)
    )
    extended.append(
        {
            "name": "probability_columns_follow_model_classes",
            "pass": bool(probability_ok),
            "detail": {"probability_columns": list(PROBABILITY_COLUMNS[:3]) + ["..."], "n_features": loaded.metadata.get("n_features")},
        }
    )
    extended.append(
        {
            "name": "saved_pipeline_metadata_matches_reference",
            "pass": bool(metadata_ok),
            "detail": {"model_name": loaded.metadata.get("model_name")},
        }
    )

    if golden is not None:
        golden_predictions = _sorted(pd.read_csv(golden / "predictions.csv"))
        golden_predictions_missing = [
            column for column in REQUIRED_COLUMNS["predictions"] if column not in golden_predictions.columns
        ]
        check(
            golden_checks,
            "golden_oof_predictions_exact",
            not primary_predictions_missing
            and not golden_predictions_missing
            and primary_predictions[identity_columns].equals(
                golden_predictions[identity_columns]
            ),
            {
                "primary_missing_required_columns": primary_predictions_missing,
                "golden_missing_required_columns": golden_predictions_missing,
            },
        )
        golden_pairs = (
            ("metrics.csv", pd.read_csv(golden / "metrics.csv")),
            ("fold_metrics.csv", pd.read_csv(golden / "fold_metrics.csv")),
            ("metrics_summary.csv", pd.read_csv(golden / "metrics_summary.csv")),
            ("selection_trace.csv", pd.read_csv(golden / "selection_trace.csv")),
            ("parameter_search.csv", pd.read_csv(golden / "parameter_search.csv")),
        )
        golden_ok = True
        golden_differences: dict[str, float] = {}
        golden_missing_required: dict[str, list[str]] = {}
        for name, golden_frame in golden_pairs:
            table_name = name.removesuffix(".csv")
            current = pd.read_csv(primary / name)
            current_missing = missing_required_columns(current, table_name)
            golden_missing = missing_required_columns(golden_frame, table_name)
            if current_missing or golden_missing:
                golden_ok = False
                golden_missing_required[name] = {
                    "primary": current_missing,
                    "golden": golden_missing,
                }
                continue
            for column in current.columns:
                if column not in golden_frame.columns:
                    continue
                if pd.api.types.is_numeric_dtype(current[column]):
                    golden_ok &= bool(
                        np.allclose(
                            current[column],
                            golden_frame[column],
                            atol=1e-12,
                            rtol=0,
                            equal_nan=True,
                        )
                    )
                    golden_differences[f"{name}:{column}"] = max_abs_diff(
                        current[column], golden_frame[column]
                    )
                else:
                    golden_ok &= (
                        current[column].fillna("").tolist()
                        == golden_frame[column].fillna("").tolist()
                    )
        check(
            golden_checks,
            "golden_metrics_match",
            golden_ok,
            {
                "max_abs_difference": max(golden_differences.values(), default=0.0),
                "atol": 1e-12,
                "missing_required_columns": golden_missing_required,
                "scope": (
                    "frozen baseline recorded on Linux; cross-platform float differences "
                    "must be reported, never hidden"
                ),
            },
        )

    payload = {
        "passed": all(
            item["pass"]
            for bucket in (numerical, structural, extended, golden_checks)
            for item in bucket
        ),
        "counts": {
            "numerical": len(numerical),
            "structural": len(structural),
            "extended": len(extended),
            "golden": len(golden_checks),
        },
        "checks": numerical + structural + extended + golden_checks,
        "scope": (
            "Same-environment software conformance under the frozen tolerances; "
            "not external validation."
        ),
    }
    dsa_case.write_json(output / "checks.json", payload)
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--observed", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--golden",
        type=Path,
        default=None,
        help="Optional frozen primary result directory for exact golden comparison",
    )
    args = parser.parse_args(argv)
    payload = compare(
        args.config,
        args.primary,
        args.reference,
        args.observed,
        args.output,
        golden_dir=args.golden,
    )
    failures = [item for item in payload["checks"] if not item["pass"]]
    print(
        json.dumps(
            {"passed": payload["passed"], "counts": payload["counts"], "failures": failures},
            indent=2,
        )
    )
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
