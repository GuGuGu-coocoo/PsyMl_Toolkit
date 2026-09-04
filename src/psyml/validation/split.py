"""Train/test splitting with optional group isolation."""

import pandas as pd
from sklearn.model_selection import GroupShuffleSplit, train_test_split


def split_train_test(
    features: pd.DataFrame,
    target: pd.Series,
    task: str,
    test_size: float,
    random_seed: int,
    groups: pd.Series | None = None,
):
    """Split before fitting preprocessing or estimators.

    Classification uses stratification when every class can be represented in
    both partitions. Grouped data uses group-aware splitting instead.
    """
    if groups is not None:
        splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_seed)
        train_index, test_index = next(splitter.split(features, target, groups))
        return (
            features.iloc[train_index],
            features.iloc[test_index],
            target.iloc[train_index],
            target.iloc[test_index],
        )
    stratify = None
    if task == "classification":
        class_counts = target.value_counts(dropna=False)
        if len(class_counts) > 1 and class_counts.min() >= 2:
            stratify = target
    return train_test_split(
        features,
        target,
        test_size=test_size,
        random_state=random_seed,
        stratify=stratify,
    )
