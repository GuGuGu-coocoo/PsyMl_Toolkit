import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from psyml import ExperimentConfig, run_experiment
from psyml.reporting import research as reporting


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
    assert "Fold means are unweighted" in methods
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


def _pyplot():
    """Return a headless pyplot module without depending on the test order."""
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    return plt


def test_confusion_matrix_style_scales_with_class_count():
    small = reporting._confusion_matrix_style(2)
    medium = reporting._confusion_matrix_style(12)
    large = reporting._confusion_matrix_style(19)
    assert small["figure_size"] == (6.0, 5.2)
    assert small["annotate_zeros"] is True
    assert medium["annotate_zeros"] is True
    assert large["annotate_zeros"] is False
    assert large["figure_size"][0] > medium["figure_size"][0] > small["figure_size"][0]
    assert large["figure_size"][1] > small["figure_size"][1]
    assert large["tick_fontsize"] < medium["tick_fontsize"] < small["tick_fontsize"]
    assert large["annotation_fontsize"] < small["annotation_fontsize"]
    assert small["rotation"] == 30.0
    assert large["rotation"] == 90.0
    with pytest.raises(ValueError):
        reporting._confusion_matrix_style(0)


def test_confusion_matrix_figure_keeps_all_categories_and_nonzero_counts():
    values = np.zeros((19, 19), dtype=int)
    values[0, 0] = 123
    values[5, 7] = 7
    values[18, 18] = 4560
    labels = [f"Class {index + 1}" for index in range(19)]
    style = reporting._confusion_matrix_style(len(values))
    original = values.copy()
    plt = _pyplot()
    figure, axis = plt.subplots(figsize=style["figure_size"])
    reporting._draw_confusion_matrix(axis, values, labels, style)
    assert sorted(text.get_text() for text in axis.texts) == ["123", "4560", "7"]
    assert [tick.get_text() for tick in axis.get_xticklabels()] == labels
    assert [tick.get_text() for tick in axis.get_yticklabels()] == labels
    assert axis.get_xlabel() == "Predicted"
    assert axis.get_ylabel() == "Observed"
    # Drawing must not touch the counts or the matrix they came from.
    assert np.array_equal(values, original)
    plt.close(figure)


def test_small_confusion_matrix_keeps_zero_annotations():
    values = np.array([[3, 0], [0, 4]])
    style = reporting._confusion_matrix_style(len(values))
    plt = _pyplot()
    figure, axis = plt.subplots(figsize=style["figure_size"])
    reporting._draw_confusion_matrix(axis, values, ["Class 1", "Class 2"], style)
    assert sorted(text.get_text() for text in axis.texts) == ["0", "0", "3", "4"]
    plt.close(figure)


def _cjk_font_family():
    """Return an installed CJK-capable family, or None when the host has none."""
    from matplotlib import font_manager

    available = {font.name for font in font_manager.fontManager.ttflist}
    for candidate in (
        "Noto Sans CJK SC",
        "PingFang SC",
        "Hiragino Sans GB",
        "Heiti SC",
        "Arial Unicode MS",
    ):
        if candidate in available:
            return candidate
    return None


def test_confusion_matrix_scenarios_export_pngs(tmp_path):
    import warnings

    import matplotlib

    long_labels = [
        "A very long category name one",
        "Second long category name here",
        "Third category with a long name",
        "Fourth long category label",
        "Fifth label that is long too",
        "Sixth long category name",
    ]
    scenarios = {
        "binary": (np.array([[18, 2], [3, 17]]), ["Class 1", "Class 2"]),
        "few_classes": (np.arange(25).reshape(5, 5), [f"Class {i + 1}" for i in range(5)]),
        "long_labels": (np.eye(6, dtype=int), long_labels),
        "cjk_labels": (
            np.eye(4, dtype=int) + np.fliplr(np.eye(4, dtype=int)),
            ["类别一", "类别二（较长的中文名称）", "类别三", "类别四"],
        ),
        "all_zero_matrix": (np.zeros((3, 3), dtype=int), ["Class 1", "Class 2", "Class 3"]),
        "missing_class_row": (
            np.array([[4, 0, 0], [0, 0, 0], [0, 0, 2]]),
            ["Class 1", "Class 2", "Class 3"],
        ),
        "nineteen_classes": (np.diag(np.arange(1, 20)), [f"Class {i + 1}" for i in range(19)]),
    }
    plt = _pyplot()
    cjk_family = _cjk_font_family()
    previous_family = matplotlib.rcParams["font.family"]
    try:
        for name, (values, labels) in scenarios.items():
            if name == "cjk_labels" and cjk_family is not None:
                matplotlib.rcParams["font.family"] = [cjk_family, "DejaVu Sans"]
            with warnings.catch_warnings():
                if name == "cjk_labels" and cjk_family is None:
                    # Glyph coverage depends on the host's installed fonts; this
                    # test covers layout, and a host without CJK fonts cannot
                    # render these labels anyway.
                    warnings.filterwarnings("ignore", message="Glyph .* missing from font")
                style = reporting._confusion_matrix_style(len(values))
                figure, axis = plt.subplots(figsize=style["figure_size"])
                reporting._draw_confusion_matrix(axis, values, labels, style)
                figure.tight_layout()
                path = tmp_path / f"{name}.png"
                figure.savefig(path, dpi=160)
                plt.close(figure)
            assert path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    finally:
        matplotlib.rcParams["font.family"] = previous_family


def test_confusion_figure_keeps_prediction_and_metric_files_identical(tmp_path):
    rows = []
    for group in range(6):
        for index in range(15):
            label = index % 3
            rows.append({"score": group * 100 + index * 3 + label, "group": group, "label": label})
    frame = pd.DataFrame(rows)
    outputs = {}
    for name, figures in (("with_figure", ["confusion_matrix"]), ("without_figure", [])):
        output_dir = tmp_path / name
        config = ExperimentConfig(
            task="classification",
            target_column="label",
            group_column="group",
            model_name="logistic_regression",
            output_dir=output_dir,
            validation_strategy="group_k_fold",
            n_splits=3,
            figure_types=figures,
            random_seed=7,
        )
        run_experiment(config, frame)
        outputs[name] = output_dir
    with_figure = outputs["with_figure"]
    without_figure = outputs["without_figure"]
    for name in ("confusion_matrix.csv", "predictions.csv", "metrics.csv", "fold_metrics.csv"):
        assert (with_figure / name).read_bytes() == (without_figure / name).read_bytes()
    assert not (without_figure / "figures" / "confusion_matrix.png").exists()
    assert (with_figure / "figures" / "confusion_matrix.png").is_file()
