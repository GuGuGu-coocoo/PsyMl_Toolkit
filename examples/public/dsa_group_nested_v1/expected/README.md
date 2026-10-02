# Frozen expectations — `dsa_group_nested_v1`

These files pin the values recorded by the original frozen case run (UCI Daily
and Sports Activities, PsyML commit `de33abfe52ccfee67f461a850edd00a14d2fbfaa`,
Linux, case-parity environment in `environment.json`). They are the reference
side of the acceptance checks; the quick test suite never downloads data or
fits the 9,120-row case.

| File | Contents |
| --- | --- |
| `case_summary.json` | Data/protocol/source hashes, structure, baseline metrics, tolerances, acceptance counts and scope limits |
| `fold_membership_expected.json` | Expected outer and inner participant membership and the recorded inner-selection trace |
| `golden_hashes.json` | SHA-256 of the frozen case artifacts retained outside this repository, for byte-level golden comparison |
| `environment.json` | Case-parity environment of the frozen run; not the official locked environment |
| `reverification_macos.json` | Record of one later re-run on macOS (when present); additive evidence that never replaces the frozen baseline |
| `reverification_uv_lock.json` | Record of the full case re-run inside the repository's official `uv.lock` environment (2026-10-02); additive evidence that never replaces the frozen baseline |

## How a rerun uses these values

1. `tools/cases/prepare_dsa.py` must reproduce
   `hashes.derived_csv_sha256` exactly from the official archive.
2. `tools/cases/reference_dsa.py`, `tools/cases/observe_psyml_dsa.py` and the
   CLI result are compared by `tools/cases/compare_dsa.py` under the tolerances
   in `case_summary.json`; all checks must pass.
3. `tools/cases/compare_dsa.py --golden <frozen-primary-dir>` adds exact
   out-of-fold comparison against the frozen artifacts when they are available
   locally. `golden_hashes.json` identifies those files.
4. `tools/cases/check_dsa_controls.py` reproduces the fold-1 perturbations and
   the within-subject shuffled-label canary, including the recorded
   `shuffled_labels_csv_sha256`.

## Provenance and limits

- The frozen baseline was recorded before this directory existed; it was not
  re-derived from the repository tests. `case_summary.json` documents that
  provenance explicitly.
- Hashes identify files; they are not signatures and do not establish trust.
- The byte-identical [prepared input CSV](../../downloads/README.md) is now public.
  The full 9,120-row out-of-fold prediction tables remain outside this repository,
  which ignores `**/results/`. Only small reference records live in this directory.
- A failure at the same environment and pinned code must be investigated; a
  difference on another platform or dependency set must be reported as a new
  result, never used to overwrite these values or relax the tolerances. The
  official-lock re-run reproduced the macOS re-run exactly and kept the same
  platform-associated difference against the frozen baseline; both records are
  additive.
