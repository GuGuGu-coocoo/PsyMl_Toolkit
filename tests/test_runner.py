import json

import numpy as np
import pandas as pd

from psyml import ExperimentConfig, run_experiment
from psyml.validation import split_train_test


def _classification_frame() -> pd.DataFrame:
    values = np.arange(40, dtype=float)
    return pd.DataFrame(
        {
            "continuous": values,
            "category": ["a", "b"] * 20,
            "target": [0, 1] * 20,
        }
    )


def test_classification_pipeline_fits_scaler_to_training_partition_only(tmp_path):
    frame = _classification_frame()
    config = ExperimentConfig(
        task="classification",
        target_column="target",
        model_name="svm",
        output_dir=tmp_path / "classification",
        random_seed=7,
    )

    result = run_experiment(config, frame)

    train_x, _, _, _ = split_train_test(
        frame[["continuous", "category"]],
        frame["target"],
        "classification",
        config.test_size,
        config.random_seed,
    )
    scaler = result.model.named_steps["preprocess"].named_transformers_["numeric"].named_steps["scale"]
    assert scaler.mean_[0] == train_x["continuous"].mean()
    assert scaler.mean_[0] != frame["continuous"].mean()
    assert {"accuracy", "balanced_accuracy", "f1_weighted", "roc_auc"} <= result.metrics.keys()
    assert (config.output_dir / "metrics.csv").is_file()
    assert (config.output_dir / "predictions.csv").is_file()
    saved_config = json.loads((config.output_dir / "config.json").read_text(encoding="utf-8"))
    assert saved_config["random_seed"] == 7


def test_regression_outputs_holdout_metrics(tmp_path):
    features = np.linspace(0, 10, 48)
    frame = pd.DataFrame({"feature": features, "target": 2 * features + 1})
    config = ExperimentConfig(
        task="regression",
        target_column="target",
        model_name="lasso",
        output_dir=tmp_path / "regression",
        random_seed=3,
        model_params={"alpha": 0.001},
    )

    result = run_experiment(config, frame)

    assert {"r2", "mae", "rmse"} == result.metrics.keys()
    assert result.metrics["r2"] > 0.99
    assert len(result.predictions) > 0
