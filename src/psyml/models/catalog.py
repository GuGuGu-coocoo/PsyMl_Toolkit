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


def supported_models(task: str) -> tuple[str, ...]:
    """Return supported model names for a task."""
    if task == "classification":
        return tuple(sorted(CLASSIFICATION_MODELS))
    if task == "regression":
        return tuple(sorted(REGRESSION_MODELS))
    raise ValueError(f"Unsupported task: {task}")
