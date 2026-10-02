#!/usr/bin/env python3
"""Independent public-sklearn reconstruction of the frozen California GUI case.

No PsyML imports or runner helpers. The same sklearn estimators/splitters are
shared, so this audits workflow conformance, not the sklearn solvers themselves.
All output directories must be new. Frozen scientific identities are mandatory;
input/output paths may be relocated without changing historical hashes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import scipy
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, ParameterGrid
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_info, threadpool_limits

FEATURES = [
    "MedInc",
    "HouseAge",
    "AveRooms",
    "AveBedrms",
    "Population",
    "AveOccup",
    "Latitude",
    "Longitude",
]
FAMILIES = ["dummy", "ridge", "random_forest"]
TARGET = "MedHouseVal"
SEED = 20261002
DATA_HASH = "157b6c0d3acd6d93a50c411d0cd4130d8c719ce5eb17b61f1c45300f2af6fc85"
ATOL = RTOL = 1e-10

if __package__:
    from .california_case import (
        AMENDED_CONFIG_SHA256,
        FROZEN_CONFIG_SHA256,
        config_identity,
        science_sha256,
    )
else:
    from california_case import (
        AMENDED_CONFIG_SHA256,
        FROZEN_CONFIG_SHA256,
        config_identity,
        science_sha256,
    )


def jsonable(value):
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [jsonable(v) for v in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    return value


def write_json(path, value):
    Path(path).write_text(
        json.dumps(jsonable(value), indent=2, sort_keys=True, allow_nan=False) + "\n"
    )


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rowhash(rows):
    return hashlib.sha256(np.asarray(rows, dtype="<i8").tobytes()).hexdigest()


def estimator(family, overrides):
    if family == "dummy":
        return DummyRegressor(**overrides)
    if family == "ridge":
        return Ridge(**{"random_state": SEED, **overrides})
    if family == "random_forest":
        return RandomForestRegressor(**{"random_state": SEED, **overrides})
    raise ValueError(family)


def pipeline(family, overrides):
    numeric = Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())])
    preprocess = ColumnTransformer([("numeric", numeric, FEATURES)], remainder="drop")
    return Pipeline([("preprocess", preprocess), ("model", estimator(family, overrides))])


def metrics(y, prediction):
    return {
        "r2": float(r2_score(y, prediction)),
        "mae": float(mean_absolute_error(y, prediction)),
        "rmse": float(math.sqrt(mean_squared_error(y, prediction))),
    }


def direct_metrics(y, prediction):
    a, b = np.asarray(y, dtype=np.float64), np.asarray(prediction, dtype=np.float64)
    residual = a - b
    return {
        "r2": float(1.0 - np.sum(residual**2) / np.sum((a - np.mean(a)) ** 2)),
        "mae": float(np.mean(np.abs(residual))),
        "rmse": float(np.sqrt(np.mean(residual**2))),
    }


def validate_config(config):
    config_identity(config)
    required = {
        "task": "regression",
        "target_column": TARGET,
        "feature_columns": FEATURES,
        "model_names": FAMILIES,
        "random_seed": SEED,
        "n_splits": 5,
        "inner_splits": 3,
        "missing_strategy": "median",
        "scaling": "standard",
        "selection_metric": "rmse",
        "tuning_mode": "custom",
        "selection_protocol": "nested_family_v1",
        "save_best_model": True,
        "permutation_importance": False,
    }
    for key, value in required.items():
        if config.get(key) != value:
            raise ValueError(f"Frozen protocol mismatch: {key}: {config.get(key)!r} != {value!r}")
    if config.get("group_column") is not None:
        raise ValueError("Frozen row-KFold case must have no grouping column")
    if config.get("validation_strategies", [config.get("validation_strategy")]) != ["k_fold"]:
        raise ValueError("Frozen outer validation must be k_fold only")
    if config.get("primary_validation") not in ("k_fold", "first_selected"):
        raise ValueError("Frozen primary validation must be k_fold")
    candidates = {
        family: list(ParameterGrid(config["parameter_grids"][family])) for family in FAMILIES
    }
    if [len(candidates[f]) for f in FAMILIES] != [1, 3, 1]:
        raise ValueError("Frozen candidate counts must be 1/3/1")
    if any(len(items) > config["max_candidates"] for items in candidates.values()):
        raise ValueError("Frozen case prohibits candidate sampling")
    expected = {
        "dummy": [DummyRegressor(strategy="mean").get_params(deep=False)],
        "ridge": [
            Ridge(alpha=a, solver="svd", fit_intercept=True, random_state=SEED).get_params(
                deep=False
            )
            for a in [0.1, 1.0, 10.0]
        ],
        "random_forest": [
            RandomForestRegressor(
                n_estimators=100, max_depth=10, min_samples_leaf=3, n_jobs=1, random_state=SEED
            ).get_params(deep=False)
        ],
    }
    for family in FAMILIES:
        actual = [estimator(family, p).get_params(deep=False) for p in candidates[family]]
        if json.dumps(actual, sort_keys=True) != json.dumps(expected[family], sort_keys=True):
            raise ValueError(f"Frozen effective parameters mismatch for {family}: {actual!r}")
    return candidates


def first_minimum(previous, candidate):
    """Strict minimum, finite scores only; ties preserve configuration order."""
    if not math.isfinite(candidate["score"]):
        raise ValueError("Nonfinite candidate score")
    return candidate if previous is None or candidate["score"] < previous["score"] else previous


def fitted_state(model, x, family, params, *, phase, outer_fold, candidate, inner_fold=0):
    numeric = model.named_steps["preprocess"].named_transformers_["numeric"]
    scale = numeric.named_steps["scale"]
    est = model.named_steps["model"]
    return {
        "family": family,
        "overrides": params,
        "phase": phase,
        "outer_fold": outer_fold,
        "candidate": candidate,
        "inner_fold": inner_fold,
        "train_rows": x.index.tolist(),
        "train_rows_sha256": rowhash(x.index),
        "feature_names": list(x.columns),
        "imputer_statistics": numeric.named_steps["impute"].statistics_.tolist(),
        "scaler_mean": scale.mean_.tolist(),
        "scaler_var": scale.var_.tolist(),
        "scaler_scale": scale.scale_.tolist(),
        "scaler_n_samples_seen": int(scale.n_samples_seen_),
        "effective_parameters": est.get_params(deep=False),
        "coef": jsonable(getattr(est, "coef_", [])),
        "intercept": jsonable(getattr(est, "intercept_", [])),
        "constant": jsonable(getattr(est, "constant_", [])),
    }


def run(args):
    config_path = args.config.resolve()
    if args.approved_config_sha256 and sha256(config_path) != args.approved_config_sha256:
        raise ValueError("Config no longer matches its approved pre-run freeze hash")
    config = json.loads(config_path.read_text())
    if sklearn.__version__ != "1.8.0" and not args.allow_environment_change:
        raise ValueError(
            f"Frozen sklearn is 1.8.0; found {sklearn.__version__}. Use --allow-environment-change for a separately recorded revalidation, never to replace historical results."
        )
    variant = config_identity(config)
    candidates = validate_config(config)
    data_path = Path(config["input_path"])
    if sha256(data_path) != DATA_HASH:
        raise ValueError("Prepared CSV hash does not match the predeclared dataset")
    frame = pd.read_csv(data_path)  # pandas default parser, exactly as frozen
    if list(frame.columns) != FEATURES + [TARGET] or frame.shape != (20640, 9):
        raise ValueError("Prepared data schema or row count mismatch")
    if not np.isfinite(frame.to_numpy()).all():
        raise ValueError("Prepared California case expects finite data with zero missing values")
    x, y = frame[FEATURES], frame[TARGET]
    fixture = pd.read_csv(args.prediction_fixture)
    if fixture.shape != (10, 9) or list(fixture.columns) != ["sample_id"] + list(
        reversed(FEATURES)
    ):
        raise ValueError(
            "Prediction fixture must be ten rows, sample ID, and reversed feature order"
        )
    if not np.array_equal(fixture[FEATURES].to_numpy(), x.iloc[:10].to_numpy()):
        raise ValueError(
            "Prediction fixture feature values must equal first ten prepared rows after parsing"
        )
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    started = datetime.now(timezone.utc).isoformat()
    start = time.monotonic()
    write_json(
        output / "environment.json",
        {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
            "sklearn": sklearn.__version__,
            "joblib": joblib.__version__,
            "threadpool_info": threadpool_info(),
            "thread_variables": {
                k: os.environ.get(k)
                for k in [
                    "OPENBLAS_NUM_THREADS",
                    "OMP_NUM_THREADS",
                    "MKL_NUM_THREADS",
                    "NUMEXPR_NUM_THREADS",
                ]
            },
            "python_executable": sys.executable,
            "reference_script_sha256": sha256(__file__),
            "config_sha256": sha256(config_path),
            "config_science_sha256": science_sha256(config),
            "historical_config_sha256": FROZEN_CONFIG_SHA256
            if variant == "v1"
            else AMENDED_CONFIG_SHA256,
            "config_variant": variant,
            "environment_change_explicit": bool(args.allow_environment_change),
            "csv_sha256": sha256(data_path),
            "prediction_fixture_sha256": sha256(args.prediction_fixture),
            "started_utc": started,
        },
    )
    write_json(
        output / "effective_candidates.json",
        {f: [estimator(f, p).get_params(deep=False) for p in candidates[f]] for f in FAMILIES},
    )
    audit, search, inner_scores, selected, family_predictions, family_folds = [], [], [], [], [], []
    memberships, scopes = {}, {}

    def scope(rows):
        key = rowhash(rows)
        if key not in scopes:
            values = x.loc[rows].to_numpy(dtype=np.float64)
            medians = np.median(values, axis=0)
            means = np.mean(values, axis=0)
            variance = np.var(values, axis=0, ddof=0)
            scopes[key] = {
                "train_rows": list(rows),
                "n_rows": len(rows),
                "median": medians.tolist(),
                "mean": means.tolist(),
                "var": variance.tolist(),
                "scale": np.where(variance == 0, 1.0, np.sqrt(variance)).tolist(),
            }
        return key

    def fit(family, params, rows, phase, fold, candidate, inner=0):
        model = pipeline(family, params)
        model.fit(x.loc[rows], y.loc[rows])
        state = fitted_state(
            model,
            x.loc[rows],
            family,
            params,
            phase=phase,
            outer_fold=fold,
            candidate=candidate,
            inner_fold=inner,
        )
        state["independent_scope_id"] = scope(rows)
        audit.append(state)
        return model

    def choose(rows, fold):
        folds = list(KFold(n_splits=3, shuffle=True, random_state=SEED + fold).split(rows))
        members = []
        for train, valid in folds:
            members.append(
                {
                    "train_rows": np.asarray(rows)[train].tolist(),
                    "test_rows": np.asarray(rows)[valid].tolist(),
                }
            )
        memberships[f"inner_{fold}"] = {
            "seed": SEED + fold,
            "input_rows": list(rows),
            "folds": members,
        }
        family_best = {}
        winner = None
        for family in FAMILIES:
            best = None
            for number, params in enumerate(candidates[family], 1):
                scores = []
                for inner, member in enumerate(members, 1):
                    model = fit(family, params, member["train_rows"], "inner", fold, number, inner)
                    prediction = model.predict(x.loc[member["test_rows"]])
                    score = float(
                        math.sqrt(mean_squared_error(y.loc[member["test_rows"]], prediction))
                    )
                    if not math.isfinite(score):
                        raise ValueError("Nonfinite inner score; never average a partial candidate")
                    scores.append(score)
                    inner_scores.append(
                        {
                            "model": family,
                            "outer_fold": fold,
                            "candidate": number,
                            "inner_fold": inner,
                            "n_train": len(member["train_rows"]),
                            "n_test": len(member["test_rows"]),
                            "rmse": score,
                        }
                    )
                row = {
                    "model": family,
                    "validation": "k_fold",
                    "outer_fold": fold,
                    "selection_scope": "final_full_data" if fold == 0 else "outer_training_fold",
                    "candidate": number,
                    "selection_metric": "rmse",
                    "score": float(np.mean(scores)),
                    "parameters": json.dumps(params, sort_keys=True),
                    "status": "completed",
                    "error": "",
                }
                search.append(row)
                best = first_minimum(best, row)
                winner = first_minimum(winner, row)
            family_best[family] = best
        selected.append(
            {
                k: winner[k]
                for k in [
                    "validation",
                    "outer_fold",
                    "selection_scope",
                    "model",
                    "parameters",
                    "score",
                ]
            }
        )
        return family_best, winner

    with warnings.catch_warnings(record=True) as caught, threadpool_limits(limits=1):
        warnings.simplefilter("always")
        outer = list(KFold(n_splits=5, shuffle=True, random_state=SEED).split(x))
        memberships["outer"] = {
            "seed": SEED,
            "input_rows": x.index.tolist(),
            "folds": [{"train_rows": a.tolist(), "test_rows": b.tolist()} for a, b in outer],
        }
        for fold, (train, test) in enumerate(outer, 1):
            best, winner = choose(train.tolist(), fold)
            for family in FAMILIES:
                params = json.loads(best[family]["parameters"])
                model = fit(
                    family, params, train.tolist(), "outer", fold, int(best[family]["candidate"])
                )
                prediction = model.predict(x.iloc[test])
                family_folds.append(
                    {
                        "fold": fold,
                        "model": family,
                        "validation": "k_fold",
                        **metrics(y.iloc[test], prediction),
                    }
                )
                family_predictions.append(
                    pd.DataFrame(
                        {
                            "row_index": test,
                            "fold": fold,
                            "observed": y.iloc[test].to_numpy(),
                            "predicted": prediction,
                            "model": family,
                        }
                    )
                )
            write_json(
                output / f"checkpoint_fold_{fold}.json",
                {
                    "completed_fold": fold,
                    "fits": len(audit),
                    "selection": selected,
                    "family_fold_metrics": family_folds,
                },
            )
            write_json(output / "fit_audit_inprogress.json", audit)
            pd.concat(family_predictions, ignore_index=True).to_csv(
                output / "family_predictions_inprogress.csv", index=False, float_format="%.17g"
            )
            print(
                json.dumps(
                    {
                        "phase": "outer_completed",
                        "fold": fold,
                        "fits": len(audit),
                        "selected_model": winner["model"],
                    }
                ),
                flush=True,
            )
        _final_best, final_winner = choose(x.index.tolist(), 0)
        final = fit(
            final_winner["model"],
            json.loads(final_winner["parameters"]),
            x.index.tolist(),
            "final",
            0,
            int(final_winner["candidate"]),
        )
        final_prediction = final.predict(x)
        fixture_prediction = final.predict(fixture)  # tests name-based ColumnTransformer selection
        joblib.dump(final, output / "final_model.joblib", compress=3)
        replay = joblib.load(output / "final_model.joblib")
        if not np.array_equal(replay.predict(x), final_prediction):
            raise ValueError("Independent saved-model replay is not exact")
        if not np.array_equal(replay.predict(fixture), fixture_prediction):
            raise ValueError("Independent reordered fixture replay is not exact")
    if len(audit) != 106 or len(inner_scores) != 90 or len(search) != 30:
        raise ValueError(f"Fit/search count wrong: {len(audit)}/{len(inner_scores)}/{len(search)}")
    families_oof = pd.concat(family_predictions, ignore_index=True)
    folds_frame = pd.DataFrame(family_folds)
    procedure = pd.concat(
        [
            families_oof[
                (families_oof.fold == r["outer_fold"]) & (families_oof.model == r["model"])
            ]
            for r in selected
            if r["outer_fold"] > 0
        ],
        ignore_index=True,
    )
    procedure_folds = pd.concat(
        [
            folds_frame[(folds_frame.fold == r["outer_fold"]) & (folds_frame.model == r["model"])]
            for r in selected
            if r["outer_fold"] > 0
        ],
        ignore_index=True,
    )
    summary_rows, pooled = [], []
    for name, table, folds_table in [("procedure", procedure, procedure_folds)] + [
        (f, families_oof[families_oof.model == f], folds_frame[folds_frame.model == f])
        for f in FAMILIES
    ]:
        if len(table) != 20640 or sorted(table.row_index.tolist()) != list(range(20640)):
            raise ValueError(f"OOF coverage incomplete for {name}")
        pooled.append(
            {"scope": name, "n_rows": len(table), **direct_metrics(table.observed, table.predicted)}
        )
        for metric in ["r2", "mae", "rmse"]:
            series = folds_table[metric]
            summary_rows.append(
                {
                    "scope": name,
                    "metric": metric,
                    "mean": float(np.mean(series)),
                    "std": float(np.std(series, ddof=0)),
                    "min": float(np.min(series)),
                    "max": float(np.max(series)),
                    "n_folds": len(series),
                }
            )
    all_summaries = pd.DataFrame(summary_rows)
    procedure_summary = all_summaries[all_summaries.scope == "procedure"].drop(columns="scope")
    tables = {
        "predictions.csv": procedure,
        "family_predictions.csv": families_oof,
        "fold_metrics.csv": procedure_folds,
        "family_fold_metrics.csv": folds_frame,
        "parameter_search.csv": pd.DataFrame(search),
        "inner_fold_scores.csv": pd.DataFrame(inner_scores),
        "selection_trace.csv": pd.DataFrame(selected),
        "metrics_summary.csv": procedure_summary,
        "all_metrics_summary.csv": all_summaries,
        "pooled_metrics.csv": pd.DataFrame(pooled),
        "metrics.csv": pd.DataFrame(
            [{r["metric"]: r["mean"] for r in summary_rows if r["scope"] == "procedure"}]
        ),
        "final_predictions.csv": pd.DataFrame(
            {"row_index": x.index, "observed": y, "predicted": final_prediction}
        ),
        "prediction_fixture_expected.csv": pd.DataFrame(
            {"sample_id": fixture.sample_id, "predicted": fixture_prediction}
        ),
    }
    for name, table in tables.items():
        table.to_csv(output / name, index=False, float_format="%.17g")
    write_json(output / "fit_audit.json", audit)
    write_json(output / "fold_membership.json", memberships)
    write_json(output / "independent_scope_statistics.json", scopes)
    write_json(output / "best_parameters.json", final.named_steps["model"].get_params(deep=False))
    write_json(
        output / "warnings.json",
        [{"category": w.category.__name__, "message": str(w.message)} for w in caught],
    )
    max_scope_difference = 0.0
    for record in audit:
        stats = scopes[record["independent_scope_id"]]
        for fitted_key, direct_key in [
            ("imputer_statistics", "median"),
            ("scaler_mean", "mean"),
            ("scaler_var", "var"),
            ("scaler_scale", "scale"),
        ]:
            a, b = np.asarray(record[fitted_key]), np.asarray(stats[direct_key])
            max_scope_difference = max(max_scope_difference, float(np.max(np.abs(a - b))))
            if not np.allclose(a, b, atol=ATOL, rtol=RTOL):
                raise ValueError(f"Independent direct scope statistics mismatch {fitted_key}")
    summary = {
        "status": "completed",
        "fit_counts": {"inner": 90, "outer_family": 15, "final": 1, "total": 106},
        "n_rows": len(frame),
        "n_features": len(FEATURES),
        "csv_sha256": sha256(data_path),
        "config_sha256": sha256(config_path),
        "config_science_sha256": science_sha256(config),
        "historical_config_sha256": FROZEN_CONFIG_SHA256
        if variant == "v1"
        else AMENDED_CONFIG_SHA256,
        "config_variant": variant,
        "environment_change_explicit": bool(args.allow_environment_change),
        "sklearn_version": sklearn.__version__,
        "selection": selected,
        "fold_mean": tables["metrics.csv"].iloc[0].to_dict(),
        "pooled_oof": pooled[0],
        "between_fold_sd_ddof0": {
            r["metric"]: r["std"] for r in summary_rows if r["scope"] == "procedure"
        },
        "scope_count": len(scopes),
        "max_absolute_direct_scope_difference": max_scope_difference,
        "warnings_count": len(caught),
        "elapsed_seconds": time.monotonic() - start,
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "tolerance": {"atol": ATOL, "rtol": RTOL},
        "limits": [
            "Random row splits do not establish spatial, temporal, or geographic external validity.",
            "Equal-fold means and pooled metrics are distinct estimands; fold SD is descriptive, not a standard error.",
            "Final full-data predictions and ten-row fixture are persistence checks, not external test scores.",
        ],
    }
    write_json(output / "summary.json", summary)
    lines = [
        "# Independent California Housing reference",
        "",
        "Independent workflow reconstruction using public scikit-learn APIs only; no PsyML imports.",
        "",
        f"Completed {len(audit)} fits: 90 inner, 15 family-specific outer, one selected final full-data fit.",
        "",
        "## Procedure metrics",
        "",
        "| Metric | Fold mean | Between-fold SD (ddof=0) | Pooled OOF |",
        "|---|---:|---:|---:|",
    ]
    for metric in ["rmse", "mae", "r2"]:
        lines.append(
            f"| {metric} | {summary['fold_mean'][metric]:.17g} | {summary['between_fold_sd_ddof0'][metric]:.17g} | {pooled[0][metric]:.17g} |"
        )
    lines += ["", "## Selection", ""] + [
        f"- {'Final full data' if r['outer_fold'] == 0 else 'Outer fold ' + str(r['outer_fold'])}: {r['model']}; inner mean RMSE {r['score']:.17g}; parameters {r['parameters']}"
        for r in selected
    ]
    lines += ["", "## Scope", ""] + ["- " + text for text in summary["limits"]]
    lines += [
        "",
        "Fitted preprocessing statistics were independently recomputed from each exact training scope. Reference serialization replay was exact, including the reordered ten-row fixture.",
        "",
        "Production acceptance is reported separately by the comparator; this file alone makes no GUI conformance claim.",
    ]
    (output / "SUMMARY.md").write_text("\n".join(lines) + "\n")
    write_json(
        output / "artifact_hashes.json",
        {p.name: sha256(p) for p in output.iterdir() if p.is_file()},
    )
    print(json.dumps(summary), flush=True)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument(
        "--approved-config-sha256",
        help="Optional exact hash of this relocated config, in addition to mandatory frozen science identity",
    )
    parser.add_argument(
        "--allow-environment-change",
        action="store_true",
        help="Record a new verification in this environment; do not overwrite the frozen baseline",
    )
    parser.add_argument("--prediction-fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    run(args)


if __name__ == "__main__":
    main()
