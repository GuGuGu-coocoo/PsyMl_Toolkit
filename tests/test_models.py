import numpy as np
import pandas as pd
import pytest

from psyml import ExperimentConfig, run_experiment
from psyml.models import supported_models


@pytest.mark.parametrize(
    "model_name",
    supported_models("regression"),
)
def test_all_regression_models_run(model_name, tmp_path):
    rng = np.random.default_rng(11)
    features = rng.normal(size=(50, 3))
    frame = pd.DataFrame(features, columns=["a", "b", "c"])
    frame["target"] = 2 * frame["a"] - frame["b"] + rng.normal(scale=0.1, size=50)
    config = ExperimentConfig(
        task="regression",
        target_column="target",
        model_name=model_name,
        output_dir=tmp_path / model_name,
    )

    result = run_experiment(config, frame)

    assert {"r2", "mae", "rmse"} == result.metrics.keys()


@pytest.mark.parametrize(
    "model_name",
    supported_models("classification"),
)
@pytest.mark.filterwarnings("ignore::sklearn.exceptions.ConvergenceWarning")
def test_all_classification_models_run(model_name, tmp_path):
    rng = np.random.default_rng(23)
    features = rng.normal(size=(90, 4))
    frame = pd.DataFrame(features, columns=["a", "b", "c", "d"])
    frame["target"] = np.argmax(
        np.column_stack([features[:, 0], features[:, 1], -features[:, 0] - features[:, 1]]),
        axis=1,
    )
    config = ExperimentConfig(
        task="classification",
        target_column="target",
        model_name=model_name,
        output_dir=tmp_path / model_name,
    )

    result = run_experiment(config, frame)

    assert {"accuracy", "balanced_accuracy", "precision_macro", "f1_macro"} <= result.metrics.keys()
    assert result.confusion_matrix is not None


def test_supported_model_catalog_contains_phase_10_models():
    assert {"linear_regression", "ridge", "elastic_net", "dummy"} <= set(
        supported_models("regression")
    )
    assert {"logistic_regression", "gaussian_nb", "lda", "qda", "dummy"} <= set(
        supported_models("classification")
    )
