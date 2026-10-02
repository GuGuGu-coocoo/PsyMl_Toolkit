"""Prediction output must stay traceable: class mapping and file provenance.

Sanitized probability column names are portable but lose the original class
label (for example Chinese labels both become ``probability_model``-style
names). ``prediction_manifest.json`` keeps the durable mapping from every
appended column back to the original label, its index and type, plus the model
and input fingerprints.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from psyml import ExperimentConfig, run_experiment
from psyml.cli import main
from psyml.prediction import write_prediction_manifest


def _save_model(tmp_path: Path, labels: tuple[str, str] = ("实验组", "对照组")):
    frame = pd.DataFrame(
        {
            "x": range(40),
            "category": ["a", "b"] * 20,
            "target": [labels[index % 2] for index in range(40)],
        }
    )
    config = ExperimentConfig(
        task="classification",
        model_name="logistic_regression",
        target_column="target",
        output_dir=tmp_path / "run",
        figure_types=[],
    )
    result = run_experiment(config, frame)
    return config.output_dir / result.model_export["model_path"], frame


def _predict(capsys, tmp_path: Path, model_path: Path, frame: pd.DataFrame, name: str):
    input_path = tmp_path / f"{name}_input.csv"
    frame.drop(columns="target").to_csv(input_path, index=False)
    output = tmp_path / f"{name}_predictions.csv"
    assert main(
        [
            "predict",
            "--model",
            str(model_path),
            "--input",
            str(input_path),
            "--output",
            str(output),
            "--trust-model",
        ]
    ) == 0
    payload = json.loads(capsys.readouterr().out)
    manifest_path = tmp_path / "prediction_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return payload, manifest, manifest_path, input_path, output


def test_manifest_maps_sanitized_probability_columns_to_original_labels(tmp_path, capsys):
    model_path, frame = _save_model(tmp_path)
    payload, manifest, manifest_path, input_path, output = _predict(
        capsys, tmp_path, model_path, frame, "chinese"
    )
    assert payload["prediction_manifest_path"] == str(manifest_path)
    assert manifest["rows"] == len(frame)
    assert manifest["model_sha256"] == hashlib.sha256(model_path.read_bytes()).hexdigest()
    assert manifest["input_sha256"] == hashlib.sha256(input_path.read_bytes()).hexdigest()
    assert manifest["feature_order"] == ["x", "category"]
    assert manifest["manual_mapping"] is False
    assert manifest["classes"] == ["实验组", "对照组"]

    by_label = {
        entry["class_label"]: entry
        for entry in manifest["columns"]
        if entry["kind"] == "probability"
    }
    assert set(by_label) == {"实验组", "对照组"}
    for label, entry in by_label.items():
        assert entry["class_index"] == manifest["classes"].index(label)
        assert entry["class_type"] == "str"
    assert {
        entry["column"] for entry in by_label.values()
    } == {"probability_model", "probability_model_2"}
    predicted = pd.read_csv(output)
    for entry in manifest["columns"]:
        assert entry["column"] in predicted.columns


def test_manifest_resolves_sanitized_name_collisions(tmp_path, capsys):
    model_path, frame = _save_model(tmp_path, labels=("a.b", "a_b"))
    _payload, manifest, _manifest_path, _input_path, output = _predict(
        capsys, tmp_path, model_path, frame, "collision"
    )
    by_label = {
        entry["class_label"]: entry["column"]
        for entry in manifest["columns"]
        if entry["kind"] == "probability"
    }
    assert by_label == {"a.b": "probability_a_b", "a_b": "probability_a_b_2"}
    predicted = pd.read_csv(output)
    assert set(by_label.values()) <= set(predicted.columns)


def test_manifest_records_deduplicated_names_when_input_already_has_them(tmp_path, capsys):
    model_path, frame = _save_model(tmp_path)
    input_frame = frame.drop(columns="target").copy()
    input_frame["predicted_class"] = "original"
    input_frame["probability_model"] = 0.25
    _payload, manifest, _manifest_path, _input_path, output = _predict(
        capsys, tmp_path, model_path, input_frame.assign(target=frame["target"]), "existing"
    )
    probability_columns = {
        entry["class_index"]: entry["column"]
        for entry in manifest["columns"]
        if entry["kind"] == "probability"
    }
    # Both labels sanitize to the same base and the input already uses it, so
    # the two appended columns must still get distinct final names.
    assert probability_columns == {0: "probability_model_2", 1: "probability_model_3"}
    prediction_column = next(
        entry["column"] for entry in manifest["columns"] if entry["kind"] == "prediction"
    )
    assert prediction_column == "predicted_class_2"
    predicted = pd.read_csv(output)
    assert (predicted["predicted_class"] == "original").all()
    assert predicted["predicted_class_2"].notna().all()
    assert predicted["probability_model"].eq(0.25).all()


def test_manifest_writer_refuses_to_overwrite_without_consent(tmp_path):
    output = tmp_path / "predictions.csv"
    output.write_text("x\n", encoding="utf-8")
    write_prediction_manifest({"schema_version": "1.0"}, output)
    with pytest.raises(ValueError, match="already exists"):
        write_prediction_manifest({"schema_version": "1.0"}, output)
    write_prediction_manifest({"schema_version": "1.0", "rows": 1}, output, overwrite=True)
    manifest = json.loads((tmp_path / "prediction_manifest.json").read_text(encoding="utf-8"))
    assert manifest["rows"] == 1
