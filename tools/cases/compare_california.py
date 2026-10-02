#!/usr/bin/env python3
"""Fail-closed GUI-export/reference comparison under predeclared tolerances.

This comparator inspects locally produced trusted joblib files. It is an audit
adapter, not a second independent model implementation. It never fits a model.
"""

from __future__ import annotations

import argparse
import copy
import json
import traceback
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.model_selection import ParameterGrid

if __package__:
    from .california_case import (
        AMENDED_CONFIG_SHA256,
        FROZEN_CONFIG_SHA256,
        FROZEN_PROTOCOL_SHA256,
        config_identity,
        frozen_config,
        science,
        science_sha256,
    )
    from .reference_california import (
        ATOL,
        DATA_HASH,
        FAMILIES,
        FEATURES,
        RTOL,
        TARGET,
        direct_metrics,
        estimator,
        fitted_state,
        sha256,
        write_json,
    )
else:
    from california_case import (
        AMENDED_CONFIG_SHA256,
        FROZEN_CONFIG_SHA256,
        FROZEN_PROTOCOL_SHA256,
        config_identity,
        frozen_config,
        science,
        science_sha256,
    )
    from reference_california import (
        ATOL,
        DATA_HASH,
        FAMILIES,
        FEATURES,
        RTOL,
        TARGET,
        direct_metrics,
        estimator,
        fitted_state,
        sha256,
        write_json,
    )

CONTRACTS = {
    "predictions.csv": (
        ["row_index", "fold", "observed", "predicted", "model"],
        ["row_index"],
        ["row_index", "fold", "model"],
    ),
    "fold_metrics.csv": (
        ["fold", "model", "validation", "r2", "mae", "rmse"],
        ["fold"],
        ["fold", "model", "validation"],
    ),
    "metrics.csv": (["r2", "mae", "rmse"], [], []),
    "metrics_summary.csv": (
        ["metric", "mean", "std", "min", "max", "n_folds"],
        ["metric"],
        ["metric", "n_folds"],
    ),
    "parameter_search.csv": (
        [
            "model",
            "validation",
            "outer_fold",
            "selection_scope",
            "candidate",
            "selection_metric",
            "score",
            "parameters",
            "status",
            "error",
        ],
        ["model", "outer_fold", "candidate"],
        [
            "model",
            "validation",
            "outer_fold",
            "selection_scope",
            "candidate",
            "selection_metric",
            "parameters",
            "status",
            "error",
        ],
    ),
    "selection_trace.csv": (
        ["validation", "outer_fold", "selection_scope", "model", "parameters", "score"],
        ["outer_fold"],
        ["validation", "outer_fold", "selection_scope", "model", "parameters"],
    ),
}


class Audit:
    def __init__(self):
        self.checks = []
        self.resolve_parameter_defaults = False
        self.diagnostics = []

    def check(self, name, passed, **details):
        self.checks.append({"check": name, "passed": bool(passed), **details})
        return bool(passed)

    def equal(self, name, actual, expected):
        # Exact identities include JSON number types: sklearn integer constraints
        # distinguish verbose=0 from invalid verbose=0.0.
        passed = json.dumps(actual, sort_keys=True, allow_nan=False) == json.dumps(
            expected, sort_keys=True, allow_nan=False
        )
        return self.check(
            name, passed, **({} if passed else {"actual": actual, "expected": expected})
        )

    def close(self, name, actual, expected):
        try:
            a, b = np.asarray(actual, dtype=float), np.asarray(expected, dtype=float)
            if a.shape != b.shape:
                return self.check(
                    name,
                    False,
                    reason="shape mismatch",
                    actual_shape=list(a.shape),
                    expected_shape=list(b.shape),
                )
            if not np.isfinite(a).all() or not np.isfinite(b).all():
                return self.check(name, False, reason="nonfinite numeric value")
            delta = np.abs(a - b)
            valid = np.isclose(a, b, atol=ATOL, rtol=RTOL)
            return self.check(
                name,
                bool(valid.all()),
                max_absolute_difference=float(delta.max()) if delta.size else 0.0,
                exact_equal=bool(np.array_equal(a, b)),
                different_cells=int(np.count_nonzero(a != b)),
                beyond_tolerance_cells=int(np.count_nonzero(~valid)),
            )
        except (ValueError, TypeError) as error:
            return self.check(name, False, reason=str(error))

    def frame(self, name, actual, expected, required, keys, exact):
        good = True
        for label, table in [("production", actual), ("reference", expected)]:
            missing = sorted(set(required) - set(table.columns))
            good &= self.check(
                name + "/" + label + "/required_columns", not missing, missing=missing
            )
        if not good:
            return
        self.equal(name + "/row_count", len(actual), len(expected))
        if len(actual) != len(expected):
            return
        self.equal(name + "/column_contract", sorted(actual.columns), sorted(expected.columns))
        if keys:
            for label, table in [("production", actual), ("reference", expected)]:
                if not self.check(
                    name + "/" + label + "/unique_keys", not table.duplicated(keys).any()
                ):
                    return
            actual = actual.sort_values(keys, kind="stable").reset_index(drop=True)
            expected = expected.sort_values(keys, kind="stable").reset_index(drop=True)
        for column in required:
            a, b = actual[column], expected[column]
            if column in exact:
                if column == "parameters":
                    try:
                        a, b = a.map(json.loads), b.map(json.loads)
                        if self.resolve_parameter_defaults:
                            a = pd.Series(
                                [
                                    estimator(family, p).get_params(deep=False)
                                    for family, p in zip(actual["model"], a)
                                ]
                            )
                            b = pd.Series(
                                [
                                    estimator(family, p).get_params(deep=False)
                                    for family, p in zip(expected["model"], b)
                                ]
                            )
                    except (ValueError, TypeError) as error:
                        self.check(name + "/" + column, False, reason=str(error))
                        continue
                elif column == "error":
                    # Empty diagnostic errors are the one permitted missing-text field.
                    a, b = a.fillna(""), b.fillna("")
                elif a.isna().any() or b.isna().any():
                    self.check(name + "/" + column, False, reason="missing exact field")
                    continue
                self.equal(name + "/" + column, a.tolist(), b.tolist())
            else:
                self.close(name + "/" + column, a, b)

    def attempt(self, name, function):
        try:
            return function()
        except Exception as error:  # noqa: BLE001 - audit boundary must emit a failed check, never a silent pass
            self.check(
                name,
                False,
                reason=f"{type(error).__name__}: {error}",
                traceback=traceback.format_exc(),
            )
            return None


def load_json(path):
    return json.loads(Path(path).read_text())


def run(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    audit = Audit()
    reference, production = args.reference, args.production
    config = load_json(args.config)
    if config_identity(config) != "v1":
        raise ValueError("--config must identify original v1; use --execution-config for v1.1")
    protocol = load_json(args.protocol)
    execution_config = config
    if bool(args.execution_config) != bool(args.compatibility_amendment):
        raise ValueError("Supply execution config and compatibility amendment together")
    if args.execution_config:
        amendment = load_json(args.compatibility_amendment)
        execution_config = load_json(args.execution_config)
        allowed = copy.deepcopy(config)
        del allowed["parameter_grids"]["random_forest"]["verbose"]
        okay = audit.equal(
            "amendment/original_protocol_hash",
            sha256(args.protocol),
            amendment["original_protocol_sha256"],
        )
        okay &= audit.equal(
            "amendment/original_config_hash",
            FROZEN_CONFIG_SHA256,
            amendment["original_config_sha256"],
        )
        okay &= audit.equal(
            "amendment/execution_config_historical_hash",
            AMENDED_CONFIG_SHA256,
            amendment["amended_config_sha256"],
        )
        okay &= audit.equal(
            "amendment/execution_config_science_identity", config_identity(execution_config), "v1.1"
        )
        okay &= audit.equal(
            "amendment/only_verbose_omission", science(execution_config), science(allowed)
        )
        for family in FAMILIES:
            before = [
                estimator(family, p).get_params(deep=False)
                for p in ParameterGrid(config["parameter_grids"][family])
            ]
            after = [
                estimator(family, p).get_params(deep=False)
                for p in ParameterGrid(execution_config["parameter_grids"][family])
            ]
            okay &= audit.equal("amendment/effective_candidates/" + family, after, before)
        audit.resolve_parameter_defaults = okay
    reference_summary = load_json(reference / "summary.json")
    audit.check(
        "production_terminal_result_exists",
        (production / "result.json").is_file(),
        reason="Native result.json is written only after the complete run succeeds",
    )
    data_path = args.data
    audit.equal("frozen_protocol_hash", sha256(args.protocol), FROZEN_PROTOCOL_SHA256)
    audit.equal("frozen_config_historical_hash", FROZEN_CONFIG_SHA256, protocol["config_sha256"])
    audit.equal("relocated_config_science_identity", science(config), science(frozen_config("v1")))
    audit.equal("prepared_csv_hash", sha256(data_path), DATA_HASH)
    audit.equal("reference_csv_hash", reference_summary["csv_sha256"], DATA_HASH)
    if reference_summary["config_sha256"] == FROZEN_CONFIG_SHA256:
        audit.equal(
            "reference_config_historical_hash",
            reference_summary["config_sha256"],
            protocol["config_sha256"],
        )
    else:
        audit.equal(
            "reference_config_science_hash",
            reference_summary.get("config_science_sha256"),
            science_sha256(config),
        )
        audit.equal(
            "reference_config_historical_hash",
            reference_summary.get("historical_config_sha256"),
            FROZEN_CONFIG_SHA256,
        )
    reference_environment = load_json(reference / "environment.json")
    reference_sklearn = reference_environment["sklearn"]
    audit.diagnostics.append(
        {
            "diagnostic": "environment",
            "reference_sklearn": reference_sklearn,
            "comparison_sklearn": sklearn.__version__,
            "historical_sklearn": "1.8.0",
            "new_verification": reference_sklearn != "1.8.0",
        }
    )
    audit.equal(
        "predeclared_tolerances",
        {"atol": ATOL, "rtol": RTOL},
        {k: protocol["numeric_acceptance"][k] for k in ["atol", "rtol"]},
    )
    audit.equal(
        "reference_fit_counts",
        reference_summary["fit_counts"],
        {"inner": 90, "outer_family": 15, "final": 1, "total": 106},
    )
    for filename, (required, keys, exact) in CONTRACTS.items():
        audit.attempt(
            filename,
            lambda filename=filename, required=required, keys=keys, exact=exact: audit.frame(
                filename,
                pd.read_csv(production / filename),
                pd.read_csv(reference / filename),
                required,
                keys,
                exact,
            ),
        )

    frame = pd.read_csv(data_path)
    x, y = frame[FEATURES], frame[TARGET]
    memberships = load_json(reference / "fold_membership.json")
    structural = []
    for name, entry in memberships.items():
        input_set = set(entry["input_rows"])
        held_out = []
        for fold, members in enumerate(entry["folds"], 1):
            train, test = set(members["train_rows"]), set(members["test_rows"])
            good = not train.intersection(test) and train.union(test) == input_set
            structural.append(good)
            audit.check(f"reference_split/{name}/{fold}/disjoint_cover", good)
            held_out.extend(members["test_rows"])
            if name.startswith("inner_") and name != "inner_0":
                outer = memberships["outer"]["folds"][int(name.split("_")[1]) - 1]
                audit.equal(
                    f"reference_split/{name}/{fold}/outer_training_scope",
                    sorted(input_set),
                    outer["train_rows"],
                )
        audit.equal(f"reference_split/{name}/test_coverage", sorted(held_out), sorted(input_set))

    def verify_exported_outer():
        predictions = pd.read_csv(production / "predictions.csv")
        audit.equal(
            "production_oof_row_coverage",
            sorted(predictions.row_index.tolist()),
            list(range(20640)),
        )
        audit.equal(
            "production_oof_row_order",
            predictions.row_index.tolist(),
            pd.read_csv(reference / "predictions.csv").row_index.tolist(),
        )
        for fold, members in enumerate(memberships["outer"]["folds"], 1):
            audit.equal(
                f"production_export_outer_fold/{fold}",
                predictions.loc[predictions.fold == fold, "row_index"].tolist(),
                members["test_rows"],
            )
        audit.close(
            "production_observed_values",
            predictions.observed,
            y.iloc[predictions.row_index.astype(int)],
        )
        exported = pd.read_csv(production / "fold_metrics.csv").set_index("fold")
        reconstructed = []
        for fold, table in predictions.groupby("fold", sort=True):
            vals = direct_metrics(table.observed, table.predicted)
            reconstructed.append({"fold": fold, **vals})
            for metric, value in vals.items():
                audit.close(
                    f"production_direct_fold_metric/{fold}/{metric}",
                    value,
                    exported.loc[fold, metric],
                )
        reconstructed = pd.DataFrame(reconstructed)
        pooled = direct_metrics(predictions.observed, predictions.predicted)
        audit.close(
            "production_direct_pooled_vs_reference",
            list(pooled.values()),
            [reference_summary["pooled_oof"][k] for k in pooled],
        )
        summary = pd.read_csv(production / "metrics_summary.csv").set_index("metric")
        for metric in ["rmse", "mae", "r2"]:
            for stat, value in [
                ("mean", reconstructed[metric].mean()),
                ("std", reconstructed[metric].std(ddof=0)),
                ("min", reconstructed[metric].min()),
                ("max", reconstructed[metric].max()),
            ]:
                audit.close(
                    f"production_direct_summary/{metric}/{stat}", value, summary.loc[metric, stat]
                )
        write_json(
            output / "production_recomputed_metrics.json",
            {
                "pooled_oof": pooled,
                "fold_mean": {m: reconstructed[m].mean() for m in ["rmse", "mae", "r2"]},
                "descriptive_sd_ddof0": {
                    m: reconstructed[m].std(ddof=0) for m in ["rmse", "mae", "r2"]
                },
            },
        )

    audit.attempt("recompute_exported_oof", verify_exported_outer)

    def verify_leaderboard():
        expected = []
        families = pd.read_csv(reference / "family_fold_metrics.csv")
        for family in FAMILIES:
            means = families[families.model == family][["r2", "mae", "rmse"]].mean().to_dict()
            expected.append(
                {
                    "rank": 0,
                    "model": family,
                    "validation": "k_fold",
                    "selection_metric": "rmse",
                    "selection_score": means["rmse"],
                    "status": "completed",
                    "error": "",
                    **means,
                }
            )
        expected.sort(key=lambda row: row["selection_score"])
        for rank, row in enumerate(expected, 1):
            row["rank"] = rank
        required = [
            "rank",
            "model",
            "validation",
            "selection_metric",
            "selection_score",
            "status",
            "error",
            "r2",
            "mae",
            "rmse",
        ]
        audit.frame(
            "model_comparison.csv",
            pd.read_csv(production / "model_comparison.csv"),
            pd.DataFrame(expected),
            required,
            ["model"],
            ["rank", "model", "validation", "selection_metric", "status", "error"],
        )
        differences = []
        procedure = pd.read_csv(reference / "fold_metrics.csv").set_index("fold")
        dummy = families[families.model == "dummy"].set_index("fold")
        for fold in range(1, 6):
            differences.append(
                {
                    "fold": fold,
                    "dummy_minus_procedure_rmse": float(
                        dummy.loc[fold, "rmse"] - procedure.loc[fold, "rmse"]
                    ),
                    "dummy_minus_procedure_mae": float(
                        dummy.loc[fold, "mae"] - procedure.loc[fold, "mae"]
                    ),
                    "procedure_minus_dummy_r2": float(
                        procedure.loc[fold, "r2"] - dummy.loc[fold, "r2"]
                    ),
                }
            )
        pd.DataFrame(differences).to_csv(
            output / "same_fold_dummy_differences.csv", index=False, float_format="%.17g"
        )

    audit.attempt("family_aggregate_export", verify_leaderboard)

    def verify_config():
        produced = load_json(production / "analysis_config.json")
        # Runtime path relocation is operational; all scientific fields remain exact.
        operational = {"input_path", "output_dir"}
        for key in execution_config:
            if key not in operational:
                audit.equal(
                    "executed_science_config/" + key, produced.get(key), execution_config[key]
                )
        if args.roundtrip_config:
            roundtrip = load_json(args.roundtrip_config)
            if args.execution_config:
                # Record raw type drift rather than concealing it. Only documented
                # count fields that production restores may be normalized here.
                raw_equal = json.dumps(
                    roundtrip.get("parameter_grids"), sort_keys=True
                ) == json.dumps(execution_config["parameter_grids"], sort_keys=True)
                audit.diagnostics.append(
                    {
                        "diagnostic": "raw_gui_saved_parameter_grid_type_identity",
                        "exact_equal": raw_equal,
                        "note": "Raw GUI JSON may serialize these integral count fields as doubles; execution must restore exact types.",
                    }
                )
                normalized = copy.deepcopy(roundtrip)
                safe_counts = {
                    "n_estimators",
                    "max_depth",
                    "min_samples_leaf",
                    "min_samples_split",
                    "max_leaf_nodes",
                    "max_iter",
                    "random_state",
                    "n_jobs",
                }
                for grid in normalized.get("parameter_grids", {}).values():
                    for parameter, values in grid.items():
                        if parameter in safe_counts:
                            grid[parameter] = [
                                int(value)
                                if type(value) is float
                                and value.is_integer()
                                and not (
                                    parameter in {"min_samples_leaf", "min_samples_split"}
                                    and value == 1.0
                                )
                                else value
                                for value in values
                            ]
                for key in execution_config:
                    if key not in operational:
                        audit.equal(
                            "gui_roundtrip_effective_science_config/" + key,
                            normalized.get(key),
                            execution_config[key],
                        )
            else:
                for key in config:
                    if key not in operational:
                        audit.equal(
                            "gui_roundtrip_science_config/" + key, roundtrip.get(key), config[key]
                        )
        else:
            audit.check(
                "gui_roundtrip_config_supplied",
                False,
                reason="GUI saved configuration required for this acceptance claim",
            )

    audit.attempt("scientific_config_roundtrip", verify_config)

    def verify_final():
        metadata = load_json(production / "model/model_metadata.json")
        model_path = production / "model" / metadata["model_file"]
        if model_path.resolve().parent != (production / "model").resolve():
            raise ValueError("Model metadata must name a local file directly inside model/")
        if not audit.equal(
            "model_loading_runtime_matches_reference", sklearn.__version__, reference_sklearn
        ):
            raise ValueError(
                "Run comparator in the same sklearn environment as the reference; cross-version joblib loading is not accepted"
            )
        audit.equal("saved_model_sha256", sha256(model_path), metadata["sha256"])
        # Only load artifacts produced in this authorized local run, never untrusted uploads.
        model = joblib.load(model_path)
        reference_model = joblib.load(reference / "final_model.joblib")
        winner = next(r for r in reference_summary["selection"] if r["outer_fold"] == 0)
        for name, expected in {
            "feature_names": FEATURES,
            "target_column": TARGET,
            "n_features": 8,
            "analyzed_row_count": 20640,
            "fit_scope": "all_analyzed_rows",
            "model_name": winner["model"],
            "task": "regression",
            "selection_metric": "rmse",
            "validation_strategy": "k_fold",
            "scaling": "standard",
            "missing_strategy": "median",
            "sklearn_version": reference_sklearn,
        }.items():
            audit.equal("model_metadata/" + name, metadata.get(name), expected)
        if audit.resolve_parameter_defaults:
            audit.equal(
                "model_metadata/effective_overrides",
                estimator(winner["model"], metadata["parameter_overrides"]).get_params(deep=False),
                estimator(winner["model"], json.loads(winner["parameters"])).get_params(deep=False),
            )
        else:
            audit.equal(
                "model_metadata/parameter_overrides",
                metadata["parameter_overrides"],
                json.loads(winner["parameters"]),
            )
        audit.equal(
            "model_effective_parameters",
            model.named_steps["model"].get_params(deep=False),
            reference_model.named_steps["model"].get_params(deep=False),
        )
        audit.equal(
            "model_metadata/effective_parameters",
            metadata["best_parameters"],
            model.named_steps["model"].get_params(deep=False),
        )
        actual_state = fitted_state(
            model,
            x,
            winner["model"],
            json.loads(winner["parameters"]),
            phase="final",
            outer_fold=0,
            candidate=0,
        )
        expected_state = load_json(reference / "fit_audit.json")[-1]
        for key in ["feature_names", "scaler_n_samples_seen", "effective_parameters"]:
            audit.equal("final_fitted_state/" + key, actual_state[key], expected_state[key])
        for key in [
            "imputer_statistics",
            "scaler_mean",
            "scaler_var",
            "scaler_scale",
            "coef",
            "intercept",
            "constant",
        ]:
            audit.close("final_fitted_state/" + key, actual_state[key], expected_state[key])
        vals = x.to_numpy()
        for key, manual in [
            ("imputer_statistics", np.median(vals, axis=0)),
            ("scaler_mean", np.mean(vals, axis=0)),
            ("scaler_var", np.var(vals, axis=0, ddof=0)),
            ("scaler_scale", np.sqrt(np.var(vals, axis=0, ddof=0))),
        ]:
            audit.close("production_final_scope_direct/" + key, actual_state[key], manual)
        actual_prediction = model.predict(x)
        audit.close("saved_model_full_data_replay", actual_prediction, reference_model.predict(x))
        fixture = pd.read_csv(args.prediction_fixture)
        actual_fixture = model.predict(fixture)
        audit.close(
            "saved_model_reordered_fixture", actual_fixture, reference_model.predict(fixture)
        )
        audit.close(
            "saved_model_reordered_invariance", actual_fixture, model.predict(fixture[FEATURES])
        )
        rejected = False
        try:
            model.predict(fixture.drop(columns=[FEATURES[0]]))
        except (ValueError, KeyError):
            rejected = True
        audit.check("saved_model_missing_feature_rejected", rejected)
        pd.DataFrame({"row_index": x.index, "predicted": actual_prediction}).to_csv(
            output / "production_model_replay.csv", index=False, float_format="%.17g"
        )
        pd.DataFrame({"sample_id": fixture.sample_id, "predicted": actual_fixture}).to_csv(
            output / "production_fixture_replay.csv", index=False, float_format="%.17g"
        )
        write_json(output / "production_final_state.json", actual_state)
        if args.gui_prediction_export:
            table = pd.read_csv(args.gui_prediction_export)
            if args.gui_prediction_column:
                column = args.gui_prediction_column
            else:
                candidates = [c for c in table.columns if c.startswith(("prediction", "predicted"))]
                if len(candidates) != 1:
                    raise ValueError(f"Need unambiguous prediction column, found {candidates}")
                column = candidates[0]
            audit.equal("gui_prediction_row_count", len(table), 10)
            audit.equal(
                "gui_prediction_sample_ids", table.sample_id.tolist(), fixture.sample_id.tolist()
            )
            audit.equal(
                "gui_prediction_original_column_order",
                list(table.columns),
                list(fixture.columns) + [column],
            )
            audit.close("gui_prediction_input_values_preserved", table[FEATURES], fixture[FEATURES])
            audit.close(
                "gui_prediction_against_reference", table[column], reference_model.predict(fixture)
            )
        else:
            audit.check(
                "gui_prediction_export_supplied",
                False,
                reason="Actual GUI batch prediction export required",
            )

    audit.attempt("saved_final_model", verify_final)

    # Independent reference includes all inner scopes, but GUI native exports do
    # not expose them. Do not manufacture production observation from source code.
    not_observed = [
        "Production per-inner-fold scores (only candidate mean scores are exported).",
        "Production inner fold memberships and preprocessing state for all 90 inner fits.",
        "Production per-family row-level OOF for non-selected families and 15 outer fitted preprocessing states.",
        "Production fit-call count as a runtime trace (106 is the planned reference count; GUI progress may provide separate evidence).",
    ]
    failed = [c for c in audit.checks if not c["passed"]]
    report = {
        "status": "passed_observed_scope" if not failed else "failed",
        "passed": not failed,
        "n_checks": len(audit.checks),
        "n_passed": len(audit.checks) - len(failed),
        "n_failed": len(failed),
        "tolerances": {"atol": ATOL, "rtol": RTOL},
        "checks": audit.checks,
        "diagnostics": audit.diagnostics,
        "compatibility_amendment_applied": audit.resolve_parameter_defaults,
        "not_observed_in_gui_exports": not_observed,
        "scope_note": "Numerical agreement of actual GUI exports and final model with independent reference. No blanket claim for unobserved production internals.",
        "paths": {"reference": str(reference), "production": str(production)},
        "provenance": {
            "comparator_script_sha256": sha256(__file__),
            "input_config_sha256": sha256(args.config),
            "historical_original_config_sha256": FROZEN_CONFIG_SHA256,
            "input_config_science_sha256": science_sha256(config),
            "original_protocol_sha256": sha256(args.protocol),
            "execution_config_sha256": sha256(args.execution_config)
            if args.execution_config
            else None,
            "amendment_sha256": sha256(args.compatibility_amendment)
            if args.compatibility_amendment
            else None,
        },
        "reference_summary": reference_summary,
    }
    write_json(output / "comparison.json", report)
    lines = [
        "# California Housing GUI acceptance comparison",
        "",
        f"Status: **{report['status']}**. {report['n_passed']}/{report['n_checks']} checks passed; {report['n_failed']} failed.",
        "",
        f"Predeclared tolerance: atol={ATOL:g}, rtol={RTOL:g}; nonfinite numeric values fail.",
        "",
        "## Evidence scope",
        "",
        report["scope_note"],
        "",
        "## Unobserved internals",
        "",
    ]
    lines += ["- " + item for item in not_observed]
    if audit.diagnostics:
        lines += ["", "## Raw configuration diagnostics", ""] + [
            "- " + json.dumps(d, sort_keys=True) for d in audit.diagnostics
        ]
    lines += ["", "## Failed checks", ""] + (
        ["- " + c["check"] + ": " + str(c.get("reason", c)) for c in failed] or ["None."]
    )
    lines += [
        "",
        "## Numeric maximum differences",
        "",
        "| Check | Max absolute difference | Exact equality |",
        "|---|---:|---|",
    ]
    lines += [
        f"| {c['check']} | {c['max_absolute_difference']:.17g} | {c['exact_equal']} |"
        for c in audit.checks
        if "max_absolute_difference" in c
    ]
    (output / "COMPARISON.md").write_text("\n".join(lines) + "\n")
    write_json(
        output / "artifact_hashes.json",
        {p.name: sha256(p) for p in output.iterdir() if p.is_file()},
    )
    print(json.dumps({k: report[k] for k in ["status", "n_checks", "n_passed", "n_failed"]}))
    return 0 if not failed else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in [
        "config",
        "protocol",
        "data",
        "reference",
        "production",
        "prediction-fixture",
        "output",
    ]:
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--roundtrip-config", type=Path)
    parser.add_argument("--execution-config", type=Path)
    parser.add_argument("--compatibility-amendment", type=Path)
    parser.add_argument("--gui-prediction-export", type=Path)
    parser.add_argument("--gui-prediction-column")
    return run(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
