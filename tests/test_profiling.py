"""Reusable column profiling, category counts and identifier hints."""

from __future__ import annotations

import math

import pandas as pd

from psyml.data.profiling import (
    DEFAULT_MAX_CATEGORIES,
    category_summary,
    column_profile,
    identifier_signals,
    profile_columns,
)
from psyml.protocol import dataframe_preview, preview_payload


def test_category_summary_counts_and_proportions_use_nonmissing_denominator():
    series = pd.Series(["a", "a", "b", None, "b", "c"])
    summary = category_summary(series)

    assert summary["total_rows"] == 6
    assert summary["missing_count"] == 1
    assert summary["nonmissing_count"] == 5
    assert summary["category_count"] == 3
    by_value = {entry["value"]: entry for entry in summary["categories"]}
    assert by_value["a"]["count"] == 2
    assert by_value["a"]["fraction_of_nonmissing"] == 2 / 5
    assert by_value["c"]["fraction_of_nonmissing"] == 1 / 5


def test_all_missing_target_has_no_division_by_zero_and_no_real_category():
    summary = category_summary(pd.Series([None, float("nan"), None]))
    assert summary["nonmissing_count"] == 0
    assert summary["category_count"] == 0
    assert summary["categories"] == []


def test_nan_and_none_are_not_counted_as_a_real_category():
    series = pd.Series([None, float("nan"), "x", "x"])
    summary = category_summary(series)
    values = [entry["value"] for entry in summary["categories"]]
    assert values == ["x"]
    assert None not in values
    assert summary["category_count"] == 1


def test_unobserved_categorical_categories_are_not_counted():
    series = pd.Series(pd.Categorical(["a", "a", "b"], categories=["a", "b", "c"]))
    summary = category_summary(series)
    # Only observed labels count; the declared-but-unobserved "c" is excluded.
    assert summary["category_count"] == 2
    assert {entry["value"] for entry in summary["categories"]} == {"a", "b"}


def test_high_cardinality_listing_is_truncated_but_totals_stay_exact():
    series = pd.Series([f"id-{index}" for index in range(150)])
    profile = column_profile("record", series, include_values=True, max_categories=100)

    assert profile["category_count"] == 150
    assert profile["unique_count"] == 150
    assert profile["value_counts_truncated"] is True
    assert profile["value_counts_omitted"] == 50
    assert len(profile["value_counts"]) == 100
    # The denominator stays the full observed set, not the truncated listing.
    assert profile["nonmissing_count"] == 150
    assert all(
        math.isclose(entry["fraction_of_nonmissing"], 1 / 150)
        for entry in profile["value_counts"]
    )


def test_string_and_numeric_labels_are_both_reported_with_their_types():
    numeric = column_profile("group", pd.Series([1, 2, 2]), include_values=True)
    textual = column_profile("group", pd.Series(["1", "2", "2"]), include_values=True)
    assert numeric["dtype"] != textual["dtype"]
    assert numeric["dtype"] in {"int64", "Int64", "float64", "int32"}
    assert {entry["value"] for entry in numeric["value_counts"]} == {1, 2}
    assert {entry["value"] for entry in textual["value_counts"]} == {"1", "2"}
    assert all(isinstance(entry["value"], str) for entry in textual["value_counts"])


def test_default_preview_hides_values_but_lists_identifier_hints():
    frame = pd.DataFrame({"participant_id": [f"p{i}" for i in range(25)], "y": [0, 1] * 12 + [0]})
    payload = dataframe_preview(frame, include_sample=False)

    assert "sample" not in payload
    by_name = {column["name"]: column for column in payload["columns"]}
    assert "value_counts" not in by_name["y"]
    assert by_name["y"]["missing_count"] == 0
    assert by_name["y"]["nonmissing_count"] == 25
    assert by_name["participant_id"]["identifier_suspected"] is True
    assert "name_token" in by_name["participant_id"]["identifier_signals"]
    # No raw identifier value leaks into the default payload.
    assert "p0" not in str(payload)


def test_sampled_preview_exposes_value_counts_but_not_whole_high_cardinality_column():
    frame = pd.DataFrame({"y": ["a"] * 3 + ["b"], "n": list(range(4))})
    payload = dataframe_preview(frame, include_sample=True)
    by_name = {column["name"]: column for column in payload["columns"]}
    assert {entry["value"] for entry in by_name["y"]["value_counts"]} == {"a", "b"}
    assert payload["sample"]


def test_continuous_float_measurements_are_not_flagged_just_for_being_unique():
    series = pd.Series([index * 0.5 + 0.1 for index in range(50)], dtype="float64")
    signals = identifier_signals("blood_pressure", series)
    assert signals["suspected"] is False
    assert signals["signals"] == []


def test_near_unique_integer_and_text_columns_are_flagged_with_a_reason():
    integers = pd.Series(list(range(30)), name="record_number")
    text = pd.Series([f"case-{index}" for index in range(30)], name="note")
    assert identifier_signals("record_number", integers)["suspected"] is True
    assert identifier_signals("note", text)["suspected"] is True
    profile = column_profile("record_number", integers)
    assert profile["identifier_suspected"] is True
    assert "unique" in profile["identifier_reason"]


def test_small_integer_columns_are_not_flagged_by_uniqueness_alone():
    series = pd.Series([1, 2, 3, 4, 5])
    assert identifier_signals("rating", series)["suspected"] is False


def test_profile_columns_caps_default_listing_at_configured_limit():
    frame = pd.DataFrame({"many": [f"v{index}" for index in range(DEFAULT_MAX_CATEGORIES + 5)]})
    (profile,) = profile_columns(frame, include_values=True)
    assert profile["category_count"] == DEFAULT_MAX_CATEGORIES + 5
    assert len(profile["value_counts"]) == DEFAULT_MAX_CATEGORIES


def test_preview_payload_default_is_privacy_first(tmp_path):
    path = tmp_path / "data.csv"
    pd.DataFrame({"x": [1, 2, 3], "y": ["a", "b", "a"]}).to_csv(path, index=False)
    payload = preview_payload(path)
    assert payload["row_count"] == 3
    assert "sample" not in payload
    assert all("value_counts" not in column for column in payload["columns"])
