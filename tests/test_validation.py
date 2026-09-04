import pandas as pd

from psyml.validation import split_train_test


def test_group_split_never_places_a_group_in_both_partitions():
    features = pd.DataFrame({"value": range(12)})
    target = pd.Series([0, 1] * 6)
    groups = pd.Series(["a"] * 3 + ["b"] * 3 + ["c"] * 3 + ["d"] * 3)

    train_x, test_x, _, _ = split_train_test(
        features, target, "classification", test_size=0.25, random_seed=11, groups=groups
    )

    assert set(groups.loc[train_x.index]).isdisjoint(set(groups.loc[test_x.index]))
