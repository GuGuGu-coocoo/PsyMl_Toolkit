"""Persist the final full-data Pipeline with a small, inspectable sidecar."""

import hashlib
import json
import platform
import re
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import joblib
import sklearn

from psyml.models.parameters import effective_parameters, parameter_value

INDEPENDENT_SAVING_MESSAGE = (
    "Automatic model saving is disabled for independent validation mode "
    "because no global final model is selected."
)


def safe_name(value: str) -> str:
    """Stable portable names for models and prediction columns."""
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", str(value)).strip("_") or "model"


def save_final_model(pipeline, config, features) -> dict:
    """Called only after full-data fit; never select an estimator here."""
    directory = Path(config.output_dir) / "model"
    directory.mkdir(exist_ok=False)
    path = directory / f"best_{safe_name(config.model_name)}.joblib"
    estimator = pipeline.named_steps["model"]
    # This attached dictionary keeps ordinary joblib/Pipeline usability and supports
    # moving the model without its sidecar. It contains no participant rows.
    metadata = {
        "psyml_version": version("psyml-toolkit"),
        "python_version": platform.python_version(),
        "sklearn_version": sklearn.__version__,
        "created_time": datetime.now(timezone.utc).isoformat(),
        "task": config.task,
        "model_name": config.model_name,
        "estimator_class": f"{type(estimator).__module__}.{type(estimator).__qualname__}",
        "pipeline_steps": list(pipeline.named_steps),
        "target_column": config.target_column,
        "feature_names": list(features.columns),
        "feature_types": {
            column: "numeric" if column in features.select_dtypes(include="number")
            else "categorical" for column in features.columns
        },
        "n_features": len(features.columns),
        "best_parameters": effective_parameters(estimator),
        "parameter_overrides": config.model_params,
        "selection_metric": config.resolved_selection_metric(),
        "validation_strategy": config.resolved_primary_validation(),
        "supports_probability": hasattr(pipeline, "predict_proba"),
        "classes": parameter_value(getattr(pipeline, "classes_", None)),
        "analyzed_row_count": len(features),
        "missing_strategy": config.missing_strategy,
        "scaling": config.scaling,
        "fit_scope": "all_analyzed_rows",
    }
    pipeline.psyml_metadata_ = metadata
    try:
        joblib.dump(pipeline, path, compress=3)
        sidecar = {**metadata, "model_file": path.name,
                   "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        metadata_path = directory / "model_metadata.json"
        metadata_path.write_text(json.dumps(sidecar, indent=2, ensure_ascii=False,
                                            allow_nan=False) + "\n", encoding="utf-8")
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return {"status": "saved", "model_name": config.model_name,
            "model_path": str(path.relative_to(config.output_dir)),
            "metadata_path": str(metadata_path.relative_to(config.output_dir)),
            "fit_scope": "all_analyzed_rows"}
