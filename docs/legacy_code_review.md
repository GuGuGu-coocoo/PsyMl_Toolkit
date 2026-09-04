# Legacy Code Review

Review date: 2026-09-04

## Scope and method

This is a read-only review of `legacy/original/program/`. No legacy file was changed or executed against research data.

- All 72 Python files were parsed with Python AST; there were no syntax failures.
- The review examined the current classifier, regressor, decision-tree and RNN implementations, their entry points and their repeated historical copies.
- Runtime viability was checked only where it did not require loading legacy data. In scikit-learn 1.9, the Lasso default `selection='cycic'` raises `InvalidParameterError`; valid values are `cyclic` and `random`.
- Prior baseline results remain applicable: legacy end-to-end workflows have not been run because their hard-coded paths and saved-model paths do not exist in the current layout.

## Executive conclusion

The algorithms are useful reference material, but no legacy training script is suitable for direct reuse. The modern `src/psyml/` implementation should remain the only path for new analyses. In particular, the legacy preprocessing and feature-importance procedures can leak test information, and saved estimators lack the preprocessing needed for reliable prediction.

## P0 — Correctness and statistical risks

### Preprocessing uses the full dataset before the split

The classifier families calculate global minima and maxima before `train_test_split` (for example, `Classiffication_Models-v1.1.2/programs/KNN_Classiffication_Sklearn.py`, lines 47–68). The scaler therefore observes test-set values. The regression Lasso and SVR scripts likewise call `StandardScaler.fit_transform` on the full feature matrix and target before splitting (for example, `Regression_Models-v1.1.0/programs/Lasso_Regressor_sklearn.py`, lines 37–58). This makes held-out performance optimistic.

**Required replacement:** use a fitted-on-train-only scikit-learn Pipeline, as the modern core now does.

### Feature importance uses test observations or resubstitution data

The classification scripts fit on the training subset but call `permutation_importance(model, X, y, ...)` on the complete dataset (for example, KNN lines 76–80). Regression scripts additionally refit on all rows before producing overall importance and metrics (for example, `KNN_Regressor_sklearn.py`, lines 84–101). Those importance scores and overall metrics are not independent held-out evidence.

**Required replacement:** compute importance on a held-out set or inside a correctly nested validation procedure, and label any training-set diagnostic as such.

### Regression outcomes are reported on scaled targets

Lasso, SVR and MLP regression standardize `y` before splitting, then calculate MAE and MSE on the standardized scale without inverse transformation. R² is invariant to this scaling, but MAE and MSE are no longer in the target variable's original units. The saved estimator also lacks the target transformer.

**Required replacement:** use `TransformedTargetRegressor` or inverse-transform predictions before reporting original-unit errors; serialize the complete pipeline.

### Lasso default cannot run

`Lasso_Regressor_sklearn.py` declares `selection='cycic'` in both `lasso` and `save_lasso` (lines 19 and 160). This is a spelling error and fails parameter validation in the locked environment.

**Required replacement:** use `selection='cyclic'` and cover the default configuration with a test.

### Validation does not reflect common research designs

All observed classifier and RNN holdout splits use `train_test_split` without `stratify`; none use group-aware splitting. Repeated measures from one participant can therefore enter both partitions, and small/imbalanced classes can be absent from a partition. No hyperparameter search is nested in validation.

**Required replacement:** expose stratified and group-aware strategies, define the unit of independence, and use nested cross-validation when tuning parameters.

## P1 — Engineering, reproducibility and safety risks

- **Prediction mismatch:** training helpers preprocess differently from `save_*` helpers; saved scikit-learn estimators contain no scaler or encoder. Prediction scripts load those estimators and feed raw Excel values (for example, `Classiffication_Models-v1.1.2/programs/predict.py`, lines 24–98).
- **Hard-coded paths and import-time execution:** entry points contain absolute `E:\\...` input/model paths and start threads at module import (for example, `Classiffication_Models-v1.1.2/programs/main.py`, lines 23–25 and 167–174). They are neither portable nor safe to import as library code.
- **Output can modify input data:** prediction scripts append sheets to the same workbook passed as input. This risks overwriting or contaminating the source dataset and has no run-specific output directory.
- **Unreliable result writing:** many loop scripts use the private `ExcelWriter._save()` API rather than a context manager. They also write fixed filenames in the working directory, so runs overwrite one another.
- **No defensive error handling:** no legacy Python source contains a `try`/`except` block. Invalid file paths, types, model parameters and existing sheet names surface as raw exceptions.
- **Non-deterministic estimators:** MLP, Random Forest and Decision Tree objects frequently omit `random_state`; fixed shuffling alone does not make a full run reproducible.
- **Duplicate implementations:** exact-file hashes show multiple repeated historical copies, including four copies of `if_miss.py`, three copies each of several v1.1.0 classifier/loop modules, and duplicate decision-tree modules. Bug fixes would otherwise diverge.
- **Unsafe model loading:** the RNN predictor uses `torch.load(model_path)` on a whole serialized model. This must not be used for untrusted files; future code should store a state dict plus explicit architecture and use the safe loading mode supported by the target PyTorch version.

## P2 — Model-specific concerns

- Classifiers report accuracy and weighted precision/recall/F1 but do not report balanced accuracy, ROC-AUC or explicit class support in a consistent way. Probability output is enabled for SVM despite no AUC workflow.
- The `StackingClassifier` functions use instantiated estimator lists as mutable default arguments. The current defaults differ from the configured entry-point stack and omit fixed seeds.
- Decision-tree visualization hard-codes five class labels (`['0', '1', '2', '3', '4']`), which can disagree with the actual target classes; its classifier also lacks a fixed random seed.
- The RNN assumes labels are contiguous non-negative class indices for `CrossEntropyLoss`, has no validation split or early stopping, and does not establish reproducible PyTorch seeds. Its constructor parameter order is confusing: the call at line 167 passes `hidden_size, L1, L2` into parameters named `L1, L2, hidden_size`.
- Correlation p-values calculated between a target and in-sample predictions are exploratory diagnostics, not valid confirmatory inference; the workflow does not account for model selection or repeated testing.

## Classification and migration decision

| Legacy asset | Classification | Decision |
| --- | --- | --- |
| KNN, MLP, Random Forest, SVM and Stacking classifier scripts | General tabular classification algorithms | **Core Candidate (algorithm only).** Retain as reference; use `src/psyml/`, not these files. |
| Decision-tree scripts | General tabular classification | **Core Candidate (algorithm only).** The two directory copies are duplicates; preserve but do not migrate their implementation. |
| KNN, Lasso, MLP, Random Forest and SVR regressor scripts | General tabular regression algorithms | **Core Candidate (algorithm only).** Rebuild via the modern pipeline; correct the Lasso default and target scaling. |
| `OH_NLP-v1.1.0` / `v1.1.1` RNN projects | Chinese text classification | **Specialized / Experimental.** Keep outside the GUI and modern tabular core until a separate data specification, deterministic training and safe artifact format exist. |
| `simulate_0` | Small SVM/MLP experiment | **Specialized / Experimental.** Retain as a synthetic-data reference only. |
| Classification v1.0.0, v1.1.0 and v1.1.1 script sets; duplicate top-level decision tree; `NLP_test`; `test` placeholders | Historical releases, duplicates and prototypes | **Archive Only.** Preserve history but make no functional changes. |

## Follow-up order

1. Keep all new work in `src/psyml/`; do not patch legacy scripts except for an explicit preservation task.
2. In Phase 10, add baseline models to the modern factory and tests; do not import legacy preprocessing.
3. Add explicit validation configuration, group-aware cross-validation and optional held-out permutation importance before presenting feature rankings.
4. Add run manifests and source-data provenance before the GUI phase.
5. Keep the RNN project archived until it has an independent experimental protocol and reproducibility plan.
