"""Model catalog and lazily imported estimator factory."""

from typing import Any

from psyml.models.catalog import supported_models


def build_model(task: str, model_name: str, random_seed: int, params: dict[str, Any]):
    """Build an estimator while keeping capability discovery lightweight."""
    from psyml.models.factory import build_model as build

    return build(task, model_name, random_seed, params)


__all__ = ["build_model", "supported_models"]
