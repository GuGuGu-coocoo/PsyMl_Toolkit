# Researcher reference: models, metrics, results and terminology

Applies to code version **v0.1.1**. See `analysis_manifest.json` in each analysis output for runtime and dependency versions.

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

The file descriptions below apply to a primary-design run or each successful child directory in independent mode. The root validation_summary.csv uses `role=independent`. Python callers obtain full results from `validation_results[strategy]`; the top-level model is None and its metric dictionary is empty.

### Find a file by question

| Question | Files | Interpretation |
| --- | --- | --- |
| Were there risks or failures? | `warnings.json`, `result.json` | Read warnings first. Only completed output represents a fully successful run; warnings do not necessarily prevent completion |
| What is held-out performance and variability? | `metrics.csv`, `metrics_summary.csv`, `fold_metrics.csv` | Read headline metrics, valid counts and variability, then individual folds |
| Is a different prespecified validation consistent? | `validation_summary.csv` | Separate primary and sensitivity results; do not choose the highest score across designs |
| Which model was finally chosen? | `best_model`, `best_parameters` in `result.json` | Final full-data selection, not necessarily the model used in every outer fold |
| Which families merit further investigation? | `model_comparison.csv` | Exploratory ranks restart within each validation; rank 1 can differ from the final model |
| What was selected in each fold? | `selection_trace.csv` | `outer_training_fold` versus `final_full_data`; `outer_fold=0` means full-data selection, not a zeroth test fold |
| Why was a candidate selected or rejected? | `parameter_search.csv` | Inspect inner score, parameters, status and error. Score remains on the metric's original scale: smaller RMSE/MAE is still better |
| Can final parameters be reused? | `best_parameters.json`, `best_parameters_configure.json` | The former stores overrides; `{}` means defaults are used. The latter is a runnable fixed-model, fixed-parameter recipe with search disabled |
| How can the original design be repeated? | `config.json`, `analysis_config.json`, `study_config.json` | Preserve the original search design; names support different interfaces. Check input_path and use a new empty output_dir |
| What do configuration fields mean? | `configuration_guide.md` | Brief Chinese/English definitions kept outside standard JSON |
| Which predictions were wrong? | `predictions.csv`, classification `confusion_matrix.csv` | `observed` is truth, `predicted` the prediction. For file inputs, `row_index` is a zero-based data-row index, not a spreadsheet row number including the header |
| Do the environment and sample sizes match? | `analysis_manifest.json` | Input/analyzed rows, feature count, fingerprint and dependency versions. Input features are not the number of one-hot encoded columns |
| How should reporting start? | `methods_summary.md` / `methods_summary_zh.md`, `reproducibility_report.md` / `reproducibility_report_zh.md` | Offline English/Chinese drafts to check, not reviewed manuscript text |

**Best parameters** means the settings selected under this candidate range, metric, data and splitting design, not a global optimum or a universal choice. `best_parameters_configure.json` reuses data that participated in selection; its new score is not independent validation and does not reproduce the original nested-search estimate. The GUI currently does not export a loadable fitted-model file: this configuration is a recipe for retraining.

### Figures

| Figure file | Axes or contents | Questions to investigate |
| --- | --- | --- |
| `confusion_matrix.png` | Actual classes in rows, predicted classes in columns, counts in cells | Which classes are confused? A dark diagonal alone can obscure imbalance |
| `class_distribution.png` | Actual and predicted held-out class counts | Is the model mostly predicting the majority class? Matching totals can coexist with wrong individual predictions |
| `observed_vs_predicted.png` | Observed on x, predicted on y; dashed equality line | Is there systematic over- or underprediction? Interpret scatter relative to the outcome scale and error metrics |
| `residuals.png` | Predicted on x; residual = observed − predicted on y | Positive residuals indicate underprediction; negative residuals indicate overprediction. Curvature or a funnel can suggest missed structure or unequal error variability |
| `residual_distribution.png` | Histogram of residuals | Look for shifts, heavy tails or extreme errors. A histogram alone cannot establish normality or independence |

Figures use held-out predictions from the primary validation, or from the current independent child. Holdout includes only test observations; CV generally includes one outer prediction per retained observation. Classification labels Class 1, Class 2, etc. follow `confusion_matrix.csv` order and do not designate a GUI-selected clinical positive class. Select multiple figures or none; they are stored in the run's `figures/` directory. SHAP, feature-importance, ROC and confidence-interval plots are not currently exported.

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

On page 1, **Import configuration…** opens a bundled example, a result folder’s `config.json`, or `best_parameters_configure.json`; no terminal is required. Relink the corresponding data if its path is unavailable; required columns are checked. Review variables, validation and parameters, then choose a local output folder and run on page 2. Each run creates a new subfolder instead of reusing the imported output path. **Save configuration…** saves current settings. Rerunning fixed best parameters neither reproduces the original search nor provides independent validation.
