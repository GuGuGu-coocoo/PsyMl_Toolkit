"""Metrics calculated only from held-out predictions."""

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
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
        "precision_weighted": float(
            precision_score(observed, predicted, average="weighted", zero_division=0)
        ),
        "recall_weighted": float(
            recall_score(observed, predicted, average="weighted", zero_division=0)
        ),
        "f1_weighted": float(f1_score(observed, predicted, average="weighted", zero_division=0)),
        "precision_macro": float(
            precision_score(observed, predicted, average="macro", zero_division=0)
        ),
        "recall_macro": float(recall_score(observed, predicted, average="macro", zero_division=0)),
        "f1_macro": float(f1_score(observed, predicted, average="macro", zero_division=0)),
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
    elif len(labels) > 2 and hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(features)
        metrics["roc_auc_ovr_weighted"] = float(
            roc_auc_score(observed, probabilities, multi_class="ovr", average="weighted")
        )
    return metrics


def classification_confusion_matrix(observed, predicted) -> pd.DataFrame:
    """Return a labelled confusion matrix suitable for CSV export."""
    labels = np.unique(np.concatenate([np.asarray(observed), np.asarray(predicted)]))
    matrix = confusion_matrix(observed, predicted, labels=labels)
    return pd.DataFrame(
        matrix,
        index=[f"observed_{label}" for label in labels],
        columns=[f"predicted_{label}" for label in labels],
    )


def regression_metrics(observed, predicted) -> dict[str, float]:
    """Calculate regression metrics from held-out predictions."""
    mse = mean_squared_error(observed, predicted)
    return {
        "r2": float(r2_score(observed, predicted)),
        "mae": float(mean_absolute_error(observed, predicted)),
        "rmse": float(np.sqrt(mse)),
    }
