"""JSON records of actual estimator configuration, excluding learned attributes."""

import math
from pathlib import Path

import numpy as np
from sklearn.base import BaseEstimator


def parameter_value(value):
    """Preserve structured parameter values without truncated estimator repr strings."""
    if isinstance(value, BaseEstimator):
        return {
            "class": f"{type(value).__module__}.{type(value).__qualname__}",
            "parameters": effective_parameters(value),
        }
    if isinstance(value, dict):
        return {str(key): parameter_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [parameter_value(item) for item in value]
    if isinstance(value, np.generic):
        return parameter_value(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if callable(value):
        return f"{value.__module__}.{value.__qualname__}"
    return str(value)


def effective_parameters(estimator):
    """Read constructor hyperparameters, including defaults and nested estimators."""
    return {key: parameter_value(value)
            for key, value in estimator.get_params(deep=False).items()}
