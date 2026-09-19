"""File-level tests for exported permutation-importance artefacts.

These check the numbers actually written to disk against the engine output:
raw repeat rows, per-fold repeat SD (ddof=0), the equal-weight cross-fold mean,
between-fold SD (ddof=1, null for one fold), signed values, JSON validity and
the result/manifest index. They also prove OFF runs and failed folds create no
misleading success files.
"""

import json

import jsonschema
import numpy as np
import pandas as pd
import pytest

from psyml import ExperimentConfig, run_experiment, runner
from psyml.evaluation.permutation import NonFiniteScoreError
from psyml.protocol import schema_text


def grouped_classification(n_groups: int = 12) -> pd.DataFrame:
    rows = n_groups * 4
    return pd.DataFrame(
        {
            "signal": ([-1.0, 1.0] * (rows // 2)),
            "category": (["x", "y"] * (rows // 2)),
            "target": ([0, 1] * (rows // 2)),
            "group": np.repeat(np.arange(n_groups), 4),
        }
    )


def make_config(path, **kwargs) -> ExperimentConfig:
    settings = {
        "task": "classification",
        "target_column": "target",
        "group_column": "group",
        "feature_columns": ["signal", "category"],
        "model_name": "decision_tree",
        "output_dir": path / "run",
        "validation_strategy": "group_k_fold",
        "n_splits": 3,
        "inner_splits": 2,
        "permutation_importance": True,
        "permutation_repeats": 3,
    }
    settings.update(kwargs)
    return ExperimentConfig(**settings)


def only_validation(result) -> tuple[str, list[dict]]:
    name, records = next(iter(result.permutation_results.items()))
    return name, records


def test_exports_match_engine_repeats_and_fold_statistics(tmp_path):
    config = make_config(tmp_path)
    result = run_experiment(config, grouped_classification())
    validation, records = only_validation(result)
    base = config.output_dir / "interpretations" / validation
    for name in [
        "permutation_raw.csv",
        "permutation_folds.csv",
        "permutation_summary.csv",
        "permutation.json",
        "permutation_importance.png",
    ]:
        assert (base / name).is_file(), name

    raw = pd.read_csv(base / "permutation_raw.csv")
    folds = pd.read_csv(base / "permutation_folds.csv")
    summary = pd.read_csv(base / "permutation_summary.csv")

    assert set(raw.columns) >= {
        "validation",
        "fold",
        "model_family",
        "variable",
        "repeat",
        "metric",
        "importance",
    }
    completed = [record for record in records if record["status"] == "completed"]
    expected_rows = sum(
        len(record["variables"]) * len(record["variables"][0]["importances"])
        for record in completed
    )
    assert len(raw) == expected_rows
    assert set(raw["variable"]) == {"signal", "category"}
    assert set(raw["validation"]) == {validation}

    # Per-fold repeat SD must be the engine's ddof=0 value, untouched.
    for record in completed:
        for variable in record["variables"]:
            row = folds[
                (folds["fold"] == record["fold"]) & (folds["variable"] == variable["name"])
            ].iloc[0]
            assert row["mean"] == pytest.approx(variable["mean"])
            assert row["repeat_std"] == pytest.approx(variable["std"])
            repeats = np.asarray(variable["importances"], dtype=float)
            assert row["repeat_std"] == pytest.approx(repeats.std(ddof=0))
            assert row["repeats"] == config.permutation_repeats

    # Summary equal-weight mean across fold means; between-fold SD is ddof=1.
    for variable in ["signal", "category"]:
        fold_rows = folds[folds["variable"] == variable]
        means = fold_rows["mean"].to_numpy(dtype=float)
        summary_row = summary[summary["variable"] == variable].iloc[0]
        assert summary_row["n_folds_successful"] == len(means)
        assert summary_row["n_folds_planned"] == config.n_splits
        assert summary_row["status"] == "completed"
        assert summary_row["fold_mean_equal_weight"] == pytest.approx(means.mean())
        assert summary_row["between_fold_std"] == pytest.approx(means.std(ddof=1))


def test_single_fold_between_std_is_null_and_values_stay_signed(tmp_path):
    config = make_config(
        tmp_path, validation_strategy="holdout", validation_strategies=None,
        n_splits=3, permutation_repeats=2,
    )
    result = run_experiment(config, grouped_classification(n_groups=20))
    validation, _ = only_validation(result)
    base = config.output_dir / "interpretations" / validation
    summary = pd.read_csv(base / "permutation_summary.csv")
    assert (summary["n_folds_successful"] == 1).all()
    assert (summary["n_folds_planned"] == 1).all()
    assert summary["between_fold_std"].isna().all()
    assert (base / "permutation_importance.png").is_file()

    metadata = json.loads((base / "permutation.json").read_text(encoding="utf-8"))
    assert metadata["status"] == "completed"
    assert metadata["metric"] == config.resolved_selection_metric()
    assert metadata["seed"] == config.random_seed
    assert metadata["repeats"] == config.permutation_repeats
    assert metadata["n_folds_planned"] == 1
    assert metadata["n_folds_successful"] == 1
    assert len(metadata["planned_folds"]) == 1
    assert metadata["planned_folds"][0]["n_rows"] >= 1
    for variable in metadata["variables"]:
        assert variable["between_fold_std"] is None
        assert variable["between_fold_std_available"] is False
        assert variable["between_fold_std_ddof"] == 1
    # No NaN/Infinity token escapes into strict JSON.
    assert "NaN" not in (base / "permutation.json").read_text(encoding="utf-8")
    assert "Infinity" not in (base / "permutation.json").read_text(encoding="utf-8")


def test_result_and_manifest_index_only_existing_interpretation_files(tmp_path):
    config = make_config(tmp_path)
    result = run_experiment(config, grouped_classification())
    result_payload = json.loads((config.output_dir / "result.json").read_text(encoding="utf-8"))
    jsonschema.validate(result_payload, json.loads(schema_text("result")))
    assert result_payload["permutation"]["enabled"] is True
    for key, relative in result_payload["artifacts"].items():
        if key.startswith("permutation_"):
            assert (config.output_dir / relative).is_file(), relative
    validation = next(iter(result.permutation_results))
    entry = result_payload["permutation"]["validations"][validation]
    assert entry["status"] == "completed"
    assert entry["n_folds_successful"] == config.n_splits
    assert f"permutation_{validation}_figure" in entry["artifacts"]

    manifest = json.loads(
        (config.output_dir / "analysis_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["interpretations"]["permutation_importance_enabled"] is True
    assert manifest["interpretations"]["validations"][validation]["status"] == "completed"
    for relative in manifest["interpretations"]["files"].values():
        assert (config.output_dir / relative).is_file()


def test_off_switch_creates_no_interpretation_directory(tmp_path):
    config = make_config(tmp_path, permutation_importance=False)
    result = run_experiment(config, grouped_classification())
    assert result.permutation_results == {}
    assert not (config.output_dir / "interpretations").exists()
    payload = json.loads((config.output_dir / "result.json").read_text(encoding="utf-8"))
    assert "permutation" not in payload
    assert not [key for key in payload["artifacts"] if key.startswith("permutation_")]


def test_failed_fold_exports_partial_status_without_fabricated_rows(tmp_path, monkeypatch):
    real_engine = runner.permutation_importance
    failures = {"count": 0}

    def flaky(model, features, target, **kwargs):
        failures["count"] += 1
        if failures["count"] == 2:
            raise NonFiniteScoreError("injected non-finite score")
        return real_engine(model, features, target, **kwargs)

    monkeypatch.setattr(runner, "permutation_importance", flaky)
    config = make_config(tmp_path)
    result = run_experiment(config, grouped_classification())
    validation, records = only_validation(result)
    assert any(record["status"] == "failed" for record in records)
    assert any(record["status"] == "completed" for record in records)

    base = config.output_dir / "interpretations" / validation
    summary = pd.read_csv(base / "permutation_summary.csv")
    assert set(summary["status"]) == {"partial"}
    folds = pd.read_csv(base / "permutation_folds.csv")
    assert set(folds["status"]) == {"completed", "failed"}
    # A failed fold contributes no variable means.
    assert folds[folds["status"] == "failed"]["variable"].isna().all()

    metadata = json.loads((base / "permutation.json").read_text(encoding="utf-8"))
    assert metadata["status"] == "partial"
    assert metadata["n_folds_failed"] >= 1
    assert metadata["n_folds_planned"] == config.n_splits
    assert metadata["metric"] == config.resolved_selection_metric()
    assert metadata["seed"] == config.random_seed
    assert metadata["repeats"] == config.permutation_repeats
    failed_entries = metadata["failed_folds"]
    assert failed_entries and failed_entries[0]["error_type"] == "NonFiniteScoreError"
    assert failed_entries[0]["n_rows"] >= 1
    # A partial run still produces a self-describing ranking figure.
    assert (base / "permutation_importance.png").is_file()

    payload = json.loads((config.output_dir / "result.json").read_text(encoding="utf-8"))
    assert payload["permutation"]["validations"][validation]["status"] == "partial"
    # Outer evaluation must be untouched by the interpretation failure.
    assert result.metrics


def test_all_folds_failed_writes_no_success_table_or_figure(tmp_path, monkeypatch):
    def always_fail(*args, **kwargs):
        raise NonFiniteScoreError("injected")

    monkeypatch.setattr(runner, "permutation_importance", always_fail)
    config = make_config(tmp_path)
    result = run_experiment(config, grouped_classification())
    validation, records = only_validation(result)
    base = config.output_dir / "interpretations" / validation
    assert all(record["status"] == "failed" for record in records)
    assert (base / "permutation.json").is_file()
    assert not (base / "permutation_summary.csv").exists()
    assert not (base / "permutation_importance.png").exists()
    metadata = json.loads((base / "permutation.json").read_text(encoding="utf-8"))
    assert metadata["status"] == "failed"
    assert metadata["n_folds_successful"] == 0
    # Requested settings must survive an all-failed run; a failed computation
    # never erases the metric, seed, repeats or the planned fold plan.
    assert metadata["metric"] == config.resolved_selection_metric()
    assert metadata["direction"] == "higher_is_better"
    assert metadata["seed"] == config.random_seed
    assert metadata["repeats"] == config.permutation_repeats
    assert metadata["n_folds_planned"] == config.n_splits
    assert len(metadata["planned_folds"]) == config.n_splits
    assert all(entry["n_rows"] >= 1 for entry in metadata["planned_folds"])
    assert len(metadata["failed_folds"]) == config.n_splits
    assert all(entry["n_rows"] >= 1 for entry in metadata["failed_folds"])
    assert metadata["variables"] == []


def test_figure_keeps_unicode_names_and_restores_font_settings(tmp_path):
    import matplotlib

    from psyml.reporting import permutation as reporting

    frame = pd.DataFrame(
        {
            "variable": ["变量_基线得分_测量值_研究版_甲", "变量_基线得分_测量值_研究版_乙"],
            "metric": ["balanced_accuracy", "balanced_accuracy"],
            "direction": ["higher_is_better", "higher_is_better"],
            "fold_mean_equal_weight": [0.12, -0.03],
            "between_fold_std": [0.02, 0.01],
        }
    )
    before = matplotlib.rcParams["font.family"]
    out = tmp_path / "unicode.png"
    reporting._write_figure(
        out,
        "group_k_fold",
        frame,
        status="completed",
        successful_folds=3,
        planned_folds=3,
    )
    assert out.is_file() and out.stat().st_size > 0
    assert matplotlib.rcParams["font.family"] == before


def test_figure_caption_names_validation_fold_counts_status_and_error_meaning():
    from psyml.reporting import permutation as reporting

    complete = reporting.figure_caption(
        validation="group_k_fold",
        metric="balanced_accuracy",
        direction="higher_is_better",
        status="completed",
        successful_folds=3,
        planned_folds=3,
        between_fold_std_available=True,
    )
    assert "group_k_fold" in complete["title"]
    assert "3/3" in complete["title"]
    assert "completed" in complete["title"]
    assert "ddof=1" in complete["error_note"]
    assert "not a confidence interval" in complete["error_note"]
    assert "decrease after permutation" in complete["xlabel"]

    partial = reporting.figure_caption(
        validation="holdout",
        metric="mae",
        direction="lower_is_better",
        status="partial",
        successful_folds=1,
        planned_folds=3,
        between_fold_std_available=False,
    )
    assert "holdout" in partial["title"]
    assert "1/3" in partial["title"]
    assert "partial" in partial["title"]
    assert "unavailable" in partial["error_note"]
    assert "no error bars drawn" in partial["error_note"]
    assert "increase after permutation" in partial["xlabel"]


def test_independent_validations_keep_interpretations_isolated(tmp_path):
    config = make_config(
        tmp_path,
        validation_strategies=["holdout", "group_k_fold"],
        primary_validation=None,
        model_names=["decision_tree", "dummy"],
    )
    result = run_experiment(config, grouped_classification(n_groups=20))
    assert set(result.validation_results) == {"holdout", "group_k_fold"}
    for validation, child in result.validation_results.items():
        assert set(child.permutation_results) == {validation}
        child_base = (
            config.output_dir / "validations" / validation / "interpretations" / validation
        )
        assert (child_base / "permutation_raw.csv").is_file()
        raw = pd.read_csv(child_base / "permutation_raw.csv")
        assert set(raw["validation"]) == {validation}

    root = json.loads((config.output_dir / "result.json").read_text(encoding="utf-8"))
    jsonschema.validate(root, json.loads(schema_text("result")))
    assert root["evaluation_scope"] == "independent_validations"
    assert set(root["permutation"]["validations"]) == {"holdout", "group_k_fold"}
    for relative in root["artifacts"].values():
        if relative.startswith("validations/"):
            assert (config.output_dir / relative).is_file(), relative
