"""Observed class counts, independent of unused pandas category metadata."""

import pandas as pd


def observed_class_counts(target: pd.Series, *, dropna: bool = True) -> pd.Series:
    counts = target.value_counts(dropna=dropna)
    return counts[counts > 0]
