# Developer guide

[README](../README.md#english) · [中文](DEVELOPMENT_ZH.md) · [Français](DEVELOPMENT_FR.md)

For contributors modifying, maintaining or building PsyML. Researchers use the GUI without developer tools or these commands. See [pyproject.toml](../pyproject.toml) for the code version and Releases for published builds.

## Environment and launch

Use Git, Python 3.10–3.12, [uv](https://docs.astral.sh/uv/) and [Godot 4.7.2](https://godotengine.org/download/archive/4.7.2-stable/). Standalone builds use Python 3.12.13. From a full checkout’s root:

```bash
uv sync --locked --group dev
uv run python tools/launch_gui.py
```

The launcher sets `PSYML_PYTHON` to the current environment. Set `PSYML_GODOT` to the full executable path if Godot is absent from PATH. After setup, macOS users can also launch `Launch PsyML.command`. Do not resolve `.venv/bin/python` to an interpreter outside the environment: that can lose access to project dependencies.

## Repository map

| Location | Responsibility |
| --- | --- |
| `src/psyml/config.py`, `protocol.py`, `schemas/` | Configuration validation and versioned JSON contracts |
| `src/psyml/runner.py` | Orchestration, nested family/parameter selection, independent validations |
| `src/psyml/data/`, `preprocessing/`, `validation/` | Readers, training-only preprocessing, splits |
| `src/psyml/models/catalog.py`, `factory.py`, `evaluation/metrics.py` | Model/parameter catalog, estimators, metrics |
| `src/psyml/reporting/` | Predictions, metrics, figures, reports, environment versions |
| `src/psyml/gui_config.py` | Imported data-path resolution and column checks |
| `gui/main.tscn`, `gui/scripts/main.gd` | Layout and interaction |
| `gui/scripts/core_bridge.gd`, `configuration_io.gd` | Subprocess bridge, configuration import/save |
| `gui/scripts/i18n.gd`, `light_theme.gd` | Three-language text and interaction colors |
| `tests/`, `gui/tests/`, `examples/synthetic/` | Core/GUI tests and synthetic data/configurations |
| `tools/`, `.github/workflows/` | Launch, build, checks and CI |
| `src/psyml/models/persistence.py`, `parameters.py`, `src/psyml/prediction.py` | Final Pipeline saving, effective parameters, model checks and batch inference |
| `gui/scripts/prediction_page.gd`, `data_preview.gd` | Page 4 interaction and shared previews |
| `examples/quickstart/`, `tests/test_quickstart.py` | Portable user kit and training-to-prediction verification |

`legacy/` preserves historical code and synthetic fixtures, not the current entry point. Do not commit local `dist/`, `tmp/`, `output/`, `.venv/` artifacts or real research data.

## Core interfaces

The GUI invokes the local Python core, using the virtual environment during development and bundled `psyml-core` in standalone apps. Keep analysis logic in the core.

```bash
uv run psyml --help
uv run psyml capabilities
uv run psyml preview --input examples/synthetic/classification.csv
uv run psyml import-config --config examples/synthetic/classification_config.json
uv run psyml schema analysis_config
uv run psyml run --config examples/synthetic/classification_config.json --events
uv run psyml run --config examples/synthetic/regression_config.json --events
```

`capabilities` lists models, formats, metrics and validation. `preview` returns metadata unless `--include-sample` is added. `schema` accepts `analysis_config`, `event`, `result`. Keep `run --events` output valid JSONL, including progress and terminal events, without mixed logging. The Python API exports `ExperimentConfig` and `run_experiment` from `psyml`; `psyml.protocol.load_config` reads JSON.

CLI relative paths resolve from the working directory. CLI runs use the exact `output_dir` and reject existing results; choose a fresh empty directory before repeating. GUI imports resolve data relative to the configuration first and support repository-style examples. Missing paths prompt for relinking; missing columns fail. The GUI always uses a new subfolder in the chosen local output directory. Saved data paths are relative only when data and configuration share a directory.

In JSON, `primary_validation: null` enables separate outputs per validation, a strategy name selects an explicit primary, and omission preserves legacy first-selected behavior. Python callers use `validation_results[strategy]`; root `model=None` and `metrics={}` are intentional.

### 0.2.0 training, saving and prediction interfaces

`examples/quickstart/` is the user-testing entry; `examples/synthetic/` and `matrix/` remain developer fixtures, and the earlier commands remain valid. The quickstart JSONs use adjacent training filenames: enter that directory first for CLI runs. `load_config()` does not rebase relative paths to the JSON directory. Ensure `results/quickstart_classification` and `results/quickstart_regression` contain no previous results; choose new output directories in the JSONs before rerunning.

```bash
cd examples/quickstart
uv run psyml run --config classification_config.json --events
uv run psyml model-info --model results/quickstart_classification/model/best_decision_tree.joblib --trust-model
uv run psyml predict --model results/quickstart_classification/model/best_decision_tree.joblib --input classification_predict.csv --check-only --trust-model
uv run psyml predict --model results/quickstart_classification/model/best_decision_tree.joblib --input classification_predict.csv --output results/quickstart_classification/new_predictions.xlsx --trust-model
uv run psyml export-table --input results/quickstart_classification/new_predictions.xlsx --output results/quickstart_classification/new_predictions.csv
uv run psyml run --config regression_config.json --events
uv run psyml predict --model results/quickstart_regression/model/best_ridge.joblib --input regression_predict.csv --output results/quickstart_regression/new_predictions.csv --trust-model
cd ../..
```

Each prediction has 10 rows retaining sample_id/category/score. Classification adds predicted_class and two probability_* columns; regression adds predicted_value. `model-info` returns metadata. Inspect `compatibility.compatible` and errors from `predict --check-only`, not just the exit code. Actual prediction requires `--output`, whose suffix controls format; overwriting is disabled unless explicitly requested with `--overwrite`. Repeat `--feature` in training order for manual mapping. `export-table` converts an existing table without rerunning the model. XLS/SAS7BDAT are read-only; export XLSX instead.

Python interfaces in `psyml.prediction`: `load_model(path, trusted=True)`, `compatibility_check(loaded, frame, mapping=None)`, `predict_dataframe(loaded, frame, mapping=None)`. The last returns `(DataFrame, list_of_added_columns)`. Loading requires explicit trust even when merely inspecting metadata.

`save_best_model` defaults to true. A primary run records status and relative paths in `model_export`, indexed by `result.json.artifacts.saved_model` / `model_metadata`; independent runs do not automatically save models. `best_parameters.json`, `result.json.effective_parameters` and metadata best_parameters contain effective defaults. `result.json.best_parameters` and the fixed-parameter recipe retain overrides; preserve this distinction.

### Data-check and result-interpretation interfaces

FR-007: `psyml.data.profiling` is a pure helper; `profile_columns` / `column_profile` / `category_summary` / `identifier_signals` build per-column metadata from a DataFrame (non-missing count, unique count, near-unique ratio, optional value counts with truncation, and evidence-based identifier signals). `protocol.dataframe_preview` attaches values only when `include_sample=True` and returns none by default; the page-1 GUI `gui/scripts/data_check_ui.gd` consumes that metadata instead of estimating from the first five rows, and never deletes columns or changes roles.

FR-009: `build_interpretation` in `psyml.reporting.interpretation` aggregates only evidence the runner already produced (procedure_results, per-combination folds, tuning_rows, leaderboard, validation_summary) and adds no model fit; `write_interpretation_outputs` writes `result_interpretation.json`, `interpretation_baseline_differences.csv` and `result_interpretation.md`, indexed by `result.json.artifacts`. For independent validations `build_independent_interpretation` writes only a root overview/index. The GUI summary lives in `gui/scripts/result_interpretation_ui.gd`. Core regression: `tests/test_profiling.py`, `tests/test_interpretation.py`; GUI: `gui/tests/test_data_check.gd`, `gui/tests/test_interpretation_results.gd`. The baseline compares only a successfully completed dummy on the same validation, fold set and metric, with a fixed sign (positive = better); descriptive statistics never flow back into selection or tuning. FR-008 only edits the trilingual researcher guides and changes no GUI or splitting algorithm.

### Permutation-importance interfaces

`ExperimentConfig.permutation_importance` (default `false`) and `permutation_repeats` (1–100, default `10`) control this feature; legacy configs that omit them stay off. The engine lives in `psyml.evaluation.permutation`, artefact writing in `psyml.reporting.permutation`. The runner passes only the inner-selected outer-fold Pipeline and its test rows to the engine, and writes `interpretations/<validation>/` after selection is frozen. Results are stored per validation as `dict[validation, list[record]]`; failed records keep `status=failed` plus `error_type/error` and never fabricate variables. `result.json.permutation`, `analysis_manifest.json.interpretations` and the Methods/reproducibility reports index only files that exist. Core regression lives in `tests/test_permutation*.py`; GUI settings and result display are in `gui/scripts/permutation_ui.gd` with regression in `gui/tests/test_permutation.gd`; `examples/quickstart/*_permutation_config.json` gives an importable classification/regression smoke. Keep it OFF by default and do not change selection, splitting or metric semantics.

## Behavior to preserve

- Fit encoding, imputation and scaling on the relevant training partition only. Select families/parameters internally, never from outer rankings. Explain scientific changes; passing tests is not scientific justification.
- `primary_validation: null` produces separate complete results or failure records. There is no global winner or headline metric at the root and no automatic highest-score selection.
- Coordinate configuration changes across dataclasses, schemas, protocol, GUI import/save and tests; preserve old configurations and all parameters, candidates, variable order and figure choices.
- Use OS-native file/directory dialogs. Check hover, focus, selection and disabled contrast in custom controls.
- Update Chinese, English and French UI text, README, researcher guides and matching screenshots when visible behavior changes. Language changes must not change the analysis. README documents exported-figure and raw-error language limits.
- Record runtime versions in `analysis_manifest.json`. When dependencies change, update `uv.lock`, reports, packaged metadata and licenses.

## Verification and contributions

[TESTING.md](TESTING.md) contains developer regression commands and manual checks; it is not a prerequisite for GUI users. Match checks to changes. Inspect UI changes in a real window and validate methodological changes against small, checkable datasets. Use synthetic or publicly shareable minimal examples only.

PRs should explain the problem, resulting behavior, validation and limitations. Avoid unrelated refactoring; identify scientific, compatibility and dependency impacts. Contributions follow [Apache-2.0](../LICENSE). Never upload participant data, unpublished material or credentials. Keep developer commands out of researcher instructions.

## Optional single-sample explanation extra

The FR-004 explanation feature depends on `shap`, `numba` and `llvmlite`, kept out of the default install so ordinary analysis and prediction retain their cold-start and package size. Install them only when needed:

```bash
uv sync --extra explain
uv pip install -e ".[explain]"   # pip/venv equivalent
```

`pyproject.toml` pins version-appropriate SHAP releases per Python (3.10 → 0.49.x, 3.11 → 0.51.x, 3.12 → 0.52.x). `uv.lock` records them without upgrading unrelated dependencies such as scikit-learn. `tools/build_native.py` bundles shap/numba/llvmlite into the core, copies their licenses into `tools/licenses/`, and `--explain-smoke` checks bundled classification/regression explanation and reconstruction. Windows is not executed on this Mac.

## Fitted coefficients (FR-005, no extra dependency)

[coefficients.py](../src/psyml/models/coefficients.py) reads `coef_`/`intercept_` only from an already fitted PsyML `preprocess`+`model` pipeline. It builds an exact transformed-feature/source-column/category mapping from `ColumnTransformer.output_indices_` and each sub-step (imputer `statistics_`, scaler `mean_/scale_` or `min_/scale_/data_min_/data_max_`, OneHotEncoder `categories_`), and verifies reconstruction of `predict` (regression) or `decision_function` (classification) through the same pipeline transform on supplied rows (atol 1e-7 / rtol 1e-6). It never fits, never changes the model, never feeds back into tuning and never converts to raw units. The report also records `input_features`/`dropped_features` (all-missing columns with reason, original index, missing strategy), `encoding.per_source` (per-column categories and `drop_idx_`) and the training-dtype source (saved metadata or explicitly unknown). With supplied rows, a failed check (tolerance/shape/non-finite) returns `status=error` and refuses to publish a success artifact; without rows the report stays explicitly unverified, and CLI/GUI keep the two states apart. The normal runner writes CSV/JSON/notes under `coefficients/`; the CLI is `psyml coefficients` (reusing trust/hash/version and `model_input`, writing only to a new/empty directory, JSON last). The loaded-model path validates the PsyML provenance (`psyml_version`/`fit_scope`) and estimator type; unknown models get a specific reason and ordinary prediction is unaffected. Tests live in `tests/test_coefficients.py`, `tests/test_coefficients_cli.py` and `gui/tests/test_coefficients.gd`; `--coefficients-smoke` checks bundled classification/regression extraction.

## Building and release maintenance

[build_native.py](../tools/build_native.py) freezes the core with PyInstaller and exports Godot on the target OS. Matching Godot export templates are required. Targets are Apple Silicon macOS and Windows x64; a Mac build does not validate Windows.

```bash
uv sync --locked --group dev --group build
uv run --group build python tools/build_native.py
```

The script rebuilds the same named output directory under `dist/`, checks classification and regression with the bundled runtime, and writes a ZIP and SHA-256. `--reuse-core` is only for local GUI debugging when core/dependencies are unchanged; rebuild fully for delivery. Verify versions, lockfile, architecture, licenses, extracted-app startup and native dialogs. Apps without commercial signing/notarization may trigger OS prompts.

[Core CI](../.github/workflows/ci.yml) covers three operating systems. The [standalone workflow](../.github/workflows/native-test-build.yml) builds Windows on manual dispatch or pushes to `desktop-test`. A push consumes build resources; use this branch when a test package is needed. It retains artifacts without creating a release.

### Release assets and the local researcher kit

The 0.2.0 GitHub Release uploads only the Windows-x64 and macOS-arm64 application ZIPs, with Chinese, English and French notes. Build scripts still generate SHA-256 files for local verification; do not upload them or an extra source ZIP. GitHub provides automatic Source code downloads. `tools/package_release.py` is an optional local source archiver requiring a clean checkout and current PDFs; keep its output out of application assets.

First verify the README and researcher guide against 0.2.0, then generate PDFs. Replace the font path below with an embeddable Chinese-capable TrueType font. `output/pdf/sources.json` records source hashes; regenerate and visually inspect every page after source changes.

```bash
uv run --with reportlab python tools/build_release_pdfs.py --font /path/to/chinese-font.ttf
uv run python tools/package_researcher_share.py --windows-zip dist/PsyML-Toolkit-0.2.0-Windows-x64.zip
```

The sharing script never calls release APIs. It creates `PsyML-Toolkit-Researcher-Share-v0.2.0.zip` at the root for direct sharing only; **never upload it to Release**. Windows/ contains the app, TestData/ training/configuration/prediction files, Documents/ two Chinese PDFs, and 从这里开始.txt explains folders and steps and directs Mac users to GitHub. If the destination exists, move or back up the old kit before rebuilding; do not reuse stale PDFs.

When changing versions, check pyproject.toml, src/psyml/__init__.py, uv.lock, gui/export_presets.cfg, tools/build_native.py, tools/NATIVE_START_HERE.txt, PDF-builder versions/links and trilingual release notes. Inspect BUILD.json commit, initial checkout status and generated changes; verify archives against local hashes. Bundled GUI smoke tests cover classification/regression training, saving/loading, ten new predictions each and XLSX export, without replacing real-window inspection. Commit each independent completed feature and push immediately; do not accumulate pushes.
