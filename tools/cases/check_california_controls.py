#!/usr/bin/env python3
"""Offline comparator fault injections and tiny reference-pipeline controls.

These are software-contract controls on synthetic data. They do not rerun the
20,640-row acceptance case, observe production internals, or establish a real-
data leakage/permutation test. All output directories must be new.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

if __package__:
    from .compare_california import Audit
    from .reference_california import FEATURES, pipeline, write_json
else:
    from compare_california import Audit
    from reference_california import FEATURES, pipeline, write_json


def run_controls():
    checks = []

    def record(name, success):
        checks.append({"check": name, "passed": bool(success)})

    required, keys, exact = ["row_index", "fold", "predicted"], ["row_index"], ["row_index", "fold"]
    base = pd.DataFrame({"row_index": [0, 1], "fold": [1, 2], "predicted": [1.0, 2.0]})
    altered = {}
    altered["missing_required_both_sides"] = (
        base.drop(columns="predicted"),
        base.drop(columns="predicted"),
    )
    altered["one_sided_nonfinite"] = (base.assign(predicted=[1.0, np.nan]), base)
    altered["both_sides_nonfinite"] = (base.assign(predicted=np.inf), base.assign(predicted=np.inf))
    altered["duplicate_row_keys"] = (base.assign(row_index=[0, 0]), base)
    altered["wrong_outer_fold"] = (base.assign(fold=[2, 1]), base)
    altered["extra_column"] = (base.assign(unexpected=0), base)
    altered["outside_frozen_tolerance"] = (base.assign(predicted=[1.0, 2.001]), base)
    for name, (actual, expected) in altered.items():
        audit = Audit()
        audit.frame(name, actual, expected, required, keys, exact)
        record(name + "_rejected", any(not c["passed"] for c in audit.checks))
    audit = Audit()
    audit.frame("identical", base, base.copy(), required, keys, exact)
    record("unaltered_table_accepted", all(c["passed"] for c in audit.checks))
    audit = Audit()
    audit.close("roundoff", [1.0 + 1e-12], [1.0])
    record("within_frozen_tolerance_accepted", audit.checks[-1]["passed"])
    audit = Audit()
    audit.equal("typed_verbose", {"verbose": 0.0}, {"verbose": 0})
    record("invalid_verbose_float_rejected", not audit.checks[-1]["passed"])

    rng = np.random.default_rng(20261002)
    frame = pd.DataFrame(rng.normal(size=(36, len(FEATURES))), columns=FEATURES)
    target = pd.Series(rng.normal(size=36))
    frame.loc[0, FEATURES[0]] = np.nan
    train = frame.iloc[:24]
    model = pipeline("ridge", {"alpha": 1.0, "solver": "svd"})
    model.fit(train, target.iloc[:24])
    numeric = model.named_steps["preprocess"].named_transformers_["numeric"]
    medians = np.nanmedian(train, axis=0)
    imputed = np.where(np.isnan(train), medians, train)
    record(
        "reference_imputer_uses_training_only",
        np.array_equal(numeric.named_steps["impute"].statistics_, medians),
    )
    record(
        "reference_scaler_uses_imputed_training_only",
        np.allclose(
            numeric.named_steps["scale"].mean_, imputed.mean(axis=0), atol=1e-10, rtol=1e-10
        ),
    )
    before = numeric.named_steps["scale"].mean_.copy()
    model.predict(frame.iloc[24:] + 1e6)
    record(
        "held_out_feature_perturbation_does_not_mutate_fitted_reference",
        np.array_equal(before, numeric.named_steps["scale"].mean_),
    )
    return {
        "passed": all(c["passed"] for c in checks),
        "n_checks": len(checks),
        "checks": checks,
        "scope": "Synthetic comparator and independent-reference controls only; no production instrumentation or real-data leakage test.",
        "real_data_fits": 0,
        "synthetic_reference_fits": 1,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=False)
    report = run_controls()
    write_json(args.output / "controls.json", report)
    print(
        f"{sum(c['passed'] for c in report['checks'])}/{report['n_checks']} synthetic contract controls passed"
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
