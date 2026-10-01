"""Independent scikit-learn recomputation of the public DSA case protocol.

This module deliberately does not import ``psyml`` and does not call or copy its
runner call chain. It rebuilds the frozen protocol from public scikit-learn
APIs only:

* outer ``GroupKFold(n_splits=4)`` over the original row order;
* inner ``StratifiedGroupKFold(n_splits=3, shuffle=True)`` with seed
  ``random_seed + outer_fold`` (outer folds numbered from 1);
* a fresh ``SimpleImputer(median) -> StandardScaler`` fitted inside every
  training partition, followed by ``DummyClassifier`` or
  ``LogisticRegression``;
* explicit candidate loops with an unweighted mean of the inner balanced
  accuracies, strict-greater replacement and first-in-order tie retention;
* the same procedure re-run on all rows for the final full-data pipeline.

Both implementations share scikit-learn estimators, splitters and metrics, so
this is an independent reconstruction of the *workflow*, not an independent
validation of the scikit-learn solvers themselves.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import warnings
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import (
    GroupKFold,
    ParameterGrid,
    StratifiedGroupKFold,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

if __package__ in {None, ""}:  # direct script execution
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.cases import dsa_case

FROZEN_FAMILIES = ("dummy", "logistic_regression")
METRIC_NAMES = (
    "accuracy",
    "balanced_accuracy",
    "precision_weighted",
    "recall_weighted",
    "f1_weighted",
    "precision_macro",
    "recall_macro",
    "f1_macro",
    "roc_auc_ovr_weighted",
)


def collect_candidates(config: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Expand each family grid with ParameterGrid, preserving its value order."""
    families = list(config["model_names"])
    candidates: dict[str, list[dict[str, Any]]] = {}
    for family in families:
        grid = config["parameter_grids"].get(family, {})
        combos = [dict(combo) for combo in ParameterGrid(grid)] if grid else [{}]
        if len(combos) > int(config["max_candidates"]):
            raise ValueError(
                f"{family}: {len(combos)} candidates exceed max_candidates="
                f"{config['max_candidates']}; refusing silent ParameterSampler behaviour"
            )
        candidates[family] = combos
    return candidates


def build_pipeline(
    features: pd.DataFrame, family: str, params: dict[str, Any], seed: int
) -> Pipeline:
    """Build one fresh preprocessing-plus-estimator pipeline."""
    preprocessor = ColumnTransformer(
        [
            (
                "numeric",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="median")),
                        ("scale", StandardScaler()),
                    ]
                ),
                list(features.columns),
            )
        ],
        remainder="drop",
    )
    if family == "dummy":
        estimator = DummyClassifier(**{"random_state": seed, **params})
    elif family == "logistic_regression":
        # Mirrors the PsyML catalog default; explicit grid values override it.
        estimator = LogisticRegression(**{"max_iter": 1000, "random_state": seed, **params})
    else:
        raise ValueError(f"Unsupported family: {family}")
    return Pipeline([("preprocess", preprocessor), ("model", estimator)])


def plan_splits(
    features: pd.DataFrame,
    target: pd.Series,
    groups: pd.Series,
    strategy: str,
    n_splits: int,
    seed: int,
) -> tuple[list[tuple[list[int], list[int]]], dict[str, Any]]:
    """Return positional folds plus an exact membership record."""
    if strategy == "group_k_fold":
        splitter = GroupKFold(n_splits=n_splits)
    elif strategy == "stratified_group_k_fold":
        splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    else:
        raise ValueError(f"Unsupported strategy for this case: {strategy}")
    folds = list(splitter.split(features, target, groups))
    entry: dict[str, Any] = {
        "strategy": strategy,
        "n_splits": n_splits,
        "random_seed": seed,
        "input_rows": features.index.tolist(),
        "folds": [],
    }
    for train, test in folds:
        train_groups = set(groups.iloc[train].tolist())
        test_groups = set(groups.iloc[test].tolist())
        if train_groups & test_groups:
            raise ValueError("Splitter produced overlapping groups")
        entry["folds"].append(
            {
                "train_rows": features.iloc[train].index.tolist(),
                "test_rows": features.iloc[test].index.tolist(),
                "train_groups": sorted(train_groups),
                "test_groups": sorted(test_groups),
            }
        )
    key = (
        f"{strategy}|{n_splits}|{seed}|"
        + hashlib.sha256(np.asarray(features.index, dtype=np.int64).tobytes()).hexdigest()
    )
    return folds, {key: entry}


def fit_state(model: Pipeline, features: pd.DataFrame, family: str, params: dict[str, Any]) -> dict:
    """Record the fitted preprocessing state and estimator parameters."""
    numeric = model.named_steps["preprocess"].named_transformers_["numeric"]
    estimator = model.named_steps["model"]
    return {
        "family": family,
        "overrides": params,
        "train_rows": features.index.tolist(),
        "feature_names": features.columns.tolist(),
        "imputer_statistics": numeric.named_steps["impute"].statistics_.tolist(),
        "scaler_mean": numeric.named_steps["scale"].mean_.tolist(),
        "scaler_var": numeric.named_steps["scale"].var_.tolist(),
        "scaler_scale": numeric.named_steps["scale"].scale_.tolist(),
        "scaler_n_samples_seen": int(numeric.named_steps["scale"].n_samples_seen_),
        "classes": estimator.classes_.tolist(),
        "effective_parameters": estimator.get_params(deep=False),
        "coef": getattr(estimator, "coef_", np.array([])).tolist(),
        "intercept": getattr(estimator, "intercept_", np.array([])).tolist(),
        "n_iter": getattr(estimator, "n_iter_", np.array([])).tolist(),
    }


def classification_metrics(observed, predicted, probability, classes) -> dict[str, float]:
    """Report the same metric set as the primary workflow.

    Mirror the production metric naming: binary folds report ``roc_auc`` and
    multi-class folds report ``roc_auc_ovr_weighted``, and the rank metric is
    omitted when the fold does not contain every training class.
    """
    metrics = {
        "accuracy": float(accuracy_score(observed, predicted)),
        "balanced_accuracy": float(balanced_accuracy_score(observed, predicted)),
        **{
            f"{name}_{average}": float(
                function(observed, predicted, average=average, zero_division=0)
            )
            for average in ("weighted", "macro")
            for name, function in (
                ("precision", precision_score),
                ("recall", recall_score),
                ("f1", f1_score),
            )
        },
    }
    labels = np.unique(observed)
    classes = np.asarray(classes)
    if set(labels) != set(classes):
        return metrics
    if len(classes) == 2:
        metrics["roc_auc"] = float(
            roc_auc_score(np.asarray(observed) == classes[1], probability[:, 1])
        )
    elif len(labels) > 2:
        metrics["roc_auc_ovr_weighted"] = float(
            roc_auc_score(
                observed, probability, multi_class="ovr", average="weighted", labels=classes
            )
        )
    return metrics


def _first_max_index(scores: Sequence[float]) -> int:
    """Return the first finite maximum; raise when no candidate completed."""
    eligible = [index for index, score in enumerate(scores) if math.isfinite(score)]
    if not eligible:
        raise ValueError("All parameter candidates failed during inner selection")
    return max(eligible, key=lambda index: scores[index])


def _first_max_key(scores: dict[str, float]) -> str:
    """Return the first family with the highest finite score (configuration order)."""
    eligible = [family for family, score in scores.items() if math.isfinite(score)]
    if not eligible:
        raise ValueError("All model families failed during inner selection")
    return max(eligible, key=lambda family: scores[family])


def run(config_path: str | Path, output_dir: str | Path) -> dict[str, Any]:
    """Execute the frozen protocol and write the reference artefacts."""
    config = dsa_case.load_case_config(config_path)
    _validate_protocol(config)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=False)

    frame = pd.read_csv(config["input_path"])
    features = frame[config["feature_columns"]]
    target = frame[config["target_column"]]
    groups = frame[config["group_column"]]
    if features.isna().any().any():
        raise ValueError("The frozen case expects no missing feature values")

    seed = int(config["random_seed"])
    families = list(config["model_names"])
    candidates = collect_candidates(config)
    splits: dict[str, Any] = {}
    audit: list[dict[str, Any]] = []
    tune_rows: list[dict[str, Any]] = []

    def fit_partition(
        partition_features: pd.DataFrame,
        partition_target: pd.Series,
        family: str,
        params: dict[str, Any],
    ) -> Pipeline:
        model = build_pipeline(partition_features, family, params, seed)
        model.fit(partition_features, partition_target)
        audit.append(fit_state(model, partition_features, family, params))
        return model

    def select_family(
        family: str,
        scope_features: pd.DataFrame,
        scope_target: pd.Series,
        inner_folds: list[tuple[list[int], list[int]]],
        fold_number: int,
    ) -> tuple[dict[str, Any], float]:
        scores: list[float] = []
        for candidate_index, params in enumerate(candidates[family], start=1):
            values: list[float] = []
            error_text = ""
            for inner_train, inner_test in inner_folds:
                try:
                    model = fit_partition(
                        scope_features.iloc[inner_train],
                        scope_target.iloc[inner_train],
                        family,
                        params,
                    )
                    predicted = model.predict(scope_features.iloc[inner_test])
                    values.append(
                        float(balanced_accuracy_score(scope_target.iloc[inner_test], predicted))
                    )
                except Exception as error:  # noqa: BLE001 - record, never average around it
                    error_text = f"{type(error).__name__}: {error}"
            score = float(pd.Series(values).mean()) if values and not error_text else math.nan
            scores.append(score)
            tune_rows.append(
                {
                    "model": family,
                    "validation": "group_k_fold",
                    "outer_fold": fold_number,
                    "selection_scope": (
                        "final_full_data" if fold_number == 0 else "outer_training_fold"
                    ),
                    "candidate": candidate_index,
                    "selection_metric": "balanced_accuracy",
                    "score": score,
                    "parameters": json.dumps(params, sort_keys=True),
                    "status": "failed" if error_text else "completed",
                    "error": error_text,
                    "inner_scores": json.dumps(values),
                }
            )
        best = _first_max_index(scores)
        return candidates[family][best], scores[best]

    outer_folds, outer_record = plan_splits(
        features, target, groups, "group_k_fold", int(config["n_splits"]), seed
    )
    splits.update(outer_record)

    inner_by_fold: dict[int, list[tuple[list[int], list[int]]]] = {}
    for fold_number, (train_index, _test_index) in enumerate(outer_folds, start=1):
        train_features = features.iloc[train_index]
        inner, record = plan_splits(
            train_features,
            target.iloc[train_index],
            groups.iloc[train_index],
            "stratified_group_k_fold",
            min(int(config["inner_splits"]), int(groups.iloc[train_index].nunique())),
            seed + fold_number,
        )
        inner_by_fold[fold_number] = inner
        splits.update(record)

    final_inner, final_record = plan_splits(
        features,
        target,
        groups,
        "stratified_group_k_fold",
        min(int(config["inner_splits"]), int(groups.nunique())),
        seed,
    )
    splits.update(final_record)

    fold_results: dict[tuple[int, str], tuple[float, dict, pd.DataFrame, dict]] = {}
    for family in families:
        for fold_number, (train_index, test_index) in enumerate(outer_folds, start=1):
            params, inner_score = select_family(
                family,
                features.iloc[train_index],
                target.iloc[train_index],
                inner_by_fold[fold_number],
                fold_number,
            )
            model = fit_partition(
                features.iloc[train_index], target.iloc[train_index], family, params
            )
            predicted = model.predict(features.iloc[test_index])
            probability = model.predict_proba(features.iloc[test_index])
            metrics = classification_metrics(
                target.iloc[test_index], predicted, probability, model.classes_
            )
            table = pd.DataFrame(
                {
                    "row_index": features.iloc[test_index].index,
                    "fold": fold_number,
                    "observed": target.iloc[test_index].to_numpy(),
                    "predicted": predicted,
                    "model": family,
                }
            )
            for column, label in enumerate(model.classes_):
                table[f"probability_{label}"] = probability[:, column]
            fold_results[(fold_number, family)] = (inner_score, metrics, table, params)

    selected_rows: list[dict[str, Any]] = []
    selected_predictions: list[pd.DataFrame] = []
    selection_trace: list[dict[str, Any]] = []
    for fold_number, _fold in enumerate(outer_folds, start=1):
        family_scores = {
            family: fold_results[(fold_number, family)][0] for family in families
        }
        winner = _first_max_key(family_scores)
        score, metrics, table, params = fold_results[(fold_number, winner)]
        selected_rows.append(
            {"fold": fold_number, "model": winner, "validation": "group_k_fold", **metrics}
        )
        selected_predictions.append(table)
        selection_trace.append(
            {
                "validation": "group_k_fold",
                "outer_fold": fold_number,
                "selection_scope": "outer_training_fold",
                "model": winner,
                "parameters": json.dumps(params, sort_keys=True),
                "score": score,
            }
        )

    final_choices = {
        family: select_family(family, features, target, final_inner, 0) for family in families
    }
    final_family = _first_max_key({family: score for family, (_, score) in final_choices.items()})
    final_params, final_score = final_choices[final_family]
    selection_trace.append(
        {
            "validation": "group_k_fold",
            "outer_fold": 0,
            "selection_scope": "final_full_data",
            "model": final_family,
            "parameters": json.dumps(final_params, sort_keys=True),
            "score": final_score,
        }
    )
    final_model = fit_partition(features, target, final_family, final_params)
    joblib.dump(final_model, output / "final_model.joblib", compress=3)

    predictions = pd.concat(selected_predictions, ignore_index=True)
    fold_metrics = pd.DataFrame(selected_rows)
    predictions.to_csv(output / "predictions_with_probabilities.csv", index=False)
    fold_metrics.to_csv(output / "fold_metrics.csv", index=False)
    pd.DataFrame(tune_rows).to_csv(output / "parameter_search.csv", index=False)
    pd.DataFrame(selection_trace).to_csv(output / "selection_trace.csv", index=False)
    dsa_case.write_json(output / "fold_membership.json", splits)
    dsa_case.write_json(output / "fit_audit.json", audit)

    summary = [
        {
            "metric": name,
            "mean": float(fold_metrics[name].mean()),
            "std": float(fold_metrics[name].std(ddof=0)),
            "min": float(fold_metrics[name].min()),
            "max": float(fold_metrics[name].max()),
            "n_folds": len(fold_metrics),
        }
        for name in METRIC_NAMES
        if name in fold_metrics.columns
    ]
    pd.DataFrame(summary).to_csv(output / "metrics_summary.csv", index=False)
    probability_columns = [f"probability_{label}" for label in final_model.classes_]
    pooled = classification_metrics(
        predictions["observed"],
        predictions["predicted"],
        predictions[probability_columns].to_numpy(),
        final_model.classes_,
    )
    result = {
        "fold_mean": {
            name: float(fold_metrics[name].mean())
            for name in METRIC_NAMES
            if name in fold_metrics.columns
        },
        "pooled_oof": pooled,
        "selected_family": final_family,
        "selected_overrides": final_params,
        "fit_count": len(audit),
        "rows": len(frame),
        "classes": final_model.classes_.tolist(),
    }
    dsa_case.write_json(output / "summary.json", result)
    np.savez_compressed(
        output / "final_predictions.npz",
        row_index=np.arange(len(features)),
        predicted=final_model.predict(features),
        probabilities=final_model.predict_proba(features),
        classes=final_model.classes_,
    )
    for family in families:
        family_oof = pd.concat(
            [fold_results[(fold_number, family)][2] for fold_number in range(1, len(outer_folds) + 1)],
            ignore_index=True,
        )
        family_oof.to_csv(output / f"{family}_oof.csv", index=False)
    return result


def _validate_protocol(config: dict[str, Any]) -> None:
    """Refuse protocols that differ from the frozen case."""
    if config["validation_strategy"] != "group_k_fold":
        raise ValueError("The frozen case requires validation_strategy='group_k_fold'")
    if config["missing_strategy"] != "median" or config["scaling"] != "standard":
        raise ValueError("The frozen case requires median imputation and standard scaling")
    if config["selection_metric"] != "balanced_accuracy":
        raise ValueError("The frozen case requires selection_metric='balanced_accuracy'")
    if config["tuning_mode"] != "custom":
        raise ValueError("The frozen case requires tuning_mode='custom'")
    if tuple(config["model_names"]) != FROZEN_FAMILIES:
        raise ValueError(f"The frozen case requires model_names={list(FROZEN_FAMILIES)}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New or empty directory")
    args = parser.parse_args(argv)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = run(args.config, args.output)
        dsa_case.write_json(
            args.output / "warnings.json",
            [{"category": item.category.__name__, "message": str(item.message)} for item in caught],
        )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
