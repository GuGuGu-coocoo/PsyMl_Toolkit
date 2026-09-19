"""CLI end-to-end tests for the fitted-coefficients command."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from psyml import ExperimentConfig, run_experiment
from psyml.cli import main


@pytest.fixture(scope="module")
def workspace(tmp_path_factory):
    root = tmp_path_factory.mktemp("coefficients_cli")
    rng = np.random.default_rng(21)
    features = pd.DataFrame({
        "age": rng.normal(size=90),
        "score": rng.normal(size=90),
        "group": (["a", "b", "c"] * 30),
    })
    features.to_csv(root / "sample.csv", index=False)

    clf_frame = features.copy()
    clf_frame["target"] = ((features["score"] + 0.2) > 0).astype(int)
    clf = ExperimentConfig(task="classification", model_name="logistic_regression",
                           target_column="target", output_dir=root / "clf_run",
                           figure_types=[])
    clf_result = run_experiment(clf, clf_frame)
    clf_model = clf.output_dir / clf_result.model_export["model_path"]

    reg_frame = features.copy()
    reg_frame["value"] = 3 * features["age"] - features["score"] + 1.0
    reg = ExperimentConfig(task="regression", model_name="ridge", target_column="value",
                           output_dir=root / "reg_run", figure_types=[])
    reg_result = run_experiment(reg, reg_frame)
    reg_model = reg.output_dir / reg_result.model_export["model_path"]

    unsupported = ExperimentConfig(task="classification", model_name="random_forest",
                                   target_column="target", output_dir=root / "rf_run",
                                   figure_types=[], model_params={"n_estimators": 5})
    rf_result = run_experiment(unsupported, clf_frame)
    rf_model = unsupported.output_dir / rf_result.model_export["model_path"]
    return {"root": root, "clf_model": clf_model, "reg_model": reg_model,
            "rf_model": rf_model, "sample": root / "sample.csv"}


def run_cli(args, capsys):
    code = main(args)
    captured = capsys.readouterr()
    text = captured.out + captured.err
    payload = json.loads(text.strip().splitlines()[-1]) if text.strip() else {}
    return code, payload


def test_check_only_does_not_write(workspace, capsys):
    code, payload = run_cli(
        ["coefficients", "--model", str(workspace["clf_model"]), "--trust-model",
         "--input", str(workspace["sample"]), "--check-only"], capsys)
    assert code == 0 and "error" not in payload
    report = payload["coefficients"]
    assert report["status"] == "available"
    assert report["verification"]["verified"] is True


def test_export_writes_artifacts_and_verifies(workspace, tmp_path, capsys):
    out = tmp_path / "coefs"
    code, payload = run_cli(
        ["coefficients", "--model", str(workspace["reg_model"]), "--trust-model",
         "--input", str(workspace["sample"]), "--output-dir", str(out)], capsys)
    assert code == 0 and "error" not in payload
    assert payload["coefficients"]["verification"]["verified"] is True
    for path in payload["artifacts"].values():
        assert Path(path).is_file()
    document = json.loads((out / "coefficients.json").read_text(encoding="utf-8"))
    assert document["coefficient_space"] == "preprocessed_feature_space"


def test_unsupported_model_reports_reason_without_writing(workspace, tmp_path, capsys):
    out = tmp_path / "rf"
    code, payload = run_cli(
        ["coefficients", "--model", str(workspace["rf_model"]), "--trust-model",
         "--input", str(workspace["sample"]), "--output-dir", str(out)], capsys)
    assert code == 0 and "error" not in payload
    assert payload["coefficients"]["status"] == "unsupported"
    assert "RandomForestClassifier" in payload["coefficients"]["reason"]
    assert not out.exists()


def test_existing_output_and_overwrite_are_refused(workspace, tmp_path, capsys):
    out = tmp_path / "occupied"
    out.mkdir()
    (out / "keep.txt").write_text("original", encoding="utf-8")
    code, payload = run_cli(
        ["coefficients", "--model", str(workspace["clf_model"]), "--trust-model",
         "--output-dir", str(out)], capsys)
    assert code == 2 and payload["error"]["code"] == "invalid_input"
    assert (out / "keep.txt").read_text(encoding="utf-8") == "original"
    code, payload = run_cli(
        ["coefficients", "--model", str(workspace["clf_model"]), "--trust-model",
         "--output-dir", str(tmp_path / "fresh"), "--overwrite"], capsys)
    assert code == 2 and payload["error"]["code"] == "invalid_input"
    assert not (tmp_path / "fresh").exists()


def test_trust_is_required(workspace, capsys):
    code, payload = run_cli(
        ["coefficients", "--model", str(workspace["clf_model"]), "--check-only"], capsys)
    assert code == 2 and payload["error"]["code"] == "invalid_input"
    assert "trust" in payload["error"]["message"].lower()


def test_export_without_input_records_unverified(workspace, tmp_path, capsys):
    out = tmp_path / "unverified"
    code, payload = run_cli(
        ["coefficients", "--model", str(workspace["clf_model"]), "--trust-model",
         "--output-dir", str(out)], capsys)
    assert code == 0 and "error" not in payload
    assert payload["coefficients"]["verification"]["performed"] is False
    assert payload["coefficients"]["verification"]["verified"] is False


def test_manual_mapping_is_used_for_verification(workspace, capsys):
    frame = pd.read_csv(workspace["sample"])
    frame = frame[["group", "age", "score"]]
    shuffled = frame.copy()
    shuffled.to_csv(workspace["root"] / "shuffled.csv", index=False)
    code, payload = run_cli(
        ["coefficients", "--model", str(workspace["clf_model"]), "--trust-model",
         "--input", str(workspace["root"] / "shuffled.csv"),
         "--feature", "age", "--feature", "score", "--feature", "group",
         "--check-only"], capsys)
    assert code == 0 and "error" not in payload
    assert payload["coefficients"]["verification"]["verified"] is True


def test_failed_verification_reports_error_and_writes_nothing(workspace, tmp_path, capsys,
                                                              monkeypatch):
    from psyml.models import coefficients as coefficients_module

    def failing_verification(pipeline, verify_frame, report):
        return {
            "performed": True,
            "verified": False,
            "rows": len(verify_frame),
            "shape_ok": True,
            "finite": True,
            "max_abs_error": 1.0,
            "tolerance": {"atol": 1e-7, "rtol": 1e-6},
            "output_unit": report["output"]["unit"],
            "row_max_abs_error": [],
            "reference": "pipeline.predict",
            "note": "synthetic failing reconstruction for the CLI error-state test",
        }

    monkeypatch.setattr(coefficients_module, "verify_reconstruction", failing_verification)
    out = tmp_path / "failed_verification"
    code, payload = run_cli(
        ["coefficients", "--model", str(workspace["reg_model"]), "--trust-model",
         "--input", str(workspace["sample"]), "--output-dir", str(out)], capsys)
    assert code == 0 and "error" not in payload
    assert payload["coefficients"]["status"] == "error"
    assert payload["coefficients"]["verification"]["verified"] is False
    assert "artifacts" not in payload
    assert not out.exists()
