"""Construct estimators without embedding data paths or global configuration."""

from typing import Any

from sklearn.discriminant_analysis import LinearDiscriminantAnalysis, QuadraticDiscriminantAnalysis
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import (
    GradientBoostingClassifier,
    GradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
    StackingClassifier,
)
from sklearn.linear_model import ElasticNet, Lasso, LinearRegression, LogisticRegression, Ridge
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.neural_network import MLPClassifier, MLPRegressor
from sklearn.svm import SVC, SVR
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

from psyml.models.catalog import supported_models


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
    if name == "dummy":
        return DummyClassifier(**params)
    if name == "logistic_regression":
        return LogisticRegression(max_iter=1000, random_state=random_seed, **params)
    if name == "gaussian_nb":
        return GaussianNB(**params)
    if name == "lda":
        return LinearDiscriminantAnalysis(**params)
    if name == "qda":
        return QuadraticDiscriminantAnalysis(**params)
    if name == "gradient_boosting":
        return GradientBoostingClassifier(random_state=random_seed, **params)
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
    if name == "svr":
        return SVR(**params)
    if name == "dummy":
        return DummyRegressor(**params)
    if name == "linear_regression":
        return LinearRegression(**params)
    if name == "ridge":
        return Ridge(random_state=random_seed, **params)
    if name == "elastic_net":
        return ElasticNet(random_state=random_seed, **params)
    if name == "decision_tree":
        return DecisionTreeRegressor(random_state=random_seed, **params)
    return GradientBoostingRegressor(random_state=random_seed, **params)
