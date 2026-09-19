"""Reusable, privacy-aware column profiling for data inspection.

This module is a pure helper: it never imports the GUI, never fits a model and
never mutates the source frame. Raw category values are only enumerated when the
caller explicitly allows value counts, so the default preview never leaks them.

Design notes
------------
* Missing values are never counted as a real category and never enter the
  denominator of a category proportion.
* Category totals and the non-missing denominator stay exact even when the
  per-category listing is truncated for very high-cardinality columns.
* Identifier detection is a heuristic hint ("suspected, please judge"). It never
  removes a column, changes a role or blocks an analysis.
"""

from __future__ import annotations

import math
import re
from typing import Any

import pandas as pd

DEFAULT_MAX_CATEGORIES = 100
MIN_IDENTIFIER_ROWS = 20
NEAR_UNIQUE_RATIO = 0.98

# Standalone name tokens that usually mark an identifier rather than a predictor.
_ID_TOKENS = {
    "id",
    "ids",
    "pid",
    "uid",
    "sid",
    "subject",
    "subjects",
    "participant",
    "participants",
    "record",
    "records",
    "case",
    "cases",
    "编号",
    "序号",
    "受试者",
    "参与者",
    "个案",
    "被试",
}

_TOKEN_SPLIT = re.compile(r"[^0-9A-Za-z\u4e00-\u9fff]+")
_CAMEL_SPLIT = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def _json_safe(value: Any) -> Any:
    """Convert one raw cell to a JSON-serialisable value without leaking NaN."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, bool):
        return bool(value)
    if hasattr(value, "item"):
        try:
            value = value.item()
        except (AttributeError, ValueError):
            return str(value)
    if isinstance(value, (int, float, str, bool)) or value is None:
        if isinstance(value, float) and not math.isfinite(value):
            return None
        return value
    return str(value)


def _name_tokens(name: str) -> list[str]:
    """Split a column name into lowercase word tokens (snake and camel case)."""
    spaced = _CAMEL_SPLIT.sub(" ", str(name))
    return [token.lower() for token in _TOKEN_SPLIT.split(spaced) if token]


def identifier_signals(name: str, series: pd.Series) -> dict[str, Any]:
    """Return the heuristic signals that suggest a column is an identifier.

    The result records *why* a column was flagged so the UI can show a
    traceable, user-dismissable hint. Continuous float measurements are never
    flagged merely because every value is unique.
    """
    tokens = set(_name_tokens(name))
    matched = sorted(tokens & _ID_TOKENS)
    row_count = int(series.notna().sum())
    unique_count = int(series.nunique(dropna=True))
    ratio = (unique_count / row_count) if row_count else None
    signals: list[str] = []
    if matched:
        signals.append("name_token")
    dtype = series.dtype
    value_like = (
        pd.api.types.is_integer_dtype(dtype)
        or pd.api.types.is_object_dtype(dtype)
        or pd.api.types.is_string_dtype(dtype)
        or pd.api.types.is_bool_dtype(dtype)
        or isinstance(dtype, pd.CategoricalDtype)
    )
    # Floats are continuous measurements; near-uniqueness alone is expected and
    # must not be treated as an identifier cue.
    if (
        value_like
        and row_count >= MIN_IDENTIFIER_ROWS
        and ratio is not None
        and ratio >= NEAR_UNIQUE_RATIO
    ):
        signals.append("near_unique_values")
    return {
        "suspected": bool(signals),
        "signals": signals,
        "name_tokens": matched,
        "unique_ratio": ratio,
        "nonmissing_count": row_count,
        "unique_count": unique_count,
    }


def _identifier_reason(signals: dict[str, Any]) -> str:
    parts: list[str] = []
    if "name_token" in signals["signals"]:
        parts.append("column name contains an ID/participant marker")
    if "near_unique_values" in signals["signals"]:
        ratio = signals.get("unique_ratio")
        shown = f"{ratio:.2f}" if isinstance(ratio, float) else "n/a"
        parts.append(
            f"{signals.get('unique_count', 0)}/{signals.get('nonmissing_count', 0)} "
            f"non-missing values are unique (ratio {shown})"
        )
    return "; ".join(parts)


def category_summary(
    series: pd.Series, *, max_categories: int = DEFAULT_MAX_CATEGORIES
) -> dict[str, Any]:
    """Summarise observed categories of one column with an exact denominator.

    ``fraction_of_nonmissing`` is the proportion of the non-missing denominator
    represented by each observed category. Missing values are excluded from both
    the categories and their denominator.
    """
    total_rows = len(series)
    missing_count = int(series.isna().sum())
    nonmissing_count = total_rows - missing_count
    counts = series.dropna().value_counts()
    # Categorical dtypes list declared-but-unobserved categories with count 0;
    # they are not real observed classes and must be excluded.
    counts = counts[counts > 0]
    entries = []
    for value, count in counts.iloc[:max_categories].items():
        entries.append(
            {
                "value": _json_safe(value),
                "count": int(count),
                "fraction_of_nonmissing": (
                    float(count) / nonmissing_count if nonmissing_count else None
                ),
            }
        )
    category_count = len(counts)
    return {
        "total_rows": total_rows,
        "nonmissing_count": nonmissing_count,
        "missing_count": missing_count,
        "category_count": category_count,
        "categories": entries,
        "truncated": category_count > max_categories,
        "omitted_count": max(category_count - max_categories, 0),
    }


def column_profile(
    name: str,
    series: pd.Series,
    *,
    include_values: bool = False,
    max_categories: int = DEFAULT_MAX_CATEGORIES,
) -> dict[str, Any]:
    """Profile one column, optionally enumerating its observed categories."""
    nonmissing_count = int(series.notna().sum())
    unique_count = int(series.nunique(dropna=True))
    signals = identifier_signals(name, series)
    profile: dict[str, Any] = {
        "name": str(name),
        "dtype": str(series.dtype),
        "missing_count": int(series.isna().sum()),
        "nonmissing_count": nonmissing_count,
        "unique_count": unique_count,
        "unique_ratio": (
            (unique_count / nonmissing_count) if nonmissing_count else None
        ),
        "category_count": unique_count,
        "identifier_suspected": signals["suspected"],
        "identifier_signals": signals["signals"],
        "identifier_reason": _identifier_reason(signals) if signals["suspected"] else "",
    }
    if include_values:
        profile["value_counts"] = category_summary(
            series, max_categories=max_categories
        )["categories"]
        profile["value_counts_truncated"] = unique_count > max_categories
        profile["value_counts_omitted"] = max(unique_count - max_categories, 0)
    return profile


def profile_columns(
    frame: pd.DataFrame,
    *,
    include_values: bool = False,
    max_categories: int = DEFAULT_MAX_CATEGORIES,
) -> list[dict[str, Any]]:
    """Profile every column positionally, preserving column order."""
    return [
        column_profile(
            str(frame.columns[position]),
            frame.iloc[:, position],
            include_values=include_values,
            max_categories=max_categories,
        )
        for position in range(len(frame.columns))
    ]
