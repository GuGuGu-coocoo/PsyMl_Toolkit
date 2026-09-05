"""Lightweight catalog of supported estimator names."""

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


# JSON clients such as Godot decode all numbers as doubles. These fields use
# integer counts; genuine fractions for min_samples_* remain fractions.
INTEGER_PARAMETERS = {
    "n_neighbors", "n_estimators", "max_depth", "min_samples_leaf", "min_samples_split",
    "max_leaf_nodes", "max_iter", "random_state", "cv", "n_jobs", "degree", "n_components",
}


def normalize_parameter(parameter: str, value: object) -> object:
    """Restore integral JSON counts without rounding or changing fractional values."""
    # 1.0 is a valid fraction for sklearn min_samples_*, whereas counts >= 2
    # cannot be fractions. Keep existing Python/CLI fraction semantics intact.
    if parameter in {"min_samples_leaf", "min_samples_split"} and value == 1.0 and isinstance(value, float):
        return value
    if parameter in INTEGER_PARAMETERS and isinstance(value, float) and value.is_integer():
        return int(value)
    if parameter == "hidden_layer_sizes" and isinstance(value, list):
        return [int(v) if isinstance(v, float) and v.is_integer() else v for v in value]
    return value
