"""CLI end-to-end tests for the single-sample explanation command."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from psyml import ExperimentConfig, run_experiment
from psyml.cli import main

shap = pytest.importorskip("shap", reason="optional explain extra not installed")


@pytest.fixture(scope="module")
def workspace(tmp_path_factory):
    root = tmp_path_factory.mktemp("explain_cli")
    rng = np.random.default_rng(11)
    features = pd.DataFrame({
        "age": rng.normal(size=90),
        "score": rng.normal(size=90),
        "group": (["a", "b", "c"] * 30),
    })
    features.to_csv(root / "sample.csv", index=False)
    features.iloc[:40].to_csv(root / "background.csv", index=False)

    clf_frame = features.copy()
    clf_frame["target"] = ((features["score"] + 0.2) > 0).astype(int)
    clf = ExperimentConfig(task="classification", model_name="decision_tree",
                           target_column="target", output_dir=root / "clf_run", figure_types=[])
    clf_result = run_experiment(clf, clf_frame)
    clf_model = clf.output_dir / clf_result.model_export["model_path"]

    reg_frame = features.copy()
    reg_frame["value"] = 3 * features["age"] - features["score"] + 1.0
    reg = ExperimentConfig(task="regression", model_name="ridge", target_column="value",
                           output_dir=root / "reg_run", figure_types=[])
    reg_result = run_experiment(reg, reg_frame)
    reg_model = reg.output_dir / reg_result.model_export["model_path"]
    return {"root": root, "clf_model": clf_model, "reg_model": reg_model,
            "sample": root / "sample.csv", "background": root / "background.csv"}


def base_args(workspace, model="clf_model"):
    return ["--model", str(workspace[model]), "--input", str(workspace["sample"]),
            "--background", str(workspace["background"]), "--trust-model"]


def run_cli(args, capsys):
    code = main(args)
    captured = capsys.readouterr()
    text = captured.out + captured.err
    payload = json.loads(text.strip().splitlines()[-1]) if text.strip() else {}
    return code, payload


def test_explain_classification_writes_real_artifacts(workspace, tmp_path, capsys):
    out = tmp_path / "explained"
    code, payload = run_cli(
        ["explain"] + base_args(workspace) + ["--row", "4", "--class-index", "1",
                                              "--background-size", "20", "--cycles", "3",
                                              "--output-dir", str(out)], capsys)
    assert code == 0 and "error" not in payload
    assert payload["explanation"]["output_space"] == "probability"
    assert payload["explanation"]["reconstruction_abs_error"] <= 1e-7
    for path in payload["artifacts"].values():
        assert Path(path).is_file()
    saved = json.loads((out / "shap_explanation.json").read_text())
    assert saved["schema_version"] == "1.0" and saved["approximate"] is True


def test_explain_regression(workspace, tmp_path, capsys):
    out = tmp_path / "reg_explained"
    code, payload = run_cli(
        ["explain"] + base_args(workspace, "reg_model") + ["--row", "2",
                                                           "--background-size", "15",
                                                           "--cycles", "2",
                                                           "--output-dir", str(out)], capsys)
    assert code == 0 and "error" not in payload
    assert payload["explanation"]["output_space"] == "predicted_value"
    assert payload["explanation"]["target_class"] is None


def test_check_only_does_not_create_output(workspace, tmp_path, capsys):
    out = tmp_path / "never"
    code, payload = run_cli(
        ["explain"] + base_args(workspace) + ["--row", "4", "--class-index", "0",
                                              "--background-size", "50", "--cycles", "5",
                                              "--output-dir", str(out), "--check-only"], capsys)
    assert code == 0
    assert payload["check_only"] is True
    assert payload["explanation"]["shap_installed"] is True
    assert not out.exists()


def test_trust_gate_blocks_without_flag(workspace, capsys):
    args = ["explain", "--model", str(workspace["clf_model"]),
            "--input", str(workspace["sample"]), "--background", str(workspace["background"]),
            "--row", "4", "--class-index", "0", "--check-only"]
    code, payload = run_cli(args, capsys)
    assert code == 2
    assert payload["error"]["code"] == "invalid_input"
    assert "trust" in payload["error"]["message"].lower()


@pytest.mark.parametrize(
    "extra",
    [
        ["--row", "0", "--class-index", "0"],
        ["--row", "4"],
        ["--row", "4", "--class-index", "9"],
        ["--row", "4", "--class-index", "0", "--background-size", "0"],
        ["--row", "4", "--class-index", "0", "--cycles", "99"],
    ],
)
def test_invalid_arguments_return_json_errors(workspace, extra, capsys):
    args = ["explain"] + base_args(workspace) + extra + ["--check-only"]
    code, payload = run_cli(args, capsys)
    assert code == 2
    assert payload["error"]["code"] == "invalid_input"


def test_nonempty_output_directory_is_preserved_without_overwrite(workspace, capsys):
    root = workspace["root"]
    out = root / "occupied"
    out.mkdir(exist_ok=True)
    (out / "user.txt").write_text("keep me")
    args = ["explain"] + base_args(workspace) + ["--row", "4", "--class-index", "0",
                                                 "--background-size", "10", "--cycles", "2",
                                                 "--output-dir", str(out)]
    code, _payload = run_cli(args, capsys)
    assert code == 2
    assert (out / "user.txt").read_text() == "keep me"
    assert not (out / "shap_explanation.json").exists()


def test_explain_overwrite_flag_is_rejected(workspace, tmp_path, capsys):
    out = tmp_path / "fresh"
    code, payload = run_cli(
        ["explain"] + base_args(workspace) + ["--row", "4", "--class-index", "0",
                                              "--background-size", "10", "--cycles", "2",
                                              "--output-dir", str(out), "--overwrite"], capsys)
    assert code == 2
    assert payload["error"]["code"] == "invalid_input"
    assert "overwrite" in payload["error"]["message"].lower()
    assert not out.exists()


def test_ordinary_predict_is_unaffected(workspace, tmp_path, capsys):
    out = tmp_path / "prediction.csv"
    code, payload = run_cli(
        ["predict", "--model", str(workspace["clf_model"]), "--input", str(workspace["sample"]),
         "--output", str(out), "--trust-model"], capsys)
    assert code == 0 and payload["compatibility"]["compatible"]
    assert out.is_file()


def _drop_shap_modules():
    import sys

    for name in list(sys.modules):
        if name == "shap" or name.startswith("shap."):
            del sys.modules[name]


def test_explanation_module_import_is_lazy():
    import importlib
    import sys

    _drop_shap_modules()
    importlib.reload(importlib.import_module("psyml.explanation"))
    assert "shap" not in sys.modules


def test_prediction_commands_do_not_import_shap(workspace, capsys):
    import sys

    _drop_shap_modules()
    code, _payload = run_cli(
        ["model-info", "--model", str(workspace["clf_model"]), "--trust-model"], capsys)
    assert code == 0
    code, _payload = run_cli(
        ["predict", "--model", str(workspace["clf_model"]), "--input", str(workspace["sample"]),
         "--check-only", "--trust-model"], capsys)
    assert code == 0
    assert "shap" not in sys.modules


def test_feature_flag_is_accepted_for_named_models(workspace, tmp_path, capsys):
    out = tmp_path / "mapped"
    code, payload = run_cli(
        ["explain"] + base_args(workspace) + ["--row", "1", "--class-index", "0",
                                              "--background-size", "8", "--cycles", "2",
                                              "--feature", "age", "--feature", "score",
                                              "--feature", "group", "--output-dir", str(out)],
        capsys)
    assert code == 0 and "error" not in payload
    assert payload["explanation"]["feature_order"] == ["age", "score", "group"]
