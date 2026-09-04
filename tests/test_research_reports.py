import hashlib
import json

import numpy as np
import pandas as pd

from psyml import ExperimentConfig, run_experiment


def test_regression_research_outputs_match_executed_file_run(tmp_path):
    private_directory = tmp_path / "Sensitive Participant Folder"
    private_directory.mkdir()
    input_path = private_directory / "input.csv"
    values = np.linspace(0, 8, 32)
    pd.DataFrame({"predictor": values, "outcome": values * 1.5 + 2}).to_csv(input_path, index=False)
    output_dir = tmp_path / "result 中文"
    config = ExperimentConfig(
        task="regression",
        target_column="outcome",
        model_name="ridge",
        model_params={"alpha": 0.25},
        input_path=input_path,
        output_dir=output_dir,
        validation_strategy="k_fold",
        n_splits=4,
        missing_strategy="mean",
        scaling="minmax",
        random_seed=19,
    )

    run_experiment(config)

    manifest = json.loads((output_dir / "analysis_manifest.json").read_text(encoding="utf-8"))
    expected_hash = hashlib.sha256(input_path.read_bytes()).hexdigest()
    assert manifest["schema_version"] == "1.0"
    assert manifest["data"] == {
        "source_kind": "file",
        "input_rows": 32,
        "input_columns": 2,
        "analyzed_rows": 32,
        "feature_columns": 1,
        "sha256": expected_hash,
        "hash_basis": "source_file_bytes",
    }
    assert {"numpy", "pandas", "scikit-learn", "matplotlib"} <= set(manifest["dependencies"])

    methods = (output_dir / "methods_summary.md").read_text(encoding="utf-8")
    report = (output_dir / "reproducibility_report.md").read_text(encoding="utf-8")
    assert "`ridge`" in methods
    assert "4-fold cross-validation" in methods
    assert '"alpha": 0.25' in methods
    assert "metrics_summary.csv" not in methods
    assert expected_hash in report
    assert "Sensitive Participant Folder" not in report
    figure = output_dir / "figures" / "observed_vs_predicted.png"
    assert figure.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_classification_report_omits_data_values_and_can_disable_hash(tmp_path):
    frame = pd.DataFrame(
        {
            "score": np.arange(40),
            "participant": [f"secret-person-{index // 2}" for index in range(40)],
            "diagnosis": ["private-label-a", "private-label-b"] * 20,
        }
    )
    output_dir = tmp_path / "classification"
    config = ExperimentConfig(
        task="classification",
        target_column="diagnosis",
        group_column="participant",
        model_name="logistic_regression",
        output_dir=output_dir,
        validation_strategy="group_k_fold",
        n_splits=4,
        include_data_hash=False,
    )

    run_experiment(config, frame)

    manifest_text = (output_dir / "analysis_manifest.json").read_text(encoding="utf-8")
    methods = (output_dir / "methods_summary.md").read_text(encoding="utf-8")
    report = (output_dir / "reproducibility_report.md").read_text(encoding="utf-8")
    manifest = json.loads(manifest_text)
    assert manifest["data"]["sha256"] is None
    assert "secret-person" not in manifest_text + methods + report
    assert "private-label" not in manifest_text + methods + report
    assert "The grouping variable `participant` was excluded" in methods
    figure = output_dir / "figures" / "confusion_matrix.png"
    assert figure.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
