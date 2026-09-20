# Researcher reference: models, metrics, results and terminology

This guide describes the behavior of the source checkout **0.3.0** (single version source) with the features and human-feedback fixes added after v0.2.0 (permutation importance, data checks and result interpretation, single-sample SHAP, fitted coefficients; first round FR-012–FR-016; second round FR-016 supplement and FR-017–FR-020). Standalone packages and distribution PDFs follow their own version: check the assets listed on the Releases page. The v0.2.0 and earlier packages and their PDFs do not contain these features or fixes, so their interface and output layout may differ from a source checkout. There is one maintained version source: the `__version__` constant in `src/psyml/__init__.py`. `pyproject.toml` reads it through dynamic metadata, the standalone `BUILD.json` is generated from the same constant by `tools/build_native.py`, and the interface shows the same value (the official `0.3.0` unchanged, a `0.3.0.dev0` development release as `0.3.0-dev`). Check `analysis_manifest.json` in each analysis output for runtime and dependency versions, and do not infer the download package's contents from this guide's title.

[Back to the English README](../README.md#english) · [中文](RESEARCHER_GUIDE_ZH.md) · **English** · [Français](RESEARCHER_GUIDE_FR.md)

This guide explains concepts used by the current PsyML Toolkit implementation. Consult it while configuring an analysis or interpreting outputs. Code names match configuration keys and CSV fields. The guide is readable offline; external references require internet access. Short formulas support understanding, not manual calculation. If your Markdown reader does not render mathematics, use the accompanying plain-language explanations.

Suitability depends on the research question, data structure and validation design. There is no universally best model or acceptable score. The project performs prediction; it does not automatically establish causality, statistical significance or clinical decision rules. Automatically generated summaries and reports are not guaranteed to be correct and require researcher review.

## Navigation

- [1. Data and preprocessing](#data)
- [2. Supported models](#models)
- [3. Classification and regression metrics](#metrics)
- [4. Validation, tuning and the final model](#validation)
- [5. Reading output files and figures](#results)
- [6. Parameter and terminology reference](#glossary)
- [7. Common misconceptions and review order](#checklist)
- [8. Implementation and further reading](#references)

<a id="data"></a>

## 1. Data and preprocessing

| Term | Meaning in this project |
| --- | --- |
| Classification | Predicting discrete categories, such as condition A/B; at least two target classes are required. Numeric class labels do not automatically make the task regression |
| Regression | Predicting numerical outcomes, such as a scale score; prediction errors use the outcome's units |
| Target / outcome, `target_column` | The column to predict. It supplies training answers and is excluded from predictors |
| Predictor / feature, `feature_columns` | Input columns used for prediction. Identifiers and information available only after the outcome can introduce leakage |
| Group identifier, `group_column` | Links rows from the same participant, household or centre. It is excluded from predictors and is distinct from the target's class labels |
| Row / independent sample | Ten observations from one participant are not ten independent participants. Validation must reflect this dependence |
| Pipeline | Combines imputation, scaling, encoding and the estimator, refitting them within each training partition |

**Missing values:** rows with a missing target are removed first. With `drop`, rows still missing values in selected predictors, the target or the group column are removed; unselected administrative columns do not trigger removal. Otherwise, numeric predictors use mean, median or mode imputation, while categorical predictors always use mode imputation. Remaining missing group identifiers cause an error rather than an inferred group assignment. Imputation does not establish that the missingness mechanism is unbiased.

**Scaling:** `standard` uses training statistics, `z = (x − mean_train) / std_train`. `minmax` uses the training minimum and maximum. New values outside the training range can map outside [0, 1]. `none` disables scaling. Distances, regularization and gradient optimization are often sensitive to measurement units; tree models usually do not depend on such scaling.

**One-hot encoding:** categorical predictors become category-indicator columns. The implementation distinguishes numeric and categorical inputs by dtype. Nominal categories stored as numeric 1/2/3 will therefore be treated as numbers unless addressed during data preparation. Unseen categories are ignored by the encoder; this does not mean their meaning has been learned.

**Data-check preview.** For a classification target the interface shows the observed number of categories, each category's count and its share of the **non-missing target**, together with total rows, the non-missing denominator and the missing count. An all-missing target never divides by zero, and unobserved categories plus NaN/None are not real classes. A heuristic hint flags **suspected identifier/participant columns** (by name token, or by near-unique integer/text values) and records the reason and ratio; it is a "suspected, please judge" note only, never deleting columns, changing roles or blocking the analysis, and the group column itself may be an identifier. Category and value counts come from the local preview mode; the default preview returns no values.

These details follow the [preprocessing pipeline](../src/psyml/preprocessing/pipeline.py) and [data preparation and runner](../src/psyml/runner.py).

<a id="models"></a>

## 2. Supported models

There are 12 classification options and 11 regression options, with 17 distinct code names. A shared name may instantiate different estimators for the two tasks. The GUI filters models by task. The limitations below explain behavior rather than prescribe automatic model selection. See the [model factory](../src/psyml/models/factory.py) and [catalog](../src/psyml/models/catalog.py).

### Available for both tasks

| Model and code | Main idea | Interpretation and limitations |
| --- | --- | --- |
| Dummy baseline, `dummy` | Ignores relationships with predictors. Classification uses training class frequencies or a majority rule; regression uses a mean or median, depending on `strategy` | A useful reference, not a useless model. Compare more complex models under the same validation design |
| K-nearest neighbors, `knn` | Uses K similar training observations: voting for classification, averaging for regression, optionally weighted by distance | Sensitive to scaling and distance. Neighborhoods can become less informative in high dimensions; K cannot exceed the relevant training fold's sample count |
| Decision tree, `decision_tree` | Recursively partitions observations using conditions, then predicts within leaves | Captures thresholds and interactions. Deep trees can overfit and small data changes can alter their structure |
| Random forest, `random_forest` | Combines randomized trees, averaging class probabilities or numerical predictions | Often more stable than one tree. More trees cannot repair a flawed design; regression generally extrapolates poorly beyond the training range |
| Gradient boosting, `gradient_boosting` | Adds trees sequentially to improve the current loss | Learning rate, tree count and depth interact. Expanding the search can increase both computational cost and overfitting risk |
| Multilayer perceptron, MLP, `mlp` | Learns mappings through layers of weighted transformations and nonlinear activations | Check scaling, sample size and convergence warnings. A neural network is not automatically superior with small samples |

### Classification only

| Model and code | Main idea | Interpretation and limitations |
| --- | --- | --- |
| Logistic regression, `logistic_regression` | Models class probabilities, usually with regularization; despite its name, this option is a classifier | The basic decision boundary is linear in transformed features. Coefficients do not automatically establish causality or significance |
| Support vector classification, `svm` | Finds a large-margin boundary; kernels can represent nonlinear boundaries | Sensitive to scaling and `C`. A decision score is not a calibrated probability |
| Gaussian naïve Bayes, `gaussian_nb` | Assumes conditional independence of features within a class and Gaussian feature distributions | Strong correlations or markedly non-Gaussian inputs can undermine these assumptions. Probability output does not imply calibration |
| Linear discriminant analysis, LDA, `lda` | Models Gaussian classes with a shared covariance matrix, producing a linear boundary | Distributional and covariance assumptions matter; high dimensionality, small samples and collinearity require attention |
| Quadratic discriminant analysis, QDA, `qda` | Allows a different covariance matrix for each class, producing a quadratic boundary | Estimates more quantities than LDA. Small class sizes and redundant features can make covariance estimation unstable |
| Stacking, `stacking` | Trains a meta-model on cross-fitted predictions from base models | Here, base models are KNN, random forest and SVM; the meta-model is logistic regression. Complete preprocessing pipelines are cross-fitted, with group-aware splits when groups are supplied. Computational cost is higher |

For intuition, binary logistic regression can be written as:

$$
p(y=1\mid x)=\frac{1}{1+\exp[-(b+\beta^\top x)]}.
$$

Here, 1 denotes the mathematical positive class, `b` is the intercept, `β` contains coefficients and `x` contains preprocessed features. This formula does not imply that the GUI allows arbitrary selection of a clinical positive class. The training objective can also differ from the metric, such as F1, used for model selection.

### Regression only

| Model and code | Main idea | Interpretation and limitations |
| --- | --- | --- |
| Linear regression, `linear_regression` | Predicts a weighted sum of features by minimizing squared residuals | Its basic form does not automatically represent arbitrary nonlinearity; collinearity can destabilize coefficients |
| Ridge regression, `ridge` | Adds an L2 penalty to shrink linear coefficients | Usually retains multiple nonzero coefficients; larger `alpha` means a stronger penalty |
| Lasso regression, `lasso` | Adds an L1 penalty, which can set some coefficients to zero | A zero coefficient is conditional on this fit and penalty, not proof that the variable has no scientific role |
| Elastic Net, `elastic_net` | Combines L1 and L2 penalties, with `l1_ratio` controlling their mix | Interpret feature selection cautiously with correlated inputs; strength and mixing ratio must be considered together |
| Support vector regression, `svr` | Fits with an ε-insensitive tolerance region, optionally using a kernel | `epsilon` is a tolerance parameter on the outcome scale, not a confidence interval; scaling, `C` and kernel choice matter |

Linear prediction is `ŷ = b + Σ βⱼxⱼ`. A conceptual description of regularization is:

$$
\text{objective}=\text{fit loss}+\lambda\times\text{penalty},\qquad
L_1=\sum_j|\beta_j|,\quad L_2=\sum_j\beta_j^2.
$$

This is not a single exact objective shared by all estimators: loss normalization and parameter meanings differ. Equal `alpha` values need not imply equal regularization across models. Smaller `C` generally means stronger regularization in SVM and logistic regression. For background, see scikit-learn's [linear models](https://scikit-learn.org/stable/modules/linear_model.html) and [ensembles](https://scikit-learn.org/stable/modules/ensemble.html).

<a id="metrics"></a>

## 3. Classification and regression metrics

The formulas describe one test partition. Cross-fold aggregation is explained at the end of this section. Output keys follow the [metric implementation](../src/psyml/evaluation/metrics.py).

### Classification metrics

For one class viewed against all others, TP means correctly predicted membership, FP means incorrect predicted membership, FN means missed membership and TN means correctly predicted non-membership.

$$
\mathrm{Precision}=\frac{TP}{TP+FP},\qquad
\mathrm{Recall}=\frac{TP}{TP+FN},\qquad
F_1=\frac{2TP}{2TP+FP+FN}.
$$

Precision asks how many predictions of a class are correct. Recall, also called sensitivity for a specified positive class, asks how many actual members are recovered. Precision is distinct from accuracy.

| Output key | Meaning and direction | Interpretation |
| --- | --- | --- |
| `accuracy` | Correct predictions / total predictions; higher is better | Can obscure minority-class failures when one class dominates |
| `balanced_accuracy` | Equal-weight average of recall across actual classes; higher is better | Default classification selection metric. In binary data with both classes present, it averages sensitivity and specificity |
| `precision_macro` / `recall_macro` / `f1_macro` | Compute each metric per class, then average classes equally; higher is better | Small and large classes have equal weight. Macro F1 is not the harmonic mean of macro precision and macro recall |
| `precision_weighted` / `recall_weighted` / `f1_weighted` | Average per-class metrics using actual test-class counts as weights; higher is better | Larger classes dominate. For the current single-label classification setting, weighted recall equals accuracy |
| `roc_auc` | Binary ranking discrimination across scores; higher is better | Not accuracy or probability calibration. AUC 0.5 is a no-discrimination reference, not a universal chance level for all metrics |
| `roc_auc_ovr_weighted` | One-vs-rest multiclass AUC, weighted by actual class counts | Generated only when probability output exists and the test and training class sets match |

In notation, `macro = Σ m_c / C` and `weighted = Σ (n_c / n) m_c`, where `m_c` is a class metric, `n_c` its test support and `C` the number of classes included in the average. These are class weights, not cross-validation fold weights.

**Project conventions:** precision, recall and F1 use `zero_division=0`. Binary AUC treats estimator `classes_[1]` as positive, using probabilities when available or otherwise an available decision score. The GUI currently has no separate positive-class or decision-threshold selector. AUC is omitted when training and test class sets differ. Missing AUC means its conditions were unmet; do not replace it with zero. General definitions are documented in the [scikit-learn metric guide](https://scikit-learn.org/stable/modules/model_evaluation.html).

**Small example:** of 100 test observations, 90 are negative and 10 positive. Predicting every observation as negative gives accuracy 0.90, positive recall 0 and balanced accuracy 0.50. High accuracy can therefore coexist with missing every positive case. These numbers are an illustration, not recommended study thresholds.

### Regression metrics

Let `yᵢ` be observed, `ŷᵢ` predicted, `n` the current test-partition size and `ȳ` the mean observed outcome in that test partition.

$$
\mathrm{MAE}=\frac{1}{n}\sum_{i=1}^{n}|y_i-\hat y_i|,\qquad
\mathrm{RMSE}=\sqrt{\frac{1}{n}\sum_{i=1}^{n}(y_i-\hat y_i)^2}.
$$

$$
R^2=1-\frac{\sum_i(y_i-\hat y_i)^2}{\sum_i(y_i-\bar y)^2}.
$$

| Output key | Direction and units | Interpretation |
| --- | --- | --- |
| `mae`, mean absolute error | Lower is better, minimum 0; outcome units | Average absolute deviation from the observed outcome |
| `rmse`, root mean squared error | Lower is better, minimum 0; outcome units | Emphasizes larger errors. Default regression selection metric; not the standard deviation across folds |
| `r2`, coefficient of determination | Higher is better, best 1; unitless and possibly negative | Zero matches the squared error of using this test partition's observed mean. A negative value is not a software error or evidence of negative correlation |

The ordinary R² formula does not apply when its denominator is zero. The current call uses scikit-learn `r2_score` default finite-value handling: for a constant target, a perfect prediction gives 1 and an imperfect prediction gives 0. R² is undefined with fewer than two test observations. Undefined secondary metrics are excluded and reflected in valid fold counts; an undefined selection metric can fail an analysis. R² is not generally interchangeable with squared Pearson correlation.

**Small example:** observed `[1, 2, 3]` and predicted `[1, 2, 2]` give MAE = 1/3, RMSE = √(1/3) and R² = 0.5. This illustrates the formulas, not an adequate research sample size.

### Selection metrics and aggregation

- Inner selection supports classification `balanced_accuracy` (default), `f1_macro`, `accuracy`; regression `rmse` (default), `mae`, `r2`. Not every reported metric is available as a tuning objective.
- `metrics.csv` contains the **unweighted mean of outer-fold metrics for the primary validation**, rather than metrics recalculated from pooled predictions. Unequal fold sizes can matter; nonlinear metrics such as RMSE can differ even with equally sized folds.
- In `metrics_summary.csv`, `std` uses `ddof=0`: for K valid folds, `std = √[Σ(m_k − mean)² / K]`. `n_folds` gives the valid count for that metric. Folds share training information; this standard deviation is not a standard error or confidence interval (CI).
- Holdout has one outer test partition, so its reported std can be zero without implying an absence of uncertainty.

<a id="validation"></a>

## 4. Validation, tuning and the final model

### Six validation strategies

| Configuration value | Purpose | Current implementation limits |
| --- | --- | --- |
| `holdout` | A single training/test split | With groups, splits by group: `test_size` is a group fraction and need not equal the row fraction. Ungrouped classification is stratified when possible; very small samples can still fail |
| `k_fold` | Each of K folds acts as test data in turn | Shuffles rows; supplying a group column does not make the outer split group-disjoint |
| `stratified_k_fold` | Tries to maintain class proportions across folds | Classification only; does not isolate outer groups |
| `group_k_fold` | Keeps each group's rows together | Requires enough independent groups; class proportions may be uneven |
| `stratified_group_k_fold` | Tries to balance classes while keeping groups disjoint | Classification only; cannot guarantee every class in every fold |
| `leave_one_group_out` | Tests on one whole group at a time | Requires at least two groups; the group count determines the folds, not `n_splits`. Inner search also needs sufficient training groups |

**A group column does not automatically make every outer validation group-aware.** Repeated measurements require a strategy aligned with the research question. There is no dedicated time-series split at present. See the general [cross-validation guide](https://scikit-learn.org/stable/modules/cross_validation.html).

**What random and grouped splitting mean in practice.** Random splits without a group column (`holdout`, `k_fold`, `stratified_k_fold`) separate rows at random, so records from the same participant can land in both training and test; you cannot claim that a person appears on one side only. Grouped splits (`holdout` with a group column, `group_k_fold`, `stratified_group_k_fold`, `leave_one_group_out`) keep a whole group on one side **within a single split**; **across folds** the same group may rotate to the other side, which is normal group cross-validation and does not break isolation. Only when the group column really is a participant identifier may you read this as "one person's records do not cross training and test"; a family, centre or batch column instead isolates those units, not individuals. **Selecting a group column alone does not isolate groups for an ordinary holdout or K-fold**: isolation depends on the chosen strategy (table above). The GUI always uses the professional method names, does not rename strategies into scenario presets, and does not change the splitting algorithm.

### Order of nested selection

1. Set aside the current outer test fold.
2. Use inner CV only within the outer training data to choose the model family and parameters; inner splits isolate groups when supplied.
3. Fit that choice on the outer training data and predict its test fold. Outer scores cannot substitute another family for the inner-selected family.
4. Aggregate outer results to evaluate the complete selection procedure. Different folds can select different families.
5. Repeat inner selection on all analyzed data, then fit the final model. This chooses settings for the final fit; it does not produce a new independent test score.

A prespecified single family with one parameter candidate needs no inner search. Multiple families are still compared internally when `tuning_mode="none"`. A candidate failing any inner fold is ineligible; ties follow configured family/candidate order. The project uses `selection_protocol="nested_family_v1"`; see the [runner](../src/psyml/runner.py) for implementation and the [nested versus non-nested example](https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html) for methodological background.

**Primary validation** is chosen in the GUI dropdown and saved first in `validation_strategies`. It determines headline metrics, predictions and figures. Other strategies are **sensitivity analyses**, used to inspect dependence on the validation design, not to choose what to report after seeing the highest score. Alternatively choose **no primary validation**, represented by `primary_validation: null`. The same nested procedure runs separately for each validation, with complete outputs in `validations/<strategy>/`. The result page starts with a neutral selector; no validation is highlighted automatically. There are no global headline metrics or winning model across validations. `completed_with_errors` marks partial failure while successful results remain available; all-failed runs have no success marker. Omitting the field keeps legacy first-selected semantics; a strategy name explicitly designates a primary.

<a id="results"></a>

## 5. Reading output files and figures

The file descriptions below apply to a primary-design run or each successful child directory in independent mode. In independent mode only, the root validation_summary.csv uses `role=independent`; Python callers obtain full results from `validation_results[strategy]`, while the top-level model is None and its metric dictionary is empty.

### Find a file by question

| Question | Files | Interpretation |
| --- | --- | --- |
| Were there risks or failures? | `warnings.json`, `result.json` | Read warnings first. Only completed output represents a fully successful run; warnings do not necessarily prevent completion |
| What is held-out performance and variability? | `metrics.csv`, `metrics_summary.csv`, `fold_metrics.csv` | Read headline metrics, valid counts and variability, then individual folds |
| How large is the difference from the same-fold Dummy baseline, and where did failures occur? | `result_interpretation.json`, `interpretation_baseline_differences.csv`, `result_interpretation.md` | Paired differences and fold variability under the same validation, fold set and metric; a descriptive summary that never feeds back into selection or tuning |
| Is a different prespecified validation consistent? | `validation_summary.csv` | Separate primary and sensitivity results; do not choose the highest score across designs |
| Which model was finally chosen? | `best_model`, `best_parameters` in `result.json` | Final full-data selection, not necessarily the model used in every outer fold |
| Which families merit further investigation? | `model_comparison.csv` | Exploratory ranks restart within each validation; rank 1 can differ from the final model |
| What was selected in each fold? | `selection_trace.csv` | `outer_training_fold` versus `final_full_data`; `outer_fold=0` means full-data selection, not a zeroth test fold |
| Why was a candidate selected or rejected? | `parameter_search.csv` | Inspect inner score, parameters, status and error. Score remains on the metric's original scale: smaller RMSE/MAE is still better |
| Can final parameters be reused? | `best_parameters.json`, `best_parameters_configure.json` | The former stores effective hyperparameters, including defaults. The latter is a runnable fixed-model, fixed-parameter recipe with search disabled |
| How can the original design be repeated? | `config.json`, `analysis_config.json`, `study_config.json` | Preserve the original search design; names support different interfaces. Check input_path and use a new empty output_dir |
| What do configuration fields mean? | `configuration_guide.md` | Brief Chinese/English definitions kept outside standard JSON |
| Which predictions were wrong? | `predictions.csv`, classification `confusion_matrix.csv` | `observed` is truth, `predicted` the prediction. For file inputs, `row_index` is a zero-based data-row index, not a spreadsheet row number including the header |
| Do the environment and sample sizes match? | `analysis_manifest.json` | Input/analyzed rows, feature count, fingerprint and dependency versions. Input features are not the number of one-hot encoded columns |
| How should reporting start? | `methods_summary.md` / `methods_summary_zh.md`, `reproducibility_report.md` / `reproducibility_report_zh.md` | Offline English/Chinese drafts to check, not reviewed manuscript text |
| Where is the saved model? | `model/best_<model>.joblib`, `model/model_metadata.json` | Produced only when saving a primary-validation run; load on page 4, unlike a retraining JSON |

**Best parameters** means the settings selected under this candidate range, metric, data and splitting design, not a global optimum or a universal choice. `best_parameters_configure.json` reuses data that participated in selection; its new score is not independent validation and does not reproduce the original nested-search estimate. Since v0.2.0, primary-validation runs can save a fitted Pipeline for loading on page 4. This JSON configuration remains a retraining recipe, distinct from the saved model.

### Result interpretation (baseline difference, fold variability and failures)

The results page's **Result interpretation** block only aggregates evidence already produced by the selected fold evaluations (per-combination folds, `parameter_search.csv`, `model_comparison.csv`, `validation_summary.csv`) and writes `result_interpretation.json`, `interpretation_baseline_differences.csv` and `result_interpretation.md`; it never refits, never reselects a family or parameter, and never feeds a descriptive comparison back into selection or tuning.

- **Baseline difference** uses only the user-selected `dummy` that completed successfully, and requires the same validation, the same fold set and the same metric with all paired fold scores finite; otherwise it gives an explicit not-comparable reason and invents no difference. Higher-is-better metrics use procedure−dummy, MAE/RMSE use dummy−procedure, so a positive value always means the procedure did better than the baseline; a fold that selected Dummy itself has difference 0 and is labelled, which is valid.
- **Fold variability** reuses the existing summary definition and states ddof=0; it is descriptive only. A single fold has no assessable standard deviation or stability, no significance/reliability/instability threshold is set, and a score difference is not statistical significance; the between-fold standard deviation is not a confidence interval.
- **Failures are layered**: inner-search candidate failures, outer model+validation failures and whole validation/procedure failures are counted separately and remain traceable; representative reasons are visible and full records stay in `parameter_search.csv`, `warnings.json` and failed child folders.
- **Independent validations** are summarised separately; the root only gives an overview/index with no cross-validation comparison.

### Saved models and prediction outputs

Primary-validation runs enable `save_best_model` by default. The final Pipeline is saved as `model/best_<model>.joblib`, with `model_metadata.json` recording original features, types, classes, effective parameters, fit scope and versions. Disabling saving still allows analysis. With `primary_validation: null`, neither the root nor validation children automatically save a model.

Distinguish three parameter records: `best_parameters.json` and `result.json.effective_parameters` contain effective hyperparameters including defaults; `result.json.best_parameters` retains selected overrides and may be empty; `best_parameters_configure.json` is a retraining recipe, not a fitted model. The model file comes from the final full-data fit, not the highest-scoring outer fold.

Page 4 automatically checks a trusted model and new table. Only required predictors are needed, not target or group columns. Named features are reordered automatically; a model with only a feature count needs confirmed manual mapping and order. Missing columns, invalid numbers, infinity or missing values without fitted imputation block prediction. Compatibility does not establish population comparability or guarantee that model execution succeeds. Training with `drop` does not silently delete new rows during prediction.

Outputs preserve original row order and all input columns, adding `predicted_class` or `predicted_value`. Only classifiers with native probabilities add `probability_*`. Class names are made suitable for column names; collisions receive numeric suffixes on new columns. An input target is retained without automatic external-validation metrics, probability calibration or threshold optimization.

Nine input formats are supported; export CSV, TSV, XLSX, SAV, DTA, XPT or Parquet. XLS/SAS7BDAT are read-only, so the GUI defaults to XLSX. Statistical-format limits can prevent export; try XLSX or Parquet. Keep the model and metadata together. Corruption, hash mismatch or a different scikit-learn version causes errors; missing metadata triggers recovery where possible, without guaranteeing completeness.

**Where page-4 artifacts and training results are written.** Page 4 shares one result root with page 2: a new training run is written to `<result root>/training/run_<timestamp>_<usec>/`, prediction to `<result root>/prediction/run_<timestamp>_<usec>/predictions.csv`, and single-sample SHAP and coefficients to `explanation/run_*/` and `coefficients/run_*/`. Each operation freezes a new run directory at its start and never overwrites existing files; **Open prediction results folder** and **Open results folder** point to that actual run directory, and **Open waterfall image** points to this run's `shap_waterfall.png`. Legacy training folders written directly under the result root as `run_*` stay in place and still open without any migration or rewriting; only new training runs go into `training/`. An unset root, a relative path or an unwritable root reports an error instead of falling back to the hidden application-data folder, and changing the root only affects later operations while completed artifacts stay on disk.

**How to read prediction output (`prediction/run_*/predictions.csv`).** The file keeps your raw data and row order and only appends prediction columns: regression adds `predicted_value`, classification adds `predicted_class`, and classifiers with native probabilities add `probability_<class>` in class order. Original columns (including a target) are not modified; name collisions only add numeric suffixes to the new columns. A present target is retained without automatically computing external-validation metrics, calibrating probabilities or optimizing a threshold. **Classification vs regression:** classification outputs classes and non-negative, not necessarily calibrated, probabilities, while regression outputs a continuous value and no probability columns. **Open prediction results folder** opens the run folder, not the CSV file itself. Predicting new data does not require a true target, and this is **not external validation**: external validation needs an independent sample, true outcomes and an appropriate evaluation design. Changing model, data or mapping clears previous predictions and re-checks; files in earlier run folders stay on disk.

### Single-sample SHAP explanation (optional, FR-004)

Once a model and data pass the page-4 check, you can explain one sample: choose a background reference file (**background**), the 1-based sample row, the background row count (default 50, 1–100) and permutation cycles (**permutation cycles**, default 5, 1–20); for classification also choose the class and see its original label. The computation runs in a cancellable subprocess, may be slow on the first run, and can be stopped at any time. The result block shows a cumulative waterfall that steps from the **base value** to the model output (signed direction, original names and values, top N plus an "other N (sum)" bar while the CSV keeps every contribution) together with **Open waterfall image** and **Open results folder** only; there is no copy or save-as export entry in the interface. Artifacts (by default under `explanation/run_*/`) are `shap_explanation.json`, `shap_contributions.csv`, `shap_waterfall.png` and `shap_explanation_notes.md`, satisfying `base + Σφ = selected output` (tolerance 1e-7/1e-6); completed artifacts stay on disk when the row/class/settings change or the page closes. The command line `psyml explain --output-dir` still requires a new/empty directory and rejects `--overwrite`, but the interface no longer offers an export action.

How to read these results:

- **Base value:** the mean model output for the selected output axis over the background reference rows; every contribution adds to it.
- **Background reference:** the reference data used to approximate what the model outputs when a variable takes a reference value; more rows are usually more stable but slower, and it is not a population norm.
- **Selected sample and class:** determine which row and which output axis are explained; classification requires a chosen class, regression has a single output axis.
- **Signed contributions:** how much each variable pushes the output above (positive) or below (negative) the base value; `base + Σφ = selected output`, with the CSV listing every contribution while the interface folds everything beyond the top N together.
- **Reconstruction:** the identity holds within tolerance as a check; it does not imply a causal mechanism, and values depend on the background set and permutation cycles.
- **Approximation limits:** **approximate** finite-permutation SHAP, not exact SHAP; background replacement does not preserve predictor correlation; not a causal effect and not outer test performance.

These are **approximate** finite-permutation SHAP values: not exact SHAP, not causal, not outer test performance, and marginal background replacement does not preserve predictor correlation. The first release supports classification `logistic_regression`/`decision_tree`/`random_forest` and regression `linear_regression`/`ridge`/`lasso`/`elastic_net`/`decision_tree`/`random_forest`, and only accepts saved models with PsyML export metadata (`psyml_version`/`fit_scope`) and the standard `preprocess`+`model` structure; external or custom-preprocess models report a clear unsupported reason. Ordinary prediction is unaffected. Without the optional `explain` dependencies this section is unavailable.

Implementation: [persistence](../src/psyml/models/persistence.py), [effective parameters](../src/psyml/models/parameters.py), [prediction](../src/psyml/prediction.py), [explanation](../src/psyml/explanation.py).

### Fitted coefficients and intercepts (FR-005)

The page-4 **Fitted coefficients and intercepts** block only reads the **already fitted** model's parameters in the **preprocessed coordinate space** (after imputation, scaling and one-hot encoding); it never refits, never feeds back into tuning and never converts back to raw units. This first release supports regression `linear_regression`/`ridge`/`lasso`/`elastic_net`/`svr` (`kernel='linear'`) and classification `logistic_regression`/`lda`/`svm` (`kernel='linear'`, binary only); multi-class SVC pairwise coefficients, non-linear kernels, trees, KNN, MLP and stacking report a specific unsupported reason. With compatible prediction data loaded it rebuilds the regression prediction or classification decision score through the same pipeline within tolerance 1e-7/1e-6 and shows the verification state; without data it explicitly reports "not verified". The block shows the intercept, output unit and fit scope for every output axis and distinguishes "no verification data" from "verification failed"; a failed check blocks publishing any artifact (concrete reason shown, no "extraction complete", no export). `coefficients.json` records removed all-missing columns with their reason, the per-original-column mapping, `drop_idx_` and per-column categories, with training dtypes sourced from saved metadata or explicitly unknown. Classification labels the output axis: binary logistic is the log-odds of `classes_[1]` relative to `classes_[0]`, multi-class logistic is a per-class softmax logit, and linear SVC is only a margin (not a probability or log-odds); real labels, types and indices are preserved. Page 4 keeps only **Open results folder** (pointing to this run's `coefficients/run_*/`) and no copy or save-as export entry; a successful extraction writes `coefficients.csv`, `coefficients.json` and `coefficients_notes.md` into that run directory (JSON last). A normal analysis also writes the same three files under `coefficients/` of the analysis run folder, marked `fit_scope=all_analyzed_rows`. These are fitted parameters (not hyperparameters) of the final all-analyzed-rows model with no p-values, confidence intervals, significance, causal claims or defined standardized effects; ordinary prediction, the hyperparameter section and the SHAP section are unchanged. The equivalent CLI is `psyml coefficients --model … --trust-model [--input …] [--output-dir …]` with `--check-only`, and it does not need the `explain` extra.

How to read these results:

- **Intercept:** the output baseline for each axis when every transformed feature is zero; it uses the output axis's unit and does not mean "no person" or "no measurement" in the raw data.
- **Transformed-feature units:** each coefficient belongs to a column after imputation, scaling or one-hot encoding (for example `numeric_score` or `categorical_category_A`), not to the raw variable's original unit; do not convert back by raw units or compare magnitudes across models directly.
- **Output unit:** classification must be read together with the class axis — binary logistic is log-odds relative to the reference class, multi-class logistic is a per-class softmax logit, and linear SVC is a margin (a raw decision score, neither a probability nor a log-odds); regression `predict` output keeps the target's unit.
- **Fit scope (`fit_scope`):** these are fitted parameters of the final all-analyzed-rows model (`all_analyzed_rows`), not an outer-fold model and not hyperparameters.
- **Unverified and failed:** without compatible prediction data the block reports "no verification data (unverified)"; when reconstruction exceeds tolerance, has a wrong shape or is non-finite it reports "verification failed" and refuses to publish any coefficient artifact.
- **Not causal:** coefficients describe association under this fit and penalty; the block provides no p-values, confidence intervals, significance, causal claims or defined standardized effects.

Implementation: [coefficients](../src/psyml/models/coefficients.py).

### Figures

| Figure file | Axes or contents | Questions to investigate |
| --- | --- | --- |
| `confusion_matrix.png` | Actual classes in rows, predicted classes in columns, counts in cells | Which classes are confused? A dark diagonal alone can obscure imbalance |
| `class_distribution.png` | Actual and predicted held-out class counts | Is the model mostly predicting the majority class? Matching totals can coexist with wrong individual predictions |
| `observed_vs_predicted.png` | Observed on x, predicted on y; dashed equality line | Is there systematic over- or underprediction? Interpret scatter relative to the outcome scale and error metrics |
| `residuals.png` | Predicted on x; residual = observed − predicted on y | Positive residuals indicate underprediction; negative residuals indicate overprediction. Curvature or a funnel can suggest missed structure or unequal error variability |
| `residual_distribution.png` | Histogram of residuals | Look for shifts, heavy tails or extreme errors. A histogram alone cannot establish normality or independence |

Figures use held-out predictions from the primary validation, or from the current independent child. Holdout includes only test observations; CV generally includes one outer prediction per retained observation. Classification labels Class 1, Class 2, etc. follow `confusion_matrix.csv` order and do not designate a GUI-selected clinical positive class. Select multiple figures or none; they are stored in the run's `figures/` directory. They are not SHAP, ROC or confidence-interval plots. Feature importance is exported only when `permutation_importance` is explicitly enabled, as the separate `interpretations/<validation>/permutation_importance.png` (next section).

### Permutation importance (optional, `permutation_importance`)

When enabled on page 1, for every outer fold of each validation the inner-selected fold model is explained by permuting each variable only on that fold's outer test rows, using the current `selection_metric` to measure the performance change. Results are written under `interpretations/<validation>/`:

- `permutation_raw.csv` — one row per permutation (validation, fold, model_family, variable, repeat, metric, importance, direction, baseline_score, n_rows);
- `permutation_folds.csv` — per-fold baseline, `repeats`, `mean`, `repeat_std` (ddof=0), `n_rows` and status/error;
- `permutation_summary.csv` — equal-weight mean of fold means within one validation (`fold_mean_equal_weight`) and `between_fold_std` (ddof=1), plus successful/planned fold counts;
- `permutation.json` — metric and direction, seed/repeats, held-out rows, `model_scope=outer_fold_model`, encoding map, limitations and failure reasons;
- `permutation_importance.png` — signed ranking figure with a zero line.

How to read it: `importance` is signed. For MAE/RMSE a positive value means the error increased; for other metrics it means performance dropped. Negatives are kept, values are not normalised to percentages and are not confidence intervals or R² percentages. `repeat_std` is within-fold repeat variation and `between_fold_std` is between-fold variation; never mix them, and the between-fold value is empty for a single fold. The between-fold standard deviation is descriptive variability, not a standard error or a confidence interval. Correlated variables share or mask attribution, and row-wise permutation does not preserve repeated-measures/group structure, so group-data interpretation is weaker and needs design judgement. Missing or failed folds are marked partial/failed and never fabricate a complete ranking; an all-failed validation yields no success table or blank figure. This is the fold model's sensitivity to variable perturbation under one metric, not a causal effect, and not an explanation of the saved all-data model. No `interpretations/` files are created unless explicitly enabled.

<a id="glossary"></a>

## 6. Parameter and terminology reference

| Term / key | Explanation |
| --- | --- |
| Model family | A method such as random forest or Ridge; different hyperparameter candidates can belong to the same family |
| Parameter / hyperparameter | Coefficients are usually learned; depth or penalty strength is usually specified or searched. `model_params` mainly supplies estimator initialization hyperparameters |
| Candidate / parameter grid | One candidate is a concrete set of settings; a grid lists candidate values for each parameter. Combinations can grow rapidly |
| `tuning_mode` | `none`: fixed parameters; `quick`: bounded built-in grid; `custom`: user grid. Quick search does not guarantee an optimal recommendation |
| `max_candidates` | Per-family candidate limit. Larger grids are sampled, not necessarily exhaustively evaluated |
| `n_splits` / `inner_splits` | Outer / inner fold counts; rows, classes and groups must support the split. The actual inner fold count may be reduced |
| `random_seed` | Controls random splits and seeded estimators; explicit estimator `random_state` overrides its seed. Equal seeds do not guarantee bitwise identity across dependency versions |
| `n_neighbors` | KNN neighborhood size, an integer count |
| `n_estimators` / `max_depth` / `min_samples_leaf` | Tree count, maximum depth, minimum leaf sample requirement. `null` can mean unlimited depth. The GUI treats integral candidates as counts; fractions must satisfy that parameter's rules |
| `C` / `alpha` / `l1_ratio` | Penalty controls: smaller C usually strengthens regularization; larger alpha usually strengthens it; l1_ratio mixes L1/L2. Exact meanings depend on the model |
| `learning_rate` / `learning_rate_init` | Boosting learning rate / initial MLP learning rate; the configuration keys are not interchangeable |
| `epsilon` | SVR tolerance parameter, not a confidence range for estimation error |
| `class_weight` / class imbalance | class_weight changes class influence during training; it differs from weighted averaging during evaluation |
| Overfitting / underfitting | Learning training noise / missing important structure. A single test score alone does not diagnose the specific cause |
| Data leakage | Test information enters fitting or selection when it should have remained unavailable, making evaluation optimistic |
| Held-out prediction | The observation was excluded from its corresponding model fit; nested selection also excludes it from that model/parameter choice |
| Generalization / external validation | Performance on unseen data / evaluation on independent external data. Internal CV is not validation in a new centre, time or population |
| Calibration | Agreement between predicted probabilities and observed frequencies. Good ranking AUC does not ensure good calibration |
| SHA-256 fingerprint | Identifies input-content changes. It is not encryption, anonymization or proof of data quality |
| Convergence warning | Optimization did not meet its stopping criterion under the configured conditions. Output may exist without the fit being sufficiently stable |
| Final model | Full-data fitted Pipeline after final selection; not an outer-fold winner |
| Effective parameters | Applied estimator initialization settings, including defaults; not learned coefficients |
| model_metadata.json | Feature names/types, classes, parameters, fit scope and versions kept beside the model |
| Feature compatibility | Required input names and usable types; does not establish population comparability |
| predicted_class / predicted_value | Predicted label / numerical value, not an observed outcome |
| probability_* | Native classifier probabilities, not automatically calibrated; absent for regression |
| New-data prediction | Generates outputs without needing a target; independent external validation requires labeled data and an evaluation design |
| Prediction output (`prediction/run_*/predictions.csv`) | Keeps raw data and row order and only appends `predicted_class` or `predicted_value`, plus native `probability_*` for some classifiers; **Open prediction results folder** opens the run folder, not the CSV |
| Base value and background reference | In single-sample explanation, the selected output axis's mean over the background rows and the reference set itself; the background is not a population norm |
| Contribution (φ) and reconstruction | How much each variable pushes the output above or below the base value; `base + Σφ = selected output` is checkable, but it is not causal |
| Intercept | The output baseline when all transformed features are zero, in preprocessed coordinate space, not raw variable units |
| Transformed feature | A column after imputation, scaling or one-hot encoding; coefficients refer to these columns and cannot be converted by raw units |
| log-odds / margin | Classification coefficient units: binary logistic is log-odds, multi-class logistic is a softmax logit and linear SVC is a margin; a margin is neither a probability nor a log-odds |
| Fit scope (`fit_scope`) | Which fit the coefficients come from; `all_analyzed_rows` is the final all-analyzed-rows model, not an outer fold |
| Trusted model source | Loading joblib/pickle can execute code; load only your own or verified trusted models |

<a id="checklist"></a>

## 7. Common misconceptions and review order

Check the target, predictors, groups and missing-value handling first; then warnings and analyzed sample size; then headline metrics, fold variability and systematic errors; finally prespecified baselines and sensitivity analyses. Record design changes rather than repeatedly changing validation or metrics after viewing results.

- **“Rank 1 must be the final model.”** Not necessarily: exploratory outer ranks and final full-data inner selection serve different purposes.
- **“R² = 0.6 means every individual is predicted 60% correctly.”** No: R² compares squared errors; it is not individual accuracy.
- **“Higher F1 or AUC guarantees clinical usefulness.”** No: error costs, population, thresholds, calibration and external evidence still matter.
- **“Zero standard deviation means no uncertainty.”** No, especially with one holdout partition.
- **“Variables retained by Lasso are causal factors.”** Predictive selection does not establish causality.
- **“Completed output can go straight into a paper.”** Completion is a software state, not scientific or data-quality acceptance.

<a id="references"></a>

## 8. Implementation and further reading

Project behavior follows the [catalog](../src/psyml/models/catalog.py), [factory](../src/psyml/models/factory.py), [metrics](../src/psyml/evaluation/metrics.py), [splits](../src/psyml/validation/split.py), [runner](../src/psyml/runner.py) and [reporting code](../src/psyml/reporting/research.py). Defaults and behavior can change across versions; check `analysis_manifest.json` when reproducing a run.

For general principles, consult scikit-learn's [metrics](https://scikit-learn.org/stable/modules/model_evaluation.html), [linear models](https://scikit-learn.org/stable/modules/linear_model.html), [ensembles](https://scikit-learn.org/stable/modules/ensemble.html), [cross-validation](https://scikit-learn.org/stable/modules/cross_validation.html) and [nested-validation example](https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html). These references do not imply that every feature they describe is implemented in PsyML.

## Reproduce from a configuration

Start user testing in [examples/quickstart/](../examples/quickstart/README.md): each task has a configuration, 48 training rows and 10 new prediction rows, all synthetic. Follow the [README analysis workflow](../README.md#english); model saving and prediction are integrated as step 9.

On page 1, **Import configuration…** opens a bundled example, a result folder’s `config.json`, or `best_parameters_configure.json`; no terminal is required. Relink the corresponding data if its path is unavailable; required columns are checked. Review variables, validation and parameters, then choose a local output folder and run on page 2. Each run creates a new `training/run_*` subfolder instead of reusing the imported output path. **Save configuration…** saves current settings. Rerunning fixed best parameters neither reproduces the original search nor provides independent validation.

## Source-checkout re-test steps

A standalone package and a source checkout can contain different fixes. The five points below are for re-testing a source checkout; passing them is not human acceptance. Packaging and releasing 0.3.0 have been explicitly authorised by the user; this guide does not claim that these features passed human acceptance item by item.

1. Start the interface from the source checkout root (on macOS you can double-click `Launch PsyML.command`); dependency installation is in the [developer guide](DEVELOPMENT_EN.md). Standalone packages do not include the developer test environment. Import the classification or regression configuration from `examples/quickstart/` and run it once.
2. **Version label:** a small label under the application name should show the current version number `0.3.0`. A source run's single source is `__version__` in `src/psyml/__init__.py` (`pyproject.toml` is dynamic); a standalone package reads its bundled `BUILD.json`, generated from that same constant, and a `0.3.0.dev0` development release displays as `0.3.0-dev` while the official `0.3.0` displays unchanged.
3. **Output folders and legacy results:** a new page-2 training run appears under `training/run_*` in the chosen result root; page-4 prediction, SHAP and coefficients land in new `run_*` directories under `prediction/`, `explanation/` and `coefficients/` in the shared root, never overwriting existing files and never writing to the hidden application-data folder. Legacy `run_*` training folders directly under the result root still open in place, and their contents are not rewritten.
4. **Page 4 opens, never exports:** all three blocks offer only **Open results folder** (prediction: **Open prediction results folder**, which opens the run folder rather than the CSV) and **Open waterfall image**; there is no copy or save-as entry. Prediction output is a directly openable `predictions.csv`, and no `predictions.parquet` is produced any more.
5. **Scroll ownership and finalising status:** when a gesture starts on the page it keeps scrolling the page past a nested small table, and only a gesture that starts on the table scrolls that table; a pause of about 250 ms starts a new gesture that may choose a different layer (the lock only affects wheel/swipe scrolling). During final result writing the status should read "Finalizing and writing results…" with the progress bar not yet full; the result page opens only after `completed`. Use **Copy full error** when reporting a problem.
