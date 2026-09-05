"""Portable GUI imports must validate without running or losing settings."""

import json
from pathlib import Path

import pytest

from psyml.gui_config import import_configuration

EXAMPLES = Path(__file__).parents[1] / "examples/synthetic"


def test_repository_example_from_unrelated_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = import_configuration(EXAMPLES / "classification_config.json")
    assert not result["needs_data"]
    assert result["preview"]["row_count"] == 48
    assert result["config"]["group_column"] == "participant"


def test_missing_data_can_be_relinked_without_changing_design(tmp_path):
    payload = json.loads((EXAMPLES / "classification_config.json").read_text())
    payload.update(input_path="/other-computer/missing.csv", primary_validation=None,
                   random_seed=17, test_size=0.3, include_data_hash=False,
                   model_params={"max_depth": 3}, figure_types=[])
    path = tmp_path / "配置.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert import_configuration(path)["needs_data"]
    result = import_configuration(path, EXAMPLES / "classification.csv")
    for key in ["primary_validation", "random_seed", "test_size", "include_data_hash",
                "model_params", "figure_types"]:
        assert result["config"][key] == payload[key]
    assert not (tmp_path / "results").exists()


def test_relinked_data_must_contain_configured_columns(tmp_path):
    payload = json.loads((EXAMPLES / "classification_config.json").read_text())
    payload["target_column"] = "missing_column"
    path = tmp_path / "config.json"
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="missing_column"):
        import_configuration(path, EXAMPLES / "classification.csv")


def test_config_relative_data_has_priority(tmp_path):
    payload = json.loads((EXAMPLES / "regression_config.json").read_text())
    payload["input_path"] = "regression.csv"
    path = tmp_path / "config.json"
    path.write_text(json.dumps(payload))
    (tmp_path / "regression.csv").write_bytes((EXAMPLES / "regression.csv").read_bytes())
    result = import_configuration(path)
    assert result["config"]["input_path"] == str(tmp_path / "regression.csv")
