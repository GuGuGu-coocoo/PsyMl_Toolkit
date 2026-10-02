# Public acceptance examples

Start with the two documented validation cases:

- [DSA activity classification](../../docs/VALIDATION_DSA_EN.md): [中文](../../docs/VALIDATION_DSA_ZH.md) · [Français](../../docs/VALIDATION_DSA_FR.md)
- [California housing regression](../../docs/CALIFORNIA_VALIDATION_EN.md): [中文](../../docs/CALIFORNIA_VALIDATION_ZH.md) · [Français](../../docs/CALIFORNIA_VALIDATION_FR.md)

Both have [prepared CSV downloads, official sources and conversion scripts](downloads/README.md). The GUI route uses CSV + JSON and needs no code. Only readers who want to rebuild the data or run an independent comparison need the commands below. Application-version limits are stated in the main README.

Iris and Concrete examples below are also from UCI under CC BY 4.0. Their fetch tool checks pinned source hashes and keeps generated CSVs local. DSA and California's explicitly published prepared copies are in `downloads/`; locally generated data in `data/` remain Git-ignored.

## Classification — Iris

- Source: R. A. Fisher, *Iris*, UCI Machine Learning Repository.
- DOI: <https://doi.org/10.24432/C56C76>
- License: <https://creativecommons.org/licenses/by/4.0/>
- UCI page: <https://archive.ics.uci.edu/dataset/53/iris>

## Regression — Concrete Compressive Strength

- Source: I-Cheng Yeh, *Concrete Compressive Strength*, UCI Machine Learning Repository.
- DOI: <https://doi.org/10.24432/C5PK67>
- License: <https://creativecommons.org/licenses/by/4.0/>
- UCI page: <https://archive.ics.uci.edu/dataset/165/concrete+compressive+strength>

## Classification — Daily and Sports Activities (participant-grouped validation case)

- Source: Billur Barshan and Kerem Altun, *Daily and Sports Activities*, UCI Machine Learning Repository.
- DOI: <https://doi.org/10.24432/C5C59F>
- License: <https://creativecommons.org/licenses/by/4.0/>
- UCI page: <https://archive.ics.uci.edu/dataset/256/daily+and+sports+activities>

This case keeps participants grouped, uses only per-segment torso
acceleration/angular-rate statistics, and compares the frozen nested workflow
against an independent scikit-learn recomputation. It is an optional,
minutes-long verification rather than part of the quick test suite; protocol,
expected values and limits are in
[dsa_group_nested_v1](dsa_group_nested_v1/README.md) and
[VALIDATION_DSA_EN.md](../../docs/VALIDATION_DSA_EN.md).

```bash
# Optional: rebuild the derived CSV from the official ZIP (strict hash/shape checks)
uv run python tools/cases/prepare_dsa.py \
  --archive /path/to/daily_and_sports_activities.zip \
  --output-dir examples/public/data
# Primary result (fresh output directory required; see the case README for the
# reference, observation, comparison and control commands)
uv run psyml run --config examples/public/configs/dsa_group_nested_v1.json --events
```

## Reproduce

From the repository root:

```bash
uv run python tools/fetch_public_examples.py
uv run psyml run --config examples/public/configs/iris_classification.json
uv run psyml run --config examples/public/configs/concrete_regression.json
```

The first command performs no silent substitution: a changed upstream archive fails its checksum before extraction. The resulting data remain local under `examples/public/data/`; analysis results are written under `examples/public/results/`.
