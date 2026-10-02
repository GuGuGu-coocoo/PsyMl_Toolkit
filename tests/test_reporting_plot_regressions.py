"""Rendered regressions for fold SD and many-category distribution figures."""

from itertools import pairwise

import numpy as np
import pandas as pd
import pytest

from psyml import ExperimentConfig, run_experiment
from psyml.reporting import permutation, research


@pytest.fixture
def saved_figures(monkeypatch):
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib.figure import Figure

    figures = []
    savefig = Figure.savefig

    def capture(figure, *args, **kwargs):
        figures.append(figure)
        return savefig(figure, *args, **kwargs)

    monkeypatch.setattr(Figure, "savefig", capture)
    return figures


def _summary(folds, errors, means=None):
    count = len(folds)
    return pd.DataFrame(
        {
            "variable": [f"predictor_{index}" for index in range(count)],
            "metric": ["balanced_accuracy"] * count,
            "direction": ["higher_is_better"] * count,
            "n_folds_successful": folds,
            "fold_mean_equal_weight": means if means is not None else [0.3] * count,
            "between_fold_std": errors,
        }
    )


def _errorbar_segments(axis):
    from matplotlib.container import ErrorbarContainer

    return [
        segment
        for container in axis.containers
        if isinstance(container, ErrorbarContainer)
        for collection in container.lines[2]
        for segment in collection.get_segments()
    ]


@pytest.mark.parametrize(
    "successful_folds,contributing_folds,sd,expected_errorbar",
    [
        (3, 3, 0.2, True),  # F12: one predictor can have a valid between-fold SD.
        (3, 3, 0.0, True),  # Zero is a valid finite SD.
        (1, 1, 0.2, False),  # A supplied SD cannot invent a second fold.
        (3, 1, 0.2, False),
        (3, 3, np.nan, False),
        (3, 3, np.inf, False),
        (3, 3, -0.2, False),
    ],
)
def test_single_predictor_errorbar_uses_fold_count_and_finite_sd(
    tmp_path, saved_figures, successful_folds, contributing_folds, sd, expected_errorbar
):
    summary = _summary([contributing_folds], [sd])
    original = summary.copy(deep=True)
    output = tmp_path / "permutation.png"
    permutation._write_figure(
        output, "group_k_fold", summary, status="partial",
        successful_folds=successful_folds, planned_folds=4,
    )
    figure = saved_figures[0]
    segments = _errorbar_segments(figure.axes[0])
    assert bool(segments) is expected_errorbar
    caption = "\n".join(text.get_text() for text in figure.texts)
    if expected_errorbar:
        assert len(segments) == 1
        np.testing.assert_allclose(segments[0], [[0.3 - sd, 0.0], [0.3 + sd, 0.0]])
        assert "between-fold SD of fold means (ddof=1)" in caption
    else:
        assert "no error bars drawn" in caption
        if successful_folds >= 2:
            assert "fewer than two successful folds" not in caption
    assert f"{successful_folds}/4 folds successful, partial" in figure.axes[0].get_title()
    pd.testing.assert_frame_equal(summary, original)
    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_multiple_predictors_in_single_fold_never_draw_sd(tmp_path, saved_figures):
    permutation._write_figure(
        tmp_path / "one_fold.png", "holdout", _summary([1, 1], [0.1, 0.2]),
        status="completed", successful_folds=1, planned_folds=1,
    )
    assert _errorbar_segments(saved_figures[0].axes[0]) == []
    assert "fewer than two successful folds" in saved_figures[0].texts[0].get_text()


def test_unavailable_variable_sd_does_not_hide_other_valid_sd(tmp_path, saved_figures):
    summary = _summary([3, 1, 3], [0.2, 0.05, np.nan], means=[-0.3, 0.4, 0.1])
    original = summary.copy(deep=True)
    permutation._write_figure(
        tmp_path / "partial_sd.png", "group_k_fold", summary,
        status="partial", successful_folds=3, planned_folds=4,
    )
    figure = saved_figures[0]
    segments = _errorbar_segments(figure.axes[0])
    assert len(segments) == 1
    np.testing.assert_allclose(segments[0], [[-0.5, 0.0], [-0.1, 0.0]])
    assert "Only variables with at least two contributing folds" in figure.texts[0].get_text()
    assert [patch.get_x() for patch in figure.axes[0].patches] == [-0.3, 0.0, 0.0]
    pd.testing.assert_frame_equal(summary, original)


def test_legacy_summary_uses_explicit_validation_fold_count(tmp_path, saved_figures):
    summary = _summary([3], [0.2]).drop(columns="n_folds_successful")
    permutation._write_figure(
        tmp_path / "legacy.png", "group_k_fold", summary,
        status="completed", successful_folds=3, planned_folds=3,
    )
    assert len(_errorbar_segments(saved_figures[0].axes[0])) == 1


@pytest.mark.parametrize("class_count", [2, 8, 9, 19, 32, 64])
@pytest.mark.parametrize("dpi", [100, 160])
def test_exported_class_labels_have_disjoint_renderer_bboxes(
    tmp_path, saved_figures, class_count, dpi
):
    from matplotlib.backends.backend_agg import FigureCanvasAgg

    # Off-diagonal entries ensure row/column totals genuinely differ.
    values = np.diag(np.arange(1, class_count + 1))
    values[0, -1] = 7
    confusion = pd.DataFrame(values)
    original = confusion.copy(deep=True)
    config = ExperimentConfig(
        task="classification", target_column="target",
        model_name="decision_tree", figure_types=["class_distribution"],
    )
    research._write_figure(tmp_path, config, pd.DataFrame(), confusion)
    figure = saved_figures[0]
    axis = figure.axes[0]
    figure.set_dpi(dpi)
    canvas = FigureCanvasAgg(figure)
    canvas.draw()
    renderer = canvas.get_renderer()
    ticks = axis.get_xticklabels()
    assert [tick.get_text() for tick in ticks] == [
        f"Class {index + 1}" for index in range(class_count)
    ]
    bounds = [tick.get_window_extent(renderer) for tick in ticks]
    for left, right in pairwise(bounds):
        assert left.x1 + 1 < right.x0, (class_count, dpi, left, right)
    for bound in bounds:
        assert figure.bbox.contains(bound.x0, bound.y0)
        assert figure.bbox.contains(bound.x1, bound.y1)
    np.testing.assert_array_equal(
        [bar.get_height() for bar in axis.containers[0]], values.sum(axis=1)
    )
    np.testing.assert_array_equal(
        [bar.get_height() for bar in axis.containers[1]], values.sum(axis=0)
    )
    pd.testing.assert_frame_equal(confusion, original)
    assert (tmp_path / "class_distribution.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_class_distribution_style_rejects_empty_classes():
    with pytest.raises(ValueError, match="at least one class"):
        research._class_distribution_style(0)


def test_class_distribution_preserves_numerical_export_files(tmp_path):
    labels = np.tile(np.arange(19), 8)
    frame = pd.DataFrame({"predictor": labels.astype(float), "target": labels})
    for name, figures in (("with_figure", ["class_distribution"]), ("without_figure", [])):
        config = ExperimentConfig(
            task="classification", target_column="target", model_name="decision_tree",
            validation_strategy="k_fold", n_splits=3, inner_splits=2,
            figure_types=figures, output_dir=tmp_path / name, random_seed=7,
        )
        run_experiment(config, frame)
    for name in ("confusion_matrix.csv", "predictions.csv", "metrics.csv", "fold_metrics.csv"):
        assert (tmp_path / "with_figure" / name).read_bytes() == (
            tmp_path / "without_figure" / name
        ).read_bytes()
