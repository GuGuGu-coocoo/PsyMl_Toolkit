"""Row-wise marginal permutation importance for already-fitted models.

This module is a pure computation layer. It never fits a model, never reads
training or full-data partitions, never aggregates across folds, and never
mutates the model or the input data. Callers are responsible for passing a
model/``Pipeline`` fitted on the corresponding training partition and a raw
held-out evaluation frame, and for recording the resulting metadata next to the
fold it belongs to.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

PERMUTATION_METRICS = ("accuracy", "balanced_accuracy", "f1_macro", "r2", "mae", "rmse")
PERMUTATION_SCHEME = "rowwise_marginal"
DATA_SCOPE = "outer_test"

DIRECTION_HIGHER_IS_BETTER = "higher_is_better"
DIRECTION_LOWER_IS_BETTER = "lower_is_better"
_LOWER_IS_BETTER = frozenset({"mae", "rmse"})

_REQUIRED_CONTEXT_KEYS = ("validation", "fold", "model_family")

_METADATA_NOTES = [
    (
        "Importance is row-wise marginal permutation calculated inside one held-out "
        "evaluation set; it is not block or group permutation."
    ),
    (
        "Correlated predictor variables can share or mask attribution; importance is "
        "not a causal effect and not a percentage of explained variance."
    ),
    (
        "For grouped or repeated-measures data this rowwise scheme does not preserve "
        "within-group dependence, even when group-aware validation was used."
    ),
    (
        "The repeat standard deviation is descriptive variation across repeats, not a "
        "confidence interval and not a significance test."
    ),
    "Negative importances are retained and values are not normalised.",
    (
        "Context fields are recorded as declared by the caller; this function does not "
        "verify the actual train/test split."
    ),
]


class PermutationImportanceError(ValueError):
    """Raised for invalid permutation importance requests."""


class NonFiniteScoreError(PermutationImportanceError):
    """Raised when a baseline or permuted score is not finite."""


def default_score(metric: str, observed: Any, predicted: Any) -> float:
    """Score held-out predictions with the same definitions the runner uses."""
    if metric == "accuracy":
        return float(accuracy_score(observed, predicted))
    if metric == "balanced_accuracy":
        return float(balanced_accuracy_score(observed, predicted))
    if metric == "f1_macro":
        return float(f1_score(observed, predicted, average="macro", zero_division=0))
    if metric == "r2":
        return float(r2_score(observed, predicted))
    if metric == "mae":
        return float(mean_absolute_error(observed, predicted))
    if metric == "rmse":
        return float(math.sqrt(mean_squared_error(observed, predicted)))
    raise PermutationImportanceError(
        f"Unsupported permutation importance metric: {metric!r}; "
        f"expected one of {', '.join(PERMUTATION_METRICS)}"
    )


def _validate_repeats(repeats: int) -> int:
    if isinstance(repeats, bool) or not isinstance(repeats, (int, float)):
        raise TypeError("repeats must be an integer")
    if isinstance(repeats, float):
        if not math.isfinite(repeats) or not repeats.is_integer():
            raise ValueError("repeats must be an integer")
        repeats = int(repeats)
    if not 1 <= repeats <= 100:
        raise ValueError("repeats must be between 1 and 100")
    return repeats


def _validate_seed(seed: int) -> int:
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("seed must be an integer")
    return seed


def _resolve_direction(metric: str) -> str:
    if metric not in PERMUTATION_METRICS:
        raise PermutationImportanceError(
            f"Unsupported permutation importance metric: {metric!r}; "
            f"expected one of {', '.join(PERMUTATION_METRICS)}"
        )
    return DIRECTION_LOWER_IS_BETTER if metric in _LOWER_IS_BETTER else DIRECTION_HIGHER_IS_BETTER


def _resolve_context(
    context: Mapping[str, Any],
    *,
    seed: int,
    repeats: int,
    metric: str,
    direction: str,
    n_rows: int,
) -> dict[str, Any]:
    if not isinstance(context, Mapping):
        raise TypeError("context must be a mapping")
    missing = [key for key in _REQUIRED_CONTEXT_KEYS if context.get(key) is None]
    if missing:
        raise ValueError(f"context is missing required fields: {', '.join(missing)}")
    payload = dict(context)
    # Derived fields always win, so a caller cannot mislabel scope or scheme.
    payload.update(
        {
            "validation": context["validation"],
            "fold": context["fold"],
            "model_family": context["model_family"],
            "data_scope": DATA_SCOPE,
            "random_seed": seed,
            "repeats": repeats,
            "metric": metric,
            "direction": direction,
            "n_rows": n_rows,
            "permutation_scheme": PERMUTATION_SCHEME,
        }
    )
    return payload


def _finite_score(value: Any, label: str) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError) as error:
        raise NonFiniteScoreError(f"{label} is not a numeric score: {value!r}") from error
    if not math.isfinite(score):
        raise NonFiniteScoreError(f"{label} is not finite: {score!r}")
    return score


def permutation_importance(
    model: Any,
    features: pd.DataFrame,
    target: Sequence[Any] | pd.Series,
    *,
    metric: str,
    context: Mapping[str, Any],
    seed: int = 42,
    repeats: int = 10,
    score: Callable[[Any, Any], float] | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Return per-repeat and per-variable importance for a fitted model.

    Only the held-out ``features``/``target`` given here are used. Each repeat
    permutes one original column at a time (keeping every other column, the row
    index, and the dtypes untouched) and re-scores the model's predictions.
    Grouped/repeated-measures dependence is intentionally not preserved: this
    is rowwise marginal permutation, not block permutation.
    """
    direction = _resolve_direction(metric)
    repeats = _validate_repeats(repeats)
    seed = _validate_seed(seed)
    if not isinstance(features, pd.DataFrame):
        raise TypeError("features must be a pandas DataFrame")
    if features.columns.duplicated().any():
        raise ValueError("features must not contain duplicate column names")
    if features.shape[1] == 0:
        raise ValueError("features must contain at least one column")
    observed = target.copy() if hasattr(target, "copy") else np.asarray(target)
    if len(observed) != len(features):
        raise ValueError("target length must match the number of feature rows")

    def _engine_score(observed_values: Any, predicted_values: Any) -> float:
        return default_score(metric, observed_values, predicted_values)

    scorer = score if score is not None else _engine_score

    n_rows = len(features)
    columns = list(features.columns)
    baseline_prediction = model.predict(features)
    baseline_score = _finite_score(scorer(observed, baseline_prediction), "Baseline score")

    rng = np.random.default_rng(seed)
    importances: dict[Any, list[float]] = {column: [] for column in columns}
    total = repeats * len(columns)
    completed = 0
    for repeat in range(repeats):
        for column in columns:
            order = rng.permutation(n_rows)
            permuted = features.copy(deep=True)
            permuted[column] = features[column].array.take(order)
            predicted = model.predict(permuted)
            permuted_score = _finite_score(
                scorer(observed, predicted), f"Permuted score for {column!r}"
            )
            if direction == DIRECTION_HIGHER_IS_BETTER:
                importance = baseline_score - permuted_score
            else:
                importance = permuted_score - baseline_score
            importances[column].append(float(importance))
            completed += 1
            if progress_callback is not None:
                progress_callback(
                    {
                        "permutation": completed,
                        "total": total,
                        "variable": str(column),
                        "repeat": repeat,
                    }
                )

    context_payload = _resolve_context(
        context, seed=seed, repeats=repeats, metric=metric, direction=direction, n_rows=n_rows
    )
    variables = []
    for column in columns:
        values = np.asarray(importances[column], dtype=float)
        variables.append(
            {
                "name": str(column),
                "importances": [float(value) for value in values],
                "mean": float(values.mean()),
                "std": float(values.std(ddof=0)),
            }
        )

    return {
        "metric": metric,
        "direction": direction,
        "baseline_score": baseline_score,
        "seed": seed,
        "repeats": repeats,
        "n_rows": n_rows,
        "permutation_scheme": PERMUTATION_SCHEME,
        "variables": variables,
        "context": context_payload,
        "metadata": {
            "data_scope": DATA_SCOPE,
            "permutation_scheme": PERMUTATION_SCHEME,
            "aggregation": "per_fold_repeat_mean_and_std_ddof0",
            "not_a_confidence_interval": True,
            "not_a_causal_effect": True,
            "notes": list(_METADATA_NOTES),
        },
    }


def _fitted_preprocessor(model: Any) -> ColumnTransformer | None:
    if isinstance(model, Pipeline) and "preprocess" in model.named_steps:
        candidate = model.named_steps["preprocess"]
        if isinstance(candidate, ColumnTransformer):
            return candidate
    return None


def _find_one_hot_encoder(transformer: Any) -> OneHotEncoder | None:
    if isinstance(transformer, OneHotEncoder):
        return transformer
    if isinstance(transformer, Pipeline) and transformer.steps:
        last = transformer.steps[-1][1]
        if isinstance(last, OneHotEncoder):
            return last
    return None


def _transformer_output_names(transformer: Any, columns: list[Any]) -> list[str] | None:
    if transformer == "drop":
        return []
    if transformer == "passthrough":
        return [str(column) for column in columns]
    try:
        names = transformer.get_feature_names_out(columns)
    except (AttributeError, KeyError, TypeError, ValueError):
        return None
    return [str(name) for name in names]


def _unavailable(reason: str) -> dict[str, Any]:
    return {"status": "unavailable", "reason": reason}


def extract_feature_encoding(model: Any, features: pd.DataFrame | None = None) -> dict[str, Any]:
    """Map original variables to fitted preprocessing outputs, or report unavailable.

    The mapping is derived from the fitted ``ColumnTransformer`` and the final
    ``OneHotEncoder`` (categories and output names). It never guesses a mapping
    by splitting generated feature names on underscores. When the fitted
    preprocessor is absent, its output cannot be reconciled with the raw
    columns (for example a stacking template or a fully dropped column), or any
    introspection fails, the result is explicitly ``unavailable``.
    """
    preprocessor = _fitted_preprocessor(model)
    if preprocessor is None:
        return _unavailable(
            "model has no fitted 'preprocess' ColumnTransformer; encoding is unavailable"
        )
    try:
        original = [str(column) for column in preprocessor.feature_names_in_]
        transformed = [str(name) for name in preprocessor.get_feature_names_out()]
        output_indices = preprocessor.output_indices_
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        return _unavailable(f"preprocessor introspection failed: {type(error).__name__}")
    if features is not None:
        raw = [str(column) for column in features.columns]
        if raw != original:
            return _unavailable(
                "raw feature columns do not match the columns the preprocessor was fitted on; "
                "this usually means a generated/stacking template"
            )

    mapping: dict[str, Any] = {}
    for name, transformer, columns in preprocessor.transformers_:
        if name not in output_indices:
            continue
        output_slice = output_indices[name]
        full_names = transformed[output_slice]
        column_list = list(columns)
        encoder = _find_one_hot_encoder(transformer)
        if encoder is not None:
            try:
                categories = list(encoder.categories_)
                sub_names = [str(item) for item in encoder.get_feature_names_out(column_list)]
            except (AttributeError, KeyError, TypeError, ValueError):
                return _unavailable("categorical encoder introspection failed")
            if len(categories) != len(column_list) or len(sub_names) != len(full_names):
                return _unavailable("categorical encoding could not be reconciled with raw columns")
            if (
                getattr(encoder, "drop", None) is not None
                or getattr(encoder, "min_frequency", None) is not None
                or getattr(encoder, "max_categories", None) is not None
            ):
                return _unavailable(
                    "categorical encoder drops or groups categories, so outputs cannot be "
                    "mapped one-to-one to raw categories"
                )
            expected_total = sum(len(column_categories) for column_categories in categories)
            if expected_total != len(sub_names):
                return _unavailable(
                    "categorical encoder outputs do not match one feature per category"
                )
            offset = 0
            for position, column in enumerate(column_list):
                count = len(categories[position])
                encoded = list(full_names[offset : offset + count])
                mapping[str(column)] = {
                    "kind": "categorical",
                    "transformed_features": encoded,
                    "categories": [
                        {
                            "category": _category_label(value),
                            "feature": encoded[index] if index < len(encoded) else None,
                        }
                        for index, value in enumerate(categories[position])
                    ],
                }
                offset += count
            continue
        sub_names = _transformer_output_names(transformer, column_list)
        if sub_names is None or len(sub_names) != len(full_names):
            return _unavailable(
                "numeric/preprocessing outputs could not be reconciled with raw columns"
            )
        for column, feature_name in zip(column_list, full_names):
            mapping[str(column)] = {
                "kind": "numeric",
                "transformed_features": [str(feature_name)],
                "categories": None,
            }
    if set(mapping) != set(original):
        return _unavailable("not every raw column could be mapped to a transformed feature")
    return {
        "status": "available",
        "original_features": original,
        "transformed_features": transformed,
        "mapping": mapping,
    }


def _category_label(value: Any) -> str:
    return "missing" if pd.isna(value) else str(value)
