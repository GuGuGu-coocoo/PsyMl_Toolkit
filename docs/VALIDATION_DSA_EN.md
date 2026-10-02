# Participant-grouped nested cross-validation of PsyML on public human-activity data: numerical reproduction and cross-platform verification

[中文](VALIDATION_DSA_ZH.md) · [Français](VALIDATION_DSA_FR.md)

Case `psyml_dsa_group_nested_v1` · PsyML `0.3.0` (commit `de33abfe52ccfee67f461a850edd00a14d2fbfaa`) · 2026-10-01

## Abstract

**Aim.** To test the numerical behaviour of PsyML's participant-grouped nested validation workflow on real data: whether splitting, training-fold-only preprocessing, inner selection, out-of-fold prediction, metric calculation and model persistence follow a protocol frozen in advance, and whether an independent implementation reproduces them.

**Methods.** The data are the UCI *Daily and Sports Activities* (DSA) set: 8 participants, 19 activities, 60 five-second records per participant and activity, 9,120 records in total. Per segment, only the torso three-axis acceleration and three-axis angular rate are used, reduced to per-channel mean and population standard deviation, giving 12 features. The outer design is a 4-fold participant-grouped cross-validation; the inner design is a 3-fold stratified group cross-validation; the candidates are Dummy and logistic regression; selection uses the unweighted mean of inner balanced accuracies. An independent reference implementation never imports PsyML and rebuilds the same protocol with public scikit-learn APIs. Engineering controls cover a group-isolation audit, fixed outer-fold perturbations and a shuffled-label canary.

**Main results.** The primary metric, the fold mean of outer-fold balanced accuracy, is 0.5740131578947368. All 9,120 out-of-fold predictions agree row by row between the two implementations; the training rows, families, parameters and preprocessing statistics of the 54 fits align; saved-model replay matches the independent final model. These values come from the original case package's frozen Linux run. On the macOS (aarch64) re-run, hard predictions were byte-identical; only the probability-derived ROC-AUC differed by about 2.03e-7, with out-of-fold probabilities differing by at most about 1.98e-5. That difference is retained as published.

**Scope.** The results support numerical conformance and reproducibility of the tested workflow in this case only; they are not a new algorithm, a performance claim, or a clinical or population-level result, and they do not show that every toolkit feature is verified on every platform.

## 1. Introduction

The correctness of a machine-learning tool is not visible in the final score alone. For researchers, it matters just as much that splits really isolate participants, that preprocessing is fitted inside training folds, that models and parameters are chosen from training-side evidence, that out-of-fold predictions and metrics can be recomputed independently, and that a saved model replays faithfully. Checking these steps on real behavioural data with a fixed protocol exposes data-conversion and grouping problems that synthetic data may not reveal. Splitting by participant rather than by row avoids placing adjacent segments from the same person on both sides of the train/test boundary, which is the basic leakage requirement for this kind of data.

This report documents such a case: PsyML runs on the public UCI *Daily and Sports Activities* (DSA) data under a protocol frozen in advance and is compared point by point with an independent scikit-learn implementation that does not import PsyML. It is a software-maintenance and workflow-acceptance exercise, **not** a new-method paper, a reproduction of the original paper's benchmark, or a comparison against other tools; it supports no statement about psychological constructs, clinical use, causality or human-factors effects.

## 2. Data and methods

### 2.1 Source, licence and attribution

- Data: Barshan, B. & Altun, K. (2010). *Daily and Sports Activities* [Dataset]. UCI Machine Learning Repository. DOI [10.24432/C5C59F](https://doi.org/10.24432/C5C59F); page <https://archive.ics.uci.edu/dataset/256/daily+and+sports+activities>.
- Licence: the official data page marks CC BY 4.0; no member of the downloaded ZIP adds a further restriction. The data authors do not endorse PsyML or this case.
- Original paper: Altun, K., Barshan, B., & Tunçel, O. (2010). Comparative study on classifying human activities with miniature inertial and magnetic sensors. *Pattern Recognition*, 43(10), 3605–3620. <https://doi.org/10.1016/j.patcog.2010.04.019>.
- Raw ZIP: 170,800,010 bytes, SHA-256 `f42ad7744ecf14151c9fa3a86dfb5b24de9d7cb7ffe956ef5de242983459c77e`; downloaded only from the official location and fully hash-checked before reading.

### 2.2 Participants, activities and records

The dataset contains 19 daily and sports activities performed by 8 adults aged 20–30, with 60 five-second segments per participant and activity — 9,120 segments in total, each originally 125 rows × 45 columns. Folders `p1..p8` are the official participant IDs. **The 8 participants are the independent units; the 9,120 segments must not be treated as 9,120 independent individuals**, and adjacent segments may be correlated. The archive defines no train/test split.

### 2.3 Feature construction

Only the 9,120 members `data/a01..a19/p1..p8/s01..s60.txt` are read, in fixed order: missing, duplicated, extra non-directory members, a shape other than 125×45 or any NaN/infinity abort the conversion, with no silent deletion. Each segment contributes only its first six columns (torso acceleration x/y/z and torso angular rate x/y/z); per channel, the mean and the population standard deviation (`std(ddof=0)`) are computed in that order, giving 12 features. The remaining sensors and magnetometers are not used, and there is no filtering, PCA, feature selection or cross-segment normalisation. The derived CSV is UTF-8, LF, without index, `float_format %.17g`; `segment_id`, `subject_id` and `activity` serve only for joining, grouping and the target and never enter the feature columns.

### 2.4 Training-fold-only preprocessing

Every fit builds a fresh `ColumnTransformer(numeric) → SimpleImputer(strategy='median') → StandardScaler → estimator`, fitted on the corresponding training rows only. The case has no missing values, but the visible preprocessing pipeline is kept so that its fitted scope can be audited.

### 2.5 Outer and inner splits

- Outer: `GroupKFold(n_splits=4, shuffle=False)` in original row order; the test participants of the four folds are `[4,8]`, `[3,7]`, `[2,6]`, `[1,5]`; each fold holds out 2,280 segments and trains on 6,840.
- Inner: `StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=20261001 + outer fold number)` (folds numbered from 1), used to select inside the outer training set; each inner fold validates 2 participants and trains on 4, and every partition contains all 19 classes.
- Final full-data selection: the same 3-fold stratified group cross-validation with `random_state=20261001`; it only determines the final full-data model and supplies **no new unbiased test score**.

### 2.6 Candidates and selection rule

The family order is `['dummy', 'logistic_regression']`: `DummyClassifier(strategy='prior')` and `LogisticRegression(C∈[0.1, 1.0], solver='lbfgs', max_iter=2000, tol=1e-8, class_weight=None, fit_intercept=True)`, both with `random_state=20261001`. Every fixed parameter is written explicitly in the configuration; `max_candidates=2` applies per family and never triggers random sampling.

Selection: for each candidate, the unweighted mean of the three inner-fold balanced accuracies; replacement requires a **strictly greater** value, and exact ties keep the first family/candidate in configuration order; outer scores never break ties. One failing inner fold fails that candidate, and successful folds are not averaged instead; if the inner winner fails in the outer fold, the whole procedure fails and no other family is substituted. A complete workflow performs 54 fits: 45 inner fits + 8 family outer fits + 1 full-data fit. CPU only, one numerical-library thread, no SHAP.

### 2.7 Metrics and reporting conventions

- Primary: the **unweighted fold mean** of outer-fold balanced accuracy for the inner-selected procedure. The between-fold standard deviation (`ddof=0`) is reported as descriptive variation only and **must not be read as a standard error or a population confidence interval**.
- Secondary: the same aggregation for accuracy and macro-F1 (`zero_division=0`); pooled out-of-fold confusion matrix and macro-F1; paired same-fold procedure−Dummy differences; per-participant balanced accuracy (descriptive).
- **Fold mean and pooled are reported separately**: the equal-sized, class-balanced folds make pooled accuracy/BA coincide with the fold mean, but macro-F1 differs (see 3.1).
- The final full-data model is fitted on all analysed rows; its replay checks persistence and schema behaviour, **not** external validity, and cannot be read as a generalisation score.

### 2.8 Independent reference and observational supplement

- The independent reference ([`tools/cases/reference_dsa.py`](../tools/cases/reference_dsa.py)) **never imports PsyML** and rebuilds splits, preprocessing, inner selection, out-of-fold prediction and the final fit from public scikit-learn APIs; the test suite statically checks its imports, and its data flow was reviewed. It **shares scikit-learn's estimators, splitters and metrics** with PsyML, so it validates the workflow, not the sklearn solvers themselves.
- The observation supplement ([`tools/cases/observe_psyml_dsa.py`](../tools/cases/observe_psyml_dsa.py)) only wraps and records PsyML's production calls to complete fold membership and the 54-fit audit; it does not pose as an independent implementation.
- The comparator ([`tools/cases/compare_dsa.py`](../tools/cases/compare_dsa.py)) checks membership, class sets, group isolation, fit scope, preprocessing statistics, candidate parameters and scores, selection trace, out-of-fold predictions and probabilities, metrics and saved-model replay under predeclared tolerances; it may import PsyML to inspect persistence and does **not** pose as an independent implementation; it additionally recomputes balanced accuracy and macro-F1 from per-class TP/FN/FP counts. Any failure keeps its differences and exits non-zero; see appendix D.

### 2.9 Engineering controls and acceptance

Four controls run on the real data: an ordinary row-split group-leakage audit (the supplemental auditor must detect it; PsyML itself warns rather than hard-blocks, and this must not be described as a built-in safeguard); rotating the labels of fixed outer fold 1 (inner scores, selection, training statistics and test predictions/probabilities must not change); adding 1000 to the test features of fixed outer fold 1 (training statistics and inner selection must not change, predictions may); and one within-subject shuffled-label canary (ascending `subject_id`, a single `default_rng(20261002)`, features and row order untouched; the predeclared alarm threshold is fold-mean BA > 0.10). The canary is an engineering perturbation, **not a permutation test**, and does not estimate a false-positive rate.

## 3. Results

### 3.1 Primary values

The values below come from the original case package's frozen Linux cloud run and were re-checked by the macOS (aarch64) re-run (3.5).

| Quantity | Value |
| --- | --- |
| Outer fold 1 (test participants 4, 8) balanced accuracy | 0.5394736842105263 |
| Outer fold 2 (test participants 3, 7) balanced accuracy | 0.4986842105263158 |
| Outer fold 3 (test participants 2, 6) balanced accuracy | 0.6644736842105264 |
| Outer fold 4 (test participants 1, 5) balanced accuracy | 0.5934210526315788 |
| **Primary: fold-mean balanced accuracy** | **0.5740131578947368** |
| Fold-mean macro-F1 | 0.5513874769696934 |
| Between-fold SD (ddof=0, BA / macro-F1) | ≈ 0.062103 / ≈ 0.068311 |
| Same-fold Dummy balanced accuracy | 1/19 = 0.05263157894736842 |
| Fold-mean procedure − Dummy difference | 0.5213815789473684 |
| Pooled out-of-fold macro-F1 | 0.5702035749465654 |
| Participant out-of-fold balanced accuracy range | ≈ 0.4553–0.6658 (8 participants, descriptive) |

The primary value near 0.574 is this case's result under the agreed protocol, used to check that the workflow executed correctly; it is not a new algorithmic achievement and must not be compared directly with paper values obtained with different sensor placements, features or splits.

### 3.2 Per-fold results and selection trace

All four outer folds and the final full-data choice selected `logistic_regression, C=1.0`, with inner means of 0.5381578947368421, 0.577485380116959, 0.5399122807017545 and 0.508187134502924, and a final choice of 0.5450779727095517. The outer family leaderboard is exploratory only and is not a new unbiased "best model" score.

### 3.3 Software and reference conformance

- All 9,120 out-of-fold predictions agree row by row between the two implementations (exactly, per the case package; the macOS re-run's hard-prediction file is byte-identical to the frozen result, see 3.5).
- The training rows, families, parameters and preprocessing statistics of the 54 fits all align; the comparator also recomputes median/mean/var directly from the training rows and balanced accuracy/macro-F1 from per-class TP/FN/FP counts.
- The maximum probability difference between PsyML and the independent reference is 0; the native CLI and the observational re-run export identical predictions, fold metrics, search and selection files.
- After a trusted load, the saved model's classes and probabilities match the independent final model; column reordering is harmless and a missing feature is rejected. The replay uses the original analysis rows and is **not** external validation.

### 3.4 Control results

| Category | Count | Result | Summary |
| --- | --- | --- | --- |
| Numerical acceptance | 26 | Passed | Membership, fits, preprocessing, selection, out-of-fold predictions/probabilities, saved-model replay |
| Structural checks | 4 | Passed | Partitions disjoint and covering the source rows; every partition holds 19 classes; inner scopes strictly inside their outer training rows; role columns excluded |
| Export checks | 2 | Passed | Probability columns follow `classes_`; saved-model metadata matches the independent final model |
| Real-data controls | 7 | Passed | Row-split leakage detected by the supplemental auditor; fixed fold-1 label rotation changes neither inner scores/selection/training statistics nor test predictions/probabilities; fold-1 test features +1000 change neither training statistics nor inner selection |
| Shuffled-label canary | 6 + 1 | Passed | The complete nested workflow matches the independent reference; fold-mean BA = 0.0532894736842105, below the 0.10 alarm; the shuffle changes only the target column |

On group leakage, two facts must be kept apart: PsyML warns when a group column is supplied together with an ordinary k-fold but does **not** hard-block it; the fault injection in this case is detected by the supplemental auditor. In addition, the repository's existing outer-ranking perturbation and failure-backfill tests (`tests/test_nested_family_selection.py`) were actually executed and passed during this integration.

### 3.5 Cross-platform verification

During the repository integration, every stage was re-run on macOS (aarch64) with the same parity versions as the frozen case (Python 3.12.14, scikit-learn 1.8.0, SciPy 1.17.0, …); the record is in [`expected/reverification_macos.json`](../examples/public/dsa_group_nested_v1/expected/reverification_macos.json).

- Exit codes for the native CLI, reference, observation, comparison and controls were 0, 0, 0, 1, 0; the comparison's 1 comes only from the cross-platform metric difference below and is intentionally retained.
- The 9,120 out-of-fold hard predictions are **byte-identical** to the frozen result (`predictions.csv` SHA-256 `36c39a34c9317d568c79f37de17c2b566d10f24db9de0625886f3bda83022b53`); fold accuracies, selection trace, macro-F1 and Dummy differences match the frozen baseline.
- The only difference is in the probability-derived `roc_auc_ovr_weighted` (affecting `fold_metrics.csv`, `metrics.csv` and the mean/std/min of `metrics_summary.csv`): about 2.03e-7 on outer folds 1 and 2 and 0 on folds 3 and 4. The maximum out-of-fold probability difference is 1.9762588500393807e-05 (per-fold maxima 1.98e-5, 8.70e-6, 6.56e-6, 5.23e-6; 97,415 of 173,280 probability cells exceed 1e-10).
- Alignment and localisation: both sides order probability columns as `probability_1..19`, both final models' `classes_` are 1..19, and `row_index` sequences and `fold/observed/predicted/model` are identical. Recomputing ROC-AUC on macOS from the **frozen probability matrices** reproduces the frozen reported values to within 1.11e-16, so the metric computation itself is consistent across platforms; the difference follows the fitted probabilities — the two final models differ by at most about 3.07e-5 in coefficients, 7.08e-5 in intercepts and 3.03e-6 in full-data probabilities.
- The official `uv.lock` environment (scikit-learn 1.9.0, pandas 3.0.5, …, see 3.6 and appendix C) completed a full re-run of the same case on 2026-10-02: its 26 numerical, 4 structural and 2 export checks pass inside that environment, and its primary predictions, probabilities, coefficients and every metric table are **exactly identical** to the macOS (aarch64) parity re-run (probability difference 0, coefficient difference 0, metric tables byte-identical). The difference against the frozen Linux baseline is therefore the same recorded platform-associated difference; no new difference attributable to the dependency-version change was observed on this case.
- Numerical-path diagnostics (controlled OpenBLAS kernel contrast on Linux and read-only macOS (aarch64) checks) are in the [diagnostics appendix](VALIDATION_DSA_DIAGNOSTICS_EN.md): changing only the kernel, or one-ulp input perturbation, reproduces differences of the same magnitude, and the macOS re-run's two folds each reduce to exactly one strict pair reversal (fold 1 class 6, fold 2 class 13); **the original Mac root cause remains unconfirmed** and the fold-1 change was not reproduced by the Linux contrast.
- The concrete root cause of the original Mac difference remains unconfirmed. The controlled diagnostics support sensitivity of the fitted numerical path but cannot attribute the original difference uniquely to one library, instruction path or preprocessing step. This case does not claim numerical equivalence across platforms, and no tolerance or baseline was changed because of it.
- The canary's BA and shuffled-CSV hash match the frozen values; the +1000 feature shift changed 2,122 predictions, the same count as on Linux. After the run, all 423 files of the frozen repository manifest were checked: no Python/GUI/test/lock file differs; only the 3 public documents this integration intentionally edited differ.

### 3.6 Test environments, warnings and CI

Three environments are recorded separately to avoid conflating them:

- **Case parity environment**: Python 3.12.14, scikit-learn 1.8.0, etc. on Linux x86_64 and macOS aarch64, used for the values in 3.1–3.5; not the official locked environment.
- **Repository-local `.venv`** (Python 3.12.13, scikit-learn 1.9.0, plus the explain extra `shap 0.52.0`): `ruff` passes, the default suite `pytest -q` reports **1222 passed** (including this case's 24 contract/integration tests and 5 new confusion-figure layout/invariance tests), and the privacy audit passes; the SHAP explanation tests actually execute here.
- **Official `uv.lock` environment** (separate path, `UV_PROJECT_ENVIRONMENT=… uv sync --locked --group dev`; `uv.lock` unmodified, SHA-256 `9951e0701e2a0c7bd85614d3a0fd642b9407da6d98fa955bac97397626ebce56`): `pytest -q` reports **1152 passed, 2 skipped**, exit 0. The two skips are the module-level `pytest.importorskip("shap")` in `tests/test_explanation*.py` because that command intentionally omits the explain extra — those two are not recorded as passing. On 2026-10-02 this environment also completed the full DSA case (native CLI, independent reference, observation audit, comparison and controls exited 0/0/0/1/0; the comparison's 1 again came only from the retained golden metric difference); the small record is `expected/reverification_uv_lock.json`. SHAP explanations were not run in this environment.

Python warnings during the case: the native CLI `warnings.json` keeps one scientific caveat (primary metrics evaluate the nested selection procedure; the family leaderboard is exploratory); the reference, observation and control warning lists are empty; there is no ConvergenceWarning; every stage produced empty stderr.

After the push, the repository's Core CI ([run 36880091260](https://github.com/GuGuGu-coocoo/PsyMl_Toolkit/actions/runs/36880091260)) passed on Windows, macOS and Linux (lint, tests, the Godot GUI suite, wheel build and smoke). This CI record and the case's numerical re-run records are reported separately.

## 4. Discussion

### 4.1 What the evidence supports

The case supports this: for the recorded code version, protocol and environment, PsyML's participant-grouped nested workflow and an independently rebuilt scikit-learn implementation produce the same splits, selections and predictions; training-fold preprocessing and persistence behaviour can be checked point by point; and the engineering controls found no sign of group leakage or selection contamination in this workflow. It also confirms that the repository generates derived data locally and does not redistribute the dataset.

### 4.2 Relation to prior work

The original paper compares several classifiers, uses five sensor units on the chest, both arms and both legs (including magnetometers), PCA-processed features, and evaluates random subsampling, random 10-fold and leave-one-subject-out designs. Its inputs, features, model scope and split protocol differ from this case. This case uses one torso unit with 12 fixed statistics, a fixed 4-fold grouped outer and 3-fold stratified grouped inner design, and only Dummy and logistic regression as candidates; it does not aim to compare scores with the original paper or any other study. The original paper already evaluated new-participant generalisation, so this case is not a first introduction of grouped validation, and its value carries no domain-performance interpretation.

### 4.3 Scope and interpretation limits

- Eight participants' public records cannot support clinical, general-population or naturalistic claims; this case is not external validation and does not cover other acquisition protocols, devices or populations.
- The independent reference shares scikit-learn's solvers with PsyML; the shuffled-label canary is a single engineering perturbation, not a permutation test, and does not estimate a false-positive rate or prove the absence of leakage.
- The cause of the cross-platform difference is not confirmed; the report keeps the raw difference and does not interpret it as a software defect or improvement.
- This case is limited to workflow checks on the derived DSA CSV under the fixed grouped-nested protocol and recorded environments; see Sections 3.5–3.6 for the execution records.

### 4.4 Figure readability

The native 19-class confusion-matrix export was crowded under its original default layout: adjacent three-digit annotations and axis labels were dense and some digits visually touched. The underlying CSV, totals and metrics were correct. This observation is retained as history. On 2026-10-02 the native plotting path (`src/psyml/reporting/research.py`) received a minimal class-count adaptive fix: the canvas and fonts scale with the class count, tick labels rotate further for large matrices (labels remain the `Class 1..N` placeholders in `confusion_matrix.csv` order), and zero cells are no longer annotated above fourteen classes while every class and every non-zero count stays visible; axis meanings, class order, the count mode and the colour bar are unchanged. Five regression tests cover the layout policy and the binary / few-class / 19-class / long-label / CJK-label / all-zero scenarios, and verify that drawing leaves predictions, metrics and the confusion-matrix file byte-identical in the same environment. The fixed 19-class native export and the scenario figures were inspected visually: text is readable, labels are not truncated and axes do not overlap. This check concerns the statically exported native figures.

## 5. Data and code availability, and reproduction

- The data are obtained under CC BY 4.0 from the official UCI location; the repository **does not redistribute** them, and the derived CSV is generated only in the local Git-ignored `examples/public/data/`. Attribution and the modification note are in `examples/public/dsa_group_nested_v1/expected/` and `tools/cases/prepare_dsa.py`.
- The code is released under the Apache License 2.0. Case tools live in `tools/cases/`, the configuration in `examples/public/configs/dsa_group_nested_v1.json`, pinned expectations in `examples/public/dsa_group_nested_v1/expected/`, and contract/integration tests in `tests/test_public_dsa_case_contract.py`.
- Reproduction (from the repository root):

```bash
# 1) Optional: build the derived CSV from the official ZIP (strict checks, no archive code executed)
uv run python tools/cases/prepare_dsa.py --archive <official.zip> --output-dir examples/public/data
# 2-5) Native CLI, independent reference, observation audit, comparison, controls:
#      the full command sequence is in examples/public/dsa_group_nested_v1/README.md
```

The CLI and every tool require a new empty output directory; existing results are never overwritten, and `input_path`/`output_dir` resolve against the process working directory. Failure conditions include any hash mismatch, unexpected member set, non-finite value or wrong shape/count, group overlap, an approximated tie break, metrics or probabilities beyond tolerance, inconsistent saved-model replay, canary BA above 0.10, or unreviewed stderr warnings. Failures must not be turned green by changing tolerances, deleting folds, raising iterations, changing C, swapping data or picking another validation.

## 6. References

1. Barshan, B., & Altun, K. (2010). *Daily and Sports Activities* [Dataset]. UCI Machine Learning Repository. <https://doi.org/10.24432/C5C59F> (page: <https://archive.ics.uci.edu/dataset/256/daily+and+sports+activities>; licence: <https://creativecommons.org/licenses/by/4.0/>)
2. Altun, K., Barshan, B., & Tunçel, O. (2010). Comparative study on classifying human activities with miniature inertial and magnetic sensors. *Pattern Recognition*, 43(10), 3605–3620. <https://doi.org/10.1016/j.patcog.2010.04.019>
3. scikit-learn developers. Common pitfalls and recommended practices (data leakage). <https://scikit-learn.org/stable/common_pitfalls.html>
4. scikit-learn developers. Nested versus non-nested cross-validation. <https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html>
5. scikit-learn developers. Tuning the hyper-parameters of an estimator. <https://scikit-learn.org/stable/modules/grid_search.html>
6. scikit-learn developers. Cross-validation: evaluating estimator performance (group-aware cross-validation). <https://scikit-learn.org/stable/modules/cross_validation.html>
7. Collins, G. S., et al. TRIPOD+AI statement: updated guidance for reporting clinical prediction models that use regression or machine learning methods. *BMJ*, 385, e078378. <https://www.bmj.com/content/385/bmj-2023-078378>

## Appendix

### A. Frozen protocol highlights

- Protocol version `psyml_dsa_group_nested_v1`; frozen 2026-10-01 11:48:43 UTC; first real-data run started at 11:49:02.979300 UTC. The configuration was frozen before modelling and was not changed after seeing scores.
- Outer `GroupKFold(4, shuffle=False)`; inner and full-data selection `StratifiedGroupKFold(3, shuffle=True)` with seeds 20261001+fold and 20261001; candidates and selection rule as in 2.6; 54 fits expected.
- Frozen config template SHA-256 `a156dee0bde4e65f4e89ceef28320faa6931ded8dc9eccab62b514b2dba69941` (contains the then-current workspace paths, kept for forensic checking only); the repository example keeps every scientific field with relative paths.

### B. Hashes and pinned expectations

| Object | SHA-256 |
| --- | --- |
| Raw ZIP | `f42ad7744ecf14151c9fa3a86dfb5b24de9d7cb7ffe956ef5de242983459c77e` |
| Derived CSV | `75a5fe87a58f4cfde777d914d674362b5148854a3c7064d8c686c0e25c3a047e` |
| Shuffled-label CSV (canary) | `e02699c680cfaa6ec91477c79fff68d7229013d7cc9f7c2acb2ddc4b0d961d86` |
| macOS re-run primary predictions | `36c39a34c9317d568c79f37de17c2b566d10f24db9de0625886f3bda83022b53` (byte-identical to the frozen result) |

Machine-readable frozen config, metric expectations, fold membership and tolerances live in `examples/public/dsa_group_nested_v1/expected/` (`case_summary.json` for main metrics and acceptance counts, `fold_membership_expected.json` for fold participants and the selection trace, `golden_hashes.json` for frozen artifact hashes).

### C. Environments

Case parity environment: Python 3.12.14; NumPy 2.3.5; pandas 2.2.3; scikit-learn 1.8.0; SciPy 1.17.0; joblib 1.5.3; matplotlib 3.10.8; pyreadstat 1.3.6; `OPENBLAS_NUM_THREADS`, `OMP_NUM_THREADS` and `MKL_NUM_THREADS` all 1; pyarrow and SHAP not installed. It is an isolated venv with the pinned source installed `--no-deps`; the official `uv.lock` was not rebuilt. The macOS re-run used the same parity versions; the numerical backend and diagnosis summary are in the [diagnostics appendix](VALIDATION_DSA_DIAGNOSTICS_EN.md). Repository-local `.venv` and official `uv.lock` test results are in 3.6. The full case re-run inside the official `uv.lock` environment (2026-10-02) used Python 3.12.13, NumPy 2.5.2, pandas 3.0.5, scikit-learn 1.9.0, SciPy 1.18.1, joblib 1.6.0, matplotlib 3.11.1 and pyarrow 23.0.1; `uv.lock` was not modified (SHA-256 `9951e0701e2a0c7bd85614d3a0fd642b9407da6d98fa955bac97397626ebce56`), and that run's outputs are exactly identical to the macOS parity run, with the same platform-associated difference against the frozen baseline.

### D. Acceptance-tool behaviour and failure entry points

- The comparator defines a **fixed required-column contract** per acceptance table and checks the production and reference sides separately: either side missing a column, both sides missing the same critical column, a row-count mismatch or an unregistered reference-only column fails and reports the table name and missing columns; every production column must also exist in the reference and is compared.
- Numeric rules: any ±Inf, one-sided NaN, or NaN in a statistic that must be finite fails; only an empty may-be-empty diagnostic column (such as `error`) and NaN scores on `status=failed` candidate rows are allowed; a dtype mismatch also fails. The reference-only `inner_scores` diagnostic is not skipped but validated for fold count, finiteness and a mean equal to the candidate score.
- The diagnostic validation and the direct metric recomputation check their actual dependency columns first (`status/score/inner_scores`, `fold/accuracy/balanced_accuracy/f1_macro`); when incomplete they report the table name, missing columns and reason without aborting the report, and remaining executable independent checks still run.
- Tolerances: same-environment metrics ≤1e-12 absolute; preprocessing atol=rtol=1e-12; probabilities atol=1e-10, rtol=1e-8. These tolerances were not adjusted for the cross-platform difference.
- The regression tests are in `tests/test_public_dsa_case_contract.py`; public acceptance and re-run summaries are in `examples/public/dsa_group_nested_v1/expected/`.

### E. Retained differences, warnings and failure records

- The cross-platform difference (`roc_auc_ovr_weighted` about 2.03e-7 and out-of-fold probabilities up to about 1.98e-5) is retained and published; the cause is not confirmed (3.5), and no tolerance or baseline was adjusted for it. Numerical-path diagnostics are in the [diagnostics appendix](VALIDATION_DSA_DIAGNOSTICS_EN.md) (Linux kernel contrast + macOS (aarch64) checks; controlled experiments reproduce differences of the same magnitude, while the original Mac root cause remains unconfirmed).
- Confusion-figure fix (2026-10-02): the native export became class-count adaptive; layout/scenario and numeric-invariance tests pass, and the fixed 19-class export and scenario figures were inspected visually; the historical crowding observation is kept in 4.4. The fix only affects the image and leaves the confusion-matrix CSV, predictions, metrics and selection unchanged.
- Comparator fixes: the first helper misclassified the reference diagnostic column and serialised `inf` into JSON, aborting the run; later reviews found "required columns depend on the production table" and "diagnostic/recomputation missing-column exceptions prevent the report from being written", both fixed with regression and end-to-end integration tests.
- The case package's first portable rerun exited 1 at the strict stderr gate because no writable font-cache directory existed; only the subprocess cache paths were adjusted before a full passing rerun. That record concerns runner environment configuration, not training logic.
- No defect requiring a change to PsyML's core numerical workflow was found.
