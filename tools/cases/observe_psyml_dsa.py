"""Observation-only supplemental run of the DSA case through PsyML.

Original PsyML source files are never edited. Construction, splitting, fitting
and scoring stay inside PsyML; this module only wraps existing calls to record
what the production code actually did. The uninstrumented CLI run is the
primary result and must agree with this run.

The adapter is not an independent reference implementation. It is used to
complete the fold-membership and per-fit audit records that the production
export does not include.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import warnings
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

if __package__ in {None, ""}:  # direct script execution
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from psyml import runner
from psyml.protocol import load_config
from tools.cases import dsa_case


def _split_key(features: pd.DataFrame) -> bytes:
    return np.asarray(features.index, dtype=np.int64).tobytes()


def observe(config_path: str | Path, output_dir: str | Path) -> dict[str, Any]:
    """Run the production workflow while recording members, fits and warnings."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=False)
    config = replace(load_config(config_path), output_dir=output / "run")
    records: list[dict[str, Any]] = []
    splits: dict[str, Any] = {}
    meta: dict[int, tuple[str, dict[str, Any]]] = {}
    retained: list[Pipeline] = []
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        original_build = runner._build_pipeline
        original_split = runner.make_validation_splits
        original_fit = Pipeline.fit

        def build(
            config,
            training_features,
            model_name,
            model_params,
            training_target=None,
            training_groups=None,
        ):
            model = original_build(
                config,
                training_features,
                model_name,
                model_params,
                training_target,
                training_groups,
            )
            meta[id(model)] = (model_name, dict(model_params))
            retained.append(model)
            return model

        def split(
            features,
            target,
            task,
            strategy,
            n_splits,
            test_size,
            random_seed,
            groups=None,
        ):
            answer = original_split(
                features, target, task, strategy, n_splits, test_size, random_seed, groups
            )
            key = (
                f"{strategy}|{n_splits}|{random_seed}|"
                + hashlib.sha256(_split_key(features)).hexdigest()
            )
            entry: dict[str, Any] = {
                "strategy": strategy,
                "n_splits": n_splits,
                "random_seed": random_seed,
                "input_rows": features.index.tolist(),
                "folds": [],
            }
            for train, test in answer:
                entry["folds"].append(
                    {
                        "train_rows": features.iloc[train].index.tolist(),
                        "test_rows": features.iloc[test].index.tolist(),
                        "train_groups": sorted(groups.iloc[train].unique().tolist()),
                        "test_groups": sorted(groups.iloc[test].unique().tolist()),
                    }
                )
            if key in splits and splits[key] != entry:
                raise RuntimeError(f"Splitter re-query produced different results for {key}")
            splits[key] = entry
            return answer

        def fit(self, X, y=None, **params):
            answer = original_fit(self, X, y, **params)
            if id(self) in meta:
                family, overrides = meta[id(self)]
                numeric = self.named_steps["preprocess"].named_transformers_["numeric"]
                estimator = self.named_steps["model"]
                records.append(
                    {
                        "family": family,
                        "overrides": overrides,
                        "train_rows": X.index.tolist(),
                        "feature_names": X.columns.tolist(),
                        "imputer_statistics": numeric.named_steps["impute"].statistics_.tolist(),
                        "scaler_mean": numeric.named_steps["scale"].mean_.tolist(),
                        "scaler_var": numeric.named_steps["scale"].var_.tolist(),
                        "scaler_scale": numeric.named_steps["scale"].scale_.tolist(),
                        "scaler_n_samples_seen": int(numeric.named_steps["scale"].n_samples_seen_),
                        "classes": estimator.classes_.tolist(),
                        "effective_parameters": estimator.get_params(deep=False),
                        "coef": getattr(estimator, "coef_", np.array([])).tolist(),
                        "intercept": getattr(estimator, "intercept_", np.array([])).tolist(),
                        "n_iter": getattr(estimator, "n_iter_", np.array([])).tolist(),
                    }
                )
            return answer

        runner._build_pipeline = build
        runner.make_validation_splits = split
        Pipeline.fit = fit
        try:
            result = runner.run_experiment(config)
        finally:
            runner._build_pipeline = original_build
            runner.make_validation_splits = original_split
            Pipeline.fit = original_fit

    frame = pd.read_csv(config.input_path)
    features = frame[config.feature_columns]
    selected: list[pd.DataFrame] = []
    for fold, table in result.predictions.groupby("fold", sort=True):
        family = table["model"].iloc[0]
        test_rows = table["row_index"].tolist()
        train_rows = [index for index in features.index if index not in set(test_rows)]
        matching = [
            model
            for model, record in zip(retained, records)
            if record["train_rows"] == train_rows and record["family"] == family
        ]
        if len(matching) != 1:
            raise RuntimeError(f"fold {fold}: expected one fitted winner model, found {len(matching)}")
        model = matching[0]
        probabilities = model.predict_proba(features.loc[test_rows])
        output_table = table.copy()
        for column, label in enumerate(model.classes_):
            output_table[f"probability_{label}"] = probabilities[:, column]
        selected.append(output_table)

    pd.concat(selected, ignore_index=True).to_csv(
        output / "observed_oof_probabilities.csv", index=False
    )
    dsa_case.write_json(output / "fit_audit.json", records)
    dsa_case.write_json(output / "fold_membership.json", splits)
    dsa_case.write_json(
        output / "warnings.json",
        [{"category": item.category.__name__, "message": str(item.message)} for item in caught],
    )
    return {
        "fits": len(records),
        "unique_split_calls": len(splits),
        "metrics": result.metrics,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New or empty directory")
    args = parser.parse_args(argv)
    print(json.dumps(observe(args.config, args.output), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
