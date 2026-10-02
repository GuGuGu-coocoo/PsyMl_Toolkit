# Historical identities and bounded evidence

These files describe the original California Housing case recorded on
2026-10-02, PsyML 0.3.0, commit `a145e07c4b6a4135781725c1390f68192ab8e92c`.
They are **historical records**, not newly generated full-data test results.

- `PROTOCOL_FROZEN.json`: byte-identical protocol recorded before the first fit.
- `california_config.json`: byte-identical original v1 configuration.
- `PROTOCOL_AMENDMENT_v1_1.json` and `california_config_v1_1.json`: byte-identical
  compatibility amendment and amended config. Only RF `verbose` was omitted;
  typed effective defaults were verified before fitting. No tolerance change.
- `provenance.json` and `figshare_metadata.json`: original conversion provenance
  and public source/deposit metadata; attribution is in `../ATTRIBUTION.md`.
- `historical_summary.json`: a compact, explicitly labelled excerpt of original
  results. Original v1: **195/227**, 32 failed. v1.1 final saved/reimported GUI
  configuration: **270/270**, passed only within the observable export scope.
  It retains numeric maxima, failed identifiers, reference counts and unobserved
  internals. It does not substitute for the full model/CSV evidence.
- `historical_*metrics*.csv`: unchanged small reference metric tables.
- `historical_verbose_reproduction.json`: original three-row diagnostic showing
  integer `0` accepted and floating `0.0` rejected; not a new software result.
- `historical_hashes.json`: original case-relative names, bytes and SHA-256
  for relevant artifacts and the separately preserved complete case ZIP.
  The [prepared input CSV](../../downloads/README.md) is now public. The full case
  ZIP, models, audit traces and screenshots are not in Git. Hashes prove
  identity when the corresponding original files are available, not public
  availability of those large artifacts.
- `integration_verification.json`: separately dated repository-tool checks
  against retained historical files; no new GUI actions or California fits.

The parent-directory configurations change only input/output paths. Their bytes
therefore deliberately differ from the originals. `california_case.py` verifies
both historical byte identity and relocated **type-sensitive scientific**
identity. Historical hashes must never be recomputed against relocated configs
and silently relabelled as the old hashes.

To establish a new validation result, rerun the commands in the parent README,
record actual dependency/source hashes and retain a new output directory.
`atol=rtol=1e-10` and all nonfinite/type/schema failures remain fixed. A different
version, platform or GUI build must be reported separately. Passing synthetic
contracts or comparing old exports cannot certify a new GUI build.
