"""Metrics calculated only from held-out predictions."""


import numpy as np
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)


def classification_metrics(model, features, observed, predicted) -> dict[str, float]:
    """Calculate classification metrics and ROC-AUC when it is meaningful."""
    metrics = {
        "accuracy": float(accuracy_score(observed, predicted)),
        "balanced_accuracy": float(balanced_accuracy_score(observed, predicted)),
        "precision_weighted": float(precision_score(observed, predicted, average="weighted", zero_division=0)),
        "recall_weighted": float(recall_score(observed, predicted, average="weighted", zero_division=0)),
        "f1_weighted": float(f1_score(observed, predicted, average="weighted", zero_division=0)),
    }
    labels = np.unique(observed)
    if len(labels) == 2:
        if hasattr(model, "predict_proba"):
            scores = model.predict_proba(features)[:, 1]
        elif hasattr(model, "decision_function"):
            scores = model.decision_function(features)
        else:
            return metrics
        metrics["roc_auc"] = float(roc_auc_score(observed, scores))
    return metrics


def regression_metrics(observed, predicted) -> dict[str, float]:
    """Calculate regression metrics from held-out predictions."""
    mse = mean_squared_error(observed, predicted)
    return {
        "r2": float(r2_score(observed, predicted)),
        "mae": float(mean_absolute_error(observed, predicted)),
        "rmse": float(np.sqrt(mse)),
    }
