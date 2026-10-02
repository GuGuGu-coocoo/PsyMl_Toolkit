"""Successful runs must persist optimizer and estimator warnings.

The CLI stderr used to be the only place where scikit-learn warnings appeared,
while warnings.json, result.json and the GUI reported "none recorded". These
tests pin the warning capture for inner, outer and final fits: context fields,
duplicate merging, report persistence and the promise that a warning alone
never fails an otherwise valid run.
"""

from __future__ import annotations

import json
import warnings

import numpy as np
import pandas as pd

from psyml import ExperimentConfig, run_experiment
from psyml.runner import _FitWarningCollector


def _classification_frame(rows: int = 40) -> pd.DataFrame:
    rng = np.random.RandomState(0)
    features = rng.rand(rows, 3)
    return pd.DataFrame(
        {
            "f1": features[:, 0],
            "f2": features[:, 1],
            "f3": features[:, 2],
            "target": [0, 1] * (rows // 2),
        }
    )


def _config(tmp_path, **overrides) -> ExperimentConfig:
    settings = {
        "task": "classification",
        "target_column": "target",
        "model_name": "logistic_regression",
        "output_dir": tmp_path / "run",
        "random_seed": 1,
    }
    settings.update(overrides)
    return ExperimentConfig(**settings)


def test_convergence_warnings_reach_reports_after_successful_run(tmp_path):
    config = _config(tmp_path, model_params={"max_iter": 1})
    result = run_experiment(config, _classification_frame())
    assert result.metrics  # a warning alone must not fail the run

    by_scope = {entry["scope"]: entry for entry in result.fit_warnings}
    assert "outer" in by_scope and "final" in by_scope
    outer = by_scope["outer"]
    assert outer["category"] == "ConvergenceWarning"
    assert outer["model"] == "logistic_regression"
    assert outer["validation"] == "holdout"
    assert outer["fold"] == 1
    assert outer["count"] >= 1
    assert outer["parameters"] == {"max_iter": 1}
    assert "failed to converge" in outer["message"]

    assert any("ConvergenceWarning" in line for line in result.warnings)
    payload = json.loads((config.output_dir / "result.json").read_text(encoding="utf-8"))
    assert payload["status"] == "completed"
    assert any(entry["category"] == "ConvergenceWarning" for entry in payload["fit_warnings"])
    assert any("ConvergenceWarning" in line for line in payload["warnings"])
    warnings_json = json.loads((config.output_dir / "warnings.json").read_text(encoding="utf-8"))
    assert any("ConvergenceWarning" in line for line in warnings_json)
    report = (config.output_dir / "reproducibility_report.md").read_text(encoding="utf-8")
    assert "ConvergenceWarning" in report


def test_inner_selection_warnings_carry_candidate_context(tmp_path):
    config = _config(
        tmp_path,
        tuning_mode="custom",
        parameter_grids={"logistic_regression": {"max_iter": [1, 2]}},
        max_candidates=5,
    )
    result = run_experiment(config, _classification_frame())
    inner = [entry for entry in result.fit_warnings if entry["scope"] == "inner"]
    assert inner
    # Inner candidates are fitted both per outer fold and once more for the
    # final full-data selection; both scopes must carry the candidate context.
    assert any(entry["fold"] >= 1 for entry in inner)
    assert any(entry["fold"] == 0 for entry in inner)
    assert any(entry["parameters"] == {"max_iter": 1} for entry in inner)
    assert {entry["category"] for entry in inner} == {"ConvergenceWarning"}


def test_warning_collector_merges_repeated_contexts():
    collector = _FitWarningCollector()

    def fit() -> None:
        warnings.warn("same context", UserWarning, stacklevel=1)
        warnings.warn("same context", UserWarning, stacklevel=1)

    with collector.capture(
        scope="outer", model="m", validation="holdout", fold=1, parameters={"max_iter": 1}
    ):
        fit()
    records = collector.records()
    assert len(records) == 1
    assert records[0]["count"] == 2
    assert "(x2)" in collector.lines()[0]
    assert "\n" not in collector.lines()[0]
