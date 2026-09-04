# Privacy and IP Audit

Audit date: 2026-09-04

## Backup

- `psyml_legacy_backup/` is an untouched local snapshot created before sanitization.
- `psyml_legacy_backup/SHA256SUMS` records SHA-256 checksums for the copied files.
- The backup is excluded from Git and must remain local/private.

## Data sanitization

- Source workbooks in `data/`, the `simulate_0/` datasets, and the single SPSS `.sav` source are replaced with deterministic random placeholder values.
- Workbook sheet names, sheet count, used-range dimensions, column labels where present, cell types, formulas, and formatting are retained.
- The generated file-level record is `docs/data_sanitization_manifest.json`.
- The accompanying CSV files are also replaced with synthetic values while their header row, delimiter, row count, and column count are retained. The SPSS file retains its 94-row, 16-column schema and column labels.

## Files deliberately excluded from Git

The following may contain raw records, derived research results, or model state learned from those records. They remain available only in the local backup until their ownership and publication status is confirmed:

- `psyml_legacy_backup/`
- `**/results/`
- `**/subdimensions-data-result/`
- `**/saved_models/`
- `*.rar`
- `*.sav`
- `*.joblib`
- `*.pth`
- Python cache directories and IDE metadata

## Text scan findings

- No API keys, passwords, database connection strings, telephone-number patterns, or Chinese national-ID patterns were found in searchable source text.
- A legacy contact email address found in 27 Python files was replaced with `maintainer@example.invalid`; the original remains only in the private backup.
- Historical scripts contain hard-coded local Windows paths. They are not credentials, but will require portability fixes in a later engineering phase.
- Research-data ownership, client ownership, and publication permissions have not been independently verified. The repository should therefore remain private until that review is complete.
