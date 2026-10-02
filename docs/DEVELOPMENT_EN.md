# Developer guide

[README](../README.md) · [中文](DEVELOPMENT_ZH.md) · [Français](DEVELOPMENT_FR.md)

For contributors modifying, maintaining or building PsyML. Researchers use the GUI without developer tools or these commands. There is one maintained code version: the `__version__` constant in `src/psyml/__init__.py` (`pyproject.toml` reads it through hatch dynamic metadata; the current source is the official `0.3.1`, displayed unchanged, while a `0.3.1.dev0` development release displays as `0.3.1-dev`). The standalone packages available for each version are those listed on the Releases page; the v0.2.0 and earlier packages do not contain the new features or second-round fixes in this source checkout.

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

`psyml.data.profiling` is the pure helper behind the data check: `profile_columns` / `column_profile` / `category_summary` / `identifier_signals` build per-column metadata from a DataFrame (non-missing count, unique count, near-unique ratio, optional value counts with truncation, and evidence-based identifier signals). `protocol.dataframe_preview` attaches values only when `include_sample=True` and returns none by default; the page-1 GUI `gui/scripts/data_check_ui.gd` consumes that metadata instead of estimating from the first five rows, and never deletes columns or changes roles.

`build_interpretation` in `psyml.reporting.interpretation` aggregates only evidence the runner already produced (procedure_results, per-combination folds, tuning_rows, leaderboard, validation_summary) and adds no model fit; `write_interpretation_outputs` writes `result_interpretation.json`, `interpretation_baseline_differences.csv` and `result_interpretation.md`, indexed by `result.json.artifacts`. For independent validations `build_independent_interpretation` writes only a root overview/index. The GUI summary lives in `gui/scripts/result_interpretation_ui.gd`. Core regression: `tests/test_profiling.py`, `tests/test_interpretation.py`; GUI: `gui/tests/test_data_check.gd`, `gui/tests/test_interpretation_results.gd`. The baseline compares only a successfully completed dummy on the same validation, fold set and metric, with a fixed sign (positive = better); descriptive statistics never flow back into selection or tuning.

### Permutation-importance interfaces

`ExperimentConfig.permutation_importance` (default `false`) and `permutation_repeats` (1–100, default `10`) control this feature; legacy configs that omit them stay off. The engine lives in `psyml.evaluation.permutation`, artefact writing in `psyml.reporting.permutation`. The runner passes only the inner-selected outer-fold Pipeline and its test rows to the engine, and writes `interpretations/<validation>/` after selection is frozen. Results are stored per validation as `dict[validation, list[record]]`; failed records keep `status=failed` plus `error_type/error` and never fabricate variables. `result.json.permutation`, `analysis_manifest.json.interpretations` and the Methods/reproducibility reports index only files that exist. Core regression lives in `tests/test_permutation*.py`; GUI settings and result display are in `gui/scripts/permutation_ui.gd` with regression in `gui/tests/test_permutation.gd`; `examples/quickstart/*_permutation_config.json` gives an importable classification/regression smoke. Keep it OFF by default and do not change selection, splitting or metric semantics.

## Behavior to preserve

- Fit encoding, imputation and scaling on the relevant training partition only. Select families/parameters internally, never from outer rankings. Explain scientific changes; passing tests is not scientific justification.
- `primary_validation: null` produces separate complete results or failure records. There is no global winner or headline metric at the root and no automatic highest-score selection.
- Coordinate configuration changes across dataclasses, schemas, protocol, GUI import/save and tests; preserve old configurations and all parameters, candidates, variable order and figure choices.
- Use OS-native file/directory dialogs. Check hover, focus, selection and disabled contrast in custom controls.
- Update Chinese, English and French UI text, README, researcher guides and matching screenshots when visible behavior changes. Language changes must not change the analysis. Report, figure and raw-error languages are described in the [researcher guide](RESEARCHER_GUIDE_EN.md#output-languages).
- Record runtime versions in `analysis_manifest.json`. When dependencies change, update `uv.lock`, reports, packaged metadata and licenses.

## Verification and contributions

[TESTING.md](TESTING.md) contains developer regression commands and manual checks; it is not a prerequisite for GUI users. Match checks to changes. Inspect UI changes in a real window and validate methodological changes against small, checkable datasets. Use synthetic or publicly shareable minimal examples only.

PRs should explain the problem, resulting behavior, validation and limitations. Avoid unrelated refactoring; identify scientific, compatibility and dependency impacts. Contributions follow [Apache-2.0](../LICENSE). Never upload participant data, unpublished material or credentials. Keep developer commands out of researcher instructions.

## Optional single-sample explanation extra

The single-sample explanation feature depends on `shap`, `numba` and `llvmlite`, kept out of the default install so ordinary analysis and prediction retain their cold-start and package size. Install them only when needed:

```bash
uv sync --extra explain
uv pip install -e ".[explain]"   # pip/venv equivalent
```

`pyproject.toml` pins version-appropriate SHAP releases per Python (3.10 → 0.49.x, 3.11 → 0.51.x, 3.12 → 0.52.x). `uv.lock` records them without upgrading unrelated dependencies such as scikit-learn. `tools/build_native.py` bundles shap/numba/llvmlite into the core, copies the maintained notices from `tools/licenses/` into the package’s `licenses/` directory, and `--explain-smoke` checks bundled classification/regression explanation and reconstruction.

## Fitted coefficients (no extra dependency)

[coefficients.py](../src/psyml/models/coefficients.py) reads `coef_`/`intercept_` only from an already fitted PsyML `preprocess`+`model` pipeline. It builds an exact transformed-feature/source-column/category mapping from `ColumnTransformer.output_indices_` and each sub-step (imputer `statistics_`, scaler `mean_/scale_` or `min_/scale_/data_min_/data_max_`, OneHotEncoder `categories_`), and verifies reconstruction of `predict` (regression) or `decision_function` (classification) through the same pipeline transform on supplied rows (atol 1e-7 / rtol 1e-6). It never fits, never changes the model, never feeds back into tuning and never converts to raw units. The report also records `input_features`/`dropped_features` (all-missing columns with reason, original index, missing strategy), `encoding.per_source` (per-column categories and `drop_idx_`) and the training-dtype source (saved metadata or explicitly unknown). With supplied rows, a failed check (tolerance/shape/non-finite) returns `status=error` and refuses to publish a success artifact; without rows the report stays explicitly unverified, and CLI/GUI keep the two states apart. The normal runner writes CSV/JSON/notes under `coefficients/`; the CLI is `psyml coefficients` (reusing trust/hash/version and `model_input`, writing only to a new/empty directory, JSON last). The loaded-model path validates the PsyML provenance (`psyml_version`/`fit_scope`) and estimator type; unknown models get a specific reason and ordinary prediction is unaffected. Tests live in `tests/test_coefficients.py`, `tests/test_coefficients_cli.py` and `gui/tests/test_coefficients.gd`; `--coefficients-smoke` checks bundled classification/regression extraction.

## Building and release maintenance

[build_native.py](../tools/build_native.py) freezes the core with PyInstaller and exports Godot on the target OS. Matching Godot export templates are required. Targets are Apple Silicon macOS and Windows x64; a build made on macOS does not validate Windows.

```bash
uv sync --locked --group dev --group build --extra explain
uv run --locked --group build --extra explain python tools/build_native.py --output-dir dist/v0.3.1 \
    --permutation-smoke --explain-smoke --coefficients-smoke
```

The script rebuilds the same named output directory under `dist/`, checks classification and regression with the bundled runtime, and writes a ZIP and SHA-256. `--reuse-core` is only for local GUI debugging when core/dependencies are unchanged; rebuild fully for delivery. Verify versions, lockfile, architecture, licenses, extracted-app startup and native dialogs. Apps without commercial signing/notarization may trigger OS prompts.

The build checks the OS, native 64-bit Python and the Python/Godot executable headers before building, then checks the exported GUI and frozen core against the named target (Mach-O arm64 or PE x64). The commands above retain the explain extra in both installation and execution and run all three optional bundled-core smoke tests required for delivery. BUILD.json records the initial source status, commit, uv.lock SHA-256 and final status after smoke. Packaging aborts on newly modified source files or a changed commit/lockfile. The post-build source-change allowlist is intentionally empty: dist/, tmp/ and gui/.godot/ are already ignored. Review and commit any Godot source/import changes, then rebuild; do not blanket-allow GUI changes. A pre-existing dirty checkout or a reused core is suitable only for local debugging and fails release verification.

**Native export goes through `tools/build_native.py` only.** The macOS/Windows version fields in `gui/export_presets.cfg` (`application/short_version`, `application/version`, `application/file_version`, `application/product_version`) hold the placeholders `@PSYML_MACOS_VERSION@` / `@PSYML_WINDOWS_VERSION@`, not publishable version numbers; exporting directly from the Godot editor fails or writes wrong versions. `build_native.py` derives numeric export versions from the single `src/psyml/__init__.py` constant for the duration of one export (both the official `0.3.1` and the development `0.3.1.dev0` export as macOS `0.3.1`, Windows `0.3.1.0`) and restores the template in a `finally` block, so neither success nor failure leaves a modified preset. Always trigger native export through that script instead of using the Godot preset directly.

[Core CI](../.github/workflows/ci.yml) covers three operating systems. The [standalone workflow](../.github/workflows/native-test-build.yml) builds Windows on manual dispatch or pushes to `desktop-test`. A push consumes build resources; use this branch when a test package is needed. It retains artifacts without creating a release.

### Release assets

The one-version [v0.3.1 workflow](../.github/workflows/release-v0.3.1.yml) builds and verifies a candidate on `release/v0.3.1`. After the automated quality and native-build checks succeed, a separate `publish/v0.3.1` branch at the identical main commit publishes the two native ZIPs. Existing tags, releases and assets are never replaced. Uploads and unauthenticated public downloads are checked against SHA-256.

The Release contains only Windows-x64 and macOS-arm64 application ZIPs, with [three-language notes](RELEASE_NOTES_0.3.1.md). GitHub supplies source archives. Markdown documentation and offline quickstart screenshots remain available; the release workflow does not generate, require or attach PDFs. Historical manual document/share tools are outside the release path and run only when explicitly requested.

Place the two ZIPs and their `.sha256` sidecars from the same clean commit in `dist/v0.3.1/`, then create and verify the two-entry checksum manifest:

```bash
uv run python -c "import hashlib; from pathlib import Path; d=Path('dist/v0.3.1'); names=['PsyML-Toolkit-0.3.1-macOS-arm64.zip','PsyML-Toolkit-0.3.1-Windows-x64.zip']; (d/'SHA256SUMS').write_text(''.join(hashlib.sha256((d/n).read_bytes()).hexdigest()+'  '+n+'\n' for n in names), encoding='utf-8')"
uv run python tools/verify_release_artifacts.py --directory dist/v0.3.1 --platform all
```

`tools/verify_release_artifacts.py` inspects archive CRC/decompression, paths, required files, actual executable architectures and BUILD.json version/commit/lock/clean-source provenance. `all` mode requires both native ZIPs, their sidecars and `SHA256SUMS`; single-platform mode needs only that platform's ZIP and sidecar. These verification files remain workflow artifacts rather than additional Release assets.

Godot imports and exports from a disposable GUI copy under `tmp/native/gui`, preserving the tracked sources. The Mac build uses the official universal Godot template, extracts and verifies its arm64 slice, then applies and verifies the ad-hoc signature.

When changing versions, modify only `__version__` in `src/psyml/__init__.py` (`pyproject.toml` is dynamic and follows automatically; `gui/export_presets.cfg` keeps its placeholders while `tools/build_native.py` derives the numeric values at export time). Also check uv.lock, `tools/build_native.py`, `tools/NATIVE_START_HERE.txt`, trilingual release notes (`docs/RELEASE_NOTES_<version>.md`). Inspect BUILD.json commit, initial checkout status and generated changes, and verify archives against local hashes with `tools/verify_release_artifacts.py`. Bundled GUI smoke tests cover classification/regression training, saving/loading, ten new predictions each (written as `predictions.csv` in that run's folder) and that the open action targets exactly that run folder, without replacing real-window inspection. The core CLI `export-table` and multi-format read/write remain supported and are outside this bundled smoke check.


## Open the application

Check [Releases](https://github.com/GuGuGu-coocoo/PsyMl_Toolkit/releases) for available versions and platforms. The v0.3.1 standalone ZIPs (`macOS-arm64`, `Windows-x64`) are built from the same commit; the assets and platforms actually available are those listed on the [v0.3.1 Release](https://github.com/GuGuGu-coocoo/PsyMl_Toolkit/releases/tag/v0.3.1) page, and earlier official versions stay on the same Releases page. These application packages include the runtime. GitHub’s automatic Source code archives contain source only; see the [developer guide](../docs/DEVELOPMENT_EN.md) for source installation.

**Source checkout and download package.** This source checkout is the official **0.3.1** version (single version source) with the features and improvements made after v0.2.0 (permutation importance, data checks and result interpretation, single-sample SHAP, fitted coefficients, plus interface and output-flow improvements). Download packages follow their own version: rely on the assets listed on the Releases page and on the documentation and interface inside the package you download; the v0.2.0 and earlier packages do not contain these features or fixes, so their interface, output layout and screenshots remain the older version. There is one maintained version source: `__version__` in `src/psyml/__init__.py` (`pyproject.toml` is dynamic), and the standalone `BUILD.json` is generated from the same constant by `tools/build_native.py`. On macOS, a source run starts by double-clicking `Launch PsyML.command` in the project root (dependencies: [developer guide](../docs/DEVELOPMENT_EN.md)).

- **macOS (Apple Silicon)**: fully extract the matching application archive and double-click `PsyML Toolkit.app`.
- **Windows (Intel/AMD x64)**: fully extract the matching archive and double-click `PsyML Toolkit.exe`. Keep the adjacent `core` folder; do not move the EXE alone.
- Python, analysis dependencies and the GUI runtime are bundled. No terminal, additional installation or internet download is required to use the app. The user test kit is in `examples/quickstart/`; start with **Import configuration…**.
- A small version label under the application name shows the current version: a standalone package reads its bundled `BUILD.json`, a source run reads `__version__` in `src/psyml/__init__.py` (`pyproject.toml` is dynamic and reads the same constant); the official `0.3.1` displays unchanged, a `0.3.1.dev0` development release displays as `0.3.1-dev`, and the value is not hard-coded.
- The apps do not yet have commercial developer signing/notarization. Your OS may request confirmation on first launch: macOS offers confirmation under **System Settings → Privacy & Security**; Windows may show a security prompt. Verify the source and follow your institution’s device policy.

## Source-checkout checks

A standalone package and a source checkout can contain different fixes. The five points below help you check behaviour in a source checkout.

1. Start the interface from the source checkout root (on macOS you can double-click `Launch PsyML.command`); dependency installation is in the [developer guide](DEVELOPMENT_EN.md). Standalone packages do not include the developer test environment. Import the classification or regression configuration from `examples/quickstart/` and run it once.
2. **Version label:** a small label under the application name should show the current version number `0.3.1`. A source run's single source is `__version__` in `src/psyml/__init__.py` (`pyproject.toml` is dynamic); a standalone package reads its bundled `BUILD.json`, generated from that same constant, and a `0.3.1.dev0` development release displays as `0.3.1-dev` while the official `0.3.1` displays unchanged.
3. **Output folders and legacy results:** a new page-2 training run appears under `training/run_*` in the chosen result root; page-4 prediction, SHAP and coefficients land in new `run_*` directories under `prediction/`, `explanation/` and `coefficients/` in the shared root, never overwriting existing files and never writing to the hidden application-data folder. Legacy `run_*` training folders directly under the result root still open in place, and their contents are not rewritten.
4. **Page 4 result actions:** prediction, SHAP and coefficients each provide a results-folder action. Prediction uses **Open prediction results folder**, which opens that run directory. Only SHAP also provides **Open waterfall image**. Prediction data are saved as `predictions.csv`.
5. **Scroll ownership and finalising status:** when a gesture starts on the page it keeps scrolling the page past a nested small table, and only a gesture that starts on the table scrolls that table; a pause of about 250 ms starts a new gesture that may choose a different layer (the lock only affects wheel/swipe scrolling). During final result writing the status should read "Finalizing and writing results…" with the progress bar not yet full; the result page opens only after `completed`. Use **Copy full error** when reporting a problem.

This guide describes the behavior of the source checkout **0.3.1** (single version source) with the features and improvements added after v0.2.0 (permutation importance, data checks and result interpretation, single-sample SHAP, fitted coefficients, plus interface and output-flow improvements). Standalone packages follow their own version: check the assets listed on the Releases page. The v0.2.0 and earlier packages do not contain these features or fixes, so their interface and output layout may differ from a source checkout. There is one maintained version source: the `__version__` constant in `src/psyml/__init__.py`. `pyproject.toml` reads it through dynamic metadata, the standalone `BUILD.json` is generated from the same constant by `tools/build_native.py`, and the interface shows the same value (the official `0.3.1` unchanged, a `0.3.1.dev0` development release as `0.3.1-dev`). Check `analysis_manifest.json` in each analysis output for runtime and dependency versions, and do not infer the download package's contents from this guide's title.

## Batch prediction CLI

```bash
psyml predict --model output/model/best_ridge.joblib --input new_data.xlsx --output predictions.xlsx --trust-model
```

Load only trusted PsyML models: joblib/pickle loading can execute code, and `--trust-model` confirms the source. Use `--check-only` without `--output` to inspect compatibility. Required predictors are selected in training order; missing columns, invalid numbers and missing values without imputation block prediction. Every original column (including the target) and row order is retained. Regression appends `predicted_value`; classification appends `predicted_class` and native class probabilities when supported. Collisions get numeric suffixes on new columns. Repeat `--feature` in model order for older models lacking names. All 9 input formats remain supported; writable formats are CSV, TSV, XLSX, SAV, DTA, XPT and Parquet. XLS/SAS7BDAT are read-only; save as XLSX. Statistical-format naming/type restrictions produce explicit errors; choose XLSX/Parquet instead. The output extension controls CLI format; existing files are preserved by default.

The machine-learning core was written by the project author; the Godot GUI was developed with AI assistance. AI assistance does not replace human code review or scientific judgment.
