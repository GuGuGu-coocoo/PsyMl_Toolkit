"""Column-aware preprocessing for leakage-safe model pipelines."""

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder, StandardScaler


def build_preprocessor(
    features: pd.DataFrame,
    missing_strategy: str = "median",
    scaling: str = "standard",
) -> ColumnTransformer:
    """Create transformations fitted only inside a model's training fold."""
    numeric_columns = features.select_dtypes(include="number").columns.tolist()
    categorical_columns = [column for column in features.columns if column not in numeric_columns]
    transformers = []
    if numeric_columns:
        numeric_steps = []
        if missing_strategy != "drop":
            numeric_imputation = "most_frequent" if missing_strategy == "mode" else missing_strategy
            numeric_steps.append(("impute", SimpleImputer(strategy=numeric_imputation)))
        if scaling == "standard":
            numeric_steps.append(("scale", StandardScaler()))
        elif scaling == "minmax":
            numeric_steps.append(("scale", MinMaxScaler()))
        transformers.append(
            (
                "numeric",
                Pipeline(numeric_steps) if numeric_steps else "passthrough",
                numeric_columns,
            )
        )
    if categorical_columns:
        categorical_steps = []
        if missing_strategy != "drop":
            categorical_steps.append(("impute", SimpleImputer(strategy="most_frequent")))
        categorical_steps.append(
            ("encode", OneHotEncoder(handle_unknown="ignore", sparse_output=False))
        )
        transformers.append(
            (
                "categorical",
                Pipeline(categorical_steps),
                categorical_columns,
            )
        )
    if not transformers:
        raise ValueError("No feature columns are available")
    return ColumnTransformer(transformers=transformers, remainder="drop")
