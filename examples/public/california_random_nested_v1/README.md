# California housing regression

Download the prepared CSV and full configuration, import the configuration in PsyML, select the CSV if asked, then run from the GUI. You do not need to run the scripts below.

- [中文：下载与结果对照](../../../docs/CALIFORNIA_VALIDATION_ZH.md)
- [English: downloads and result comparison](../../../docs/CALIFORNIA_VALIDATION_EN.md)
- [Français : téléchargements et comparaison](../../../docs/CALIFORNIA_VALIDATION_FR.md)
- [Prepared data, official sources, conversion scripts and licences](../downloads/README.md)

The commands below are optional: rebuild the CSV from its source, run a separately written reference, or compare complete numerical exports. Downloaded prepared CSVs can also be copied into `examples/public/data/` to use the unchanged repository-relative CLI configurations. Normal GUI use only requires selecting the downloaded CSV when prompted.


[中文报告](../../../docs/CALIFORNIA_VALIDATION_ZH.md) · [English report](../../../docs/CALIFORNIA_VALIDATION_EN.md) · [Rapport français](../../../docs/CALIFORNIA_VALIDATION_FR.md)

A reproducible **software-conformance case**, based on 20,640 California census
block groups, eight fixed numerical predictors and the capped `MedHouseVal`
target. It is not a current-price benchmark or evidence for housing/lending,
causal inference, spatial transfer or temporal generalization.

The original Linux source-GUI run on commit
`a145e07c4b6a4135781725c1390f68192ab8e92c` failed: the GUI changed explicit
Random Forest `verbose=0` to `0.0`, rejected by scikit-learn. The separately
versioned v1.1 omitted only that parameter, using the same default integer zero;
its actual GUI exports passed **270/270 historical checks**. The original
**195/227 failure** is retained. Neither the frozen outcomes nor tolerances are
rewritten by this repository integration. See [`expected/`](expected/README.md).

## Data and fixed method

- Source: [Liu (2016), Figshare version 2](https://doi.org/10.6084/m9.figshare.3829992.v2),
  file 5976036, CC BY 4.0 as stated by the deposit. Original study:
  [Pace & Barry (1997)](https://doi.org/10.1016/S0167-7152(96)00140-X).
  [Attribution and transformation](ATTRIBUTION.md).
- Archive SHA-256: `aaa5c9a6afe2225cc2aed2723682ae403280c4a3695a2ddda4ffb5d8215ea681`.
  Prepared CSV SHA-256: `157b6c0d3acd6d93a50c411d0cd4130d8c719ce5eb17b61f1c45300f2af6fc85`.
- Five shuffled outer KFold splits, seed 20261002; three shuffled inner folds,
  seed 20261002 + outer fold (1–5), and 20261002 for final selection.
- Fresh median imputation and standardization inside every fit. Candidate order:
  Dummy(mean), Ridge(alpha 0.1, 1, 10; SVD), Random Forest(100 trees, depth 10,
  minimum leaf 3, one thread). Minimum mean inner RMSE; strict-lower update and
  first-in-configuration exact ties. No outer-score feedback.
- 90 inner fits, 15 outer-family fits, one full-data final fit. Frozen numeric
  acceptance: `atol=rtol=1e-10`; nonfinite values fail. Type-sensitive identity for
  science configuration, candidate identities and effective estimator parameters.
- Historical selected-procedure fold-mean RMSE: **0.5339815958325378**; pooled OOF
  RMSE: **0.5343022051161513**. All outer folds and final selection chose Random
  Forest. These are recorded historical results, not outputs of quick tests.

## Optional: rebuild data and verify independently

`input_path` and `output_dir` in these public configurations are repository-root
relative for CLI use. They differ from the historical files only in these two
operational paths. The tools check type-sensitive scientific identity against
byte-preserved historical configurations. New output directories are mandatory.

```sh
# Download the official archive yourself from:
# https://ndownloader.figshare.com/files/5976036
# Preparation is offline, verifies the checksum before reading, and never extracts files.
uv run python tools/cases/prepare_california.py \
  --archive /path/to/cal_housing.tgz --output-dir examples/public/data

# CLI production run. Use v1.1 for the historical compatibility variant.
uv run psyml run \
  --config examples/public/california_random_nested_v1/california_config.json --events

# Independent reference (no PsyML imports), all 106 fits.
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
uv run python tools/cases/reference_california.py \
  --config examples/public/california_random_nested_v1/california_config.json \
  --prediction-fixture examples/public/data/california_predict.csv \
  --allow-environment-change \
  --output examples/public/results/california_reference_new_environment

# Fast, offline synthetic contracts; no full-data fits or network access.
uv run pytest tests/test_public_california_case_contract.py -q
uv run python tools/cases/check_california_controls.py \
  --output examples/public/results/california_synthetic_controls
```

The historical environment was Python 3.12.14, NumPy 2.3.5, SciPy 1.17.0,
pandas 2.2.3, scikit-learn 1.8.0 and Godot 4.6.3 on Linux x86_64. The repository's
current lock uses scikit-learn 1.9.0 on Python ≥3.11. `--allow-environment-change`
explicitly labels a new-environment run; omit it when using the historical
scikit-learn environment. The default rejects a different sklearn version.
Every run records actual dependency versions and input/source hashes. The flag
does not relax scientific fields, numeric tolerances, or historical identities.
Do not replace historical results with a new-environment result.

## Actual GUI procedure and complete comparison

1. Import the public configuration, then explicitly select the prepared
   `examples/public/data/california_housing.csv` on page 1. GUI relative input
   paths can resolve against the configuration directory, unlike the CLI's
   working directory. Alternatively save a local copy with absolute paths;
   only these two path fields may change.
2. Confirm the nine columns, target and eight predictors; regression; no group;
   median/standard; outer 5 / inner 3; seed 20261002; RMSE; all three families.
3. On page 2 choose an explicit valid absolute output root. Save configuration,
   reimport it and save again. Preserve the actual GUI-saved JSON for comparison.
4. Run in the real window, inspect progress and results. Keep the complete fresh
   `training/run_*` output. The rounded UI and first-20-row preview are not the
   numerical acceptance evidence.
5. On page 4 load **only the trusted model from this run**, load
   `california_predict.csv`, predict and export. The fixture has ten source
   rows, reversed feature order, and `sample_id`; the output must preserve all
   input columns/order and append `predicted_value`. This is persistence/schema
   checking, not an external test set.

Substitute the actual exported paths below. A CLI run alone cannot satisfy the
GUI-specific saved-configuration and prediction-export checks.

```sh
uv run python tools/cases/compare_california.py \
  --config examples/public/california_random_nested_v1/california_config.json \
  --protocol examples/public/california_random_nested_v1/expected/PROTOCOL_FROZEN.json \
  --data examples/public/data/california_housing.csv \
  --reference examples/public/results/california_reference_new_environment \
  --production /path/to/actual/training/run_directory \
  --roundtrip-config /path/to/actual/gui_saved_config.json \
  --prediction-fixture examples/public/data/california_predict.csv \
  --gui-prediction-export /path/to/actual/prediction/predictions.csv \
  --output examples/public/results/california_comparison_new
```

For a v1.1 production run, add both arguments (the reference remains original v1):

```sh
  --execution-config examples/public/california_random_nested_v1/california_config_v1_1.json \
  --compatibility-amendment examples/public/california_random_nested_v1/expected/PROTOCOL_AMENDMENT_v1_1.json
```

The comparator runs in the same sklearn version as its reference and checks the
production model's recorded sklearn version. It loads local joblib models, which
can execute code: **never supply an untrusted model or result directory**. It
never fits a model. It writes a detailed report and returns nonzero for failed
checks. Raw v1 GUI-saved numeric types remain exact; v1.1 alone retains the
historically documented restoration of specific count fields. This never
coerces an invalid float `verbose` or fractional sample-size semantics.

## Files, evidence and limits

- `california_config*.json`: portable v1 and v1.1 templates.
- `expected/`: original protocol/config bytes, provenance, source metadata,
  compact historical metrics/failure summary and artifact hashes. Prepared data are linked above; models, GUI screenshots and bulky result trees are not tracked.
- `tools/cases/*california*.py`: preparation, independent reference, fail-closed
  comparator and bounded synthetic controls.
- `tests/test_public_california_case_contract.py`: archive and conversion
  contracts, protocol/type/hash invariants, candidate/tie rules and comparator
  fault injections. These do not run the entire GUI or 106-fit case.

Ordinary production GUI exports do not expose all inner memberships, 90
per-inner-fit preprocessing states, single-inner-fold scores, or every nonselected
family's row-level predictions. The reference audit is not evidence of those
unobserved production internals. Synthetic controls added here are not the DSA
case's real-data leakage perturbations and are not a permutation test. Random
geographic row splits can place neighboring block groups on both sides; scores
cannot establish spatial or future-market transfer. The data come from 1990,
and capped values are retained. No macOS, Windows or packaged-app GUI validation
is asserted by the historical case.

## 中文简要说明

这是有界的软件流程符合性案例。原始 v1 的 `verbose` 整数丢失失败与 v1.1
仅省略该参数后的成功分开保留。运行步骤、源文件哈希、冻结容差及环境差异见上文；
完整方法、结果和证据边界见[中文报告](../../../docs/CALIFORNIA_VALIDATION_ZH.md)。
分析用 CSV 已公开提供；模型与大体积结果不进入 Git；请在新目录复跑，不覆盖冻结证据。

## Résumé français

Ce cas vérifie un flux logiciel borné. L’échec original v1 (type entier de
`verbose` perdu) reste distinct du succès v1.1, qui omet uniquement ce paramètre.
Les commandes ci-dessus reconstruisent les données et la référence indépendante;
le [rapport français](../../../docs/CALIFORNIA_VALIDATION_FR.md) détaille les
résultats et leurs limites. Aucun score ne démontre un transfert spatial ou
une capacité à prédire les prix actuels; les nouveaux résultats ne remplacent
jamais la référence historique.
