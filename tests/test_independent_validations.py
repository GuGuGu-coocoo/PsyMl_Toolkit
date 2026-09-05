"""Protect peer-validation outputs from implicit ranking or primary selection."""
import json
from dataclasses import replace
from pathlib import Path

import jsonschema
import pandas as pd
import pytest

from psyml import ExperimentConfig, run_experiment
from psyml.cli import main
from psyml.protocol import config_from_dict, config_to_dict, schema_text

ROOT = Path(__file__).resolve().parents[1]


def config_at(path, task="classification", **kwargs):
    return ExperimentConfig(
        task=task, target_column="target", model_name="decision_tree",
        input_path=ROOT / f"examples/synthetic/{task}.csv", output_dir=path,
        feature_columns=["score", "category"], group_column="participant",
        validation_strategies=["holdout", "group_k_fold"], primary_validation=None,
        n_splits=3, inner_splits=2, **kwargs,
    )


def test_null_primary_round_trip_and_explicit_primary_not_first(tmp_path):
    config = config_at(tmp_path / "explicit")
    assert config.resolved_primary_validation() is None
    jsonschema.validate(config_to_dict(config), json.loads(schema_text("analysis_config")))
    assert config_from_dict(config_to_dict(config)) == config
    legacy = config_to_dict(config)
    del legacy["primary_validation"]
    assert config_from_dict(legacy).resolved_primary_validation() == "holdout"
    with pytest.raises(ValueError, match="primary_validation"):
        replace(config, primary_validation="k_fold")
    result = run_experiment(replace(config, primary_validation="group_k_fold"))
    assert result.best_validation_strategy == "group_k_fold"
    roles = dict(zip(result.validation_summary.validation, result.validation_summary.role))
    assert roles == {"holdout": "sensitivity", "group_k_fold": "primary"}


@pytest.mark.parametrize("task", ["classification", "regression"])
def test_complete_peer_outputs_match_standalone_and_order_does_not_pick_winner(tmp_path, task):
    figures = ["confusion_matrix", "class_distribution"] if task == "classification" else [
        "observed_vs_predicted", "residuals", "residual_distribution"
    ]
    config = config_at(tmp_path / "peers", task, model_names=["decision_tree", "dummy"], figure_types=figures)
    events = []
    result = run_experiment(config, progress_callback=lambda event: events.append(dict(event)))
    assert result.model is None and result.metrics == {} and result.predictions.empty
    assert result.best_model_name == "" and result.best_validation_strategy == ""
    assert set(result.validation_results) == {"holdout", "group_k_fold"}
    assert list(result.validation_summary.role) == ["independent", "independent"]
    payload = json.loads((config.output_dir / "result.json").read_text())
    assert payload["primary_validation"] is None and payload["metrics"] == {}
    assert not {"best_model", "best_validation", "best_parameters"} & payload.keys()
    assert not (config.output_dir / "metrics.csv").exists()
    jsonschema.validate(payload, json.loads(schema_text("result")))
    for name in payload["artifacts"].values():
        assert (config.output_dir / name).is_file()
    for validation, entry in payload["validation_results"].items():
        child_path = config.output_dir / entry["result_path"]
        child_payload = json.loads(child_path.read_text())
        jsonschema.validate(child_payload, json.loads(schema_text("result")))
        for name in child_payload["artifacts"].values():
            assert (child_path.parent / name).is_file()
        standalone = run_experiment(replace(
            config, output_dir=tmp_path / validation, primary_validation=validation,
            validation_strategy=validation, validation_strategies=[validation],
        ))
        assert standalone.metrics == result.validation_results[validation].metrics
        assert standalone.best_params == result.validation_results[validation].best_params
        pd.testing.assert_frame_equal(standalone.predictions, result.validation_results[validation].predictions)
    reversed_result = run_experiment(replace(
        config, output_dir=tmp_path / "reversed", validation_strategies=["group_k_fold", "holdout"],
    ))
    for validation, child in reversed_result.validation_results.items():
        pd.testing.assert_frame_equal(child.predictions, result.validation_results[validation].predictions)
    assert [event["progress"] for event in events] == sorted(event["progress"] for event in events)
    assert events[-1]["progress"] == 1.0


def test_partial_failure_is_visible_and_all_failure_has_no_success_marker(tmp_path):
    config = replace(config_at(tmp_path / "partial"), n_splits=20)
    result = run_experiment(config)
    assert set(result.validation_results) == {"holdout"}
    payload = json.loads((config.output_dir / "result.json").read_text())
    assert payload["status"] == "completed_with_errors"
    assert payload["validation_results"]["group_k_fold"]["status"] == "failed"
    assert (config.output_dir / "validations/group_k_fold/error.json").is_file()
    jsonschema.validate(payload, json.loads(schema_text("result")))
    failed = replace(config, output_dir=tmp_path / "all_failed", validation_strategies=["group_k_fold"])
    with pytest.raises(ValueError, match="Every independent validation failed"):
        run_experiment(failed)
    assert not (failed.output_dir / "result.json").exists()
    assert (failed.output_dir / "validation_summary.csv").is_file()


def test_cli_peer_bundle_events_are_schema_valid(tmp_path, capsys):
    config = config_at(tmp_path / "cli")
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config_to_dict(config)))
    assert main(["run", "--config", str(path), "--events"]) == 0
    events = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    for event in events:
        jsonschema.validate(event, json.loads(schema_text("event")))
    assert events[-1]["event"] == "completed"
    assert events[-1]["result_path"] == str(config.output_dir / "result.json")
