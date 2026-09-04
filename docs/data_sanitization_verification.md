# Sanitized Legacy Data Verification

Verification date: 2026-09-04

This is a current-worktree audit of the synthetic legacy datasets. The original local snapshot was deleted at the user's request, so a new byte-for-byte comparison with the originals is impossible. The preservation claims below are supported by the contemporaneous sanitization manifests and by reopening every remaining data file.

## Current inventory and structure

| Format | Files | Verification |
| --- | ---: | --- |
| XLSX | 39 | All reopened successfully; 43 worksheets, 2,030,753 non-empty cells, 2,673 formula cells, and numeric, string, boolean and formula cell types remain present. |
| CSV | 2 | `simulated_data.CSV` is 5,001 × 27 and `test_data.CSV` is 16 × 27; both are rectangular. |
| SPSS SAV | 1 | File type is an SPSS System File. The sanitization manifest records the preserved 94-row, 16-column schema and column labels. |

The contemporaneous process record is `docs/data_sanitization_manifest.json`: it records 39 sanitized workbooks, preservation of workbook/worksheet names, used-range dimensions, column labels, cell types, formulas and formatting. `docs/csv_sanitization_manifest.json` records the original CSV dimensions and headers.

## Sensitive-data checks

- No ignored legacy result, saved-model or archive directories/files remain in the current workspace.
- The 39 XLSX files and 2 CSV files were scanned cell by cell: no email address, Chinese mobile number or Chinese national-ID pattern was found.
- Printable strings from the SPSS file produced no match for those patterns.
- Searchable legacy source text contains no API key, password, database connection string, telephone-number or Chinese national-ID finding; details remain in `docs/privacy_ip_audit.md`.

## Test-data availability

The sanitized XLSX and CSV datasets are version-controlled. The verified synthetic SPSS fixture is also intentionally version-controlled despite the default `*.sav` exclusion, so a fresh clone retains a same-format test file. Its SHA-256 is `573248dd1983efce57ce4623aac3fcded0bf1140d88b585d9b11dff34b4c60c2`.
