"""Construct estimators without embedding data paths or global configuration."""

from typing import Any

from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, StackingClassifier
from sklearn.linear_model import Lasso, LogisticRegression
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.neural_network import MLPClassifier, MLPRegressor
from sklearn.svm import SVC, SVR
from sklearn.tree import DecisionTreeClassifier

CLASSIFICATION_MODELS = {
    "knn",
    "random_forest",
    "svm",
    "mlp",
    "decision_tree",
    "stacking",
}
REGRESSION_MODELS = {"knn", "lasso", "mlp", "random_forest", "svr"}


def supported_models(task: str) -> tuple[str, ...]:
    """Return supported model names for a task."""
    if task == "classification":
        return tuple(sorted(CLASSIFICATION_MODELS))
    if task == "regression":
        return tuple(sorted(REGRESSION_MODELS))
    raise ValueError(f"Unsupported task: {task}")


def build_model(task: str, model_name: str, random_seed: int, params: dict[str, Any]):
    """Build an unfitted scikit-learn estimator from explicit settings."""
    normalized = model_name.strip().lower()
    if normalized not in supported_models(task):
        choices = ", ".join(supported_models(task))
        raise ValueError(f"Unsupported {task} model '{model_name}'. Choices: {choices}")
    if task == "classification":
        return _build_classifier(normalized, random_seed, params)
    return _build_regressor(normalized, random_seed, params)


def _build_classifier(name: str, random_seed: int, params: dict[str, Any]):
    if name == "knn":
        return KNeighborsClassifier(**params)
    if name == "random_forest":
        return RandomForestClassifier(random_state=random_seed, **params)
    if name == "svm":
        return SVC(random_state=random_seed, **params)
    if name == "mlp":
        return MLPClassifier(random_state=random_seed, max_iter=500, **params)
    if name == "decision_tree":
        return DecisionTreeClassifier(random_state=random_seed, **params)
    estimators = [
        ("knn", KNeighborsClassifier()),
        ("random_forest", RandomForestClassifier(random_state=random_seed)),
        ("svm", SVC(random_state=random_seed)),
    ]
    return StackingClassifier(
        estimators=estimators,
        final_estimator=LogisticRegression(max_iter=500, random_state=random_seed),
        **params,
    )


def _build_regressor(name: str, random_seed: int, params: dict[str, Any]):
    if name == "knn":
        return KNeighborsRegressor(**params)
    if name == "lasso":
        return Lasso(random_state=random_seed, **params)
    if name == "mlp":
        return MLPRegressor(random_state=random_seed, max_iter=500, **params)
    if name == "random_forest":
        return RandomForestRegressor(random_state=random_seed, **params)
    return SVR(**params)
