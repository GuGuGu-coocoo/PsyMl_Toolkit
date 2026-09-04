# Public acceptance examples

These examples use two datasets distributed by the UCI Machine Learning Repository under CC BY 4.0. The datasets are downloaded from UCI and verified against pinned SHA-256 hashes; generated local CSV files are ignored by Git and are not redistributed by this repository.

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

## Reproduce

From the repository root:

```bash
uv run python tools/fetch_public_examples.py
uv run psyml run --config examples/public/configs/iris_classification.json
uv run psyml run --config examples/public/configs/concrete_regression.json
```

The first command performs no silent substitution: a changed upstream archive fails its checksum before extraction. The resulting data remain local under `examples/public/data/`; analysis results are written under `examples/public/results/`.
