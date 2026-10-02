"""Lightweight catalog of supported estimator names."""

from typing import Any

CLASSIFICATION_MODELS = {
    "knn",
    "random_forest",
    "svm",
    "mlp",
    "decision_tree",
    "stacking",
    "dummy",
    "logistic_regression",
    "gaussian_nb",
    "lda",
    "qda",
    "gradient_boosting",
}
REGRESSION_MODELS = {
    "knn",
    "lasso",
    "mlp",
    "random_forest",
    "svr",
    "dummy",
    "linear_regression",
    "ridge",
    "elastic_net",
    "decision_tree",
    "gradient_boosting",
}

# Deliberately small, defensible starting grids. They are not universal optima:
# every value is evaluated inside the training portion of the outer validation.
QUICK_PARAMETER_GRIDS = {
    "classification": {
        "knn": {"n_neighbors": [3, 5, 11], "weights": ["uniform", "distance"]},
        "random_forest": {
            "n_estimators": [100, 300],
            "max_depth": [None, 10],
            "min_samples_leaf": [1, 3],
        },
        "svm": {"C": [0.1, 1.0, 10.0], "kernel": ["linear", "rbf"]},
        "mlp": {"alpha": [0.0001, 0.001, 0.01], "learning_rate_init": [0.0005, 0.001]},
        "decision_tree": {"max_depth": [None, 5, 10], "min_samples_leaf": [1, 3, 5]},
        "dummy": {"strategy": ["prior", "stratified"]},
        "logistic_regression": {"C": [0.1, 1.0, 10.0], "class_weight": [None, "balanced"]},
        "gaussian_nb": {"var_smoothing": [1e-11, 1e-9, 1e-7]},
        "lda": {"solver": ["svd", "lsqr"]},
        "qda": {"reg_param": [0.0, 0.1, 0.5]},
        "gradient_boosting": {
            "n_estimators": [100, 200],
            "learning_rate": [0.03, 0.1],
            "max_depth": [2, 3],
        },
        "stacking": {"passthrough": [False, True]},
    },
    "regression": {
        "knn": {"n_neighbors": [3, 5, 11], "weights": ["uniform", "distance"]},
        "lasso": {"alpha": [0.01, 0.1, 1.0, 10.0]},
        "mlp": {"alpha": [0.0001, 0.001, 0.01], "learning_rate_init": [0.0005, 0.001]},
        "random_forest": {
            "n_estimators": [100, 300],
            "max_depth": [None, 10],
            "min_samples_leaf": [1, 3],
        },
        "svr": {
            "C": [0.1, 1.0, 10.0],
            "epsilon": [0.01, 0.1],
            "kernel": ["linear", "rbf"],
        },
        "dummy": {"strategy": ["mean", "median"]},
        "linear_regression": {"fit_intercept": [True, False]},
        "ridge": {"alpha": [0.01, 0.1, 1.0, 10.0, 100.0]},
        "elastic_net": {"alpha": [0.01, 0.1, 1.0], "l1_ratio": [0.1, 0.5, 0.9]},
        "decision_tree": {"max_depth": [None, 5, 10], "min_samples_leaf": [1, 3, 5]},
        "gradient_boosting": {
            "n_estimators": [100, 200],
            "learning_rate": [0.03, 0.1],
            "max_depth": [2, 3],
        },
    },
}


def supported_models(task: str) -> tuple[str, ...]:
    """Return supported model names for a task."""
    if task == "classification":
        return tuple(sorted(CLASSIFICATION_MODELS))
    if task == "regression":
        return tuple(sorted(REGRESSION_MODELS))
    raise ValueError(f"Unsupported task: {task}")


def quick_parameter_grid(task: str, model_name: str) -> dict[str, list[object]]:
    """Return a copy of the bounded recommended grid for one estimator."""
    if model_name not in supported_models(task):
        raise ValueError(f"Unsupported {task} model: {model_name}")
    return {
        parameter: list(values)
        for parameter, values in QUICK_PARAMETER_GRIDS[task].get(model_name, {}).items()
    }


def validate_model_parameters(
    task: str,
    model_name: str,
    params: dict[str, Any],
    *,
    source: str,
) -> None:
    """Reject estimator parameters that scikit-learn cannot accept as written.

    PsyML preserves JSON number types exactly: ``1`` is an integer count and
    ``1.0`` is a decimal fraction, and for parameters such as ``max_features``
    the two select different models. Nothing is rounded or silently replaced;
    invalid input raises a ``ValueError`` that names the parameter, the received
    value and its type before any fitting or output writing starts.
    """
    from psyml.models.factory import build_model

    estimator = build_model(task, model_name, 0, {})
    allowed = set(estimator.get_params())
    unknown = sorted(set(params) - allowed)
    if unknown:
        names = ", ".join(unknown)
        raise ValueError(f"Unknown parameters for {model_name}: {names}")
    for parameter, value in params.items():
        _validate_single_parameter(estimator, model_name, parameter, value, source=source)


def _validate_single_parameter(
    estimator: Any, model_name: str, parameter: str, value: Any, *, source: str
) -> None:
    try:
        estimator.set_params(**{parameter: value})
    except ValueError as error:
        raise ValueError(
            f"{model_name}: the {source} '{parameter}' = {value!r} cannot be applied: {error}"
        ) from error
    validator = getattr(estimator, "_validate_params", None)
    if validator is None:
        return
    try:
        validator()
    except ValueError as error:
        raise ValueError(
            f"{model_name}: the {source} '{parameter}' = {value!r} "
            f"({type(value).__name__}) is not accepted by scikit-learn: {error}"
            f"{_integer_form_hint(estimator, parameter, value)}"
        ) from error


def _integer_form_hint(estimator: Any, parameter: str, value: Any) -> str:
    """Point whole-number decimals to the integer form when that form is valid."""
    if not isinstance(value, float) or not value.is_integer():
        return ""
    validator = getattr(estimator, "_validate_params", None)
    if validator is None:
        return ""
    try:
        estimator.set_params(**{parameter: int(value)})
        validator()
    except ValueError:
        return ""
    return (
        f" PsyML preserves JSON number types: write {int(value)} (without a decimal "
        "point) if you meant the integer count, then save the configuration again."
    )
