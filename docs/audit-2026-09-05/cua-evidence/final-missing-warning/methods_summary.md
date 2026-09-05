# Methods Summary

PsyML analyzed 46 rows with 2 predictor columns for a regression task. The outcome column was `target_长期随访量表总分_用于检验很长的研究变量名称与原始列名是否保持一致`. The grouping variable `participant` was excluded from predictors and used by the configured outer split.

Missing predictor values used the `drop` strategy. Numeric scaling was `standard`, and categorical predictors were one-hot encoded. All learned preprocessing steps were fitted within each training partition only.

The `dummy` model was evaluated using 3-fold group cross-validation with random seed 42. The final full-data family was `dummy`. Final full-data parameter overrides were `{}`; outer folds may use different families/parameters recorded in `selection_trace.csv` and `parameter_search.csv`. Performance was calculated only from held-out predictions using: r2, mae, rmse.

Candidate models (`dummy`) and validation strategies (`group_k_fold`) used `rmse`. Parameter mode was `none` with at most 2 candidates per model. Inner selection used up to 2 folds restricted to each outer training partition; groups were isolated in inner splits whenever a group column was configured. The model family was prespecified. Parameters were selected within inner CV when multiple candidates existed, and reselected on all analyzed rows for the final fit. A single fixed candidate requires no inner search. The first configured validation is primary; others are sensitivity analyses, summarized separately in `validation_summary.csv`. Neither sensitivity results nor outer family ranks select the final model. Ties follow configured family/candidate order. Candidates with any failed inner fold are ineligible; if the inner-selected family fails outer evaluation, the procedure fails that validation rather than substituting a family using test outcomes. Nested evaluation is internal validation at the outer training sample size, not proof of transportability to new populations, centres or times. It also does not protect against researchers revising the design after inspecting results.



The final model was fitted on all analyzed rows. Reported metrics remain held-out evaluation metrics, not final-fit training scores. Fold means are unweighted; standard deviations are descriptive (ddof=0), not confidence intervals. Undefined secondary metrics are excluded and their available fold counts are in `metrics_summary.csv`. Binary AUC treats estimator `classes_[1]` as positive; multiclass AUC uses matching probability columns and is omitted when class sets differ. Figures use Class 1, Class 2, etc. in the same order as `confusion_matrix.csv`.

`config.json`, `analysis_config.json`, and `study_config.json` retain the original search design for reruns; `best_parameters.json` records final parameter overrides. The configured seed controls splits and seeded estimators; inner split seeds add the outer fold number (zero for final tuning), and explicit estimator random_state overrides take precedence.

This text describes the executed configuration and is intended as a starting point for a manuscript Methods section; researchers remain responsible for study-specific justification and reporting.
