"""Engineering leakage/robustness controls for the public DSA case.

These are diagnostic controls, not a second performance study and never a
source of model selection:

1. An ordinary ``StratifiedKFold`` row split is audited by a supplemental group
   auditor. PsyML itself warns rather than hard-blocking ordinary k-fold, so the
   finding is attributed to the auditor, not claimed as a product safeguard.
2. Only the fixed outer fold-1 test participants receive a rotated ``activity``
   label. Inner scores, selection, per-fit training statistics and test
   predictions/probabilities must not change. The rotation is not claimed to
   leave other outer folds or the final full-data model unchanged.
3. Only the outer fold-1 test features are shifted by +1000. Training statistics
   and inner selection must not change; predictions may change.
4. One within-subject shuffled-label canary (one shared
   ``default_rng(20261002)`` over ascending ``subject_id``) runs the complete
   nested protocol through PsyML and through this repository's independent
   reference. A mean balanced accuracy above 0.10 triggers investigation. One
   shuffled run is an engineering canary only: it is not a formal permutation
   test, not a false-positive-rate estimate and not proof that no leakage exists.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import warnings
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import balanced_accuracy_score
from sklearn.model_selection import StratifiedKFold

if __package__ in {None, ""}:  # direct script execution
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from psyml import runner
from psyml.protocol import load_config
from tools.cases import compare_dsa, dsa_case, reference_dsa

PERTURBATION_CONDITIONS = ("baseline", "outer_labels_rotated", "outer_features_plus1000")


def build_shuffled_labels_csv(
    source_path: str | Path,
    target_path: str | Path,
    *,
    target_column: str,
    group_column: str,
    seed: int = dsa_case.PLACEBO_SEED,
) -> str:
    """Permute labels within each subject, ascending, with one shared RNG state."""
    source = Path(source_path)
    with source.open(newline="") as handle:
        records = list(csv.reader(handle))
    header, rows = records[0], records[1:]
    subject_index = header.index(group_column)
    target_index = header.index(target_column)
    rng = np.random.default_rng(seed)
    for subject in sorted({int(row[subject_index]) for row in rows}):
        positions = [index for index, row in enumerate(rows) if int(row[subject_index]) == subject]
        permuted = rng.permutation([int(rows[index][target_index]) for index in positions])
        for index, value in zip(positions, permuted):
            rows[index][target_index] = str(value)
    with Path(target_path).open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)
    return dsa_case.sha256_file(target_path)


def shuffled_labels_change_only_target(
    source_path: str | Path, shuffled_path: str | Path, *, target_column: str
) -> bool:
    """Assert every non-target field and the row order are byte-identical."""
    with Path(source_path).open(newline="") as handle:
        source = list(csv.reader(handle))
    with Path(shuffled_path).open(newline="") as handle:
        shuffled = list(csv.reader(handle))
    if len(source) != len(shuffled) or source[0] != shuffled[0]:
        return False
    target_index = source[0].index(target_column)
    for original, permuted in zip(source[1:], shuffled[1:]):
        if len(original) != len(permuted):
            return False
        for index, (left, right) in enumerate(zip(original, permuted)):
            if index != target_index and left != right:
                return False
    return True


def _run_fold1_condition(
    config, frame: pd.DataFrame
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], np.ndarray, np.ndarray]:
    """Recompute only the outer fold-1 selection/fit path under one perturbation."""
    features, target, groups, _dropped = runner._prepare_data(config, frame)
    work, _total = runner._make_work_items(config, features, target, groups)
    fold_work = [item for item in work if item.fold_number == 1]
    if not fold_work:
        raise RuntimeError("No outer fold-1 work items were produced")
    test_index = fold_work[0].test_index
    tune: list[dict[str, Any]] = []
    models: dict[str, Any] = {}
    fit_records: list[dict[str, Any]] = []
    original_build = runner._build_pipeline
    retained: list[tuple[Any, pd.DataFrame, str, dict[str, Any]]] = []

    def build(*args, **kwargs):
        model = original_build(*args, **kwargs)
        retained.append((model, args[1].copy(), args[2], dict(args[3])))
        return model

    runner._build_pipeline = build
    try:
        for item in fold_work:
            train_index = item.train_index
            params = runner._choose_parameters(
                config,
                item,
                features.iloc[train_index],
                target.iloc[train_index],
                runner._ProgressTracker(100, None),
                tune,
                groups.iloc[train_index],
            )
            model = runner._build_pipeline(
                config,
                features.iloc[train_index],
                item.model_name,
                params,
                target.iloc[train_index],
                groups.iloc[train_index],
            )
            model.fit(features.iloc[train_index], target.iloc[train_index])
            models[item.model_name] = model
    finally:
        runner._build_pipeline = original_build
    winner = runner._inner_winner(tune, config.resolved_selection_metric())
    winner_model = models[winner["model"]]
    predictions = winner_model.predict(features.iloc[test_index])
    probabilities = winner_model.predict_proba(features.iloc[test_index])
    for model, training, family, params in retained:
        numeric = model.named_steps["preprocess"].named_transformers_["numeric"]
        fit_records.append(
            {
                "train_rows": training.index.tolist(),
                "family": family,
                "params": params,
                "imputer": numeric.named_steps["impute"].statistics_.tolist(),
                "mean": numeric.named_steps["scale"].mean_.tolist(),
                "var": numeric.named_steps["scale"].var_.tolist(),
                "n_samples_seen": int(numeric.named_steps["scale"].n_samples_seen_),
            }
        )
    details = {
        "winner": {key: winner[key] for key in ("model", "parameters", "score")},
        "fit_count": len(fit_records),
        "test_subjects": sorted(groups.iloc[test_index].unique().tolist()),
        "balanced_accuracy": float(
            balanced_accuracy_score(target.iloc[test_index], predictions)
        ),
    }
    return tune, fit_records, details, predictions, probabilities


def _compare_tables(
    left_path: Path,
    right_path: Path,
    *,
    table_name: str,
    numeric_atol: float = dsa_case.METRIC_ATOL,
) -> dict[str, Any]:
    """Compare with the shared no-masking policy used by the acceptance comparator."""
    return compare_dsa.compare_metric_tables(
        pd.read_csv(left_path),
        pd.read_csv(right_path),
        table_name=table_name,
        numeric_atol=numeric_atol,
    )


def run_controls(
    config_path: str | Path, output_dir: str | Path, *, alarm_threshold: float = dsa_case.PLACEBO_ALARM_THRESHOLD
) -> dict[str, Any]:
    """Execute every control and write ``checks.json`` plus its evidence files."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=False)
    config = load_config(config_path)
    raw_frame = pd.read_csv(config.input_path)
    input_sha256 = dsa_case.sha256_file(config.input_path)
    checks: list[dict[str, Any]] = []
    details: dict[str, Any] = {}

    def check(name: str, passed: bool, detail=None, bucket: str = "fold_controls") -> None:
        checks.append({"name": name, "pass": bool(passed), "detail": detail, "group": bucket})

    # 1. Supplemental group auditor against an ordinary row split.
    ordinary = list(
        StratifiedKFold(
            n_splits=4, shuffle=True, random_state=config.random_seed
        ).split(raw_frame[config.feature_columns], raw_frame[config.target_column])
    )
    overlaps = [
        sorted(
            set(raw_frame[config.group_column].iloc[train])
            & set(raw_frame[config.group_column].iloc[test])
        )
        for train, test in ordinary
    ]
    check(
        "ordinary_row_split_rejected_by_group_auditor",
        all(bool(fold) for fold in overlaps),
        {"subject_overlap_per_fold": overlaps},
        bucket="group_audit",
    )

    # 2 and 3. Fixed outer fold-1 label rotation and feature shift.
    prepared_features, prepared_target, prepared_groups, _dropped = runner._prepare_data(
        config, raw_frame
    )
    work, _total = runner._make_work_items(
        config, prepared_features, prepared_target, prepared_groups
    )
    fold_work = [item for item in work if item.fold_number == 1]
    if not fold_work:
        raise RuntimeError("No outer fold-1 work items were produced")
    test_positions = fold_work[0].test_index
    test_labels = raw_frame.index[test_positions]
    traces: dict[str, list[dict[str, Any]]] = {}
    states: dict[str, list[dict[str, Any]]] = {}
    predictions: dict[str, np.ndarray] = {}
    probabilities: dict[str, np.ndarray] = {}
    for condition in PERTURBATION_CONDITIONS:
        frame = raw_frame.copy()
        if condition == "outer_labels_rotated":
            frame.loc[test_labels, config.target_column] = (
                frame.loc[test_labels, config.target_column] % 19 + 1
            )
        if condition == "outer_features_plus1000":
            frame.loc[test_labels, config.feature_columns] = (
                frame.loc[test_labels, config.feature_columns] + 1000.0
            )
        tune, fit_records, condition_details, predicted, probability = _run_fold1_condition(
            config, frame
        )
        traces[condition] = tune
        states[condition] = fit_records
        predictions[condition] = predicted
        probabilities[condition] = probability
        details[condition] = condition_details
    for condition in ("outer_labels_rotated", "outer_features_plus1000"):
        check(
            f"{condition}_inner_scores_selection_unchanged",
            traces["baseline"] == traces[condition],
        )
        check(
            f"{condition}_all_training_fit_stats_unchanged",
            states["baseline"] == states[condition],
        )
    check(
        "outer_labels_rotated_test_predictions_unchanged",
        np.array_equal(predictions["baseline"], predictions["outer_labels_rotated"]),
    )
    check(
        "outer_labels_rotated_test_probabilities_unchanged",
        np.array_equal(probabilities["baseline"], probabilities["outer_labels_rotated"]),
    )
    changed = int(np.sum(predictions["baseline"] != predictions["outer_features_plus1000"]))

    # 4. Within-subject shuffled-label canary through both implementations.
    shuffled_csv = output / "shuffled_labels.csv"
    shuffled_sha = build_shuffled_labels_csv(
        config.input_path,
        shuffled_csv,
        target_column=config.target_column,
        group_column=config.group_column,
    )
    only_target_changed = shuffled_labels_change_only_target(
        config.input_path, shuffled_csv, target_column=config.target_column
    )
    check(
        "shuffled_labels_only_target_column_changed",
        only_target_changed,
        {"sha256": shuffled_sha},
        bucket="canary",
    )
    canary_config = replace(
        config, input_path=shuffled_csv, output_dir=output / "canary_primary"
    )
    canary_config_path = output / "canary_config.json"
    canary_payload = dsa_case.read_json(config_path)
    canary_payload["input_path"] = str(shuffled_csv)
    dsa_case.write_json(canary_config_path, canary_payload)
    runner.run_experiment(canary_config)
    reference_output = output / "canary_reference"
    reference_summary = reference_dsa.run(canary_config_path, reference_output)
    canary_metrics = pd.read_csv(canary_config.output_dir / "metrics.csv")
    canary_balanced_accuracy = float(canary_metrics["balanced_accuracy"].iloc[0])
    for name, reference_name in (
        ("fold_metrics", "fold_metrics"),
        ("metrics_summary", "metrics_summary"),
        ("selection_trace", "selection_trace"),
        ("parameter_search", "parameter_search"),
    ):
        comparison = _compare_tables(
            Path(canary_config.output_dir) / f"{name}.csv",
            reference_output / f"{reference_name}.csv",
            table_name=name,
        )
        passed = comparison["passed"]
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
        if name == "parameter_search":
            diagnostics = compare_dsa.validate_reference_diagnostics(
                pd.read_csv(reference_output / "parameter_search.csv"),
                expected_inner_folds=int(config.inner_splits),
                table_name="parameter_search",
            )
            passed = passed and diagnostics["passed"]
            detail["reference_diagnostics"] = diagnostics
        check(
            f"{name}_independent_match",
            passed,
            detail,
            bucket="canary",
        )
    canary_predictions = pd.read_csv(Path(canary_config.output_dir) / "predictions.csv").sort_values(
        ["row_index", "fold"]
    ).reset_index(drop=True)
    reference_predictions = pd.read_csv(
        reference_output / "predictions_with_probabilities.csv"
    ).sort_values(["row_index", "fold"]).reset_index(drop=True)
    identity = ["row_index", "fold", "observed", "predicted", "model"]
    check(
        "predictions_exact",
        canary_predictions[identity].equals(reference_predictions[identity]),
        bucket="canary",
    )
    check(
        "predeclared_canary_alarm_not_triggered",
        canary_balanced_accuracy <= alarm_threshold,
        {
            "balanced_accuracy": canary_balanced_accuracy,
            "alarm_if_above": alarm_threshold,
            "dummy_balanced_accuracy": float(
                balanced_accuracy_score(
                    pd.read_csv(reference_output / "dummy_oof.csv")["observed"],
                    pd.read_csv(reference_output / "dummy_oof.csv")["predicted"],
                )
            ),
        },
        bucket="canary",
    )
    details["canary"] = {
        "shuffled_csv_sha256": shuffled_sha,
        "frozen_shuffled_hash_match": shuffled_sha == dsa_case.SHUFFLED_LABELS_CSV_SHA256,
        "input_csv_sha256": input_sha256,
        "frozen_input_hash_match": input_sha256 == dsa_case.DERIVED_CSV_SHA256,
        "balanced_accuracy": canary_balanced_accuracy,
        "alarm_threshold": alarm_threshold,
        "selected_family": reference_summary["selected_family"],
        "fit_count": reference_summary["fit_count"],
        "interpretation": (
            "One engineering canary; not an inferential permutation test, "
            "not a false-positive-rate estimate and not proof that no leakage exists."
        ),
    }
    details["feature_perturbation_prediction_change_count"] = changed
    payload = {
        "passed": all(item["pass"] for item in checks),
        "checks": checks,
        "details": details,
        "caution": (
            "Perturbation evaluation scores are diagnostic only and were never used "
            "to revise the protocol or choose a model."
        ),
    }
    dsa_case.write_json(output / "checks.json", payload)
    dsa_case.write_json(output / "fold_control_states.json", states)
    dsa_case.write_json(output / "fold_control_search.json", traces)
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New or empty directory")
    parser.add_argument("--alarm-threshold", type=float, default=dsa_case.PLACEBO_ALARM_THRESHOLD)
    args = parser.parse_args(argv)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        payload = run_controls(args.config, args.output, alarm_threshold=args.alarm_threshold)
        dsa_case.write_json(
            Path(args.output) / "warnings.json",
            [{"category": item.category.__name__, "message": str(item.message)} for item in caught],
        )
    failures = [item for item in payload["checks"] if not item["pass"]]
    print(json.dumps({"passed": payload["passed"], "failures": failures}, indent=2))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
