"""Safe, explicit tabular-data loading."""

from pathlib import Path

import pandas as pd
import pyreadstat

SUPPORTED_SUFFIXES = {
    ".csv",
    ".tsv",
    ".xlsx",
    ".xls",
    ".sav",
    ".dta",
    ".sas7bdat",
    ".xpt",
    ".parquet",
}


def load_dataframe(path: Path | str) -> pd.DataFrame:
    """Load a supported table without altering its columns."""
    input_path = Path(path)
    if not input_path.is_file():
        raise FileNotFoundError(f"Input file does not exist: {input_path}")
    if input_path.suffix.lower() not in SUPPORTED_SUFFIXES:
        supported = ", ".join(sorted(SUPPORTED_SUFFIXES))
        raise ValueError(
            f"Unsupported input format '{input_path.suffix}'. Supported formats: {supported}"
        )
    suffix = input_path.suffix.lower()
    try:
        if suffix == ".csv":
            return pd.read_csv(input_path)
        if suffix == ".tsv":
            return pd.read_csv(input_path, sep="\t")
        if suffix in {".xlsx", ".xls"}:
            return pd.read_excel(input_path)
        if suffix == ".sav":
            return pyreadstat.read_sav(input_path)[0]
        if suffix == ".dta":
            return pyreadstat.read_dta(input_path)[0]
        if suffix == ".sas7bdat":
            return pyreadstat.read_sas7bdat(input_path)[0]
        if suffix == ".xpt":
            return pyreadstat.read_xport(input_path)[0]
        return pd.read_parquet(input_path)
    except ImportError as error:
        raise ImportError(
            f"Cannot read '{suffix}' because a dependency is missing: {error}"
        ) from error
    except Exception as error:
        raise ValueError(f"Failed to read '{suffix}' file '{input_path.name}': {error}") from error


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
