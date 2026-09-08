"""Lightweight catalog of supported tabular formats."""

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

# These formats have writers in the existing pandas/pyreadstat dependencies.
OUTPUT_SUFFIXES = SUPPORTED_SUFFIXES - {".xls", ".sas7bdat"}


def prediction_output_suffix(input_suffix: str) -> str:
    """Keep writable input formats; Excel is the explicit fallback for read-only ones."""
    return input_suffix.lower() if input_suffix.lower() in OUTPUT_SUFFIXES else ".xlsx"
