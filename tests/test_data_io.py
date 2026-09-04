import pandas as pd
import pytest

from psyml.data import load_dataframe, validate_dataset


def test_load_csv_and_validate_dataset(tmp_path):
    path = tmp_path / "data.csv"
    pd.DataFrame({"feature": [1, 2], "target": [0, 1]}).to_csv(path, index=False)

    frame = load_dataframe(path)

    assert frame.shape == (2, 2)
    validate_dataset(frame, "target")


def test_rejects_unknown_format_and_missing_target(tmp_path):
    path = tmp_path / "data.txt"
    path.write_text("not tabular", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported input format"):
        load_dataframe(path)
    with pytest.raises(KeyError, match="Target column"):
        validate_dataset(pd.DataFrame({"feature": [1]}), "target")


def test_rejects_empty_data_duplicate_columns_and_missing_group():
    with pytest.raises(ValueError, match="no rows"):
        validate_dataset(pd.DataFrame(columns=["feature", "target"]), "target")
    duplicate_columns = pd.DataFrame([[1, 0]], columns=["feature", "feature"])
    with pytest.raises(ValueError, match="duplicate column"):
        validate_dataset(duplicate_columns, "feature")
    with pytest.raises(KeyError, match="Group column"):
        validate_dataset(pd.DataFrame({"feature": [1], "target": [0]}), "target", "group")
