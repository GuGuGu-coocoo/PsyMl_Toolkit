"""Pin the runner progress contract the GUI interprets for the finishing state.

The desktop UI shows a dedicated "writing results" state from the existing
``phase=finalizing`` event, keeps the progress bar short of completion while
that phase is running and only treats the CLI ``completed`` event as finished.
These tests protect the event contract on the runner side without changing it:
the finalizing phase is reported last, and no ordinary progress event already
reports a full bar.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from psyml import ExperimentConfig, run_experiment

ROOT = Path(__file__).resolve().parents[1]


def _classification_frame() -> pd.DataFrame:
    values = np.arange(40, dtype=float)
    return pd.DataFrame(
        {
            "continuous": values,
            "category": ["a", "b"] * 20,
            "target": [0, 1] * 20,
        }
    )


def _events(config: ExperimentConfig, frame: pd.DataFrame | None) -> list[dict]:
    events: list[dict] = []
    run_experiment(config, frame, progress_callback=lambda event: events.append(dict(event)))
    return events


def test_finalizing_is_the_last_event_and_no_earlier_event_is_full(tmp_path):
    config = ExperimentConfig(
        task="classification",
        target_column="target",
        model_name="logistic_regression",
        output_dir=tmp_path / "finalizing",
        validation_strategy="holdout",
    )
    events = _events(config, _classification_frame())

    assert events
    assert events[-1]["phase"] == "finalizing"
    assert events[-1]["message"] == "Best model fitted on all analyzed rows"
    assert events[-1]["progress"] == 1.0
    # Only this finishing event may be at 100 %; the UI must never show a full
    # bar before it and only marks completion from the CLI `completed` event.
    assert all(event["progress"] < 1.0 for event in events[:-1])


def test_permutation_run_reports_finalizing_last(tmp_path):
    config = ExperimentConfig(
        task="classification",
        target_column="target",
        model_name="logistic_regression",
        output_dir=tmp_path / "permutation",
        validation_strategy="holdout",
        permutation_importance=True,
        permutation_repeats=2,
    )
    events = _events(config, _classification_frame())

    phases = [event["phase"] for event in events]
    assert phases[-1] == "finalizing"
    assert {"evaluating", "permutation_importance", "finalizing"} <= set(phases)
    assert all(event["progress"] < 1.0 for event in events[:-1])


def test_independent_validations_only_finalizing_reaches_a_full_bar(tmp_path):
    config = ExperimentConfig(
        task="classification",
        target_column="target",
        model_name="decision_tree",
        input_path=ROOT / "examples/synthetic/classification.csv",
        output_dir=tmp_path / "independent",
        feature_columns=["score", "category"],
        group_column="participant",
        validation_strategies=["holdout", "group_k_fold"],
        primary_validation=None,
        n_splits=3,
    )
    events = _events(config, None)

    finalizing = [event for event in events if event.get("phase") == "finalizing"]
    assert finalizing
    assert events[-1]["phase"] == "finalizing"
    # Each independent sub-run goes through the same finishing phase; only that
    # phase may already report 100 %, which the UI renders as writing results.
    assert all(
        event["progress"] < 1.0 or event.get("phase") == "finalizing" for event in events
    )
