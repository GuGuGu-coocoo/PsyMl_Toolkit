# Phase 8 and 9 Completion Record

Completion date: 2026-09-04

## Scope boundary

`legacy/original/program/` remains preserved as legacy source. The fixes and new architecture are implemented only under `src/psyml/`.

## Phase 8 — First Round Fixes

- A scikit-learn `Pipeline` fits imputation, scaling and categorical encoding using only the training partition.
- Input/output paths, task, target, model, group column, random seed and model parameters are explicit `ExperimentConfig` fields.
- CSV and Excel inputs, target/group columns and empty datasets are validated before training.
- A group column selects `GroupShuffleSplit`; ordinary classification uses stratification when feasible.
- Held-out predictions are the only source of reported metrics and exported predictions.
- SVM ROC-AUC uses `predict_proba` when available and otherwise `decision_function`, avoiding the deprecated `SVC(probability=True)` path.

## Phase 9 — Modern PsyML Core

The package under `src/psyml/` supplies:

- `psyml` / `python -m psyml` command-line entry points;
- data loading and validation for CSV, XLSX and XLS;
- classification and regression model factories;
- shared preprocessing, validation, evaluation and reporting modules;
- result files: `metrics.csv`, `predictions.csv` and `config.json`.

Supported models are KNN, Lasso, MLP, Random Forest and SVR for regression; KNN, Random Forest, SVM, MLP, Decision Tree and Stacking for classification.

## Verification

On completion, the following commands passed in the locked environment:

```text
.venv/bin/pytest -q        # 6 passed
.venv/bin/ruff check src tests
uv run psyml --help
```

The automated tests cover CSV loading and validation, group isolation, training-only scaler fitting, classification and regression result export, and the command-line path.
