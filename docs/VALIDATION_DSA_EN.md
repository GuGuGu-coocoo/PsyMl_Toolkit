# PsyML public activity-data validation: DSA participant-grouped nested case

[中文](VALIDATION_DSA_ZH.md) · [Français](VALIDATION_DSA_FR.md)

This document records a reproducible software-validation case: the public UCI
*Daily and Sports Activities* (DSA, UCI 256) data are modelled with a
prespecified participant-grouped nested cross-validation protocol, and the
result is checked point by point against an independent scikit-learn
implementation that never imports PsyML. The runnable example is in
[`examples/public/dsa_group_nested_v1/`](../examples/public/dsa_group_nested_v1/README.md);
the pinned expectations are in that directory's
[`expected/`](../examples/public/dsa_group_nested_v1/expected/README.md).

## 1. Purpose and scope

The case supports project maintenance and workflow acceptance: it checks data
conversion, split membership, training-fold-only preprocessing, nested
selection, out-of-fold prediction, metric calculation, confusion-matrix export
and saved-model replay, and asks whether the two implementations agree
numerically. It is **not** a new algorithm, not a reproduction of the original
paper's benchmark, not a comparison against other tools, and it supports no
statement about psychological constructs, clinical use, causality or reduced
user error.

> A prespecified participant-grouped nested cross-validation protocol was
> applied to a public daily-activity data set, and an independent scikit-learn
> workflow recomputed splitting, training-fold preprocessing, inner selection,
> out-of-fold prediction, evaluation and model persistence. In the frozen
> environment both implementations agreed row by row on predictions and
> preprocessing statistics and passed targeted perturbation tests. The case
> provides numerical-conformance and reproducibility evidence for the tested
> workflow; it makes no empirical claim about algorithmic novelty, external
> validity in other populations, or user-error reduction.

As research-software maintenance, the describable contribution is the unified
execution and recording of study design, training-fold preprocessing, nested
selection, evaluation semantics and reproducible artifacts; this is not a new
model, a leading-performance claim or a human-factors result.

## 2. Version, time and environment

- Pinned source commit: `de33abfe52ccfee67f461a850edd00a14d2fbfaa` (PsyML `0.3.0`).
- Protocol frozen 2026-10-01 11:48:43 UTC; the first real-data run started at
  11:49:02.979300 UTC. Frozen before modelling; nothing was changed after
  seeing scores.
- Original frozen config template SHA-256:
  `a156dee0bde4e65f4e89ceef28320faa6931ded8dc9eccab62b514b2dba69941`
  (contains the then-current workspace paths; kept for forensic checking only.
  The repository example keeps the science fields and uses relative paths).
- Case-parity environment (Linux x86_64): Python 3.12.14, NumPy 2.3.5,
  pandas 2.2.3, scikit-learn 1.8.0, SciPy 1.17.0, joblib 1.5.3,
  matplotlib 3.10.8, pyreadstat 1.3.6; `OPENBLAS_NUM_THREADS`,
  `OMP_NUM_THREADS` and `MKL_NUM_THREADS` all 1. pyarrow and SHAP were not
  installed.
- This is a **case-parity environment**: an isolated venv installed those
  dependencies and built the pinned source with `--no-deps`. The repository's
  official `uv.lock` environment was **not** rebuilt (the current lock pins
  scikit-learn 1.9.0 on Python ≥ 3.11) and was not used for the per-value
  baseline.
- Running `uv run psyml ...` uses whatever repository environment is active.
  Another version or platform produces a **new verification result**; it must
  never overwrite `expected/` or relax the tolerances.

## 3. Data, attribution and conversion

- Data: Barshan, B. & Altun, K. (2010). *Daily and Sports Activities* [Dataset].
  UCI Machine Learning Repository. DOI
  <https://doi.org/10.24432/C5C59F>; page
  <https://archive.ics.uci.edu/dataset/256/daily+and+sports+activities>;
  licence CC BY 4.0 (per the official data page; no additional restricting
  member was found inside the ZIP). The authors do not endorse PsyML or this
  case.
- Structure: 8 adult participants (aged 20–30), 19 activities, 60 five-second
  segments per participant and activity, 9,120 segments total; each segment is
  125×45. Folders `p1..p8` are the official participant IDs. **The 8
  participants are the independent units; the 9,120 segments are not 9,120
  independent people**, and adjacent segments may be correlated. The archive
  defines no train/test split.
- Raw ZIP: 170,800,010 bytes, SHA-256
  `f42ad7744ecf14151c9fa3a86dfb5b24de9d7cb7ffe956ef5de242983459c77e`;
  downloaded only from the official URL and fully hash-checked before reading.
- Conversion: only the 9,120 members `data/a01..a19/p1..p8/s01..s60.txt` are
  read (strict enumeration: missing, duplicated, extra non-directory members,
  a shape other than 125×45 or any NaN/infinity abort the run). Only the first
  six columns are used (torso acceleration x/y/z and torso angular rate
  x/y/z); each segment contributes per-channel mean then population standard
  deviation (`ddof=0`) in that order, giving 12 features. No filtering, PCA,
  feature selection or cross-segment normalisation.
- Derived CSV: 2,343,871 bytes, SHA-256
  `75a5fe87a58f4cfde777d914d674362b5148854a3c7064d8c686c0e25c3a047e`;
  columns fixed to `segment_id,subject_id,activity` plus the 12 features;
  UTF-8, LF, no index, `float_format %.17g`; exactly 60 rows per
  participant × activity, 480 per class, 1,140 per participant. An independent
  `csv.reader` + `math.fsum` recomputation of all 12 statistics had maximum
  absolute difference 1.2434497875801753e-14 (atol=rtol=1e-12).
- The role columns `segment_id`, `subject_id`, `activity` are used only for
  joining/grouping/target and **never enter `feature_columns`**.
- The repository does not redistribute data: `examples/public/data/` is
  git-ignored and the derived CSV is local only.
  `tools/cases/prepare_dsa.py` commits the download/conversion recipe,
  attribution and hashes; it never downloads by itself, never extracts the
  whole tree and never executes code from the archive.

## 4. Frozen protocol and selection rules

- Outer: `GroupKFold(n_splits=4, shuffle=False)` over the original row order.
  Test participants per fold: `[4,8]`, `[3,7]`, `[2,6]`, `[1,5]` (2,280 test
  and 6,840 training segments per fold).
- Inner: `StratifiedGroupKFold(n_splits=3, shuffle=True,
  random_state=20261001 + outer_fold)` (folds numbered from 1, i.e.
  20261002…20261005); each fold validates 2 participants and trains on 4, and
  every partition contains all 19 classes.
- Final full-data choice: the same `StratifiedGroupKFold(n_splits=3,
  shuffle=True, random_state=20261001)`; it supplies **no new unbiased test
  score**.
- Every fit builds a fresh `ColumnTransformer(numeric) →
  SimpleImputer(strategy='median') → StandardScaler → estimator`, fitted on the
  corresponding training rows only.
- Candidates: family order `['dummy','logistic_regression']`;
  `DummyClassifier(strategy='prior', random_state=20261001)`;
  `LogisticRegression(C∈[0.1, 1.0], solver='lbfgs', max_iter=2000, tol=1e-8,
  class_weight=None, fit_intercept=True, random_state=20261001)`;
  `max_candidates=2` applies per family and never triggers random sampling.
- Selection: unweighted mean of inner balanced accuracies; replacement only on
  **strictly greater** values, exact ties keep the first family/candidate;
  outer scores never break ties. One failing inner fold fails the candidate
  (successful folds are not averaged instead); if the inner winner fails in the
  outer fold, the whole procedure fails and no other family is substituted.
- Scale: 45 inner fits + 8 family outer fits + 1 full-data fit = 54 fits per
  complete workflow; CPU only, one numerical-library thread, no SHAP.

## 5. Roles and code boundaries

| Execution | Location | Role | Boundary |
| --- | --- | --- | --- |
| Native CLI primary | `uv run psyml run --config ...` | The only primary result | Production entry point; source not modified |
| Independent reference | [`tools/cases/reference_dsa.py`](../tools/cases/reference_dsa.py) | Rebuilds the same protocol from public scikit-learn APIs | **Never imports psyml**, never copies its runner chain; the test suite statically checks imports and the data flow was reviewed |
| Observation supplement | [`tools/cases/observe_psyml_dsa.py`](../tools/cases/observe_psyml_dsa.py) | Completes fold-membership and 54-fit audit records | Only wraps and records production calls; never changes inputs/splits/models/thresholds; **not an independent implementation** |
| Comparison acceptance | [`tools/cases/compare_dsa.py`](../tools/cases/compare_dsa.py) | 26 numerical + 4 structural + 2 export checks | May import PsyML to inspect persistence; keeps differences and exits non-zero on failure |
| Engineering controls | [`tools/cases/check_dsa_controls.py`](../tools/cases/check_dsa_controls.py) | Row-split audit, fixed fold-1 perturbations, shuffled-label canary | Diagnostic only; perturbation scores are never used to revise the protocol or select models |

The independent reference shares scikit-learn estimators, splitters and metrics
with PsyML, so it validates the workflow rather than the solvers. The
comparator additionally recomputes balanced accuracy and macro-F1 from
per-class TP/FN/FP counts as a metric-level cross-check (not a second
independent fit).

The comparator never compares "only some columns": every acceptance table has a
**fixed required-column contract** defined from the frozen protocol and the
expected artifact schemas (`compare_dsa.REQUIRED_COLUMNS`), checked on the
production and the reference side **separately**; either side missing a
required column fails and reports the table name and the missing columns. Two
tables missing the same critical column also fail — the contract never depends
on the current production column names and is not an intersection of the two
tables. On top of that, every production column must exist in the reference and
is actively checked; a row-count mismatch or an unregistered reference-only
column fails. Numeric fields have explicit rules: any ±Inf, a one-sided NaN, or
a NaN in a **statistic that must be finite** fails even when both sides agree;
only two kinds of empty values are allowed — registered may-be-empty
diagnostics (for example an empty `error` column) and NaN scores on explicitly
`status=failed` candidates; a dtype mismatch (numeric vs text) also fails. The
reference-only `inner_scores` diagnostic is not skipped: it must hold a finite
score list of the configured inner-fold length for every completed candidate,
with an unweighted mean equal to that candidate's score. This policy exists
because the first helper required identical column sets, misclassified the
reference diagnostic column and serialized an `inf` diagnostic into JSON,
aborting the run; the fix is covered by four regression groups in
`tests/test_public_dsa_case_contract.py`: the fixed required-column contract
(production-side missing, reference-side missing, both sides missing the same
critical column, reordering still passing, unknown table name raising),
failures cannot be masked (missing/unregistered columns, numeric drift,
row-count mismatch), non-finite values are rejected (one-sided NaN, statistic
NaN, Inf, dtype mismatch), and the reference diagnostic must be validated.

The diagnostic validation (`inner_scores`) and the direct metric recomputation
also check their actual dependency columns first (`status/score/inner_scores`
and `fold/accuracy/balanced_accuracy/f1_macro`); a missing dependency is
reported as a failure with the table name, the missing columns and the reason,
without defaults, skipping, uncaught exceptions or aborting the report, so
later executable independent checks (for example the confusion-matrix
comparison when predictions are complete) still run. End-to-end compare()
regression tests cover a reference-only and a both-sides missing
`parameter_search` score and a production `fold_metrics` missing
`balanced_accuracy` or `fold`, asserting that `checks.json` is written, the
report carries the exact table name and missing columns, and the CLI exits
non-zero.

## 6. Metric conventions

- Primary: unweighted fold mean of outer-fold balanced accuracy for the
  inner-selected procedure. Fold SD uses `ddof=0` and is descriptive variation,
  not a standard error or confidence interval.
- Secondary: the same aggregation for accuracy and macro-F1
  (`zero_division=0`); the pooled out-of-fold confusion matrix (explicitly
  pooled); paired same-fold procedure−Dummy differences; per-participant
  balanced accuracy (descriptive).
- **Fold mean and pooled must not be mixed**: the balanced, equal-sized folds
  make pooled accuracy/BA coincide with the fold mean, but macro-F1 differs
  (pooled 0.5702035749465654 vs fold mean 0.5513874769696934).
- The final full-data model is fitted on all analysed rows only; its replay
  checks persistence and schema behaviour, **not** external validity, and
  cannot be reported as a generalisation score.

## 7. Recorded values and selection trace (frozen case)

The values in this section come from the original case package's frozen Linux
run (recorded in that package), not from numbers regenerated by this
repository's tests; this round's local re-run is in section 9 and unrun items
in section 12.

| Quantity | Value |
| --- | --- |
| Outer fold 1 (test participants 4, 8) balanced accuracy | 0.5394736842105263 |
| Outer fold 2 (test participants 3, 7) balanced accuracy | 0.4986842105263158 |
| Outer fold 3 (test participants 2, 6) balanced accuracy | 0.6644736842105264 |
| Outer fold 4 (test participants 1, 5) balanced accuracy | 0.5934210526315788 |
| **Primary balanced accuracy (fold mean)** | **0.5740131578947368** |
| Fold-mean macro-F1 | 0.5513874769696934 |
| Fold SD (ddof=0, BA / macro-F1) | ≈ 0.062103 / ≈ 0.068311 |
| Same-fold Dummy balanced accuracy | 1/19 = 0.05263157894736842 |
| Mean procedure − Dummy difference | 0.5213815789473684 |
| Pooled out-of-fold macro-F1 | 0.5702035749465654 |
| Participant out-of-fold balanced accuracy range | ≈ 0.4553–0.6658 (8 participants, descriptive) |

All four outer folds and the final full-data choice selected
`logistic_regression, C=1.0`, with inner means 0.5381578947368421,
0.577485380116959, 0.5399122807017545 and 0.508187134502924, and a final
choice score of 0.5450779727095517. The outer family leaderboard is exploratory
only; it is not a new unbiased "best model" score and does not show that family
comparison is useless.

## 8. Acceptance and control results

| Category | Count | Result | Evidence |
| --- | --- | --- | --- |
| Numerical acceptance | 26 | Passed | `checks.json` from the comparator |
| Structural checks | 4 | Passed | Partitions disjoint and covering the source rows; every partition holds 19 classes; inner scopes are strict subsets of the corresponding outer training rows; role columns excluded |
| Export checks | 2 | Passed | Probability columns follow `classes_`; saved-model metadata matches the independent final model |
| Real-data controls | 7 | Passed | The supplemental group auditor rejects the ordinary row split; rotating fixed outer fold-1 labels changes neither inner scores/selection/training statistics nor test predictions/probabilities; adding +1000 to fold-1 test features changes neither training statistics nor inner selection |
| Shuffled-label canary | 6 + 1 | Passed | The within-subject shuffled complete workflow agrees with the independent reference; BA = 0.0532894736842105, below the predeclared 0.10 alarm; the shuffle changes only the target column (1 byte-level check) |

Other key facts: all 9,120 out-of-fold predictions agree row by row; the
training rows, families, parameters and preprocessing statistics of all 54 fits
align (statistics within 1e-12, coefficients/intercepts differ by 0); the
maximum PsyML-vs-reference probability difference is 0; the native CLI and the
observational rerun produce identical files; a trusted reload of the saved model
reproduces the independent final model's classes and probabilities, is
unaffected by column reordering and rejects a missing feature; the input CSV
hash matches the frozen value. The repository's existing outer-ranking
perturbation and failure-backfill tests
(`tests/test_nested_family_selection.py`) were **actually executed** during this
integration, not merely cited.

On group leakage: PsyML warns when a group column is supplied together with an
ordinary k-fold, but it does **not** hard-block it. In this case the supplemental
auditor detects the fault injection; the behaviour must not be written as a
built-in PsyML safeguard.

Maintenance run record (2026-10-01, three environments recorded separately):

- **Repository-local `.venv`** (Python 3.12.13; numpy 2.5.2, pandas 3.0.5,
  scikit-learn 1.9.0, scipy 1.18.1, joblib 1.6.0, matplotlib 3.11.1,
  pyarrow 23.0.1, plus the explain extra `shap 0.52.0`): `ruff check src tests
  tools` passed; the default suite `pytest -q` reported **1212 passed** (current
  test set; the earlier run before the 3 comparator regression tests were added
  reported 1209 passed); `tools/audit_repository.py` passed the privacy audit.
  Because the explain extra is installed, the SHAP explanation tests actually
  execute here.
- **Official `uv.lock` environment** (separate path,
  `UV_PROJECT_ENVIRONMENT=… uv sync --locked --group dev`; `uv.lock` not
  modified): Python 3.12.13 with the same locked versions (scikit-learn 1.9.0,
  joblib 1.6.0, matplotlib 3.11.1, pyarrow 23.0.1, …); `pytest -q` reported
  **1152 passed, 2 skipped**, exit 0. The two skips are the module-level
  `pytest.importorskip("shap")` in `tests/test_explanation.py` and
  `tests/test_explanation_cli.py` because that command intentionally does not
  install the explain extra — those two are **not** recorded as passing. This
  environment did **not** re-run the DSA case itself.
- **Case-parity environment** (Python 3.12.14, scikit-learn 1.8.0, scipy 1.17.0,
  …) is used only for the DSA case recomputation and is different from both test
  environments; its numbers must not be presented as official-lock or local
  development environment results.

## 9. macOS re-run recorded during this integration (additive evidence)

The integration re-ran every stage with the pinned source and the same parity
versions (macOS aarch64, Python 3.12.14, scikit-learn 1.8.0, etc.; see
[`expected/reverification_macos.json`](../examples/public/dsa_group_nested_v1/expected/reverification_macos.json)):

- Exit codes for the native CLI, reference, observation, comparison and
  controls were 0, 0, 0, 1, 0; the comparison's 1 came only from the
  cross-platform golden metric difference below.
- All 26 numerical, 4 structural and 2 export checks passed; the 9,120
  out-of-fold predictions are **byte-identical** to the frozen result
  (`predictions.csv` SHA-256
  `36c39a34c9317d568c79f37de17c2b566d10f24db9de0625886f3bda83022b53`);
  fold BAs, selection trace, macro-F1 and Dummy differences match the frozen
  baseline.
- The only difference from the frozen baseline is the probability-derived
  `roc_auc_ovr_weighted` (affecting `fold_metrics.csv`, `metrics.csv` and the
  mean/std/min of `metrics_summary.csv`): about 2.03e-7 on outer folds 1 and 2
  and 0 on folds 3 and 4. The 9,120 out-of-fold probabilities differ by up to
  1.9762588500393807e-05 (per-fold maxima: 1.98e-5, 8.70e-6, 6.56e-6, 5.23e-6;
  97,415 of 173,280 probability cells exceed 1e-10). Hard predictions,
  memberships, selection and every label-based metric are identical; **this
  round does not claim numerical equivalence across platforms**.
- The difference details were aligned and checked: class order (`probability_1..19`
  and both final models' `classes_` are 1..19), sample alignment (`row_index`
  sequences and `fold/observed/predicted/model` identical, 9,120 hard
  predictions byte-identical), and dependency/numerical-library configuration
  (macOS numpy/scipy configuration plus both environment records) are stored in
  the git-ignored local evidence archive; per-row and per-fold differences and
  the top differing rows are in `probability_difference_details.json` and
  `probability_differences_by_row.csv`.
- Isolation experiment (same parity versions): recomputing ROC-AUC on macOS
  from the **frozen probability matrices** reproduces the frozen reported
  values to within 1.11e-16, so metric computation is consistent across
  platforms; the difference follows the probabilities — the two final models
  differ by up to about 3.07e-5 in coefficients, 7.08e-5 in intercepts and
  3.03e-6 in full-data probabilities. Conclusion: the difference originates at
  the fitted-parameter/probability level; **the cause is not confirmed and may
  be related to platform numerical implementations** — no implementation-level
  root-cause experiment was performed, and it is not written as "caused by the
  linear-algebra path". The difference is preserved and reported, never used to
  relax tolerances or replace the baseline; this case is therefore not written
  as a blanket pass.
- The canary BA and shuffled-CSV hash match the frozen values
  (`e02699c680cfaa6ec91477c79fff68d7229013d7cc9f7c2acb2ddc4b0d961d86`); the
  +1000 feature shift changed 2,122 predictions, the same count as on Linux.
- After the run, all 423 files of the frozen repository manifest were checked:
  no Python/GUI/test/lock file differs; only the 3 public documents this
  integration intentionally edited (`README.md`, `docs/TESTING.md`,
  `examples/public/README.md`) differ.
- All stages produced empty stderr; the native CLI `warnings.json` keeps the
  scientific caveat (primary metrics evaluate the nested selection procedure;
  the family leaderboard is exploratory), while reference, observation and
  control warning lists are empty and no ConvergenceWarning occurred.

This re-run is cross-platform supplementary evidence and does not replace the
frozen Linux baseline. Windows and the official locked environment remain
unrun.

## 10. Warnings, differences and retained failures

- The case package's first portable rerun stopped at the strict stderr gate
  because a fresh font scan found no writable cache directory; the numeric
  comparison had passed, logs were retained, and only subprocess cache paths
  were pointed at a new writable directory under the output before a full
  passing rerun. That is launcher portability, not a training-logic error.
- The first comparison run had an All-NaN diagnostic warning caused by an empty
  `error` column being read as all-NaN; only the reporting diagnostic was
  corrected, with no change to model, data, selection, tolerances or results.
  The repository tools skip non-finite/empty diagnostics and do not treat an
  empty error column as a scientific failure.
- No defect requiring a change to PsyML's core numerical workflow was found.

## 11. Native confusion-figure readability limitation

The native 19-class confusion-matrix export is crowded at its default compact
size: adjacent three-digit annotations and axis labels are dense and some
digits visually touch. The underlying CSV, totals and metrics are correct. This
is a real export-readability limitation, **not a numerical failure, and not
evidence that the GUI was tested**. The original figure is preserved; a clearly
labelled independently enlarged redraw (same CSV, all 361 cells checked
programmatically) is separate and is not a production output. This repository
contains no production graphics fix; any adaptive figsize/labelling change
needs its own minimal plan and trilingual multi-class verification first.

## 12. What was not run

- The full Python suite for this case is covered by the maintenance record: this
  integration actually ran `ruff check src tests tools` (passed), the default
  suite in the repository-local `.venv` (`pytest -q`: 1212 passed, including the
  19 new contract tests and the existing outer-ranking/failure-backfill tests)
  and `tools/audit_repository.py` (passed); the official `uv.lock` environment
  was separately created and ran the test suite per repository convention
  (1152 passed + 2 explain-extra skips, see section 8) but did **not** re-run the
  DSA case itself.
- Godot/GUI, real windows, Windows and macOS standalone packages (the macOS
  re-run used a source environment, not a packaged app).
- SHAP/explanation, input formats other than CSV, a dedicated cross-platform
  tolerance study, user studies, external data validation and a full security
  audit.
- Re-downloading and converting the full raw ZIP (the delivered derived CSV was
  used; `prepare_dsa.py` is covered by synthetic-ZIP contract tests for strict
  enumeration, hash, shape, finiteness and count rejection).

## 13. Rerun commands and failure conditions

```bash
# 1) Optional: build the derived CSV from the official ZIP (strict checks, no archive code executed)
uv run python tools/cases/prepare_dsa.py --archive <official.zip> --output-dir examples/public/data
# 2-5) CLI primary, independent reference, observation, comparison, controls:
#      the full command sequence is in examples/public/dsa_group_nested_v1/README.md
```

Failure conditions: any hash mismatch, unexpected member set, non-finite value,
wrong shape/count, group overlap in a partition, an approximated tie break,
metrics/probabilities beyond tolerance, inconsistent saved-model replay, canary
BA above 0.10 or unreviewed stderr output. Never "fix" a failure by changing
tolerances, deleting folds, raising iterations, changing C, swapping data or
picking another validation. The CLI and every tool require a **new empty output
directory**; existing results are never overwritten. `input_path`/`output_dir`
resolve against the process working directory.

## 14. Statement boundaries

- Eight participants' public activity records cannot support clinical,
  general-population or naturalistic claims; this case is not external
  validation.
- The independent reference shares scikit-learn's solvers; the canary is one
  engineering perturbation, not a permutation test, not a false-positive-rate
  estimate and not proof that leakage cannot occur.
- The results establish numerical conformance and reproducibility of the tested
  workflow in the recorded environment only; they claim no new algorithm,
  leading performance or user-error reduction.
