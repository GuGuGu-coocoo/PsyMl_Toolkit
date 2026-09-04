"""Safe, explicit tabular-data loading."""

from pathlib import Path

import pandas as pd

SUPPORTED_SUFFIXES = {".csv", ".xlsx", ".xls"}


def load_dataframe(path: Path | str) -> pd.DataFrame:
    """Load a CSV or Excel file into a dataframe without altering its columns."""
    input_path = Path(path)
    if not input_path.is_file():
        raise FileNotFoundError(f"Input file does not exist: {input_path}")
    if input_path.suffix.lower() not in SUPPORTED_SUFFIXES:
        supported = ", ".join(sorted(SUPPORTED_SUFFIXES))
        raise ValueError(f"Unsupported input format '{input_path.suffix}'. Supported formats: {supported}")
    if input_path.suffix.lower() == ".csv":
        return pd.read_csv(input_path)
    return pd.read_excel(input_path)


def validate_dataset(
    frame: pd.DataFrame, target_column: str, group_column: str | None = None
) -> None:
    """Validate only the requirements needed before an experiment begins."""
    if frame.empty:
        raise ValueError("Input data contains no rows")
    if frame.columns.duplicated().any():
        raise ValueError("Input data contains duplicate column names")
    if target_column not in frame.columns:
        raise KeyError(f"Target column '{target_column}' was not found")
    if group_column is not None and group_column not in frame.columns:
        raise KeyError(f"Group column '{group_column}' was not found")
    if frame[target_column].isna().all():
        raise ValueError("Target column contains only missing values")
