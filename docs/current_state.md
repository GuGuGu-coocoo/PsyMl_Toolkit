# Current State Baseline

Baseline date: 2026-09-04

## Environment

- `uv lock` and `uv sync --group dev` complete successfully.
- The locked environment uses Python 3.12.13.
- The installed baseline includes NumPy 2.5.2, pandas 3.0.5, SciPy 1.18.1, scikit-learn 1.9.0, PyTorch 2.14.0, matplotlib 3.11.1, openpyxl 3.1.5, graphviz 0.21, jieba 0.42.1, and joblib 1.6.0.
- All 72 legacy Python sources compile successfully in that environment.

## Working

- The Python environment and all declared imports load successfully.
- `legacy/original/program/test/pooling_test.py` runs successfully as a PyTorch variable-length-sequence demonstration.
- The legacy source tree passes syntax compilation.

## Broken

- 19 Python files contain hard-coded `E:\\...` Windows paths. The configured paths do not exist in the repository's current layout, so the associated training and prediction entry points are not runnable without manual changes.
- Classification v1.1.0 and v1.1.1 refer to a non-present `Classiffication_Models-v1.2.1` directory.
- Root-level `pytest` has no discoverable test functions. `autohluon_test.py` is empty; `pooling_test.py` is a runnable demonstration rather than a test function.
- The scoped legacy test directory contains no pytest tests. `autohluon_test.py` is empty; `pooling_test.py` is a runnable demonstration rather than a test function.

## Unknown

- End-to-end execution of the KNN, Lasso, MLP, Random Forest, SVM/SVR, stacking, decision-tree, and RNN workflows has not been validated after paths are configured.
- Output writing, model loading, Graphviz rendering, and RNN prediction have not been validated against the synthetic datasets.
- Statistical validity, leakage protection, and model-quality metrics are intentionally outside this baseline and remain for the read-only review phase.

## Manual configuration required

Before any legacy workflow can be run, its entry script requires manual review and usually edits to:

- input data path and prediction-data path;
- target variable and feature columns, inferred from the selected dataset;
- model choice and model hyperparameters;
- random seed, train/test split, and output destination;
- saved-model and vocabulary paths for prediction/RNN workflows.

## Inputs

- Excel workbooks (`.xlsx`) are the primary dataset format used by the training and prediction scripts.
- CSV is used by the simulation experiment.
- One SPSS `.sav` source is retained with a synthetic 94-row, 16-column dataset; no legacy Python reader for this format was identified. The original is retained only in the user's cloud backup.

## Outputs

- Excel result workbooks and prediction exports.
- Classification and regression metrics, including accuracy/precision/recall/F1 and R²/MSE/MAE.
- Saved Joblib and PyTorch model files.
- Decision-tree Graphviz output and optional matplotlib plots.

Original/derived result directories, trained-model artifacts, and archives have been removed locally and remain excluded from Git to prevent privacy leaks and accidental publication of generated artifacts.
