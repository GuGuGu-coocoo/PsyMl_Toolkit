import pandas as pd
import pytest

from psyml.validation import make_validation_splits, split_train_test


def test_group_split_never_places_a_group_in_both_partitions():
    features = pd.DataFrame({"value": range(12)})
    target = pd.Series([0, 1] * 6)
    groups = pd.Series(["a"] * 3 + ["b"] * 3 + ["c"] * 3 + ["d"] * 3)

    train_x, test_x, _, _ = split_train_test(
        features, target, "classification", test_size=0.25, random_seed=11, groups=groups
    )

    assert set(groups.loc[train_x.index]).isdisjoint(set(groups.loc[test_x.index]))


@pytest.mark.parametrize(
    "strategy", ["group_k_fold", "stratified_group_k_fold", "leave_one_group_out"]
)
def test_group_cross_validation_never_shares_groups(strategy):
    features = pd.DataFrame({"feature": range(24)})
    target = pd.Series([0, 1] * 12)
    groups = pd.Series([group for group in range(6) for _ in range(4)])

    splits = make_validation_splits(
        features, target, "classification", strategy, 3, 0.2, 42, groups
    )

    for train_index, test_index in splits:
        assert set(groups.iloc[train_index]).isdisjoint(set(groups.iloc[test_index]))


def test_stratified_group_k_fold_preserves_classes_and_groups():
    features = pd.DataFrame({"feature": range(36)})
    target = pd.Series([class_id for _group in range(6) for class_id in [0, 0, 1, 1, 2, 2]])
    groups = pd.Series([group for group in range(6) for _ in range(6)])

    splits = make_validation_splits(
        features,
        target,
        "classification",
        "stratified_group_k_fold",
        3,
        0.2,
        42,
        groups,
    )

    assert len(splits) == 3
    for train_index, test_index in splits:
        assert set(groups.iloc[train_index]).isdisjoint(set(groups.iloc[test_index]))
        assert set(target.iloc[test_index]) == {0, 1, 2}


def test_stratified_k_fold_represents_each_class():
    features = pd.DataFrame({"feature": range(30)})
    target = pd.Series([0, 1, 2] * 10)

    splits = make_validation_splits(
        features, target, "classification", "stratified_k_fold", 5, 0.2, 42
    )

    assert len(splits) == 5
    assert all(set(target.iloc[test_index]) == {0, 1, 2} for _, test_index in splits)
