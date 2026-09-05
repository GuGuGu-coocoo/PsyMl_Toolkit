import json
import signal
import subprocess
import sys
from pathlib import Path

import jsonschema
import pandas as pd
import pytest

from psyml import ExperimentConfig
from psyml.cli import main
from psyml.protocol import config_from_dict, config_to_dict, schema_text


def _schema(name):
    return json.loads(schema_text(name))


def _file_config(tmp_path):
    input_path = tmp_path / "中文 data" / "input.csv"
    input_path.parent.mkdir()
    pd.DataFrame({"feature": list(range(30)), "target": [0, 1] * 15}).to_csv(
        input_path, index=False
    )
    return ExperimentConfig(
        task="classification",
        target_column="target",
        model_name="logistic_regression",
        input_path=input_path,
        output_dir=tmp_path / "输出 results",
        validation_strategy="stratified_k_fold",
        n_splits=3,
    )


def test_analysis_config_round_trip_and_schema(tmp_path):
    config = _file_config(tmp_path)
    payload = config_to_dict(config)

    jsonschema.validate(payload, _schema("analysis_config"))
    restored = config_from_dict(payload)

    assert restored == config
    with pytest.raises(ValueError, match="Unsupported.*schema_version"):
        config_from_dict({**payload, "schema_version": "2.0"})
    with pytest.raises(ValueError, match="Unknown.*surprise"):
        config_from_dict({**payload, "surprise": True})


def test_comparative_config_round_trip_and_schema(tmp_path):
    config = _file_config(tmp_path)
    config = ExperimentConfig(
        **{
            **config.__dict__,
            "model_names": ["logistic_regression", "dummy"],
            "validation_strategies": ["stratified_k_fold", "holdout"],
            "tuning_mode": "custom",
            "parameter_grids": {
                "logistic_regression": {"C": [0.1, 1.0]},
                "dummy": {"strategy": ["prior"]},
            },
            "selection_metric": "balanced_accuracy",
            "inner_splits": 2,
            "max_candidates": 4,
        }
    )

    payload = config_to_dict(config)
    jsonschema.validate(payload, _schema("analysis_config"))
    assert config_from_dict(payload) == config


def test_capabilities_and_privacy_first_preview(tmp_path, capsys):
    config = _file_config(tmp_path)

    assert main(["capabilities"]) == 0
    capabilities = json.loads(capsys.readouterr().out)
    assert capabilities["schema_version"] == "1.0"
    assert "logistic_regression" in capabilities["models"]["classification"]
    assert capabilities["parameter_grids"]["classification"]["logistic_regression"]["C"]
    assert capabilities["selection_metrics"]["regression"] == ["rmse", "mae", "r2"]

    assert main(["preview", "--input", str(config.input_path)]) == 0
    preview = json.loads(capsys.readouterr().out)
    assert preview["row_count"] == 30
    assert preview["columns"][0]["name"] == "feature"
    assert "sample" not in preview

    assert (
        main(["preview", "--input", str(config.input_path), "--include-sample", "--rows", "2"]) == 0
    )
    sampled = json.loads(capsys.readouterr().out)
    assert sampled["sample"] == [
        {"feature": 0, "target": 0},
        {"feature": 1, "target": 1},
    ]


def test_capabilities_work_through_real_subprocess():
    completed = subprocess.run(
        [sys.executable, "-m", "psyml", "capabilities"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(completed.stdout)["schema_version"] == "1.0"
    assert completed.stderr == ""


def test_versioned_cli_run_emits_events_and_valid_outputs(tmp_path, capsys):
    config = _file_config(tmp_path)
    config = ExperimentConfig(
        **{
            **config.__dict__,
            "tuning_mode": "custom",
            "parameter_grids": {"logistic_regression": {"C": [0.1, 1.0]}},
            "inner_splits": 2,
        }
    )
    config_path = tmp_path / "配置 analysis.json"
    config_path.write_text(json.dumps(config_to_dict(config), ensure_ascii=False), encoding="utf-8")

    assert main(["run", "--config", str(config_path), "--events"]) == 0

    events = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert events[0]["event"] == "started"
    assert events[-1]["event"] == "completed"
    progress_events = [event for event in events if event["event"] == "progress"]
    assert progress_events
    assert progress_events[-1]["progress"] == 1.0
    assert progress_events[-1]["remaining_tasks"] == 0
    for event in events:
        jsonschema.validate(event, _schema("event"))
    result_path = config.output_dir / "result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    jsonschema.validate(result, _schema("result"))
    for artifact in result["artifacts"].values():
        assert (config.output_dir / artifact).is_file()
    saved_config = json.loads(
        (config.output_dir / "analysis_config.json").read_text(encoding="utf-8")
    )
    jsonschema.validate(saved_config, _schema("analysis_config"))

    first_predictions = (config.output_dir / "predictions.csv").read_bytes()
    saved_config["output_dir"] = str(tmp_path / "replayed output")
    config_path.write_text(json.dumps(saved_config), encoding="utf-8")
    assert main(["run", "--config", str(config_path)]) == 0
    capsys.readouterr()
    assert (Path(saved_config["output_dir"]) / "predictions.csv").read_bytes() == first_predictions


def test_versioned_cli_returns_structured_failure(tmp_path, capsys):
    config = _file_config(tmp_path)
    payload = config_to_dict(config)
    payload["target_column"] = "missing-target"
    config_path = tmp_path / "invalid.json"
    config_path.write_text(json.dumps(payload), encoding="utf-8")

    assert main(["run", "--config", str(config_path), "--events"]) == 2

    events = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert [event["event"] for event in events] == ["started", "failed"]
    assert events[-1]["error"]["code"] == "column_not_found"
    jsonschema.validate(events[-1], _schema("event"))


@pytest.mark.skipif(not hasattr(signal, "SIGTERM"), reason="SIGTERM is unavailable")
def test_versioned_cli_emits_cancelled_event(tmp_path, capsys, monkeypatch):
    config = _file_config(tmp_path)
    config_path = tmp_path / "cancel.json"
    config_path.write_text(json.dumps(config_to_dict(config)), encoding="utf-8")

    def cancel_run(_config, progress_callback=None):
        del progress_callback
        signal.raise_signal(signal.SIGTERM)

    monkeypatch.setattr("psyml.cli._execute", cancel_run)

    assert main(["run", "--config", str(config_path), "--events"]) == 130
    events = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert [event["event"] for event in events] == ["started", "cancelled"]
    assert events[-1]["error"]["code"] == "cancelled"
    jsonschema.validate(events[-1], _schema("event"))
