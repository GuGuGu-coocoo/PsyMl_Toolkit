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

## Building and release maintenance

[build_native.py](../tools/build_native.py) freezes the core with PyInstaller and exports Godot on the target OS. Matching Godot export templates are required. Targets are Apple Silicon macOS and Windows x64; a Mac build does not validate Windows.

```bash
uv sync --locked --group dev --group build
uv run --group build python tools/build_native.py
```

The script rebuilds the same named output directory under `dist/`, checks classification and regression with the bundled runtime, and writes a ZIP and SHA-256. `--reuse-core` is only for local GUI debugging when core/dependencies are unchanged; rebuild fully for delivery. Verify versions, lockfile, architecture, licenses, extracted-app startup and native dialogs. Apps without commercial signing/notarization may trigger OS prompts.

[Core CI](../.github/workflows/ci.yml) covers three operating systems. The [standalone workflow](../.github/workflows/native-test-build.yml) builds Windows on manual dispatch or pushes to `desktop-test`. A push consumes build resources; use this branch when a test package is needed. It retains artifacts without creating a release.

`tools/package_release.py` creates source distributions; use `tools/build_native.py` for standalone apps. `tools/build_release_pdfs.py` generates Chinese usage and terminology PDFs in `output/pdf/`; review every page before distribution. Maintainers publish tested and accepted artifacts manually.
