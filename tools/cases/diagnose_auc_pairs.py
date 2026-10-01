"""Pairwise ranking diagnosis for a weighted OVR ROC-AUC difference.

Compares two row-aligned probability tables (for example a frozen reference and
a re-run) and reports, per class, which positive/negative pairs changed
ordering, whether ties appeared or disappeared, and how those changes add up to
the weighted one-vs-rest AUC difference:

    contribution_c = weight_c * net_concordant_pairs_c / (n_positive_c * n_negative_c)

A strict concordant flip adds one net pair, a resolved tie adds half a pair and
a new tie subtracts half a pair. With equal weights (the case default, 1/19
each) the sum over classes reproduces the weighted OVR AUC difference up to
floating-point rounding.

This is a diagnostic utility for recorded evidence. It never fits a model and is
not imported by the training, acceptance or reporting workflows.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

if __package__ in {None, ""}:  # direct script execution
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.cases import dsa_case

IDENTITY_COLUMNS = ("row_index", "fold", "observed")
CHANGED_PAIR_LIMIT = 5000


def probability_columns(table: pd.DataFrame) -> list[str]:
    """Return ``probability_<label>`` columns in table order, rejecting bad labels."""
    columns = [column for column in table.columns if column.startswith("probability_")]
    if not columns:
        raise ValueError("No probability_ columns were found")
    labels = []
    for column in columns:
        suffix = column.split("_", 1)[1]
        if not suffix.isdigit():
            raise ValueError(f"Probability column {column!r} does not end in a class label")
        labels.append(int(suffix))
    if len(labels) != len(set(labels)):
        raise ValueError("Probability columns contain duplicate class labels")
    if sorted(labels) != list(range(1, len(labels) + 1)):
        raise ValueError("Probability columns must cover class labels 1..N")
    return columns


def align_probability_tables(
    baseline: pd.DataFrame,
    alternative: pd.DataFrame,
    *,
    fold: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return row-aligned tables; refuse any identity or column-order mismatch."""
    if fold is not None:
        baseline = baseline.loc[baseline["fold"] == fold]
        alternative = alternative.loc[alternative["fold"] == fold]
    if len(baseline) == 0 or len(alternative) == 0:
        raise ValueError(f"Fold {fold} has no rows in one of the tables")
    baseline = baseline.sort_values(["row_index", "fold"]).reset_index(drop=True)
    alternative = alternative.sort_values(["row_index", "fold"]).reset_index(drop=True)
    for column in IDENTITY_COLUMNS:
        if column not in baseline.columns or column not in alternative.columns:
            raise ValueError(f"Both tables need a {column!r} column")
    if not baseline["row_index"].equals(alternative["row_index"]):
        raise ValueError("row_index sequences are not identical; refusing to compare")
    if not baseline["observed"].equals(alternative["observed"]):
        raise ValueError("observed labels are not identical; refusing to compare")
    if not baseline["fold"].equals(alternative["fold"]):
        raise ValueError("fold membership is not identical; refusing to compare")
    baseline_columns = probability_columns(baseline)
    alternative_columns = probability_columns(alternative)
    if baseline_columns != alternative_columns:
        raise ValueError(
            "Probability column order differs between the tables: "
            f"{baseline_columns} vs {alternative_columns}"
        )
    if len(baseline) != len(alternative):
        raise ValueError("Tables have different row counts; refusing to compare")
    return baseline, alternative


def pairwise_class_diagnostics(
    baseline_scores: np.ndarray,
    alternative_scores: np.ndarray,
    positive_mask: np.ndarray,
    *,
    class_weight: float,
) -> dict[str, Any]:
    """Compare one class' scores and report changed positive/negative pairs."""
    baseline_scores = np.asarray(baseline_scores, dtype=float)
    alternative_scores = np.asarray(alternative_scores, dtype=float)
    positive_mask = np.asarray(positive_mask, dtype=bool)
    if baseline_scores.shape != alternative_scores.shape or baseline_scores.ndim != 1:
        raise ValueError("Both score vectors must be one-dimensional and equally long")
    if positive_mask.shape != baseline_scores.shape:
        raise ValueError("The positive mask must align with the score vectors")
    positives = np.flatnonzero(positive_mask)
    negatives = np.flatnonzero(~positive_mask)
    if len(positives) == 0 or len(negatives) == 0:
        return {
            "positive_count": len(positives),
            "negative_count": len(negatives),
            "changed_pairs": 0,
            "strict_reversals": 0,
            "new_ties": 0,
            "broken_ties": 0,
            "net_concordant_pair_delta": 0.0,
            "contribution": 0.0,
            "skipped": "class has no positives or no negatives",
        }
    old = np.sign(baseline_scores[positives][:, None] - baseline_scores[negatives][None, :])
    new = np.sign(alternative_scores[positives][:, None] - alternative_scores[negatives][None, :])
    changed_mask = old != new
    deltas = (new - old) / 2.0
    net = float(deltas.sum())
    contribution = float(class_weight) * net / (len(positives) * len(negatives))
    changed_pairs = [
        {
            "positive_index": int(positives[position]),
            "negative_index": int(negatives[negative]),
            "baseline_sign": int(old[position, negative]),
            "alternative_sign": int(new[position, negative]),
        }
        for position, negative in np.argwhere(changed_mask)[:CHANGED_PAIR_LIMIT]
    ]
    return {
        "positive_count": len(positives),
        "negative_count": len(negatives),
        "changed_pairs": int(changed_mask.sum()),
        "strict_reversals": int(np.count_nonzero(old * new == -1)),
        "new_ties": int(np.count_nonzero((old != 0) & (new == 0))),
        "broken_ties": int(np.count_nonzero((old == 0) & (new != 0))),
        "net_concordant_pair_delta": net,
        "contribution": contribution,
        "changed_pair_details": changed_pairs,
    }


def pairwise_auc_diagnostics(
    baseline: pd.DataFrame,
    alternative: pd.DataFrame,
    *,
    class_weights: dict[int, float] | None = None,
) -> dict[str, Any]:
    """Report per-class pair changes and the total weighted OVR AUC contribution."""
    baseline, alternative = align_probability_tables(baseline, alternative)
    columns = probability_columns(baseline)
    labels = [int(column.split("_", 1)[1]) for column in columns]
    if class_weights is not None:
        unknown = set(class_weights) - set(labels)
        if unknown:
            raise ValueError(f"Class weights refer to unknown labels: {sorted(unknown)}")
        weights = {label: float(class_weights.get(label, 0.0)) for label in labels}
    else:
        weights = {label: 1.0 / len(labels) for label in labels}
    observed = baseline["observed"].to_numpy()
    per_class: list[dict[str, Any]] = []
    for column, label in zip(columns, labels):
        record = pairwise_class_diagnostics(
            baseline[column].to_numpy(dtype=float),
            alternative[column].to_numpy(dtype=float),
            observed == label,
            class_weight=weights[label],
        )
        record["class_label"] = int(label)
        per_class.append(record)
    total = float(sum(record["contribution"] for record in per_class))
    absolute = float(sum(abs(record["contribution"]) for record in per_class))
    return {
        "rows": len(baseline),
        "classes": labels,
        "class_weighting": "equal" if class_weights is None else "explicit",
        "per_class": per_class,
        "total_contribution": total,
        "total_absolute_contribution": absolute,
        "cancellation": {
            "classes_with_changes": sum(1 for record in per_class if record["changed_pairs"]),
            "net_equals_absolute": bool(abs(total - absolute) < 1e-18),
        },
        "changed_row_index": [
            int(index)
            for record in per_class
            for pair in record.get("changed_pair_details", [])
            for index in (pair["positive_index"], pair["negative_index"])
        ],
    }


def attach_identifiers(
    diagnostics: dict[str, Any], table: pd.DataFrame, segments: pd.Series | None
) -> None:
    """Map positional pair indices to row_index/segment_id in place."""
    row_index = table["row_index"].to_numpy()
    segment_values = None if segments is None else segments.to_numpy()
    for record in diagnostics["per_class"]:
        for pair in record.get("changed_pair_details", []):
            positive = int(pair["positive_index"])
            negative = int(pair["negative_index"])
            pair["positive_row_index"] = int(row_index[positive])
            pair["negative_row_index"] = int(row_index[negative])
            if segment_values is not None:
                pair["positive_segment_id"] = str(segment_values[positive])
                pair["negative_segment_id"] = str(segment_values[negative])


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--alternative", type=Path, required=True)
    parser.add_argument("--fold", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--segments",
        type=Path,
        default=None,
        help="Optional CSV with segment_id per row_index for readable pair identifiers",
    )
    args = parser.parse_args(argv)
    baseline = pd.read_csv(args.baseline)
    alternative = pd.read_csv(args.alternative)
    baseline, alternative = align_probability_tables(baseline, alternative, fold=args.fold)
    diagnostics = pairwise_auc_diagnostics(baseline, alternative)
    segments = None
    if args.segments is not None:
        source = pd.read_csv(args.segments)
        if not {"row_index", "segment_id"}.issubset(source.columns):
            raise ValueError("The segments CSV needs row_index and segment_id columns")
        segments = source.set_index("row_index")["segment_id"].reindex(baseline["row_index"])
    attach_identifiers(diagnostics, baseline, segments)
    diagnostics["fold"] = args.fold
    dsa_case.write_json(args.output, diagnostics)
    print(
        json.dumps(
            {
                "fold": args.fold,
                "rows": diagnostics["rows"],
                "total_contribution": diagnostics["total_contribution"],
                "total_absolute_contribution": diagnostics["total_absolute_contribution"],
                "classes_with_changes": [
                    record["class_label"]
                    for record in diagnostics["per_class"]
                    if record["changed_pairs"]
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
