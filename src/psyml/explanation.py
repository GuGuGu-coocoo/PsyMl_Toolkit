"""Single-sample approximate SHAP explanations for trusted, fitted pipelines.

This module never fits a model, never reads the analysis training partition and
never changes prediction semantics. It explains one already-selected row from a
user-provided prediction file against a user-provided background file, using the
model-agnostic ``shap.PermutationExplainer`` on the complete fitted pipeline.

Scientific boundaries (see the FR-004 feasibility report):

* Contributions are approximate, sampling-based Shapley values, not exact SHAP.
* Contributions are additive on the single selected model output (a class
  probability for classification, the predicted value for regression).
* Marginal background replacement does not preserve predictor correlation;
  the result is neither causal nor a statement about outer test performance.
* ``shap`` is imported lazily; ordinary prediction commands never import it.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import textwrap
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import ElasticNet, Lasso, LinearRegression, LogisticRegression, Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, MinMaxScaler, OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

from psyml.prediction import LoadedModel, compatibility_check, model_input
from psyml.preprocessing.pipeline import _categorical_missing_values

EXPLANATION_SCHEMA_VERSION = "1.0"
ALGORITHM = "permutation"
DEFAULT_BACKGROUND_SIZE = 50
DEFAULT_CYCLES = 5
DEFAULT_SEED = 42
MAX_BACKGROUND_SIZE = 100
MAX_CYCLES = 20
MAX_FEATURES = 100
MAX_MODEL_ROWS = 250000
SEED_MIN = 0
SEED_MAX = 4294967295
RECONSTRUCTION_ATOL = 1e-7
RECONSTRUCTION_RTOL = 1e-6
WATERFALL_TOP_N = 15
# Fixed, documented allowance for the explainer's own base/sample evaluations on
# top of the ``cycles * (2F + 1)`` masking budget.
COUNTER_MARGIN_ROWS = 4

SUPPORTED_CLASSIFIERS = (
    LogisticRegression,
    DecisionTreeClassifier,
    RandomForestClassifier,
)
SUPPORTED_REGRESSORS = (
    LinearRegression,
    Ridge,
    Lasso,
    ElasticNet,
    DecisionTreeRegressor,
    RandomForestRegressor,
)

# The PsyML preprocessor is a ColumnTransformer built by
# ``psyml.preprocessing.pipeline.build_preprocessor``. Only those known, fitted
# step types may be explained; an arbitrary external preprocessing chain must be
# rejected with an explanation-only error (ordinary prediction still works).
_NUMERIC_STEP_TYPES = {"impute": (SimpleImputer,), "scale": (StandardScaler, MinMaxScaler)}
_CATEGORICAL_STEP_TYPES = {
    "normalize_missing": (FunctionTransformer,),
    "impute": (SimpleImputer,),
    "encode": (OneHotEncoder,),
}

_LIMITATIONS = [
    (
        "Contributions are approximate sampling-based Shapley values from a finite "
        "number of permutation cycles, not exact SHAP values."
    ),
    (
        "Masked features are replaced by independent draws from the chosen background; "
        "this marginal scheme does not preserve predictor correlation, so contributions "
        "can be affected by correlated or duplicated predictors."
    ),
    "Contributions are not causal effects.",
    (
        "Contributions describe the selected row against the chosen background only; "
        "they are not an estimate of outer test performance and do not change the model."
    ),
    (
        "Classification contributions are for one explicitly selected class and sum, "
        "with the background mean, to that class probability."
    ),
]


class ExplanationError(ValueError):
    """Raised for an invalid or unsupported single-sample explanation request."""


class ExplanationUnavailableError(ExplanationError):
    """Raised when the optional ``shap`` dependency is not installed."""


@dataclass
class ModelSupport:
    supported: bool
    reason: str
    task: str | None = None
    family: str | None = None
    estimator_class: str | None = None
    fit_scope: str | None = None


def _import_shap() -> Any:
    try:
        import shap
    except ImportError as error:  # pragma: no cover - exercised via monkeypatch
        raise ExplanationUnavailableError(
            "Single-sample explanation needs the optional 'explain' dependencies. "
            "Install them from source with: uv pip install -e '.[explain]' "
            "(or pip install -e '.[explain]'). Ordinary prediction still works."
        ) from error
    return shap


def shap_version() -> str | None:
    """Return the installed ``shap`` version without importing it eagerly."""
    try:
        from importlib.metadata import version

        return version("shap")
    except Exception:  # noqa: BLE001 - metadata absence never blocks prediction
        return None


def _pipeline_estimator(model: Any) -> Any:
    if isinstance(model, Pipeline) and model.steps:
        return model.steps[-1][1]
    return model


def _is_identity_passthrough(transform: Any) -> bool:
    """True for the sk-learn identity transform ColumnTransformer builds for 'passthrough'.

    A fitted ``ColumnTransformer`` replaces the ``'passthrough'`` string with a
    ``FunctionTransformer`` whose ``func``/``inverse_func`` are ``None``. Only that
    exact identity is accepted; any custom function stays unsupported.
    """
    return (
        isinstance(transform, FunctionTransformer)
        and getattr(transform, "func", None) is None
        and getattr(transform, "inverse_func", None) is None
    )


def _pipeline_structure_reason(model: Pipeline) -> str | None:
    """Return why a fitted pipeline is not a known PsyML pipeline, or ``None``."""
    steps = list(model.steps)
    if [name for name, _ in steps] != ["preprocess", "model"]:
        return (
            "Only the standard PsyML pipeline layout ('preprocess' then 'model') is "
            "supported for explanation."
        )
    preprocessor = model.named_steps["preprocess"]
    if not isinstance(preprocessor, ColumnTransformer):
        return "The 'preprocess' step is not a PsyML ColumnTransformer."
    if preprocessor.remainder != "drop":
        return "A non-'drop' remainder is not a supported PsyML preprocessor."
    transformers = getattr(preprocessor, "transformers_", None)
    if not transformers:
        return "The fitted preprocessor exposes no transformers."
    for name, transform, _columns in transformers:
        if name == "remainder":
            continue
        if name not in ("numeric", "categorical"):
            return f"Unsupported preprocessor block '{name}'."
        if transform == "passthrough" or _is_identity_passthrough(transform):
            if name != "numeric":
                return "A passthrough categorical block is not a supported PsyML preprocessor."
            continue
        if not isinstance(transform, Pipeline):
            return f"Unsupported {name} preprocessor block type."
        allowed = _NUMERIC_STEP_TYPES if name == "numeric" else _CATEGORICAL_STEP_TYPES
        order = list(allowed)
        seen: list[str] = []
        for step_name, step in transform.steps:
            if step_name not in allowed:
                return f"Unsupported {name} preprocessor step '{step_name}'."
            if not isinstance(step, allowed[step_name]):
                return f"Unsupported {name} preprocessor step type for '{step_name}'."
            if step_name == "normalize_missing" and (
                getattr(step, "func", None) is not _categorical_missing_values
            ):
                return "Unsupported categorical missing-value step."
            seen.append(step_name)
        if seen != [step for step in order if step in seen]:
            return f"Unexpected {name} preprocessor step order."
    return None


def model_support(loaded: LoadedModel) -> ModelSupport:
    """Verify the fitted structure and provenance against the FR-004 subset."""
    model = loaded.model
    if not isinstance(model, Pipeline):
        return ModelSupport(
            False,
            "Only a PsyML-exported fitted sklearn Pipeline is supported in this first release.",
        )
    if not loaded.metadata.get("psyml_version"):
        return ModelSupport(
            False,
            "This model has no PsyML export metadata; explanation only supports models "
            "saved by PsyML (best_*.joblib together with its metadata).",
        )
    fit_scope = loaded.metadata.get("fit_scope")
    if not fit_scope:
        return ModelSupport(
            False,
            "The model metadata does not record its fit scope; cannot confirm this is the "
            "final all-analyzed-rows PsyML model.",
        )
    structure_reason = _pipeline_structure_reason(model)
    if structure_reason:
        return ModelSupport(False, structure_reason)
    estimator = _pipeline_estimator(model)
    classifier = isinstance(estimator, SUPPORTED_CLASSIFIERS)
    regressor = isinstance(estimator, SUPPORTED_REGRESSORS)
    if not classifier and not regressor:
        name = type(estimator).__name__
        return ModelSupport(
            False,
            f"Estimator type '{name}' is not in the first-release explanation subset. "
            "Classification: logistic_regression, decision_tree, random_forest. "
            "Regression: linear_regression, ridge, lasso, elastic_net, decision_tree, "
            "random_forest.",
        )
    actual_class = f"{type(estimator).__module__}.{type(estimator).__qualname__}"
    recorded_class = loaded.metadata.get("estimator_class")
    if recorded_class and recorded_class != actual_class:
        return ModelSupport(
            False,
            "The fitted estimator does not match the estimator recorded in the PsyML metadata.",
        )
    task = loaded.metadata.get("task")
    if classifier and task != "classification":
        return ModelSupport(False, "Estimator and metadata disagree about the task.")
    if regressor and task != "regression":
        return ModelSupport(False, "Estimator and metadata disagree about the task.")
    if classifier and not hasattr(model, "predict_proba"):
        return ModelSupport(
            False,
            "This classifier has no predict_proba; probability explanation is unsupported.",
        )
    return ModelSupport(
        True,
        "supported",
        task=task,
        family=type(estimator).__name__,
        estimator_class=actual_class,
        fit_scope=fit_scope,
    )


def _validate_int(value: Any, label: str, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ExplanationError(f"{label} must be an integer between {low} and {high}.")
    if not low <= value <= high:
        raise ExplanationError(f"{label} must be between {low} and {high}.")
    return value


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    try:
        result = pd.isna(value)
    except (TypeError, ValueError):
        return False
    return bool(result) if isinstance(result, (bool, np.bool_)) else False


_SUPPORTED_VALUE_TYPES = (bool, np.bool_, int, np.integer, float, np.floating, str)


def _reject_unsupported_value(value: Any, column: str) -> None:
    if _is_missing(value):
        return
    if isinstance(value, _SUPPORTED_VALUE_TYPES):
        return
    raise ExplanationError(
        f"Feature {column!r} contains unsupported value type {type(value).__name__}; "
        "explanation supports numeric, boolean, string and missing values only. "
        "Re-encode this predictor before explaining."
    )


def _value_key(value: Any) -> tuple:
    """Exact-value key that keeps same-shaped numeric and string labels apart."""
    if _is_missing(value):
        return ("missing",)
    if isinstance(value, (bool, np.bool_)):
        return ("bool", bool(value))
    if isinstance(value, (int, np.integer)):
        return ("int", int(value))
    if isinstance(value, (float, np.floating)):
        return ("float", float(value))
    if isinstance(value, str):
        return ("str", value)
    return ("other", type(value).__name__, str(value))


def _stored_value(value: Any) -> Any:
    if _is_missing(value):
        return np.nan
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return float(value)
    if isinstance(value, str):
        return value
    return value


@dataclass
class LosslessCodec:
    """Finite integer-codec over the exact values seen in background and sample.

    Encoding is a bijection on the joint support, so a training-known category
    that never appears in this background, a training-unknown category, a
    missing value, and a real value that happens to equal any internal marker are
    all preserved exactly. The explainer only ever substitutes a code that exists
    in the background, and decoding reproduces the original Python value.
    """

    columns: list[str]
    maps: list[dict]
    inverse: list[list]

    @classmethod
    def build(cls, frames: list[pd.DataFrame], columns: list[str]) -> LosslessCodec:
        maps: list[dict] = []
        inverse: list[list] = []
        for column in columns:
            mapping: dict = {}
            decoded: list = []
            for frame in frames:
                for value in frame[column].tolist():
                    _reject_unsupported_value(value, column)
                    key = _value_key(value)
                    if key not in mapping:
                        mapping[key] = len(decoded)
                        decoded.append(_stored_value(value))
            maps.append(mapping)
            inverse.append(decoded)
        return cls(list(columns), maps, inverse)

    def encode_frame(self, frame: pd.DataFrame) -> np.ndarray:
        codes = np.empty((len(frame), len(self.columns)), dtype=np.int64)
        for position, column in enumerate(self.columns):
            mapping = self.maps[position]
            values = frame[column].tolist()
            for row, value in enumerate(values):
                key = _value_key(value)
                try:
                    codes[row, position] = mapping[key]
                except KeyError as error:  # pragma: no cover - caller bug guard
                    raise ExplanationError(
                        f"Value for feature {column!r} was not registered in the lossless codec."
                    ) from error
        return codes

    def decode(self, codes: Any) -> pd.DataFrame:
        array = np.asarray(codes)
        if array.ndim == 1:
            array = array.reshape(1, -1)
        if array.shape[1] != len(self.columns):
            raise ExplanationError("Encoded row does not match the feature count.")
        rows = [
            [self.inverse[position][int(code)] for position, code in enumerate(row)]
            for row in array
        ]
        return pd.DataFrame(rows, columns=self.columns)


def _assert_round_trip(codec: LosslessCodec, frame: pd.DataFrame, encoded: Any, label: str) -> None:
    """Verify encoded values decode back to the exact original values."""
    decoded = codec.decode(encoded)
    for column in codec.columns:
        original = frame[column].tolist()
        restored = decoded[column].tolist()
        if [_value_key(value) for value in original] != [_value_key(value) for value in restored]:
            raise ExplanationError(
                f"Lossless codec round-trip failed for {label} column {column!r}."
            )


def _selected_output(model: Any, features: Any, task: str, class_index: int | None) -> np.ndarray:
    if task == "classification":
        probabilities = np.asarray(model.predict_proba(features), dtype=float)
        if probabilities.ndim != 2 or class_index is None or not 0 <= class_index < probabilities.shape[1]:
            raise ExplanationError("Selected class index is outside the model's probability output.")
        return probabilities[:, class_index]
    return np.asarray(model.predict(features), dtype=float)


def _sample_background(
    frame: pd.DataFrame, size: int, seed: int
) -> tuple[pd.DataFrame, list[int]]:
    count = len(frame)
    if count == 0:
        raise ExplanationError("Background data contains no rows.")
    actual = min(size, count)
    rng = np.random.default_rng(seed)
    positions = rng.permutation(count)[:actual]
    subset = frame.iloc[positions]
    return subset, [int(position) + 1 for position in positions]


def _file_sha256(path: Path | str | None) -> str | None:
    if path is None:
        return None
    candidate = Path(path)
    if not candidate.is_file():
        return None
    return hashlib.sha256(candidate.read_bytes()).hexdigest()


def _json_safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (bool, str)):
        return value
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        number = float(value)
        return None if not math.isfinite(number) else number
    if _is_missing(value):
        return None
    return str(value)


def _prepare_request(
    loaded: LoadedModel,
    sample_frame: pd.DataFrame,
    background_frame: pd.DataFrame,
    *,
    row_position: int,
    mapping: list[str] | None = None,
    class_index: int | None = None,
    background_size: int = DEFAULT_BACKGROUND_SIZE,
    cycles: int = DEFAULT_CYCLES,
    seed: int = DEFAULT_SEED,
) -> dict[str, Any]:
    """Validate a request and build the lossless codec, without importing shap."""
    background_size = _validate_int(background_size, "background_size", 1, MAX_BACKGROUND_SIZE)
    cycles = _validate_int(cycles, "cycles", 1, MAX_CYCLES)
    if isinstance(seed, bool) or not isinstance(seed, int) or not SEED_MIN <= seed <= SEED_MAX:
        raise ExplanationError(f"seed must be an integer between {SEED_MIN} and {SEED_MAX}.")
    if isinstance(row_position, bool) or not isinstance(row_position, int) or row_position < 1:
        raise ExplanationError("row position must be a 1-based integer.")

    support = model_support(loaded)
    if not support.supported:
        raise ExplanationError(support.reason)
    task = support.task
    classes = list(loaded.metadata.get("classes") or [])
    if task == "classification":
        if class_index is None:
            raise ExplanationError(
                "Classification explanation requires an explicit class index into model classes."
            )
        if isinstance(class_index, bool) or not isinstance(class_index, int):
            raise ExplanationError("class index must be an integer.")
        if not 0 <= class_index < len(classes):
            raise ExplanationError(
                f"class index {class_index} is outside the model's {len(classes)} classes."
            )
    elif class_index is not None:
        raise ExplanationError("class index is only meaningful for classification.")

    if mapping is not None:
        if not isinstance(mapping, list) or any(not isinstance(name, str) for name in mapping):
            raise ExplanationError("The feature mapping must be a list of column names.")
        recorded = loaded.metadata.get("feature_names")
        if recorded and list(mapping) != list(recorded):
            raise ExplanationError(
                "A manual feature mapping is not needed for a model with named predictors; "
                "it must match the model's recorded predictor names."
            )

    if not isinstance(sample_frame, pd.DataFrame) or not isinstance(background_frame, pd.DataFrame):
        raise ExplanationError("Sample and background data must be pandas DataFrames.")
    if row_position > len(sample_frame):
        raise ExplanationError(
            f"row position {row_position} is outside the {len(sample_frame)} data rows."
        )

    sample_check = compatibility_check(loaded, sample_frame, mapping)
    if not sample_check["compatible"]:
        raise ExplanationError(
            "Sample data is incompatible with the model: "
            + "; ".join(error["message"] for error in sample_check["errors"])
        )
    background_check = compatibility_check(loaded, background_frame, mapping)
    if not background_check["compatible"]:
        raise ExplanationError(
            "Background data is incompatible with the model: "
            + "; ".join(error["message"] for error in background_check["errors"])
        )
    feature_order = list(sample_check["feature_order"])
    if list(background_check["feature_order"]) != feature_order:
        raise ExplanationError("Sample and background feature order disagree.")
    if not feature_order:
        raise ExplanationError("The model requires at least one predictor.")
    if len(feature_order) > MAX_FEATURES:
        raise ExplanationError(
            f"{len(feature_order)} predictors exceed the {MAX_FEATURES}-predictor explanation limit."
        )

    background_total_rows = len(background_frame)
    background_subset, background_positions = _sample_background(
        background_frame, background_size, seed
    )
    background_actual = len(background_subset)
    max_evals = cycles * (2 * len(feature_order) + 1)
    estimated_rows = background_actual * max_evals
    if estimated_rows > MAX_MODEL_ROWS:
        raise ExplanationError(
            f"Requested background {background_actual} x max_evals {max_evals} = "
            f"{estimated_rows} model rows exceeds the {MAX_MODEL_ROWS} row budget; "
            "reduce background_size or cycles."
        )
    row_cap = background_actual * (max_evals + COUNTER_MARGIN_ROWS) + 16

    sample_row = sample_frame.loc[:, feature_order].iloc[[row_position - 1]].reset_index(drop=True)
    background_rows = background_subset.loc[:, feature_order].reset_index(drop=True)
    codec = LosslessCodec.build([sample_row, background_rows], feature_order)
    encoded_sample = codec.encode_frame(sample_row)
    encoded_background = codec.encode_frame(background_rows)
    _assert_round_trip(codec, sample_row, encoded_sample, "sample")
    _assert_round_trip(codec, background_rows, encoded_background, "background")
    return {
        "task": task,
        "support": support,
        "classes": classes,
        "feature_order": [str(name) for name in feature_order],
        "sample_row": sample_row,
        "background_rows": background_rows,
        "background_total_rows": background_total_rows,
        "background_size_requested": background_size,
        "background_size_actual": background_actual,
        "background_positions": background_positions,
        "max_evals": max_evals,
        "estimated_rows": estimated_rows,
        "row_cap": row_cap,
        "codec": codec,
        "encoded_sample": encoded_sample,
        "encoded_background": encoded_background,
        "class_index": class_index,
        "target_class": classes[class_index] if task == "classification" else None,
        "output_space": "probability" if task == "classification" else "predicted_value",
        "feature_mapping": list(mapping) if mapping is not None else None,
        "manual_mapping": bool(sample_check["manual_mapping"]),
        "seed": seed,
    }


def plan_explanation(
    loaded: LoadedModel,
    sample_frame: pd.DataFrame,
    background_frame: pd.DataFrame,
    *,
    row_position: int,
    mapping: list[str] | None = None,
    class_index: int | None = None,
    background_size: int = DEFAULT_BACKGROUND_SIZE,
    cycles: int = DEFAULT_CYCLES,
    seed: int = DEFAULT_SEED,
) -> dict[str, Any]:
    """Validate a request for ``--check-only`` without importing shap or fitting."""
    prepared = _prepare_request(
        loaded,
        sample_frame,
        background_frame,
        row_position=row_position,
        mapping=mapping,
        class_index=class_index,
        background_size=background_size,
        cycles=cycles,
        seed=seed,
    )
    return {
        "supported": True,
        "task": prepared["task"],
        "model_family": prepared["support"].family,
        "estimator_class": prepared["support"].estimator_class,
        "fit_scope": prepared["support"].fit_scope,
        "output_space": prepared["output_space"],
        "classes": [_json_safe(label) for label in prepared["classes"]],
        "target_class_index": prepared["class_index"],
        "target_class": _json_safe(prepared["target_class"]),
        "feature_count": len(prepared["feature_order"]),
        "feature_order": prepared["feature_order"],
        "feature_mapping": prepared["feature_mapping"],
        "manual_mapping": prepared["manual_mapping"],
        "cycles": cycles,
        "max_evals": prepared["max_evals"],
        "seed": seed,
        "seed_supported_range": [SEED_MIN, SEED_MAX],
        "background_size_requested": background_size,
        "background_size_actual": prepared["background_size_actual"],
        "background_row_count": prepared["background_total_rows"],
        "background_positions": prepared["background_positions"],
        "estimated_model_rows": prepared["estimated_rows"],
        "model_row_budget": MAX_MODEL_ROWS,
        "model_row_cap": prepared["row_cap"],
        "shap_installed": shap_version() is not None,
        "approximate": True,
    }


def explain_row(
    loaded: LoadedModel,
    sample_frame: pd.DataFrame,
    background_frame: pd.DataFrame,
    *,
    row_position: int,
    mapping: list[str] | None = None,
    class_index: int | None = None,
    background_size: int = DEFAULT_BACKGROUND_SIZE,
    cycles: int = DEFAULT_CYCLES,
    seed: int = DEFAULT_SEED,
    model_file: Path | str | None = None,
    input_file: Path | str | None = None,
    background_file: Path | str | None = None,
) -> dict[str, Any]:
    """Explain one 1-based row position against a sampled background."""
    prepared = _prepare_request(
        loaded,
        sample_frame,
        background_frame,
        row_position=row_position,
        mapping=mapping,
        class_index=class_index,
        background_size=background_size,
        cycles=cycles,
        seed=seed,
    )
    task = prepared["task"]
    support = prepared["support"]
    classes = prepared["classes"]
    feature_order = prepared["feature_order"]
    sample_row = prepared["sample_row"]
    background_actual = prepared["background_size_actual"]
    background_total_rows = prepared["background_total_rows"]
    background_positions = prepared["background_positions"]
    max_evals = prepared["max_evals"]
    estimated_rows = prepared["estimated_rows"]
    row_cap = prepared["row_cap"]
    codec = prepared["codec"]
    encoded_sample = prepared["encoded_sample"]
    encoded_background = prepared["encoded_background"]
    class_index = prepared["class_index"]
    target_class = prepared["target_class"]
    output_space = prepared["output_space"]

    shap = _import_shap()
    counter = {"model_calls": 0, "model_rows": 0}

    def count_rows(rows: int) -> None:
        counter["model_calls"] += 1
        counter["model_rows"] += rows
        if counter["model_rows"] > row_cap:
            raise ExplanationError(
                f"Explanation exceeded the enforced model-row cap ({row_cap}); aborted."
            )

    def model_fn(codes: Any) -> np.ndarray:
        array = np.asarray(codes)
        if array.ndim == 1:
            array = array.reshape(1, -1)
        count_rows(int(array.shape[0]))
        decoded = codec.decode(array)
        features = model_input(loaded, decoded, mapping)
        return _selected_output(loaded.model, features, task, class_index)

    # Direct validation call on the exact original row, counted in the budget.
    original_features = model_input(loaded, sample_row, mapping)
    count_rows(1)
    pipeline_output = float(_selected_output(loaded.model, original_features, task, class_index)[0])
    if not np.isfinite(pipeline_output):
        raise ExplanationError("The model returned a non-finite output; no explanation was written.")

    rng_state = np.random.get_state()
    try:
        masker = shap.maskers.Independent(encoded_background, max_samples=background_actual)
        explainer = shap.PermutationExplainer(
            model_fn, masker, link=shap.links.identity, seed=seed, max_evals=max_evals
        )
        explanation = explainer(encoded_sample, max_evals=max_evals)
    finally:
        np.random.set_state(rng_state)

    contributions = np.asarray(explanation.values, dtype=float)
    if contributions.ndim > 1:
        contributions = contributions.reshape(-1)
    if contributions.shape[0] != len(feature_order):
        raise ExplanationError("Explainer returned an unexpected contribution shape.")
    if not np.all(np.isfinite(contributions)):
        raise ExplanationError("The explainer returned a non-finite contribution.")
    base_values = np.asarray(explanation.base_values, dtype=float).reshape(-1)
    if base_values.size != 1:
        raise ExplanationError("Explainer returned an unexpected base value shape.")
    base_value = float(base_values[0])
    if not np.isfinite(base_value):
        raise ExplanationError("The explainer returned a non-finite base value.")
    reconstruction = float(base_value + contributions.sum())
    abs_error = abs(reconstruction - pipeline_output)
    if not np.isclose(
        reconstruction, pipeline_output, rtol=RECONSTRUCTION_RTOL, atol=RECONSTRUCTION_ATOL
    ):
        raise ExplanationError(
            "Reconstruction check failed: base + sum(contributions) does not reproduce the "
            f"pipeline output (abs error {abs_error:.3e}). No explanation was written."
        )

    values = sample_row.iloc[0]
    records = []
    for position, name in enumerate(feature_order):
        raw_value = values[name]
        records.append(
            {
                "name": str(name),
                "value": _json_safe(raw_value),
                "missing": bool(_is_missing(raw_value)),
                "value_type": _value_key(raw_value)[0],
                "contribution": float(contributions[position]),
            }
        )
    records.sort(key=lambda record: abs(record["contribution"]), reverse=True)
    for rank, record in enumerate(records, start=1):
        record["rank"] = rank
        record["abs_contribution"] = abs(record["contribution"])
        record["direction"] = "positive" if record["contribution"] >= 0 else "negative"

    metadata = {
        "schema_version": EXPLANATION_SCHEMA_VERSION,
        "algorithm": ALGORITHM,
        "approximate": True,
        "exact_shap": False,
        "shap_version": shap_version(),
        "link": "identity",
        "cycles": cycles,
        "max_evals": max_evals,
        "seed": seed,
        "seed_supported_range": [SEED_MIN, SEED_MAX],
        "feature_count": len(feature_order),
        "feature_order": [str(name) for name in feature_order],
        "feature_mapping": prepared["feature_mapping"],
        "manual_mapping": prepared["manual_mapping"],
        "task": task,
        "model_family": support.family,
        "estimator_class": support.estimator_class,
        "model_file": str(model_file) if model_file is not None else None,
        "model_sha256": _file_sha256(model_file),
        "fit_scope": support.fit_scope,
        "input_file": str(input_file) if input_file is not None else None,
        "input_sha256": _file_sha256(input_file),
        "sample_row_position": row_position,
        "sample_features": records,
        "codec": "lossless_integer_codes",
        "background_file": str(background_file) if background_file is not None else None,
        "background_sha256": _file_sha256(background_file),
        "background_size_requested": background_size,
        "background_size_actual": background_actual,
        "background_row_count": background_total_rows,
        "background_positions": background_positions,
        "classes": [_json_safe(label) for label in classes],
        "target_class_index": class_index,
        "target_class": _json_safe(target_class),
        "output_space": output_space,
        "base_value": base_value,
        "model_output": pipeline_output,
        "reconstruction": reconstruction,
        "reconstruction_abs_error": abs_error,
        "tolerance": {"atol": RECONSTRUCTION_ATOL, "rtol": RECONSTRUCTION_RTOL},
        "finite_outputs_verified": True,
        "model_calls": counter["model_calls"],
        "model_rows": counter["model_rows"],
        "model_row_budget": estimated_rows,
        "model_row_cap": row_cap,
        "numpy_random_state_restored": True,
        "no_model_fit": True,
        "limitations": list(_LIMITATIONS),
    }
    return metadata


def _artifact_paths(output_dir: Path) -> dict[str, Path]:
    return {
        "json": output_dir / "shap_explanation.json",
        "csv": output_dir / "shap_contributions.csv",
        "png": output_dir / "shap_waterfall.png",
        "notes": output_dir / "shap_explanation_notes.md",
    }


def build_waterfall_segments(result: dict[str, Any], top_n: int = WATERFALL_TOP_N) -> list[dict]:
    """Build cumulative baseline-to-output waterfall segments.

    Each returned segment starts where the previous one ended, so the final
    segment ends at ``model_output``. The remainder of predictors beyond
    ``top_n`` is folded into a single signed "other" segment; no contribution is
    dropped. Returned items are ordered by descending absolute contribution.
    """
    records = sorted(
        result["sample_features"],
        key=lambda record: abs(float(record["contribution"])),
        reverse=True,
    )
    top = records[:top_n]
    remainder = records[top_n:]
    items: list[tuple[str, float]] = [
        (f"{record['name']} = {_display_value(record)}", float(record["contribution"]))
        for record in top
    ]
    if remainder:
        items.append(
            (
                f"other {len(remainder)} predictors (sum)",
                float(sum(float(record["contribution"]) for record in remainder)),
            )
        )
    running = float(result["base_value"])
    segments = []
    for label, value in items:
        start = running
        end = running + value
        segments.append({"label": label, "contribution": value, "start": start, "end": end})
        running = end
    return segments


def _display_value(record: dict[str, Any]) -> str:
    if record.get("missing"):
        return "<missing>"
    value = record.get("value")
    return "" if value is None else str(value)


def _render_waterfall(result: dict[str, Any], path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import font_manager
    from matplotlib import pyplot as plt

    from psyml.reporting.permutation import _cjk_font_families

    # Prefer a CJK-capable family so Unicode predictor names stay readable on the
    # standalone PNG; keep DejaVu for Latin and symbols.
    families = _cjk_font_families(font_manager)
    if families:
        matplotlib.rcParams["font.family"] = [*families, "DejaVu Sans"]
    matplotlib.rcParams["axes.unicode_minus"] = False

    segments = build_waterfall_segments(result)
    base_value = float(result["base_value"])
    model_output = float(result["model_output"])
    tolerance = result["tolerance"]
    if not segments or not np.isclose(
        segments[-1]["end"],
        model_output,
        rtol=float(tolerance["rtol"]),
        atol=float(tolerance["atol"]),
    ):
        raise ExplanationError(
            "Waterfall segments do not reconstruct the model output; rendering aborted."
        )

    wrapped = ["\n".join(textwrap.wrap(segment["label"], 34)) for segment in segments]
    figure, axis = plt.subplots(figsize=(10.5, max(3.4, 0.5 * len(segments) + 1.8)))
    unit = "probability" if result["output_space"] == "probability" else "predicted value"
    target = (
        f", class {result['target_class']!r}"
        if result["output_space"] == "probability"
        else ""
    )
    for index, segment in enumerate(segments):
        start, end = segment["start"], segment["end"]
        color = "#c0392b" if end >= start else "#2471a3"
        axis.barh(index, end - start, left=start, height=0.62, color=color)
        axis.text(
            end,
            index,
            f" {segment['contribution']:+.4g}",
            va="center",
            ha="left" if end >= start else "right",
            fontsize=8,
        )
    axis.set_yticks(range(len(segments)))
    axis.set_yticklabels(wrapped, fontsize=9)
    axis.invert_yaxis()
    axis.axvline(base_value, color="#7f8c8d", linestyle="--", linewidth=1.2)
    axis.axvline(model_output, color="#27ae60", linestyle="-.", linewidth=1.2)
    top_marker = -1.0
    bottom_marker = len(segments) - 0.3
    axis.scatter([base_value], [top_marker], color="#7f8c8d", s=22, zorder=3)
    axis.scatter([model_output], [bottom_marker], color="#27ae60", s=22, zorder=3)
    axis.annotate(
        f"base {base_value:.6g}",
        xy=(base_value, top_marker),
        xytext=(0, -12),
        textcoords="offset points",
        ha="center",
        va="top",
        fontsize=8.5,
        color="#5d6d7e",
    )
    axis.annotate(
        f"output {model_output:.6g}",
        xy=(model_output, bottom_marker),
        xytext=(0, 12),
        textcoords="offset points",
        ha="center",
        va="bottom",
        fontsize=8.5,
        color="#1e8449",
    )
    axis.set_ylim(len(segments) + 0.1, -1.6)
    span = [segment[key] for segment in segments for key in ("start", "end")] + [base_value, model_output]
    low, high = min(span), max(span)
    padding = (high - low) * 0.12 or 0.01
    axis.set_xlim(low - padding, high + padding)
    axis.set_xlabel(f"output value ({unit}{target}); bars step from the previous running value")
    axis.set_title(
        f"Approximate single-sample SHAP ({result['algorithm']}, {result['cycles']} cycles)\n"
        f"cumulative base {base_value:.6g} \u2192 output {model_output:.6g}"
    )
    figure.text(
        0.01,
        0.01,
        "Sampling-based approximation; not exact SHAP; not causal; not outer test performance.",
        fontsize=7,
        color="#555555",
    )
    figure.tight_layout(rect=(0, 0.03, 1, 1))
    figure.savefig(path, dpi=140)
    plt.close(figure)


def _notes_markdown(result: dict[str, Any]) -> str:
    unit = "probability" if result["output_space"] == "probability" else "predicted value"
    lines = [
        "# Single-sample SHAP explanation",
        "",
        f"- Algorithm: {result['algorithm']} (shap {result['shap_version']}), approximate: yes",
        f"- Task: {result['task']}; output: {unit}",
        f"- Model family: {result['model_family']}; fit scope: {result['fit_scope']}",
        f"- Base value: {result['base_value']!r}",
        f"- Model output: {result['model_output']!r}",
        (
            f"- Reconstruction error: {result['reconstruction_abs_error']:.3e} "
            f"(tolerance atol {result['tolerance']['atol']}, rtol {result['tolerance']['rtol']})"
        ),
        (
            f"- Background rows: {result['background_size_actual']} of "
            f"{result['background_row_count']} (requested {result['background_size_requested']})"
        ),
        f"- Permutation cycles: {result['cycles']}; seed: {result['seed']}",
        f"- Sample row (1-based, no header): {result['sample_row_position']}",
        "",
        (
            "Contributions are additive on the selected output above and are written "
            "for every predictor in `shap_contributions.csv`."
        ),
        "",
        "## Limitations",
        "",
    ]
    lines.extend(f"- {note}" for note in result["limitations"])
    lines.append("")
    return "\n".join(lines)


def _write_contributions(result: dict[str, Any], path: Path) -> None:
    frame = pd.DataFrame(result["sample_features"])
    frame[
        [
            "rank",
            "name",
            "value",
            "missing",
            "value_type",
            "contribution",
            "abs_contribution",
            "direction",
        ]
    ].to_csv(path, index=False)


def _publish(staged: dict[str, Path], targets: dict[str, Path]) -> None:
    """Replace target artifacts, restoring prior files if publishing fails."""
    backups: dict[str, tuple[Path, Path]] = {}
    published: list[str] = []
    try:
        # JSON is the completion marker and is published last.
        for name in ("csv", "png", "notes", "json"):
            target = targets[name]
            if target.exists():
                backup = target.with_name(f"{target.name}.psyml-backup-{uuid.uuid4().hex}")
                os.replace(target, backup)
                backups[name] = (target, backup)
            os.replace(staged[name], target)
            published.append(name)
    except Exception:
        for name in published:
            target = targets[name]
            if target.exists():
                target.unlink()
        for target, backup in backups.values():
            if backup.exists():
                os.replace(backup, target)
        raise
    else:
        for _, backup in backups.values():
            backup.unlink(missing_ok=True)


def write_explanation(
    result: dict[str, Any],
    output_dir: Path | str,
    *,
    protected_paths: tuple[Path | str | None, ...] = (),
) -> dict[str, str]:
    """Write the four explanation artifacts transactionally.

    Every artifact is prepared in a private staging directory first; the JSON
    completion marker is published last, so an interrupted run never leaves a
    complete-looking result. This first version always requires a new or empty
    output directory and never replaces existing files, so a failed or killed
    run cannot mix old and new artifacts. Input files are always protected.
    """
    directory = Path(output_dir)
    if directory.exists() and directory.is_file():
        raise ExplanationError(f"Output path is an existing file: {directory}")
    protected = {Path(path).resolve() for path in protected_paths if path is not None}
    paths = _artifact_paths(directory)
    for name, path in paths.items():
        if path.resolve() in protected:
            raise ExplanationError(
                f"The explanation artifact {path.name!r} would overwrite a protected input file."
            )
    if directory.exists() and any(directory.iterdir()):
        raise ExplanationError(
            f"Output directory is not empty: {directory}. Choose a new or empty directory; "
            "this version never overwrites existing explanation output."
        )
    directory.mkdir(parents=True, exist_ok=True)
    staging = directory / f".psyml-explanation-staging-{os.getpid()}-{uuid.uuid4().hex}"
    staging.mkdir(exist_ok=False)
    try:
        staged = {name: staging / path.name for name, path in paths.items()}
        _write_contributions(result, staged["csv"])
        _render_waterfall(result, staged["png"])
        staged["notes"].write_text(_notes_markdown(result), encoding="utf-8")
        document = {
            **result,
            "artifacts": {
                name: path.name for name, path in paths.items()
            },
        }
        staged["json"].write_text(
            json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        for name, path in staged.items():
            if not path.is_file() or path.stat().st_size == 0:
                raise ExplanationError(f"Prepared explanation artifact {name!r} is missing or empty.")
        _publish(staged, paths)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return {name: str(path) for name, path in paths.items()}
