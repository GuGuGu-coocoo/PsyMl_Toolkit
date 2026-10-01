# DSA numerical-difference diagnostics: Linux kernel contrast and local Mac checks

[中文](VALIDATION_DSA_DIAGNOSTICS_ZH.md) · [Français](VALIDATION_DSA_DIAGNOSTICS_FR.md)

Case `psyml_dsa_group_nested_v1`, pinned commit `de33abfe52ccfee67f461a850edd00a14d2fbfaa`, recorded 2026-10-02.

## 1. Purpose and conclusion

This appendix records a bounded diagnosis of the published cross-platform difference (`roc_auc_ovr_weighted` about 2.03e-7; out-of-fold probabilities up to about 2e-5): a controlled kernel-dispatch experiment run in the Linux parity environment (25 fits in total: 5 single-fold probe fits + 20 four-fold kernel-contrast fits), plus minimal read-only checks on this macOS machine.

**Conclusion.** In the Linux contrast, changing only the OpenBLAS CPU kernel dispatch, or perturbing the standardized inputs by one unit in the last place, was enough to produce an AUC change of the same magnitude, the same direction on fold 2 and the same single-pair ranking reversal, with hard predictions unchanged. This supports the mechanism "the fitted numerical path is sensitive to extremely small numeric differences". On this Mac the two differing folds also decompose exactly into one strict pair reversal each (fold 1 class 6, fold 2 class 13), and this machine's numerical backend is Apple Accelerate rather than OpenBLAS. **The concrete root cause of the original Mac difference (which library, instruction path or preprocessing step) remains unconfirmed**, and the fold-1 change was not reproduced by the Linux kernel contrast.

This appendix changes no training core, frozen tolerance, baseline or scientific protocol; no diagnostic `tol`/`ftol`/kernel setting becomes a product default; it does not claim that the Mac was fully simulated, nor does it claim cross-platform numerical equivalence.

## 2. Materials and provenance

- **Linux diagnosis package** (dot cloud, 2026-10-01): `REPORT_ZH.md`, `DEEP_PLAN.md`, the fold-1 probe (`probe.py`, `results.json`, `rank_pair_checks.json`, `perturbation.json`), the four-fold kernel contrast (`deep_probe.py`, `default_*`, `Haswell*`, `Sandybridge*`, `deep_comparison.json`, `common_prediction_kernel.json`, `input_checks.json`) and `remote_reverification_macos.json`. Verified on this machine against the package's `MANIFEST.json`: 26/26 hashes match.
- **Local check environment** (case parity, kept separate from the official `uv.lock` re-run): Python 3.12.14, NumPy 2.3.5, SciPy 1.17.0, scikit-learn 1.8.0, pandas 2.2.3, joblib 1.5.3, matplotlib 3.10.8; `OPENBLAS_NUM_THREADS`, `OMP_NUM_THREADS` and `MKL_NUM_THREADS` all 1.
- **Data and artifacts**: the frozen derived CSV (SHA-256 `75a5fe87a58f4cfde777d914d674362b5148854a3c7064d8c686c0e25c3a047e`), the frozen Linux reference artifacts and the local macOS re-run artifacts (see also `expected/reverification_macos.json`).
- **Tool**: `tools/cases/diagnose_auc_pairs.py` (new in this repository; analysis only, never fits a model and is not part of training); unit tests in `tests/test_auc_rank_contribution.py`.

## 3. Linux experiment summary

### 3.1 Fold-1 probe at fixed C=1 (5 fits)

| Run | Iterations | Stop condition | Gradient ∞-norm | AUC difference vs baseline | Max probability difference | Hard predictions changed |
| --- | --- | --- | --- | --- | --- | --- |
| baseline | 443 | projected gradient ≤ gtol | 9.72e-9 | 0 | 1.11e-16 | 0 |
| repeat | 443 | projected gradient ≤ gtol | 9.72e-9 | 0 | 1.11e-16 | 0 |
| inputs +1 ulp | 422 | projected gradient ≤ gtol | 8.43e-9 | −2.0305393111375025e-7 | 7.116e-5 | 0 |
| tol=1e-11 | 454 | relative function reduction | 6.20e-9 | 0 | 6.913e-6 | 0 |
| tol=1e-11 and ftol=1e-16 | 531 | relative function reduction | 1.18e-9 | 0 | 1.457e-5 | 0 |

- The perturbation moved all 82,080 standardized values one ulp toward +infinity (maximum change 3.55e-15); exactly one strict ranking reversal appeared in class 5. The weighted OVR single-pair unit is `1/(19×120×2160) = 2.0305393112410655e-7`, matching that AUC change.
- Both tightened-tolerance runs stopped on the relative-function criterion and never reached the tighter gradient condition; their AUC equals the baseline while their probabilities are not bitwise identical. These are diagnostic observations, **not a fix recommendation**.
- The frozen four-fold `n_iter` values are 443/449/451/439, far below the 2000-iteration cap.

### 3.2 Four-fold OpenBLAS kernel contrast (20 fits)

- Inputs: the four standardized train/test matrices materialized from the original pipeline; per-fold imputer statistics and scaler mean/variance/scale equal the frozen `fit_audit` exactly. The actual kernels were verified with threadpoolctl (default SkylakeX, Haswell, Sandybridge), single-threaded.
- The two default-kernel runs produced identical coefficients, intercepts and probability arrays.
- Changing only the kernel changed fitted parameters and probabilities, with hard predictions unchanged:
  - Haswell max probability differences across folds 1–4: 1.01e-5, 7.49e-6, 2.28e-6, 4.87e-6; Sandybridge: 4.52e-5, 7.64e-6, 2.57e-6, 2.15e-6.
  - Fold 2 AUC increased by 2.030539311e-7 under both Haswell and Sandybridge; the other folds' AUC did not change.
  - The exact per-pair count on fold 2 was class 13, one strict reversal, no ties, under both kernels; the rank-reconstructed AUC difference matches the reported value within floating-point rounding.
- Putting every fitted parameter back on the default kernel and recomputing with a common prediction kernel kept all AUC values unchanged (probability recomputation difference ≤3.44e-15) — the AUC change in this contrast comes from **fitted parameters**, not from prediction-stage matrix multiplication alone.
- An independent formula for the L2-penalized multinomial logistic mean negative log-likelihood and gradient matched the captured solver output (per-fold values in the archive).
- The kernel contrast did not reproduce a fold-1 AUC change (fold-1 probabilities changed, but no ranking changed).

## 4. Local Mac checks (2026-10-02)

### 4.1 Inputs and identity

The derived CSV hash matches the frozen value; the four-fold membership is identical to the frozen `fold_membership.json`; the selection trace is identical and every selected candidate is `logistic_regression, C=1.0`; both `predictions_with_probabilities.csv` tables have 9,120 rows aligned on `row_index`/`fold`/`observed` with identical probability-column order.

### 4.2 Pairwise ranking analysis for folds 1 and 2

`tools/cases/diagnose_auc_pairs.py` compared the frozen Linux probabilities with the local Mac probabilities:

| Fold | Class | Changed pairs | Strict reversals | New ties | Broken ties | Net concordant pairs | Contribution | Measured AUC difference |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 6 | 1 | 1 | 0 | 0 | +1 | 2.0305393112410655e-7 | 2.0305393111375025e-7 |
| 2 | 13 | 1 | 1 | 0 | 0 | +1 | 2.0305393112410655e-7 | 2.0305393111375025e-7 |

The net contribution equals the absolute contribution in both folds (no cancellation across classes); the reconstructed contribution differs from the measured AUC difference by about 1.04e-17 (floating-point rounding). The repository's earlier record lists fold 2 as 2.030539310e-7 (last-digit accumulation order), also within rounding.

Concrete pairs (probabilities are that class's OVR probability; segment IDs allow relinking):

- **Fold 1, class 6**: positive `a06_p4_s34` (row 2613) vs negative `a18_p8_s25` (row 8604). Frozen margin −3.709e-7 (negative ranked higher) → Mac margin +2.490e-7; the two samples' class probabilities changed by +2.77e-7 and −3.43e-7.
- **Fold 2, class 13**: positive `a13_p7_s36` (row 6155) vs negative `a17_p3_s25` (row 7824). Frozen margin −2.122e-9 → Mac +4.936e-9; probability changes +8.33e-9 and +1.27e-9 (probability level about 0.00207).

### 4.3 Preprocessing, backend and optimizer exit information

- Reconstructed per-fold imputer/scaler states versus the frozen `fit_audit`: folds 1 and 2 exactly equal; fold 3 variance differs by 8.88e-16 and fold 4 mean by 3.33e-16 (summation-order level).
- Per-fold coefficient/intercept maximum absolute differences versus the frozen reference: fold 1 3.14e-5/6.73e-5, fold 2 2.23e-5/5.97e-5, fold 3 2.31e-5/8.78e-5, fold 4 1.99e-5/6.00e-5.
- This machine's NumPy uses **Apple Accelerate** for BLAS/LAPACK (not OpenBLAS); threadpoolctl reports only the OpenMP pool with 1 thread (that backend does not expose a BLAS pool to threadpoolctl).
- Independent fixed-C=1 diagnostic refits (no production code changed): all four folds stop on "NORM OF PROJECTED GRADIENT <= PGTOL", `n_iter` 436/436/435/442 (Linux: 443/449/451/439), gradient ∞-norm 9.08–9.84e-9; probabilities match the Mac out-of-fold table to 1.11e-16 and hard predictions do not change.

## 5. Confirmed and unconfirmed

**Confirmed (within the recorded scope of this case)**

- Extremely small input changes (one ulp) or changing only the OpenBLAS CPU kernel dispatch are enough to change the optimization path and stopping position, producing probability and ranking-metric changes of the recorded magnitude while hard predictions and headline label metrics stay unchanged.
- The two differing Mac folds also decompose exactly into one strict ranking reversal each (fold 1 class 6, fold 2 class 13), with no ties and no cancellation; fold 2 matches the Linux kernel contrast's class 13.
- Mac and Linux differ in numerical backend (Accelerate vs OpenBLAS) while the optimizer stops on the same criterion (projected gradient), so the difference is not caused by a different stopping criterion.

**Not confirmed**

- Which concrete library, instruction path or preprocessing step caused the original Mac difference; this appendix offers a candidate mechanism, not a unique cause.
- The fold-1 change was not reproduced by the Linux kernel contrast and cannot be claimed as explained.
- No "the Mac was fully simulated" and no "complete numerical equivalence"; unifying seeds or tightening `tol` does not guarantee bitwise agreement either — the `tol`/`ftol` diagnostics here are the counter-example.

## 6. Minimal evidence needed to close the root cause

- The saved four-fold standardized train/test matrices from the Linux side (or replayable imputer/scaler states on the same row numbers) so both platforms can fit on **byte-identical** inputs; the package retained only their hashes (`input_checks.json`).
- Alternatively, a Mac run equivalent to the Linux kernel contrast (same matrices, same parameters, per-fold exit information) for two-way comparison.
- Until that evidence exists, widening the experiments further is not recommended; the current results are sufficient to record a reproducible numerical-path sensitivity.

## 7. Evidence and tool entry points

- Local archive (Git-ignored; contains the original Linux package, every local diagnostic artifact and per-file hashes): `docs/internal/completed/reports/2026-10-02-dsa-mac-numerical-diagnostics/`.
- Tool and tests: `tools/cases/diagnose_auc_pairs.py`, `tests/test_auc_rank_contribution.py` (no change, single strict flip, tie creation/resolution, mutual cancellation, explicit class weights, row/column misalignment rejection; all small, none runs a full fit).
- Reproduction command (repository root):

```bash
uv run python -m tools.cases.diagnose_auc_pairs \
  --baseline <frozen predictions_with_probabilities.csv> \
  --alternative <re-run predictions_with_probabilities.csv> \
  --fold 2 --segments <CSV with row_index and segment_id> \
  --output pair_diagnostics_fold2.json
```

## 8. References

1. scikit-learn 1.8.0 `sklearn/linear_model/_logistic.py` (L-BFGS stopping conditions and parameters): <https://github.com/scikit-learn/scikit-learn/blob/1.8.0/sklearn/linear_model/_logistic.py>
2. SciPy `minimize(method='L-BFGS-B')` documentation (gtol/ftol semantics): <https://docs.scipy.org/doc/scipy/reference/optimize.minimize-lbfgsb.html>
3. Repository records: `examples/public/dsa_group_nested_v1/expected/reverification_macos.json` (cross-platform) and `examples/public/dsa_group_nested_v1/expected/reverification_uv_lock.json` (official locked environment)
