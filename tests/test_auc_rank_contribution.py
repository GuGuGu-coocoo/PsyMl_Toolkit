"""Unit tests for the pairwise ranking contribution diagnostics.

Small arrays only: no model fitting, no case data and no network. The tests pin
the sign conventions (strict flip, new tie, resolved tie), cancellation,
explicit class weights, alignment rejection and the match against the weighted
OVR AUC difference.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import roc_auc_score

from tools.cases import diagnose_auc_pairs


def _table(probabilities: np.ndarray, observed: np.ndarray) -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "row_index": np.arange(len(observed)),
            "fold": 1,
            "observed": observed,
        }
    )
    for index in range(probabilities.shape[1]):
        frame[f"probability_{index + 1}"] = probabilities[:, index]
    return frame


def test_no_change_yields_zero_contribution():
    probabilities = np.array([[0.9, 0.1], [0.8, 0.2], [0.2, 0.8], [0.1, 0.9]])
    observed = np.array([1, 1, 2, 2])
    diagnostics = diagnose_auc_pairs.pairwise_auc_diagnostics(
        _table(probabilities, observed), _table(probabilities.copy(), observed)
    )
    assert diagnostics["total_contribution"] == 0.0
    assert diagnostics["total_absolute_contribution"] == 0.0
    assert all(record["changed_pairs"] == 0 for record in diagnostics["per_class"])


def test_single_strict_flip_contributes_one_pair_unit():
    baseline = np.array([0.9, 0.8, 0.2, 0.1, 0.05])
    alternative = np.array([0.15, 0.8, 0.2, 0.1, 0.05])
    mask = np.array([True, True, False, False, False])
    record = diagnose_auc_pairs.pairwise_class_diagnostics(
        baseline, alternative, mask, class_weight=1.0 / 2
    )
    assert record["changed_pairs"] == 1
    assert record["strict_reversals"] == 1
    assert record["new_ties"] == 0
    assert record["broken_ties"] == 0
    assert record["net_concordant_pair_delta"] == -1.0
    assert record["contribution"] == pytest.approx(-(1.0 / 2) / (2 * 3))
    assert record["changed_pair_details"] == [
        {"positive_index": 0, "negative_index": 2, "baseline_sign": 1, "alternative_sign": -1}
    ]


def test_new_tie_and_resolved_tie_contribute_half_units():
    combined = diagnose_auc_pairs.pairwise_class_diagnostics(
        np.array([0.9, 0.7, 0.3]), np.array([0.7, 0.7, 0.3]), np.array([True, False, False]),
        class_weight=1.0,
    )
    # Positive 0 versus negative 0: 0.9 > 0.7 became 0.7 == 0.7 (a new tie);
    # positive 0 versus negative 1 stays concordant.
    assert combined["new_ties"] == 1
    assert combined["broken_ties"] == 0
    assert combined["net_concordant_pair_delta"] == -0.5
    assert combined["contribution"] == pytest.approx(-0.5 / 2)

    resolved = diagnose_auc_pairs.pairwise_class_diagnostics(
        np.array([0.5, 0.5]), np.array([0.6, 0.5]), np.array([True, False]), class_weight=1.0
    )
    assert resolved["broken_ties"] == 1
    assert resolved["new_ties"] == 0
    assert resolved["net_concordant_pair_delta"] == 0.5
    assert resolved["contribution"] == pytest.approx(0.5)


def test_opposite_changes_cancel_in_the_total():
    observed = np.array([1, 2])
    baseline = np.array([[0.9, 0.2], [0.1, 0.15]])
    alternative = np.array([[0.05, 0.2], [0.1, 0.25]])
    diagnostics = diagnose_auc_pairs.pairwise_auc_diagnostics(
        _table(baseline, observed), _table(alternative, observed)
    )
    contributions = {record["class_label"]: record for record in diagnostics["per_class"]}
    assert contributions[1]["net_concordant_pair_delta"] == -1.0
    assert contributions[2]["net_concordant_pair_delta"] == 1.0
    assert diagnostics["total_contribution"] == 0.0
    assert diagnostics["total_absolute_contribution"] > 0.0
    assert diagnostics["cancellation"]["net_equals_absolute"] is False


def test_explicit_class_weights_scale_contributions_and_reject_unknown_labels():
    probabilities = np.array(
        [[0.9, 0.5], [0.8, 0.5], [0.1, 0.5], [0.2, 0.5]]
    )
    observed = np.array([1, 1, 2, 2])
    alternative = probabilities.copy()
    alternative[0, 0] = 0.05
    baseline_table = _table(probabilities, observed)
    alternative_table = _table(alternative, observed)
    equal = diagnose_auc_pairs.pairwise_auc_diagnostics(baseline_table, alternative_table)
    weighted = diagnose_auc_pairs.pairwise_auc_diagnostics(
        baseline_table, alternative_table, class_weights={1: 1.0, 2: 0.0}
    )
    equal_class_one = next(r for r in equal["per_class"] if r["class_label"] == 1)
    weighted_class_one = next(r for r in weighted["per_class"] if r["class_label"] == 1)
    assert weighted_class_one["contribution"] == pytest.approx(
        equal_class_one["contribution"] * 2
    )
    assert weighted["total_contribution"] == pytest.approx(weighted_class_one["contribution"])
    with pytest.raises(ValueError):
        diagnose_auc_pairs.pairwise_auc_diagnostics(
            baseline_table, alternative_table, class_weights={7: 1.0}
        )


def test_alignment_rejects_misaligned_rows_and_columns():
    probabilities = np.array([[0.9, 0.1], [0.8, 0.2], [0.1, 0.9], [0.2, 0.8]])
    observed = np.array([1, 1, 2, 2])
    baseline_table = _table(probabilities, observed)
    alternative_table = _table(probabilities.copy(), observed)

    mismatched_rows = alternative_table.copy()
    mismatched_rows["row_index"] = [0, 1, 2, 9]
    with pytest.raises(ValueError):
        diagnose_auc_pairs.align_probability_tables(baseline_table, mismatched_rows)

    with pytest.raises(ValueError):
        diagnose_auc_pairs.align_probability_tables(baseline_table, alternative_table.iloc[:-1])

    changed_labels = alternative_table.copy()
    changed_labels.loc[0, "observed"] = 2
    with pytest.raises(ValueError):
        diagnose_auc_pairs.align_probability_tables(baseline_table, changed_labels)

    swapped_columns = alternative_table[["row_index", "fold", "observed", "probability_2", "probability_1"]]
    with pytest.raises(ValueError):
        diagnose_auc_pairs.align_probability_tables(baseline_table, swapped_columns)

    missing_identity = alternative_table.drop(columns=["observed"])
    with pytest.raises(ValueError):
        diagnose_auc_pairs.align_probability_tables(baseline_table, missing_identity)

    duplicate_labels = alternative_table.rename(columns={"probability_2": "probability_1"})
    with pytest.raises(ValueError):
        diagnose_auc_pairs.align_probability_tables(baseline_table, duplicate_labels)


def test_total_contribution_matches_weighted_ovr_auc_difference():
    rng = np.random.default_rng(20261001)
    class_count = 4
    per_class = 5
    observed = np.repeat(np.arange(1, class_count + 1), per_class)
    baseline = rng.random((len(observed), class_count))
    baseline /= baseline.sum(axis=1, keepdims=True)
    alternative = baseline + rng.normal(scale=0.02, size=baseline.shape)
    alternative /= alternative.sum(axis=1, keepdims=True)
    labels = list(range(1, class_count + 1))
    expected = float(
        roc_auc_score(observed, alternative, multi_class="ovr", average="weighted", labels=labels)
        - roc_auc_score(observed, baseline, multi_class="ovr", average="weighted", labels=labels)
    )
    diagnostics = diagnose_auc_pairs.pairwise_auc_diagnostics(
        _table(baseline, observed), _table(alternative, observed)
    )
    assert diagnostics["total_contribution"] == pytest.approx(expected, abs=1e-12)
