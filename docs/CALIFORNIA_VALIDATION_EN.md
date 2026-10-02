# California housing regression: download, run and compare

[中文](CALIFORNIA_VALIDATION_ZH.md) · [Français](CALIFORNIA_VALIDATION_FR.md) · [README](../README.md)

This case predicts median house value for 20,640 California census block groups in 1990 from eight area features, including income and house age. It checks whether PsyML and a separately written scikit-learn program agree. These historical data cannot establish present-day house prices.

## Download and run in the application

- [Analysis CSV: california_housing.csv, 2.54 MB](https://raw.githubusercontent.com/GuGuGu-coocoo/PsyMl_Toolkit/main/examples/public/downloads/california_housing.csv). It is already converted using the reference transformation and ready to import.
- [Configuration: california_config.json](https://raw.githubusercontent.com/GuGuGu-coocoo/PsyMl_Toolkit/a1450dfc374b8a39109c41f2548fdc0dbcad23c1/examples/public/california_random_nested_v1/california_config.json). This is the original v1 configuration with `verbose=0`, used in the repaired-source verification.
- [Original official data, conversion scripts, licence and checksums](../examples/public/downloads/README.md). The conversion script is public for inspection; you do not need to run it to use this case.

Save the CSV and JSON in one local folder. If the browser displays file contents, use Save as and retain the extensions.

Use 0.3.1 for the repaired application workflow; [Releases](https://github.com/GuGuGu-coocoo/PsyMl_Toolkit/releases) lists the versions and assets actually available. Each historical run below identifies its source, library versions and check scope.

1. Open PsyML and click “Import configuration…” on page 1. Select `california_config.json`. If “Configured data not found — select the data file” appears, select `california_housing.csv` in that import dialog. Check the resulting data path. The import restores all configuration settings after reading the preview.
2. Check: 20,640 rows; regression; target `MedHouseVal`; eight predictors; no group; 5 outer K-fold splits and 3 inner splits; seed `20261002`; RMSE selection; Dummy, Ridge and Random Forest candidates. The data section below lists all predictor names.
3. On “2 Review & run”, choose a local results folder and click “Run analysis”. Keep the configured candidates, parameters and seed when comparing with the reference.
4. On “3 Results”, read RMSE and open the complete results folder. Retain `config.json`, `metrics.csv`, `metrics_summary.csv`, `fold_metrics.csv`, predictions and environment records.

After importing, do not select the CSV again with the ordinary “Browse…” button: reloading data resets variable roles and validation selections. If you already used Browse, reimport the original JSON. If the data-location dialog appears, select the case CSV there, then recheck the target, group, predictors and validation settings.

Each of five outer tests holds out 4,128 rows. The remaining data are split three ways to compare models and parameters before testing the selected setting. This is nested validation. Each row's test prediction comes from a model that did not train on that row; together these are out-of-fold (OOF) predictions.

## Numbers, configuration and output files

The same original v1 configuration has records from two environments. The macOS source-GUI run on 2026-10-02 used scikit-learn 1.9.0. Its maintainer-reported primary RMSE matches that environment's independent reference, and the comparator log reports 271/271 checks passed. The Linux scikit-learn 1.8.0 reference remains in the next column. Both use `california_config.json` and `california_housing.csv`; results from different environments are recorded separately.

The [macOS environment, reference metrics and comparison summary](MACOS_SKLEARN_1_9_VALIDATION_RECORD.json) are based on the maintainer's real-machine report and console logs. Values and counts come from those records; screenshots and complete GUI exports are not included in the public summary.

| Metric | macOS / scikit-learn 1.9.0 independent reference | Linux / scikit-learn 1.8.0 reference | Where to look in your output |
| --- | ---: | ---: | --- |
| Mean RMSE across five outer tests, primary | 0.5339708864410444 | 0.5339815958325378 | `rmse` in `metrics.csv` |
| Between-fold RMSE standard deviation, ddof=0 | 0.018514866644239496 | 0.01850680156369903 | `rmse/std` in `metrics_summary.csv` |
| Mean MAE across five outer tests | 0.3610492052309331 | 0.3610547401259507 | `mae` in `metrics.csv` |
| Mean R² across five outer tests | 0.7856750901682014 | 0.7856663784093894 | `r2` in `metrics.csv` |
| RMSE recomputed from all test predictions together | 0.5342917815702284 | 0.5343022051161513 | Independent reference `pooled_oof.rmse`; not directly exported in `metrics.csv` |

RMSE is root mean squared error and MAE is mean absolute error. Both are lower when predictions are closer and use units of USD 100,000. R² measures fit relative to target variation, not percentage accuracy. Fold standard deviation describes variation across the five tests, not a confidence interval. Recomputing RMSE from pooled predictions differs from averaging the five fold scores.

The macOS values are under `california.reference_metrics` in the new record. The [Linux mean/standard-deviation table](../examples/public/california_random_nested_v1/expected/historical_metrics_summary.csv) and [pooled reference table](../examples/public/california_random_nested_v1/expected/historical_pooled_metrics.csv) retain their original values. Historical Linux mean outer RMSEs for Dummy / Ridge are 1.153954483920011 / 0.7273658464149191 in the [family/fold reference table](../examples/public/california_random_nested_v1/expected/historical_family_fold_metrics.csv); check `model_comparison.csv` in your own output. The macOS summary does not report those two family means. Dummy predicts the training target mean; Ridge is regularized linear regression.

Both references selected Random Forest in every outer test and the final full-data selection. The final model trains on all rows; predicting those rows with it does not supply another independent test score. Match the environment before comparing with its reference at the predefined tolerance; do not alter settings to match a different environment's score.

## Recorded original v1 verification

[Verification record: configuration/data hashes, environment, 270-check summary and scope](CALIFORNIA_REPAIRED_V1_RECORD.json).

On 2026-10-02, the repaired Linux source GUI used the original v1 configuration, retaining integer `verbose=0`, for import, save, reimport, training and ten-row prediction after loading the saved model. All 270 observable checks passed without the v1.1 compatibility amendment. Mean outer RMSE was 0.5339815958325378. GUI progress planned 106 fits; there was no separate runtime trace of each production fit call.

The tested application code is identical to public commit [948c451](https://github.com/GuGuGu-coocoo/PsyMl_Toolkit/commit/948c451bb0e401c7ffe1c9ab65439ebc3521031b). The following `a1450df` changed only historical-file line-ending protection. This GUI run used Linux x86_64, Python 3.12.14, scikit-learn 1.8.0, NumPy 2.3.5, pandas 2.2.3, SciPy 1.17.0 and Godot 4.6.3, with one numerical-library thread. The current official lock uses scikit-learn 1.9.0; it is a separate environment. The [three-platform CI for a1450df](https://github.com/GuGuGu-coocoo/PsyMl_Toolkit/actions/runs/36978714686) is automated testing, not real-window validation of macOS, Windows or application bundles.

The archived CSV links in the table retain values from that same original v1 independent reference. Before the fix, the original v1 GUI run failed; a separate historical run succeeded with the v1.1 configuration that omitted `verbose`. Those records remain below and are distinct from the repaired original v1 run.

Formal comparison uses absolute and relative tolerances `atol=rtol=1e-10`, plus checks of row identity, splits, candidates and effective parameters. It does not promise bit-identical results on every platform. Rounded interface numbers are an initial check; the [comparator and independent reference](../examples/public/california_random_nested_v1/README.md) check complete exports. The 270/270 count covers observable checks in this run. Ordinary exports do not expose all inner memberships, preprocessing states of each inner fit, or row-level predictions of nonselected families.

Random splits can put neighboring areas in both training and testing. They do not establish performance in new regions or future markets, causality, or suitability for housing or lending decisions. Capped target values remain in the data. Keep configuration, software/library versions and a separate output directory for every new run.

## Historical record: pre-fix v1 failure and v1.1 compatibility run

The following sections describe the earlier source revision `a145e07`, separately from the repaired original v1 verification above. Their historical result table corresponds to [california_config_v1_1.json](../examples/public/california_random_nested_v1/california_config_v1_1.json); this configuration revision is not a software version.

## 1. Result and scope

The historical case tested PsyML 0.3.0's **Linux source GUI**, commit
`a145e07c4b6a4135781725c1390f68192ab8e92c`, on California Housing. It exercised
configuration/data import, scientific settings, real-window execution, result
inspection, full prediction export, saved-model loading and ten-row prediction.
The original v1 configuration **failed**. The separately versioned v1.1
compatibility configuration passed **270/270 checks within the observable scope**
against an independent reference, at the tolerance frozen before scoring.

This is a bounded software-workflow case. It does not certify every PsyML
parameter, the complete toolkit, another OS or a distributed application bundle.
The historical run did not modify production source code. The public tools can check other runs. Later GUI repairs require validation recorded against their own source revision.

## 2. Data, attribution and conversion

Source: [Liu, Nelson (2016), Figshare version 2](https://doi.org/10.6084/m9.figshare.3829992.v2),
file 5976036. The retained deposit metadata explicitly identifies **CC BY 4.0**;
see [attribution](../examples/public/california_random_nested_v1/ATTRIBUTION.md)
and [original public metadata](../examples/public/california_random_nested_v1/expected/figshare_metadata.json).
Original research: [Pace & Barry (1997), *Sparse Spatial Autoregressions*](https://doi.org/10.1016/S0167-7152(96)00140-X).
Data authors/depositors do not endorse PsyML or this case.

The archive is 441,963 bytes, SHA-256
`aaa5c9a6afe2225cc2aed2723682ae403280c4a3695a2ddda4ffb5d8215ea681`.
The derived CSV is 2,539,419 bytes, SHA-256
`157b6c0d3acd6d93a50c411d0cd4130d8c719ce5eb17b61f1c45300f2af6fc85`.
Preparation reads only the two declared regular archive members after verifying
the complete archive hash; it never extracts or executes archive content.

There are 20,640 census block groups, eight predictors and target `MedHouseVal`.
In order: `MedInc`, `HouseAge`, `AveRooms`, `AveBedrms`, `Population`, `AveOccup`,
`Latitude`, `Longitude`. With zero-based source columns, conversion is
`raw7`, `raw2`, `raw3/raw6`, `raw4/raw6`, `raw5`, `raw5/raw6`, `raw1`, `raw0`;
target is `raw8/100000`. Thus rooms, bedrooms and occupancy use households as
the denominator; the target unit is USD 100,000 in the 1990 census data.

No rows are removed, reordered or winsorized; there is no target transformation
beyond this unit conversion and no feature selection. There are no missing or
nonfinite entries. The historical descriptive audit recorded 965 target values
at the retained cap 5.00001 (4.6754%). These are block groups, not individual
households or contemporaneous property transactions.

## 3. Design frozen before the first fit

The [original protocol](../examples/public/california_random_nested_v1/expected/PROTOCOL_FROZEN.json)
and configs are retained byte-for-byte. Portable copies change only input/output
paths and are checked against type-sensitive scientific identities.

- Outer: `KFold(5, shuffle=True, random_state=20261002)`, source row order,
  4,128 test rows per fold.
- Inner: `KFold(3, shuffle=True)`, seeds 20261003–20261007 for outer folds 1–5;
  seed 20261002 for final full-data selection.
- Every fit constructs a fresh numeric `ColumnTransformer`, median imputation,
  `StandardScaler`, and estimator, fitted only to that fit's training rows.
- Ordered families: Dummy(mean); Ridge(alpha 0.1, 1, 10, SVD solver);
  Random Forest(100 trees, max depth 10, min leaf 3, `n_jobs=1`). Full parameter
  dictionaries, not only these highlights, are pinned by the original configs.
- Select the minimum unweighted mean of three inner RMSEs. Replace only on a
  strictly lower score; exact ties retain family/candidate configuration order.
  Outer scores never feed back into selection.
- Planned and independently recorded workload: 90 inner fits + 15 family-outer
  fits + one final fit = 106. GUI progress showed 106 planned tasks, but there
  was no separate trace observing every production fit call.
- Primary: unweighted mean of five selected-procedure outer RMSEs. Secondary:
  fold-mean MAE/R², descriptive fold SD (`ddof=0`), separately pooled OOF metrics,
  and same-fold differences from Dummy. CPU single-threaded; no SHAP or
  permutation importance.

All finite floating comparisons use **atol = rtol = 1e-10**, frozen before
results. Nonfinite values and one-sided missingness fail. The empty diagnostic
`error` field is the sole permitted missing-text exception. Row keys, coverage,
fold identities, candidate ordering, selected identities and scientific
configuration have exact contracts. The default pandas CSV parser is frozen;
round-trip parsing is only a subsequent diagnostic, never a replacement rule.

## 4. Original failure, then an explicit v1.1 amendment

The original config explicitly requested RF `verbose=0`. Godot serialized it as
`0.0`; PsyML's then-current integer restoration omitted `verbose`. Scikit-learn
rejected RF in all six selection scopes (five outer, one final). The remaining
families therefore did not implement the frozen intended procedure. A separate
local package-metadata setup fault also blocked the first run's final model
export. The original comparison recorded **195/227 passed, 32 failed**; missing
terminal results/models and the candidate failures are retained as failures.

The [v1.1 amendment](../examples/public/california_random_nested_v1/expected/PROTOCOL_AMENDMENT_v1_1.json)
removed only the RF `verbose` key, letting scikit-learn use its same integer-zero
default. Typed effective estimator parameters were compared before the revised
fit. Data, candidate behavior, seed, folds, predictors, metric and tolerances
were unchanged. The change followed the failure and is separately versioned;
it is not retroactively represented as the original pre-fit configuration.

For original v1, the public comparator retains exact raw GUI-roundtrip types.
For historical v1.1 only, it reports raw JSON numeric drift and applies the
explicitly documented bounded count-field restoration when checking saved
configuration semantics. Executed parameter types still must match exactly.
It never treats invalid float `verbose=0.0` as integer zero, or converts a
fractional `min_samples_*` meaning to an integer count.

## 5. Historical numerical results

| Metric | Historical v1.1 value |
|---|---:|
| Mean outer RMSE, primary | 0.5339815958325378 |
| Outer RMSE SD, ddof=0 | 0.01850680156369903 |
| Mean outer MAE | 0.3610547401259507 |
| Mean outer R² | 0.7856663784093894 |
| Pooled OOF RMSE | 0.5343022051161513 |
| Pooled OOF R² | 0.7856041590209227 |
| Dummy mean outer RMSE | 1.153954483920011 |
| Ridge mean outer RMSE | 0.7273658464149191 |

| Outer fold | Selected family | RMSE |
|---|---|---:|
| 1 | Random Forest | 0.5622963920650870 |
| 2 | Random Forest | 0.5191199276807156 |
| 3 | Random Forest | 0.5316590028567558 |
| 4 | Random Forest | 0.5460596387779938 |
| 5 | Random Forest | 0.5107730177821366 |

All five outer folds and the final full-data selection chose Random Forest.
Family scores are descriptive comparisons, not a reason to select a different
validation strategy after seeing results. Fold SD is not a standard error or
confidence interval. RMSE is in units of USD 100,000 of the historical target,
not an estimate of current-price error.

The actual GUI export covered all 20,640 unique OOF rows and matched outer-fold
membership. Default CSV parsing produced maximum prediction differences of
8.88e-16 (OOF) and 4.44e-16 (ten-row GUI prediction), within the frozen rule.
A later round-trip-parser diagnostic found exact equality for OOF values, all
30 candidate means and fold metrics; this did not replace the default parser.
Saved-model full-data/fixture replay and final preprocessing statistics matched
exactly. Ten-row output preserved `sample_id`, input values and column order,
then added `predicted_value`. All 30 revised candidate-search records completed.
These are historical measurements; quick repository tests do not regenerate them.

## 6. Environment, public tools and evidence boundary

Historical runtime: Linux x86_64; Python 3.12.14; NumPy 2.3.5; SciPy 1.17.0;
pandas 2.2.3; scikit-learn 1.8.0; joblib 1.5.3; Matplotlib 3.10.8; Godot 4.6.3.
The initial source launch required Godot resource/class-cache import and proper
Python package installation. An invalid default Documents output path on that
cloud desktop blocked configuration saving until an explicit valid output
location was selected; the error was shown on page 2. These are historical
observations, not claims about every installation or current code.

The runnable tools/commands are in the [case README](../examples/public/california_random_nested_v1/README.md).
The independent reference imports no PsyML modules or production helpers and
records splits, all 106 fitted states, 90 individual inner scores and 24 unique
training-scope statistics. It shares sklearn estimators/splitters/metrics with
PsyML and therefore checks workflow organization, not independent solver validity.

The new preparation reproduces the historical data bytes. Contract tests use
small synthetic archives/data and fault injections, with no download or full-case
fit. Synthetic controls test comparator rejection and reference preprocessing;
they are not a real-data leakage/permutation test and do not instrument PsyML.
The public comparator also checks relocated scientific identity, environment
compatibility, model paths and preservation of prediction input columns. Its
check count can differ from the historical 270; the old count remains unchanged.
A separately recorded integration check against retained old outputs is not a
new GUI run or new fit.

Native GUI exports do **not** disclose all production inner memberships,
per-inner-fit preprocessing states, individual inner scores or nonselected
families' row-level OOF. The complete reference audit must not be described as
an observation of those production internals. The repository includes compact historical summaries, source metadata, hashes and the [prepared CSV](../examples/public/downloads/README.md). Model binaries, screenshots and full result trees are excluded. Reproduction uses a new local run; rebuilding the CSV from the source archive is optional.

Random row folds can place neighboring census block groups in training and test
sets. There is no spatially held-out, temporal or external-population validation,
no causal conclusion, and no demonstrated suitability for high-impact housing or
lending decisions. Target capping and 1990 source age remain substantive limits.
The historical case did not validate macOS, Windows, application bundles or the
current official lock environment. New environments must be recorded separately;
neither new values nor a failed check justify weakening the frozen tolerance.
