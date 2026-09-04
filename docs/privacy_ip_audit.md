# Privacy and IP Audit

Audit date: 2026-09-04

## Backup

- An untouched local snapshot was created before sanitization and checksum-verified.
- On 2026-09-04, the user confirmed an independent cloud backup and requested deletion of the local original-data snapshot. The local backup and its checksum file were removed.

## Data sanitization

- Source workbooks in `data/`, the `simulate_0/` datasets, and the single SPSS `.sav` source are replaced with deterministic random placeholder values.
- Workbook sheet names, sheet count, used-range dimensions, column labels where present, cell types, formulas, and formatting are retained.
- The generated file-level record is `docs/data_sanitization_manifest.json`.
- The accompanying CSV files are also replaced with synthetic values while their header row, delimiter, row count, and column count are retained. The SPSS file retains its 94-row, 16-column schema and column labels.
- A post-sanitization, current-worktree verification is recorded in `docs/data_sanitization_verification.md`.

## Local deletion and Git exclusions

The following may contain raw records, derived research results, or model state learned from those records. They were removed from the local workspace on 2026-09-04; ignore rules remain as a defence against accidental reintroduction:

- the complete pre-sanitization legacy snapshot (370 files)
- `**/results/`
- `**/subdimensions-data-result/`
- `**/saved_models/`
- `*.rar`
- `*.sav` (except the verified synthetic SPSS test fixture)
- `*.joblib`
- `*.pth`
- Python cache directories and IDE metadata

## Text scan findings

- No API keys, passwords, database connection strings, telephone-number patterns, or Chinese national-ID patterns were found in searchable source text.
- A legacy contact email address found in 27 Python files was replaced with `maintainer@example.invalid`; the original is retained only in the user's cloud backup.
- Historical scripts contain hard-coded local Windows paths. They are not credentials, but will require portability fixes in a later engineering phase.
- Research-data ownership, client ownership, and publication permissions have not been independently verified. The repository should therefore remain private until that review is complete.
