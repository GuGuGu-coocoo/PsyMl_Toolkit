"""Train/test splitting with optional group isolation."""

import pandas as pd
from sklearn.model_selection import (
    GroupKFold,
    GroupShuffleSplit,
    KFold,
    LeaveOneGroupOut,
    StratifiedKFold,
    train_test_split,
)


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


def make_validation_splits(
    features: pd.DataFrame,
    target: pd.Series,
    task: str,
    strategy: str,
    n_splits: int,
    test_size: float,
    random_seed: int,
    groups: pd.Series | None = None,
) -> list[tuple[list[int], list[int]]]:
    """Return positional train/test indices for the configured strategy."""
    if strategy == "holdout":
        positions = pd.DataFrame({"position": range(len(features))}, index=features.index)
        train, test, _, _ = split_train_test(
            positions, target, task, test_size, random_seed, groups
        )
        return [(train["position"].tolist(), test["position"].tolist())]

    if strategy == "k_fold":
        split_iterator = KFold(n_splits=n_splits, shuffle=True, random_state=random_seed).split(
            features, target
        )
    elif strategy == "stratified_k_fold":
        split_iterator = StratifiedKFold(
            n_splits=n_splits, shuffle=True, random_state=random_seed
        ).split(features, target)
    elif strategy == "group_k_fold":
        if groups is None:
            raise ValueError("group_k_fold requires groups")
        if groups.nunique() < n_splits:
            raise ValueError("group_k_fold requires at least n_splits unique groups")
        split_iterator = GroupKFold(
            n_splits=n_splits, shuffle=True, random_state=random_seed
        ).split(features, target, groups)
    elif strategy == "leave_one_group_out":
        if groups is None or groups.nunique() < 2:
            raise ValueError("leave_one_group_out requires at least two unique groups")
        split_iterator = LeaveOneGroupOut().split(features, target, groups)
    else:
        raise ValueError(f"Unsupported validation strategy: {strategy}")
    return [(train.tolist(), test.tolist()) for train, test in split_iterator]
