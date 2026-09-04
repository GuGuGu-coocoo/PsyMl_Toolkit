# Phase 14 Release Audit

Audit date: 2026-09-04

## Decision

The repository is technically ready for researcher trials from a cloned checkout. On 2026-09-04, the repository owner confirmed that they authored the legacy code and that there is no source-code ownership issue. No project license was invented or applied during this audit; until the owner selects one, public visibility alone does not grant reuse or redistribution rights.

## Platform acceptance

GitHub Actions run [#6](https://github.com/GuGuGu-coocoo/PsyMl_Toolkit/actions/runs/33883261911) completed successfully on `windows-latest`, `macos-latest` and `ubuntu-latest` with Python 3.12 and Godot 4.7.2. Every platform completed:

- locked dependency installation, lint, 66 Python tests, sdist/wheel build and isolated wheel smoke test;
- Godot project parsing;
- the JSON/JSONL Core bridge test;
- a real GUI flow that previews random TSV data, runs classification and regression, loads metrics and figures, and verifies French localization.

Local macOS acceptance additionally used the real Metal renderer to generate and visually inspect four Chinese, four English and four French screenshots. Long labels, selected states, JSON review text, metrics, prediction tables and figures were checked for clipping and readability.

## Public examples and reproducibility

Two standard datasets were selected from the UCI Machine Learning Repository because their current dataset pages explicitly state CC BY 4.0:

| Example | DOI | Download SHA-256 | Acceptance result |
| --- | --- | --- | --- |
| Iris classification | `10.24432/C56C76` | `d11fe30213d36434a0879aab7cb00ce3c812eb7ba2495874438abff7b7b762e9` | completed; accuracy `0.953333` |
| Concrete Compressive Strength regression | `10.24432/C5PK67` | `dad85d14de8aee4e07479daa774e6b569a313715b71a3b92c95a07cf91c2c9a7` | completed; R² `0.600689`, MAE `8.347756`, RMSE `10.504809` |

`tools/fetch_public_examples.py` verifies those hashes before extraction. Third-party raw data and normalized CSV files remain ignored and are not redistributed. Both fixed configs produced `analysis_config.json`, `analysis_manifest.json`, predictions, fold metrics, summary metrics, figure, Methods summary, reproducibility report and `result.json`.

Automated tests cover saved-config round trips, deterministic prediction reruns, data hashes, report/path privacy, and Chinese plus space-containing paths.

## Privacy and secrets

`tools/audit_repository.py` reopened and scanned every retained legacy fixture: 39 XLSX workbooks, 2 CSV files and 1 SAV file. It found no email address, Chinese mobile number or Chinese national-ID pattern in cell values. It also found no AWS access key, GitHub token or private-key marker in Git-tracked text. The only contact address retained in legacy comments is the deliberately invalid `maintainer@example.invalid` placeholder.

The original local backup and original research data remain deleted as requested. Public example data, result folders, models, archives, temporary Godot files and the local development plan are protected by `.gitignore`. README screenshots use generic `/tmp/PsyML…` paths and random synthetic data.

## Dependencies and artifacts

`pip-audit` reported no known vulnerabilities in the locked runtime dependency set on the audit date; the local unpublished `psyml-toolkit` package itself was correctly skipped because it is not on PyPI. Direct runtime packages report permissive licenses (BSD, MIT, Apache-2.0, PSF-compatible or package-specific permissive terms). A future standalone binary release must collect and ship complete third-party notices, including bundled Matplotlib font notices.

The build configuration was corrected so the source distribution no longer contains legacy assets. Current local artifact sizes are approximately 29 KiB for the wheel and 21 KiB for the source archive. The twelve README screenshots total approximately 1.18 MB; the Git object pack is approximately 13.56 MiB.

## Remaining license decision

Legacy ownership is confirmed and no longer blocks publication. If the owner wants others to be allowed to copy, modify or redistribute the project, they should choose and add an explicit project license before describing it as open source or publishing distributable packages. Keeping no license is also possible for a publicly visible repository, but reserves the default copyright rights.
