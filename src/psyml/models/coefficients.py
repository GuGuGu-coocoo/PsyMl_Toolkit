"""Fitted linear-model coefficients and intercepts in preprocessed feature space.

This module reports the *already fitted* ``coef_``/``intercept_`` of supported
linear estimators as they act on the output of the fitted PsyML preprocessor
(the transformed feature space). It never fits, refits, tunes or otherwise
changes a model, and it never converts coefficients back to the original raw
units.

Scope of the first release:

* Regression: ``LinearRegression``, ``Ridge``, ``Lasso``, ``ElasticNet`` and
  ``SVR`` with ``kernel='linear'``.
* Classification: ``LogisticRegression``, ``LinearDiscriminantAnalysis`` with a
  fitted ``coef_``/``intercept_``, and binary ``SVC`` with ``kernel='linear'``.

Multi-class ``SVC`` exposes pairwise (one-vs-one) coefficients and is rejected
rather than mislabelled. Non-linear kernels, trees, KNN, MLP and stacking have
no single directly mappable linear coefficient row and are reported as
unsupported with a specific reason. Ordinary prediction is never affected.
"""

from __future__ import annotations

import json
import os
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.linear_model import ElasticNet, Lasso, LinearRegression, LogisticRegression, Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder, StandardScaler
from sklearn.svm import SVC, SVR

from psyml.explanation import _is_identity_passthrough, _pipeline_structure_reason
from psyml.prediction import LoadedModel, compatibility_check, model_input

COEFFICIENT_SCHEMA_VERSION = "1.0"
COEFFICIENT_SPACE = "preprocessed_feature_space"
RECONSTRUCTION_ATOL = 1e-7
RECONSTRUCTION_RTOL = 1e-6

SUPPORTED_LINEAR_REGRESSORS = (LinearRegression, Ridge, Lasso, ElasticNet, SVR)
SUPPORTED_LINEAR_CLASSIFIERS = (LogisticRegression, LinearDiscriminantAnalysis, SVC)

_SUPPORTED_REGRESSION_TEXT = "linear_regression, ridge, lasso, elastic_net, svr (kernel='linear')"
_SUPPORTED_CLASSIFICATION_TEXT = (
    "logistic_regression, lda, svm (kernel='linear', binary only)"
)

_REGRESSION_UNIT = "prediction in the transformed linear space (same unit as the target)"
_BINARY_LOGISTIC_UNIT = (
    "decision_function raw score: log-odds of classes_[1] relative to classes_[0]"
)
_MULTICLASS_LOGISTIC_UNIT = (
    "per-class decision_function score (softmax logit for that class; not a one-vs-rest log-odds)"
)
_BINARY_LDA_UNIT = (
    "decision_function score that separates classes_[1] from classes_[0]; for the "
    "standard two-class LDA this equals the fitted class log-odds (sigmoid of it is "
    "predict_proba for classes_[1])"
)
_MULTICLASS_LDA_UNIT = (
    "per-class LDA linear discriminant score on the decision_function scale (not a "
    "probability; softmax of the scores matches predict_proba)"
)
_BINARY_SVC_UNIT = (
    "raw decision_function margin for classes_[1] against classes_[0] "
    "(w·z + b, not normalized by ||w||); not a probability, log-odds or a geometric distance"
)

_EXPLANATION_LIMITS = [
    (
        "Coefficients act on the preprocessed (imputed, scaled, one-hot encoded) feature "
        "space, not on the original raw units; no conversion back to raw units is provided."
    ),
    (
        "These are fitted model parameters of the final all-analyzed-rows model. They are "
        "neither hyperparameters nor outer-fold performance and carry no p-values, "
        "confidence intervals, significance or causal meaning."
    ),
    (
        "Coefficient magnitudes are conditional on the chosen scaling and encoding; "
        "comparing them across differently scaled features is not a defined standardized effect."
    ),
    (
        "Coefficients are not re-fitted, tuned or fed back into model selection; they do "
        "not change prediction."
    ),
]


class CoefficientError(ValueError):
    """Raised for an invalid coefficient request."""


class CoefficientUnsupportedError(CoefficientError):
    """Raised when the fitted estimator has no directly mappable linear coefficients."""


@dataclass
class CoefficientSupport:
    supported: bool
    reason: str
    task: str | None = None
    family: str | None = None
    estimator_class: str | None = None
    fit_scope: str | None = None
    solver: str | None = None
    kernel: str | None = None
    classes: list[Any] | None = None


def _estimator(pipeline: Any) -> Any:
    if isinstance(pipeline, Pipeline) and pipeline.steps:
        return pipeline.steps[-1][1]
    return pipeline


def _json_scalar(value: Any) -> Any:
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not np.isfinite(value):
        return None
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _is_missing_stat(value: Any) -> bool:
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _dtype_name(value: Any) -> str:
    return str(value)


def _train_dtype(feature_dtypes: dict[str, Any] | None, column: str) -> str | None:
    if not feature_dtypes:
        return None
    return _dtype_name(feature_dtypes.get(column)) if column in feature_dtypes else None


def _block_positions(preprocessor: ColumnTransformer) -> dict[str, list[int]]:
    indices = getattr(preprocessor, "output_indices_", None)
    if not indices:
        raise CoefficientUnsupportedError(
            "The fitted preprocessor exposes no output column mapping."
        )
    positions: dict[str, list[int]] = {}
    for name, value in indices.items():
        if isinstance(value, slice):
            positions[name] = list(range(value.start, value.stop))
        else:
            positions[name] = [int(item) for item in np.atleast_1d(value)]
    return positions


def _numeric_drop_reason(imputer: Any) -> str:
    return (
        "all values are missing in the training data; the fitted imputer drops this "
        f"column (strategy={getattr(imputer, 'strategy', None)!r})"
    )


def _numeric_features(
    transform: Any,
    columns: list[str],
    positions: list[int],
    names: list[str],
    feature_dtypes: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if transform == "passthrough" or _is_identity_passthrough(transform):
        # A fitted ColumnTransformer replaces the 'passthrough' string with its own
        # identity FunctionTransformer; both mean "no numeric steps".
        steps: dict[str, Any] = {}
    elif isinstance(transform, Pipeline):
        steps = {name: step for name, step in transform.steps}
    else:
        raise CoefficientUnsupportedError("Unsupported numeric preprocessor block type.")
    imputer = steps.get("impute")
    scaler = steps.get("scale")
    retained: list[tuple[int, str]] = []
    dropped: list[dict[str, Any]] = []
    for source_index, column in enumerate(columns):
        if imputer is not None and _is_missing_stat(imputer.statistics_[source_index]):
            dropped.append({
                "index": source_index,
                "name": column,
                "kind": "numeric",
                "reason": _numeric_drop_reason(imputer),
                "missing_strategy": getattr(imputer, "strategy", None),
                "transformed_indices": [],
            })
            continue
        retained.append((source_index, column))
    if len(retained) != len(positions):
        raise CoefficientUnsupportedError(
            "Cannot map numeric transformed columns to their source columns."
        )
    scale_mode = "none"
    if isinstance(scaler, StandardScaler):
        scale_mode = "standard"
    elif isinstance(scaler, MinMaxScaler):
        scale_mode = "minmax"
    elif scaler is not None:
        raise CoefficientUnsupportedError("Unsupported numeric scaler type.")
    entries = []
    for local, (source_index, column) in enumerate(retained):
        entry: dict[str, Any] = {
            "index": positions[local],
            "name": names[positions[local]],
            "source": column,
            "kind": "numeric",
            "imputed": imputer is not None,
            "imputer_strategy": getattr(imputer, "strategy", None) if imputer else None,
            "imputer_fill_value": None,
            "scaling": scale_mode,
            "scaler": None,
            "category": None,
            "category_type": None,
            "category_index": None,
            "dropped_reference": False,
            "training_dtype": _train_dtype(feature_dtypes, column),
            "note": "one transformed column per retained numeric source column",
        }
        if imputer is not None:
            entry["imputer_fill_value"] = _json_scalar(imputer.statistics_[source_index])
        if isinstance(scaler, StandardScaler):
            entry["scaler"] = {
                "mean": float(scaler.mean_[local]),
                "scale": float(scaler.scale_[local]),
                "variance": _json_scalar(scaler.var_[local]),
                "with_mean": bool(scaler.with_mean),
                "with_std": bool(scaler.with_std),
            }
        elif isinstance(scaler, MinMaxScaler):
            entry["scaler"] = {
                "min": float(scaler.min_[local]),
                "scale": float(scaler.scale_[local]),
                "data_min": float(scaler.data_min_[local]),
                "data_max": float(scaler.data_max_[local]),
                "data_range": _json_scalar(scaler.data_range_[local]),
                "clip": bool(scaler.clip),
            }
        entries.append(entry)
    return entries, dropped


def _categorical_features(
    transform: Any,
    columns: list[str],
    positions: list[int],
    names: list[str],
    feature_dtypes: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    if not isinstance(transform, Pipeline):
        raise CoefficientUnsupportedError("Unsupported categorical preprocessor block type.")
    steps = {name: step for name, step in transform.steps}
    encoder = steps.get("encode")
    imputer = steps.get("impute")
    if not isinstance(encoder, OneHotEncoder):
        raise CoefficientUnsupportedError("Unsupported categorical encoder type.")
    # Only the PsyML default OneHotEncoder configuration has a simple, exact
    # category-to-column mapping. Custom dropping or infrequent grouping is
    # rejected rather than guessed.
    if (getattr(encoder, "drop", None) is not None
            or getattr(encoder, "min_frequency", None) is not None
            or getattr(encoder, "max_categories", None) is not None):
        raise CoefficientUnsupportedError(
            "A custom OneHotEncoder configuration (drop/min_frequency/max_categories) "
            "cannot be mapped to exact category axes in this version."
        )
    categories = list(getattr(encoder, "categories_", []))
    retained: list[tuple[int, str]] = []
    dropped: list[dict[str, Any]] = []
    for source_index, column in enumerate(columns):
        if imputer is not None and _is_missing_stat(imputer.statistics_[source_index]):
            dropped.append({
                "index": source_index,
                "name": column,
                "kind": "categorical",
                "reason": _numeric_drop_reason(imputer),
                "missing_strategy": getattr(imputer, "strategy", None),
                "transformed_indices": [],
            })
            continue
        retained.append((source_index, column))
    if len(retained) != len(categories):
        raise CoefficientUnsupportedError(
            "Cannot map the fitted one-hot categories to their source columns."
        )
    entries: list[dict[str, Any]] = []
    per_source: list[dict[str, Any]] = []
    for position, (source_index, column) in enumerate(retained):
        values = list(categories[position])
        column_names: list[str] = []
        for category_index, raw_value in enumerate(values):
            entries.append({
                "index": positions[len(entries)],
                "name": names[positions[len(entries)]],
                "source": column,
                "kind": "onehot",
                "imputed": imputer is not None,
                "imputer_strategy": getattr(imputer, "strategy", None) if imputer else None,
                "imputer_fill_value": (
                    _json_scalar(imputer.statistics_[source_index]) if imputer is not None else None
                ),
                "scaling": "none",
                "scaler": None,
                "category": _json_scalar(raw_value),
                "category_type": type(raw_value).__name__,
                "category_index": category_index,
                "dropped_reference": False,
                "training_dtype": _train_dtype(feature_dtypes, column),
                "note": "indicator column for one observed training category",
            })
            column_names.append(names[positions[len(entries) - 1]])
        per_source.append({
            "source": column,
            "source_index": source_index,
            "categories": [_json_scalar(value) for value in values],
            "category_types": [type(value).__name__ for value in values],
            "transformed_indices": positions[len(entries) - len(values):len(entries)],
            "transformed_names": column_names,
            "dropped_category_index": None,
            "dropped_category": None,
        })
    if len(entries) != len(positions):
        raise CoefficientUnsupportedError(
            "The fitted one-hot output width does not match the preprocessor block width."
        )
    encoding = {
        "handle_unknown": getattr(encoder, "handle_unknown", None),
        "drop": getattr(encoder, "drop", None),
        "drop_idx_": _drop_idx(encoder),
        "min_frequency": getattr(encoder, "min_frequency", None),
        "max_categories": getattr(encoder, "max_categories", None),
        "sparse_output": bool(getattr(encoder, "sparse_output", False)),
        "n_input_columns": len(retained),
        "n_output_columns": len(entries),
        "per_source": per_source,
        "unknown_behavior": (
            "An unrecognized category produces an all-zero block for that source column "
            "(handle_unknown='ignore'); no reference category is dropped, so every observed "
            "training category has its own indicator column."
        ),
    }
    return entries, encoding, dropped


def _drop_idx(encoder: OneHotEncoder) -> list[Any] | None:
    """Serializable copy of the fitted ``drop_idx_`` (``None`` when nothing is dropped)."""
    value = getattr(encoder, "drop_idx_", None)
    if value is None:
        return None
    try:
        return [
            None if item is None or _is_missing_stat(item) else int(item)
            for item in np.atleast_1d(value)
        ]
    except (TypeError, ValueError):
        return None


def _transformed_features(
    preprocessor: ColumnTransformer,
    feature_names: list[str],
    feature_dtypes: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    positions = _block_positions(preprocessor)
    names = list(preprocessor.get_feature_names_out(feature_names))
    entries: list[dict[str, Any]] = []
    input_features: list[dict[str, Any]] = []
    scaling_summary: dict[str, Any] = {"numeric_mode": "none", "applied": False}
    encoding_summary: dict[str, Any] = {}
    for name, transform, columns in preprocessor.transformers_:
        if name == "remainder":
            continue
        block = positions.get(name)
        if block is None:
            raise CoefficientUnsupportedError(f"Missing output mapping for block '{name}'.")
        columns = list(columns)
        if name == "numeric":
            numeric, numeric_dropped = _numeric_features(
                transform, columns, block, names, feature_dtypes
            )
            if numeric and numeric[0]["scaling"] != "none":
                scaling_summary = {
                    "numeric_mode": numeric[0]["scaling"],
                    "applied": True,
                    "n_output_columns": len(numeric),
                }
            entries.extend(numeric)
            input_features.extend(_input_entries(
                feature_names, columns, "numeric", numeric, numeric_dropped,
                _numeric_missing_strategy(transform),
            ))
        elif name == "categorical":
            categorical, encoding_summary, categorical_dropped = _categorical_features(
                transform, columns, block, names, feature_dtypes
            )
            entries.extend(categorical)
            input_features.extend(_input_entries(
                feature_names, columns, "categorical", categorical, categorical_dropped,
                _categorical_missing_strategy(transform),
            ))
        else:
            raise CoefficientUnsupportedError(f"Unsupported preprocessor block '{name}'.")
    if len(entries) != len(names):
        raise CoefficientUnsupportedError(
            "The mapped transformed features do not cover the preprocessor output."
        )
    entries.sort(key=lambda item: item["index"])
    input_features.sort(key=lambda item: item["index"])
    if [item["index"] for item in input_features] != list(range(len(feature_names))):
        raise CoefficientUnsupportedError(
            "The input feature mapping does not cover the recorded input columns."
        )
    dropped_features = [
        {
            "index": entry["index"],
            "name": entry["name"],
            "kind": entry["kind"],
            "reason": entry["drop_reason"],
            "missing_strategy": entry["missing_strategy"],
            "transformed_indices": [],
        }
        for entry in input_features
        if not entry["retained"]
    ]
    return entries, scaling_summary, encoding_summary, input_features, dropped_features


def _numeric_missing_strategy(transform: Any) -> str | None:
    if transform == "passthrough" or _is_identity_passthrough(transform):
        return None
    if isinstance(transform, Pipeline):
        for step_name, step in transform.steps:
            if step_name == "impute":
                return getattr(step, "strategy", None)
    return None


def _categorical_missing_strategy(transform: Any) -> str | None:
    if isinstance(transform, Pipeline):
        for step_name, step in transform.steps:
            if step_name == "impute":
                return getattr(step, "strategy", None)
    return None


def _input_entries(
    feature_names: list[str],
    columns: list[str],
    kind: str,
    transformed: list[dict[str, Any]],
    dropped: list[dict[str, Any]],
    missing_strategy: str | None,
) -> list[dict[str, Any]]:
    """Per original input column: retention, drop reason and transformed positions.

    ``columns`` is the block's local column order; ``feature_names`` gives the
    global original index that the report uses.
    """
    by_source: dict[str, list[int]] = {}
    for feature in transformed:
        by_source.setdefault(str(feature["source"]), []).append(feature["index"])
    dropped_by_local = {int(item["index"]): item for item in dropped}
    entries: list[dict[str, Any]] = []
    for local_index, column in enumerate(columns):
        global_index = feature_names.index(column)
        if local_index in dropped_by_local:
            entries.append({
                "index": global_index,
                "name": column,
                "kind": kind,
                "retained": False,
                "missing_strategy": missing_strategy,
                "drop_reason": dropped_by_local[local_index]["reason"],
                "transformed_indices": [],
            })
            continue
        entries.append({
            "index": global_index,
            "name": column,
            "kind": kind,
            "retained": True,
            "missing_strategy": missing_strategy,
            "drop_reason": None,
            "transformed_indices": by_source.get(str(column), []),
        })
    return entries


def _coefficient_rows(
    estimator: Any, task: str, classes: list[Any]
) -> tuple[np.ndarray, np.ndarray, list[dict[str, Any]]]:
    coef = np.atleast_2d(np.asarray(estimator.coef_, dtype=float))
    intercept = np.atleast_1d(np.asarray(estimator.intercept_, dtype=float))
    family = type(estimator).__name__
    if task == "regression":
        if coef.shape[0] != 1:
            raise CoefficientUnsupportedError("Regression coefficients are not a single row.")
        rows = [{
            "row_index": 0,
            "kind": "prediction",
            "label": "prediction",
            "class_index": None,
            "class_label": None,
            "class_type": None,
            "unit": _REGRESSION_UNIT,
        }]
        return coef, intercept, rows
    if not classes:
        raise CoefficientUnsupportedError("The classifier exposes no class labels.")
    if family == "SVC" and len(classes) > 2:
        raise CoefficientUnsupportedError(
            "Multi-class SVC stores pairwise (one-vs-one) coefficients and cannot be "
            "reported as one coefficient row per class."
        )
    if coef.shape[0] == 1 and len(classes) == 2:
        if family == "LogisticRegression":
            unit, kind = _BINARY_LOGISTIC_UNIT, "binary_log_odds"
        elif family == "LinearDiscriminantAnalysis":
            unit, kind = _BINARY_LDA_UNIT, "binary_discriminant_score"
        else:
            unit, kind = _BINARY_SVC_UNIT, "binary_margin"
        rows = [{
            "row_index": 0,
            "kind": kind,
            "label": str(classes[1]),
            "class_index": 1,
            "class_label": _json_scalar(classes[1]),
            "class_type": type(classes[1]).__name__,
            "unit": unit,
        }]
        return coef, intercept, rows
    if coef.shape[0] != len(classes):
        raise CoefficientUnsupportedError(
            "The coefficient row count does not match the number of classes."
        )
    if family == "LogisticRegression":
        unit, kind = _MULTICLASS_LOGISTIC_UNIT, "class_logit"
    elif family == "LinearDiscriminantAnalysis":
        unit, kind = _MULTICLASS_LDA_UNIT, "class_discriminant_score"
    else:
        raise CoefficientUnsupportedError(
            "Multi-class coefficients for this estimator cannot be mapped to class axes."
        )
    rows = [{
        "row_index": index,
        "kind": kind,
        "label": str(label),
        "class_index": index,
        "class_label": _json_scalar(label),
        "class_type": type(label).__name__,
        "unit": unit,
    } for index, label in enumerate(classes)]
    return coef, intercept, rows


def extract_coefficients(
    pipeline: Any,
    *,
    task: str,
    feature_names: list[str],
    feature_dtypes: dict[str, Any] | None = None,
    feature_dtypes_source: str | None = None,
) -> dict[str, Any]:
    """Extract fitted coefficients from a standard PsyML pipeline.

    Raises ``CoefficientUnsupportedError`` when the estimator or the fitted
    preprocessor cannot be mapped exactly. This function never fits anything.
    """
    if task not in ("classification", "regression"):
        raise CoefficientError(f"Unsupported task: {task}")
    if not isinstance(pipeline, Pipeline):
        raise CoefficientUnsupportedError(
            "Only a standard PsyML pipeline ('preprocess' then 'model') is supported."
        )
    structure_reason = _pipeline_structure_reason(pipeline)
    if structure_reason:
        raise CoefficientUnsupportedError(structure_reason)
    preprocessor = pipeline.named_steps["preprocess"]
    estimator = pipeline.named_steps["model"]
    if feature_names is None:
        feature_names = list(getattr(preprocessor, "feature_names_in_", []))
    feature_names = [str(name) for name in feature_names]
    if len(feature_names) != int(getattr(preprocessor, "n_features_in_", len(feature_names))):
        raise CoefficientUnsupportedError(
            "The recorded feature names do not match the fitted preprocessor."
        )
    family = type(estimator).__name__
    solver = getattr(estimator, "solver", None)
    kernel = getattr(estimator, "kernel", None)
    if task == "regression":
        if not isinstance(estimator, SUPPORTED_LINEAR_REGRESSORS):
            raise CoefficientUnsupportedError(
                f"Estimator type '{family}' has no directly mappable linear coefficient "
                f"row. Supported regression models: {_SUPPORTED_REGRESSION_TEXT}."
            )
        if isinstance(estimator, SVR) and kernel != "linear":
            raise CoefficientUnsupportedError(
                f"SVR with kernel='{kernel}' has no linear coefficient row; only "
                "kernel='linear' is supported."
            )
    else:
        if not isinstance(estimator, SUPPORTED_LINEAR_CLASSIFIERS):
            raise CoefficientUnsupportedError(
                f"Estimator type '{family}' has no directly mappable linear coefficient "
                f"row. Supported classification models: {_SUPPORTED_CLASSIFICATION_TEXT}."
            )
        if isinstance(estimator, SVC) and kernel != "linear":
            raise CoefficientUnsupportedError(
                f"SVC with kernel='{kernel}' has no linear coefficient row; only "
                "kernel='linear' is supported."
            )
        if isinstance(estimator, LinearDiscriminantAnalysis) and (
                not hasattr(estimator, "coef_") or not hasattr(estimator, "intercept_")):
            raise CoefficientUnsupportedError(
                "This LinearDiscriminantAnalysis solver exposes no fitted coef_/intercept_."
            )
        if not hasattr(estimator, "coef_") or not hasattr(estimator, "intercept_"):
            raise CoefficientUnsupportedError(
                "The fitted classifier exposes no coef_/intercept_."
            )
    features, scaling_summary, encoding_summary, input_features, dropped_features = (
        _transformed_features(preprocessor, feature_names, feature_dtypes)
    )
    dtype_source = feature_dtypes_source or (
        "training_frame" if feature_dtypes else "unknown"
    )
    if dtype_source == "unknown":
        dtype_note = (
            "The saved model metadata does not record the training dtypes, so "
            "'training_dtype' is unknown here (never inferred from prediction input)."
        )
    else:
        dtype_note = f"Training dtypes are recorded from {dtype_source}."
    classes = list(getattr(estimator, "classes_", [])) if task == "classification" else []
    coef, intercept, rows = _coefficient_rows(estimator, task, classes)
    if coef.shape[1] != len(features):
        raise CoefficientUnsupportedError(
            "The coefficient width does not match the mapped transformed feature count."
        )
    if len(intercept) not in (1, coef.shape[0]):
        raise CoefficientUnsupportedError(
            "The fitted intercept does not match the coefficient row count."
        )
    if len(intercept) == 1 and coef.shape[0] > 1:
        intercept = np.repeat(intercept, coef.shape[0])
    coefficients = [[float(value) for value in row] for row in coef]
    report = {
        "schema_version": COEFFICIENT_SCHEMA_VERSION,
        "status": "available",
        "coefficient_space": COEFFICIENT_SPACE,
        "task": task,
        "family": family,
        "estimator_class": f"{type(estimator).__module__}.{type(estimator).__qualname__}",
        "solver": solver,
        "kernel": kernel,
        "n_features": len(features),
        "n_output_rows": coef.shape[0],
        "classes": [_json_scalar(label) for label in classes] or None,
        "features": features,
        "coefficients": coefficients,
        "intercept": [float(value) for value in intercept],
        "output": {
            "kind": rows[0]["kind"] if len(rows) == 1 else "per_class",
            "unit": rows[0]["unit"],
            "rows": rows,
            "note": (
                "Each row of 'coefficients' follows the same feature order as 'features'; "
                "'intercept' has one entry per row."
            ),
        },
        "scaling": scaling_summary,
        "encoding": encoding_summary or None,
        "input_features": input_features,
        "dropped_features": dropped_features,
        "training_dtype_source": dtype_source,
        "training_dtype_note": dtype_note,
        "explanation_limits": list(_EXPLANATION_LIMITS),
    }
    return report


def verify_reconstruction(
    pipeline: Pipeline,
    verify_frame: Any,
    report: dict[str, Any],
) -> dict[str, Any]:
    """Rebuild predictions/scores from coefficients and compare with the pipeline."""
    preprocessor = pipeline.named_steps["preprocess"]
    transformed = np.asarray(preprocessor.transform(verify_frame), dtype=float)
    coefficients = np.asarray(report["coefficients"], dtype=float)
    intercept = np.asarray(report["intercept"], dtype=float)
    scores = transformed @ coefficients.T + intercept
    task = report["task"]
    if task == "regression":
        expected = np.asarray(pipeline.predict(verify_frame), dtype=float).reshape(-1, 1)
    else:
        expected = np.asarray(pipeline.decision_function(verify_frame), dtype=float)
        if expected.ndim == 1:
            expected = expected.reshape(-1, 1)
    finite = bool(np.isfinite(scores).all() and np.isfinite(expected).all())
    shape_ok = bool(scores.shape == expected.shape)
    if shape_ok:
        difference = np.abs(scores - expected)
        max_abs_error = float(np.max(difference))
        per_row = [float(value) for value in np.max(difference, axis=1)]
        verified = bool(finite and np.allclose(
            scores, expected, atol=RECONSTRUCTION_ATOL, rtol=RECONSTRUCTION_RTOL
        ))
    else:
        max_abs_error = None
        per_row = []
        verified = False
    return {
        "performed": True,
        "verified": verified,
        "rows": int(np.asarray(verify_frame).shape[0]),
        "shape_ok": shape_ok,
        "finite": finite,
        "max_abs_error": max_abs_error,
        "tolerance": {"atol": RECONSTRUCTION_ATOL, "rtol": RECONSTRUCTION_RTOL},
        "output_unit": report["output"]["unit"],
        "row_max_abs_error": per_row,
        "reference": (
            "pipeline.predict" if task == "regression" else "pipeline.decision_function"
        ),
        "note": (
            "Reconstruction uses the fitted preprocessor transform of the supplied rows; "
            "a passing check confirms coefficient/axis mapping, not generalization."
        ),
    }


def _verification_failure_reason(verification: dict[str, Any]) -> str:
    if not verification.get("finite", False):
        return (
            "Reconstruction produced non-finite values: the extracted coefficients and the "
            "fitted pipeline output are inconsistent, so no coefficient artifact is published."
        )
    if not verification.get("shape_ok", False):
        return (
            "The reconstructed score shape does not match the fitted pipeline output: the "
            "coefficient/class axes are inconsistent, so no coefficient artifact is published."
        )
    tolerance = verification.get("tolerance", {})
    return (
        "Reconstruction did not reproduce the fitted pipeline "
        f"(max_abs_error={verification.get('max_abs_error')}, "
        f"atol={tolerance.get('atol')}, rtol={tolerance.get('rtol')}); the extracted "
        "coefficients are inconsistent, so no coefficient artifact is published."
    )


def build_coefficient_report(
    pipeline: Any,
    *,
    task: str,
    feature_names: list[str],
    feature_dtypes: dict[str, Any] | None = None,
    feature_dtypes_source: str | None = None,
    verify_frame: Any | None = None,
    provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a structured coefficient report, verifying when data is supplied.

    When verification data is supplied and the reconstruction fails, the report is
    returned with ``status='error'`` and a specific reason: an inconsistent
    extraction must never be published as a successful coefficient artifact.
    """
    try:
        report = extract_coefficients(
            pipeline, task=task, feature_names=feature_names, feature_dtypes=feature_dtypes,
            feature_dtypes_source=feature_dtypes_source,
        )
    except CoefficientUnsupportedError as error:
        return {
            "schema_version": COEFFICIENT_SCHEMA_VERSION,
            "status": "unsupported",
            "reason": str(error),
            "task": task,
            "coefficient_space": COEFFICIENT_SPACE,
        }
    if provenance:
        report["model"] = provenance
    if verify_frame is not None:
        verification = verify_reconstruction(pipeline, verify_frame, report)
        report["verification"] = verification
        if not verification["verified"]:
            report["status"] = "error"
            report["reason"] = _verification_failure_reason(verification)
    else:
        report["verification"] = {
            "performed": False,
            "verified": False,
            "reason": "No input data was supplied; reconstruction was not verified.",
        }
    return report


def coefficient_support(loaded: LoadedModel) -> CoefficientSupport:
    """Verify provenance and estimator support for a trusted loaded model."""
    model = loaded.model
    if not isinstance(model, Pipeline):
        return CoefficientSupport(
            False,
            "Only a PsyML-exported fitted sklearn Pipeline is supported in this first release.",
        )
    metadata = loaded.metadata or {}
    if not metadata.get("psyml_version"):
        return CoefficientSupport(
            False,
            "This model has no PsyML export metadata; coefficients only support models "
            "saved by PsyML (best_*.joblib together with its metadata).",
        )
    fit_scope = metadata.get("fit_scope")
    if not fit_scope:
        return CoefficientSupport(
            False,
            "The model metadata does not record its fit scope; cannot confirm this is the "
            "final all-analyzed-rows PsyML model.",
        )
    structure_reason = _pipeline_structure_reason(model)
    if structure_reason:
        return CoefficientSupport(False, structure_reason)
    estimator = _estimator(model)
    task = metadata.get("task")
    family = type(estimator).__name__
    kernel = getattr(estimator, "kernel", None)
    solver = getattr(estimator, "solver", None)
    if task not in ("classification", "regression"):
        return CoefficientSupport(
            False,
            "The model metadata does not record whether this is a classification or "
            "regression model; refusing to guess the coefficient axes.",
            task=task, family=family, kernel=kernel, solver=solver,
        )
    classes = list(getattr(estimator, "classes_", [])) if task == "classification" else None
    try:
        report = extract_coefficients(
            model,
            task=task,
            feature_names=list(metadata.get("feature_names") or
                              getattr(model, "feature_names_in_", [])),
        )
    except CoefficientUnsupportedError as error:
        return CoefficientSupport(False, str(error), task=task, family=family,
                                  kernel=kernel, solver=solver, classes=classes)
    actual_class = report["estimator_class"]
    recorded_class = metadata.get("estimator_class")
    if recorded_class and recorded_class != actual_class:
        return CoefficientSupport(
            False,
            "The fitted estimator does not match the estimator recorded in the PsyML metadata.",
            task=task, family=family,
        )
    return CoefficientSupport(
        True, "supported", task=task, family=family, estimator_class=actual_class,
        fit_scope=fit_scope, solver=solver, kernel=kernel, classes=classes,
    )


def build_loaded_coefficient_report(
    loaded: LoadedModel,
    frame=None,
    mapping=None,
    *,
    feature_dtypes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Extract coefficients for a trusted loaded model with optional verification."""
    support = coefficient_support(loaded)
    result: dict[str, Any] = {
        "schema_version": COEFFICIENT_SCHEMA_VERSION,
        "coefficient_space": COEFFICIENT_SPACE,
        "support": {
            "supported": support.supported,
            "reason": support.reason,
            "task": support.task,
            "family": support.family,
            "fit_scope": support.fit_scope,
            "kernel": support.kernel,
            "solver": support.solver,
        },
    }
    if not support.supported:
        result.update(status="unsupported", reason=support.reason)
        return result
    dtype_source = "model_metadata"
    if feature_dtypes is None:
        feature_dtypes = loaded.metadata.get("feature_dtypes")
    if not feature_dtypes:
        feature_dtypes = None
        dtype_source = "unknown"
    verify_frame = None
    verification_note = None
    if frame is not None:
        check = compatibility_check(loaded, frame, mapping)
        if not check["compatible"]:
            raise CoefficientError(" ".join(error["message"] for error in check["errors"]))
        verify_frame = model_input(loaded, frame, mapping, check=check)
        verification_note = {"rows_used": int(verify_frame.shape[0])}
    report = build_coefficient_report(
        loaded.model,
        task=support.task,
        feature_names=list(loaded.metadata.get("feature_names") or
                           getattr(loaded.model, "feature_names_in_", [])),
        feature_dtypes=feature_dtypes,
        feature_dtypes_source=dtype_source,
        verify_frame=verify_frame,
        provenance={
            "fit_scope": support.fit_scope,
            "estimator_class": support.estimator_class,
        },
    )
    report["support"] = result["support"]
    if verification_note:
        report["verification"]["input"] = verification_note
    return report


def _write_csv(report: dict[str, Any], path: Path) -> None:
    rows = []
    for row in report["output"]["rows"]:
        for feature in report["features"]:
            rows.append({
                "output_index": row["row_index"],
                "output_kind": row["kind"],
                "output_label": row["label"],
                "class_index": row["class_index"],
                "class_label": row["class_label"],
                "class_type": row["class_type"],
                "output_unit": row["unit"],
                "intercept": report["intercept"][row["row_index"]],
                "transformed_index": feature["index"],
                "transformed_name": feature["name"],
                "source_column": feature["source"],
                "feature_kind": feature["kind"],
                "category_value": feature["category"],
                "category_type": feature["category_type"],
                "category_index": feature["category_index"],
                "dropped_reference": feature["dropped_reference"],
                "imputed": feature["imputed"],
                "imputer_strategy": feature["imputer_strategy"],
                "imputer_fill_value": feature["imputer_fill_value"],
                "scaling": feature["scaling"],
                "scaler_detail": (
                    json.dumps(feature["scaler"], sort_keys=True)
                    if feature["scaler"] else ""
                ),
                "training_dtype": feature["training_dtype"],
                "coefficient": report["coefficients"][row["row_index"]][feature["index"]],
            })
    pd.DataFrame(rows).to_csv(path, index=False)


def _notes_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# 拟合系数与截距 / Fitted coefficients and intercepts",
        "",
        "这些是**已拟合模型参数**，在**预处理后坐标空间**中作用，不是超参数，也不是显著性检验。",
        "These are fitted model parameters acting in the **preprocessed feature space**; they are",
        "not hyperparameters and carry no significance test.",
        "",
        f"- Task: `{report['task']}`",
        f"- Estimator: `{report['estimator_class']}`",
        f"- Coefficient space: `{report['coefficient_space']}`",
        f"- Output unit: {report['output']['unit']}",
    ]
    if report.get("model", {}).get("fit_scope"):
        lines.append(f"- Fit scope: `{report['model']['fit_scope']}` (deployment model, "
                     "not outer-fold performance)")
    verification = report.get("verification", {})
    if verification.get("performed"):
        status_text = "verified" if verification.get("verified") else "FAILED"
        lines.append(
            f"- Reconstruction: {status_text}, "
            f"rows={verification['rows']}, max_abs_error={verification['max_abs_error']}, "
            f"atol={verification['tolerance']['atol']}, rtol={verification['tolerance']['rtol']}"
        )
    else:
        lines.append(
            "- Reconstruction: NOT performed (no input data supplied); the coefficients are "
            "unverified, which is not the same as a failed check."
        )
    lines.extend(["", "## Intercept / 截距", ""])
    for row in report["output"]["rows"]:
        lines.append(
            f"- `{row['label']}` (row {row['row_index']}, kind `{row['kind']}`): "
            f"{report['intercept'][row['row_index']]} — unit: {row['unit']}"
        )
    lines.extend(["", "## Input feature mapping / 输入列映射", ""])
    lines.append(
        "Full machine-readable mapping (including transformed indices) is in "
        "`coefficients.json` (`input_features`, `dropped_features`, `encoding.per_source`)."
    )
    lines.append("")
    for entry in report.get("input_features", []):
        if entry["retained"]:
            lines.append(
                f"- `{entry['name']}` ({entry['kind']}, original index {entry['index']}): retained; "
                f"transformed indices {entry['transformed_indices']}; "
                f"missing strategy {entry['missing_strategy']!r}"
            )
        else:
            lines.append(
                f"- `{entry['name']}` ({entry['kind']}, original index {entry['index']}): "
                f"NOT used — {entry['drop_reason']}"
            )
    encoding = report.get("encoding") or {}
    if encoding:
        lines.extend(["", "## One-hot encoding / 独热编码", ""])
        lines.append(
            f"- handle_unknown={encoding.get('handle_unknown')!r}, drop={encoding.get('drop')!r}, "
            f"drop_idx_={encoding.get('drop_idx_')}"
        )
        for source in encoding.get("per_source", []):
            lines.append(
                f"- `{source['source']}` (original index {source['source_index']}): categories "
                f"{source['categories']} → transformed names {source['transformed_names']}"
            )
    lines.extend(["", "## Training dtypes / 训练时 dtype", ""])
    lines.append(f"- Source: `{report.get('training_dtype_source')}` — "
                 f"{report.get('training_dtype_note')}")
    lines.extend(["", "## Limitations / 解释限制", ""])
    lines.extend(f"- {limit}" for limit in report["explanation_limits"])
    return "\n".join(lines) + "\n"


def write_coefficients(
    report: dict[str, Any],
    output_dir: Path | str,
    *,
    protected_paths: tuple[Path | str | None, ...] = (),
) -> dict[str, str]:
    """Write ``coefficients.csv``, ``coefficients_notes.md`` and ``coefficients.json``.

    Only a new or empty directory is accepted and the JSON completion marker is
    written last, so an interrupted run never leaves a complete-looking result.
    """
    if report.get("status") != "available":
        raise CoefficientError("Only an available coefficient report can be written.")
    directory = Path(output_dir)
    if directory.exists() and directory.is_file():
        raise CoefficientError(f"Output path is an existing file: {directory}")
    protected = {Path(path).resolve() for path in protected_paths if path is not None}
    paths = {
        "csv": directory / "coefficients.csv",
        "notes": directory / "coefficients_notes.md",
        "json": directory / "coefficients.json",
    }
    for path in paths.values():
        if path.resolve() in protected:
            raise CoefficientError(
                f"The coefficient artifact {path.name!r} would overwrite a protected input file."
            )
    if directory.exists() and any(directory.iterdir()):
        raise CoefficientError(
            f"Output directory is not empty: {directory}. Choose a new or empty directory; "
            "this version never overwrites existing coefficient output."
        )
    directory.mkdir(parents=True, exist_ok=True)
    staging = directory / f".psyml-coefficients-staging-{os.getpid()}-{uuid.uuid4().hex}"
    staging.mkdir(exist_ok=False)
    try:
        staged = {name: staging / path.name for name, path in paths.items()}
        _write_csv(report, staged["csv"])
        staged["notes"].write_text(_notes_markdown(report), encoding="utf-8")
        document = {**report, "artifacts": {name: path.name for name, path in paths.items()}}
        staged["json"].write_text(
            json.dumps(document, ensure_ascii=True, indent=2, allow_nan=False, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        for name, path in staged.items():
            if not path.is_file() or path.stat().st_size == 0:
                raise CoefficientError(f"Prepared coefficient artifact {name!r} is empty.")
        published: list[str] = []
        try:
            for name in ("csv", "notes", "json"):
                os.replace(staged[name], paths[name])
                published.append(name)
        except Exception:
            for name in published:
                paths[name].unlink(missing_ok=True)
            raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return {name: str(path) for name, path in paths.items()}
