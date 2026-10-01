"""Contract tests for the public DSA acceptance case.

Default run: no network, no download and no 9120-row fit. These tests pin the
archive/enumeration/feature contract with small synthetic Zips, check the
repository example configuration and verify the independent reference selects
and exports as specified on a tiny grouped data set. The real frozen 9,120-row
verification is an explicit, slow case command, never part of the quick suite.
"""

from __future__ import annotations

import ast
import hashlib
import json
import warnings
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score

from tools.cases import check_dsa_controls, compare_dsa, dsa_case, prepare_dsa, reference_dsa

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_CONFIG = ROOT / "examples/public/configs/dsa_group_nested_v1.json"
EXPECTED_DIR = ROOT / "examples/public/dsa_group_nested_v1/expected"


def _segment_text(values: np.ndarray) -> str:
    rows = [",".join(repr(float(value)) for value in row) for row in values]
    return "\n".join(rows)


def build_mini_archive(
    path: Path,
    *,
    activities=(1, 2),
    participants=(1,),
    segments=(1, 2),
    rows: int = 3,
    columns: int = 7,
    overrides: dict[str, np.ndarray] | None = None,
) -> dict[str, np.ndarray]:
    """Create a minimal legal archive and return the raw values per member."""
    rng = np.random.default_rng(20261001)
    values_by_member: dict[str, np.ndarray] = {}
    with zipfile.ZipFile(path, "w") as bundle:
        for activity in activities:
            for participant in participants:
                for segment in segments:
                    name = prepare_dsa.member_name(activity, participant, segment)
                    values = rng.normal(size=(rows, columns))
                    values_by_member[name] = values
                    bundle.writestr(name, _segment_text(values))
    if overrides:
        with zipfile.ZipFile(path, "a") as bundle:
            for name, values in overrides.items():
                bundle.writestr(name, _segment_text(values))
                values_by_member[name] = values
    return values_by_member


def _mini_config(tmp_path: Path, **overrides) -> Path:
    data = tmp_path / "mini.csv"
    rows = []
    rng = np.random.default_rng(5)
    for subject in (1, 2, 3, 4):
        for label in (1, 2):
            for _ in range(3):
                rows.append(
                    {
                        "x1": float(rng.normal()),
                        "x2": float(rng.normal()),
                        "y_label": label,
                        "subject_id": subject,
                    }
                )
    pd.DataFrame(rows).to_csv(data, index=False)
    config = {
        "schema_version": "1.0",
        "task": "classification",
        "target_column": "y_label",
        "model_name": "dummy",
        "input_path": str(data),
        "output_dir": str(tmp_path / "ignored"),
        "group_column": "subject_id",
        "feature_columns": ["x1", "x2"],
        "test_size": 0.2,
        "random_seed": 20261001,
        "validation_strategy": "group_k_fold",
        "primary_validation": "group_k_fold",
        "n_splits": 2,
        "inner_splits": 2,
        "missing_strategy": "median",
        "scaling": "standard",
        "save_best_model": True,
        "include_data_hash": True,
        "model_names": ["dummy", "logistic_regression"],
        "model_params": {},
        "tuning_mode": "custom",
        "selection_metric": "balanced_accuracy",
        "parameter_grids": {
            "dummy": {"strategy": ["prior"]},
            "logistic_regression": {"C": [0.1, 1.0], "solver": ["lbfgs"], "max_iter": [2000]},
        },
        "max_candidates": 2,
        "selection_protocol": "nested_family_v1",
    }
    config.update(overrides)
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return path


def test_example_config_keeps_frozen_science_fields():
    payload = dsa_case.read_json(EXAMPLE_CONFIG)
    assert payload["schema_version"] == "1.0"
    assert payload["task"] == "classification"
    assert payload["target_column"] == "activity"
    assert payload["group_column"] == "subject_id"
    assert tuple(payload["feature_columns"]) == dsa_case.FEATURES
    assert len(payload["feature_columns"]) == 12
    assert payload["model_names"] == ["dummy", "logistic_regression"]
    assert payload["model_params"] == {}
    assert payload["validation_strategy"] == "group_k_fold"
    assert payload["validation_strategies"] == ["group_k_fold"]
    assert payload["primary_validation"] == "group_k_fold"
    assert (payload["n_splits"], payload["inner_splits"]) == (4, 3)
    assert payload["selection_metric"] == "balanced_accuracy"
    assert payload["tuning_mode"] == "custom"
    assert payload["max_candidates"] == 2
    assert payload["parameter_grids"]["dummy"] == {"strategy": ["prior"]}
    assert payload["parameter_grids"]["logistic_regression"] == {
        "C": [0.1, 1.0],
        "solver": ["lbfgs"],
        "max_iter": [2000],
        "tol": [1e-08],
        "class_weight": [None],
        "fit_intercept": [True],
    }
    assert payload["input_path"] == "examples/public/data/dsa_torso_mean_std.csv"
    assert payload["output_dir"] == "examples/public/results/dsa_group_nested_v1"
    summary = dsa_case.read_json(EXPECTED_DIR / "case_summary.json")
    science = {key: value for key, value in payload.items() if key not in {"input_path", "output_dir"}}
    canonical = json.dumps(science, sort_keys=True, separators=(",", ":")).encode()
    assert (
        hashlib.sha256(canonical).hexdigest()
        == summary["hashes"]["repository_config_science_sha256"]
    )


def test_member_enumeration_matches_upstream_layout():
    members = prepare_dsa.expected_members()
    assert len(members) == 9120
    assert len(set(members)) == 9120
    assert members[0] == "data/a01/p1/s01.txt"
    assert members[-1] == "data/a19/p8/s60.txt"
    assert all(prepare_dsa.MEMBER_PATTERN.fullmatch(name) for name in members)
    assert prepare_dsa.expected_members(activities=(1,), participants=(1,), segments=(1, 2)) == [
        "data/a01/p1/s01.txt",
        "data/a01/p1/s02.txt",
    ]


def test_mini_archive_conversion_matches_mean_and_population_std(tmp_path):
    archive = tmp_path / "mini.zip"
    values = build_mini_archive(archive)
    output = tmp_path / "derived"
    manifest = prepare_dsa.convert_archive(
        archive,
        output,
        expected_sha256=dsa_case.sha256_file(archive),
        expected_csv_sha256=None,
        activities=(1, 2),
        participants=(1,),
        segments=(1, 2),
        rows=3,
        columns=7,
    )
    frame = pd.read_csv(output / "dsa_torso_mean_std.csv")
    assert list(frame.columns) == [*dsa_case.ROLE_COLUMNS, *dsa_case.FEATURES]
    assert frame["segment_id"].tolist() == ["a01_p1_s01", "a01_p1_s02", "a02_p1_s01", "a02_p1_s02"]
    raw = values["data/a01/p1/s01.txt"][:, :6]
    expected = np.column_stack([raw.mean(axis=0), raw.std(axis=0, ddof=0)]).ravel()
    assert np.allclose(frame.iloc[0, 3:].to_numpy(dtype=float), expected, atol=1e-12, rtol=0)
    # The population (ddof=0) convention must differ from the sample convention here.
    sample_std = raw.std(axis=0, ddof=1)
    assert not np.allclose(frame.iloc[0, 4::2].to_numpy(dtype=float), sample_std)
    text = (output / "dsa_torso_mean_std.csv").read_text(encoding="utf-8")
    assert "\r" not in text and text.endswith("\n")
    header = text.splitlines()[0].split(",")
    assert header[:3] == ["segment_id", "subject_id", "activity"]
    assert len(header) == 15
    assert manifest["feature_std_ddof"] == 0
    assert manifest["rows"] == 4
    assert manifest["derived_csv_sha256"] == dsa_case.sha256_file(
        output / "dsa_torso_mean_std.csv"
    )
    hashes = dsa_case.read_json(output / "member_sha256.json")
    assert len(hashes) == 4


@pytest.mark.parametrize(
    "case",
    ["checksum", "missing", "duplicate", "extra", "non_finite", "wrong_shape"],
)
def test_conversion_rejects_invalid_archives(case, tmp_path):
    archive = tmp_path / "mini.zip"
    kwargs: dict = {}
    if case == "checksum":
        kwargs = {}
    elif case == "missing":
        kwargs = {"segments": (1,)}
    elif case == "duplicate":
        values = build_mini_archive(archive)
        kwargs = {"overrides": {"data/a01/p1/s01.txt": values["data/a01/p1/s01.txt"]}}
    elif case == "extra":
        kwargs = {"activities": (1,), "overrides": {"data/a02/p1/s01.txt": np.zeros((3, 7))}}
    elif case == "non_finite":
        values = build_mini_archive(archive)
        broken = values["data/a01/p1/s01.txt"].copy()
        broken[0, 0] = np.nan
        kwargs = {"overrides": {"data/a01/p1/s01.txt": broken}}
    elif case == "wrong_shape":
        kwargs = {"overrides": {"data/a01/p1/s01.txt": np.zeros((2, 7))}}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)  # duplicate names are the point
        build_mini_archive(archive, **kwargs)
    expected_sha = dsa_case.sha256_file(archive)
    if case == "checksum":
        expected_sha = "0" * 64
    with pytest.raises(ValueError):
        prepare_dsa.convert_archive(
            archive,
            tmp_path / "derived",
            expected_sha256=expected_sha,
            expected_csv_sha256=None,
            activities=(1, 2),
            participants=(1,),
            segments=(1, 2),
            rows=3,
            columns=7,
        )


def test_reference_module_never_imports_psyml():
    tree = ast.parse((ROOT / "tools/cases/reference_dsa.py").read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
    assert "psyml" not in imported


def test_selection_is_strict_greater_and_configuration_ordered():
    assert reference_dsa._first_max_index([0.5, 0.5]) == 0
    assert reference_dsa._first_max_index([float("nan"), 0.4, 0.4]) == 1
    assert reference_dsa._first_max_key({"dummy": 0.2, "logistic_regression": 0.2}) == "dummy"
    assert reference_dsa._first_max_key({"dummy": 0.1, "logistic_regression": 0.3}) == (
        "logistic_regression"
    )
    with pytest.raises(ValueError):
        reference_dsa._first_max_index([float("nan")])
    with pytest.raises(ValueError):
        reference_dsa._first_max_key({"dummy": float("nan")})


def test_candidate_expansion_order_and_boundary_rejection():
    config = dsa_case.read_json(EXAMPLE_CONFIG)
    candidates = reference_dsa.collect_candidates(config)
    assert candidates["dummy"] == [{"strategy": "prior"}]
    assert [candidate["C"] for candidate in candidates["logistic_regression"]] == [0.1, 1.0]
    with pytest.raises(ValueError):
        reference_dsa.collect_candidates({**config, "max_candidates": 1})


def test_reference_run_is_group_isolated_and_exports_the_frozen_schema(tmp_path):
    config_path = _mini_config(tmp_path)
    output = tmp_path / "reference"
    summary = reference_dsa.run(config_path, output)
    frame = pd.read_csv(json.loads(config_path.read_text())["input_path"])
    splits = dsa_case.read_json(output / "fold_membership.json")
    outer = [entry for entry in splits.values() if entry["strategy"] == "group_k_fold"]
    assert len(outer) == 1
    covered: set[int] = set()
    for fold in outer[0]["folds"]:
        assert set(fold["train_groups"]).isdisjoint(fold["test_groups"])
        covered |= set(fold["test_rows"])
    assert covered == set(frame.index)
    for entry in splits.values():
        for fold in entry["folds"]:
            for rows in (fold["train_rows"], fold["test_rows"]):
                assert set(frame.loc[rows, "y_label"]) == {1, 2}
    predictions = pd.read_csv(output / "predictions_with_probabilities.csv")
    assert len(predictions) == len(frame)
    assert predictions["row_index"].nunique() == len(frame)
    assert set(predictions["row_index"]) == set(frame.index)
    assert summary["fit_count"] == len(dsa_case.read_json(output / "fit_audit.json")) == 23
    assert len(pd.read_csv(output / "fold_metrics.csv")) == 2
    assert (output / "final_model.joblib").is_file()
    with pytest.raises(FileExistsError):
        reference_dsa.run(config_path, output)


def test_direct_metrics_match_the_scikit_learn_definitions():
    rng = np.random.default_rng(7)
    observed = rng.integers(1, 4, size=200)
    predicted = rng.integers(1, 4, size=200)
    direct = compare_dsa.direct_metrics(observed, predicted)
    assert direct["balanced_accuracy"] == pytest.approx(balanced_accuracy_score(observed, predicted))
    assert direct["f1_macro"] == pytest.approx(f1_score(observed, predicted, average="macro", zero_division=0))
    assert direct["accuracy"] == pytest.approx(accuracy_score(observed, predicted))


def test_max_abs_diff_ignores_non_finite_pairs():
    assert compare_dsa.max_abs_diff([np.nan, 1.0], [np.nan, 1.5]) == 0.5
    assert compare_dsa.max_abs_diff([np.nan], [np.nan]) == 0.0


def _parameter_search_table() -> pd.DataFrame:
    """A schema-compliant parameter_search table for the frozen contract."""
    return pd.DataFrame(
        {
            "model": ["dummy", "logistic_regression"],
            "validation": ["group_k_fold", "group_k_fold"],
            "outer_fold": [1, 1],
            "selection_scope": ["outer_training_fold", "outer_training_fold"],
            "candidate": [1, 2],
            "selection_metric": ["balanced_accuracy", "balanced_accuracy"],
            "score": [0.5, 0.75],
            "parameters": ['{"strategy": "prior"}', '{"C": 1.0}'],
            "status": ["completed", "completed"],
            "error": [float("nan"), float("nan")],
        }
    )


def test_metric_table_comparison_cannot_mask_failures():
    table = _parameter_search_table()
    # Identical tables pass; empty error columns are equal, not a failure.
    assert compare_dsa.compare_metric_tables(
        table, table.copy(), table_name="parameter_search"
    )["passed"]
    # The documented reference-only diagnostic column is allowed and validated separately.
    with_diagnostic = table.copy()
    with_diagnostic["inner_scores"] = ['[0.4, 0.5, 0.6]', '[0.7, 0.75, 0.8]']
    assert compare_dsa.compare_metric_tables(
        table, with_diagnostic, table_name="parameter_search"
    )["passed"]
    # Numeric drift beyond the frozen tolerance must fail.
    drifted = table.copy()
    drifted.loc[1, "score"] = 0.75 + 1e-6
    result = compare_dsa.compare_metric_tables(table, drifted, table_name="parameter_search")
    assert not result["passed"]
    assert result["max_abs_numeric_difference"] >= 1e-6
    # A production column missing from the reference must fail.
    result = compare_dsa.compare_metric_tables(
        table, table.drop(columns=["score"]), table_name="parameter_search"
    )
    assert not result["passed"]
    assert result["reference_missing_required_columns"] == ["score"]
    # An unregistered reference-only column must fail, never be silently skipped.
    unexpected = table.copy()
    unexpected["surprise"] = 1
    result = compare_dsa.compare_metric_tables(table, unexpected, table_name="parameter_search")
    assert not result["passed"]
    assert result["unexpected_reference_columns"] == ["surprise"]
    # Row-count mismatch must fail.
    result = compare_dsa.compare_metric_tables(
        table, table.iloc[:1], table_name="parameter_search"
    )
    assert not result["passed"]
    # Column reordering on either side must not change the outcome.
    reordered_left = table[list(reversed(table.columns))]
    reordered_right = table[list(table.columns[3:]) + list(table.columns[:3])]
    assert compare_dsa.compare_metric_tables(
        reordered_left, reordered_right, table_name="parameter_search"
    )["passed"]


def test_required_columns_are_fixed_per_table_and_checked_on_both_sides():
    table = _parameter_search_table()
    # Both sides missing the SAME critical column must still fail: the contract
    # is fixed per table and does not depend on the production column names.
    both_missing = compare_dsa.compare_metric_tables(
        table.drop(columns=["score"]),
        table.drop(columns=["score"]),
        table_name="parameter_search",
    )
    assert not both_missing["passed"]
    assert both_missing["production_missing_required_columns"] == ["score"]
    assert both_missing["reference_missing_required_columns"] == ["score"]
    # Production side only.
    production_missing = compare_dsa.compare_metric_tables(
        table.drop(columns=["candidate"]), table.copy(), table_name="parameter_search"
    )
    assert not production_missing["passed"]
    assert production_missing["production_missing_required_columns"] == ["candidate"]
    assert production_missing["reference_missing_required_columns"] == []
    # Reference side only.
    reference_missing = compare_dsa.compare_metric_tables(
        table.copy(), table.drop(columns=["status"]), table_name="parameter_search"
    )
    assert not reference_missing["passed"]
    assert reference_missing["production_missing_required_columns"] == []
    assert reference_missing["reference_missing_required_columns"] == ["status"]
    # A different table type has its own fixed contract.
    fold_metrics = pd.DataFrame(
        {
            "fold": [1],
            "model": ["logistic_regression"],
            "validation": ["group_k_fold"],
            "accuracy": [0.5],
            "balanced_accuracy": [0.5],
            "precision_weighted": [0.5],
            "recall_weighted": [0.5],
            "f1_weighted": [0.5],
            "precision_macro": [0.5],
            "recall_macro": [0.5],
            "f1_macro": [0.5],
            "roc_auc_ovr_weighted": [0.9],
        }
    )
    missing_contract = compare_dsa.compare_metric_tables(
        fold_metrics.drop(columns=["balanced_accuracy"]),
        fold_metrics.drop(columns=["balanced_accuracy"]),
        table_name="fold_metrics",
    )
    assert not missing_contract["passed"]
    assert missing_contract["production_missing_required_columns"] == ["balanced_accuracy"]
    # An unknown table name is a programming error, never a silent pass.
    with pytest.raises(KeyError):
        compare_dsa.compare_metric_tables(table, table.copy(), table_name="unknown_table")


def test_metric_table_comparison_rejects_non_finite_values():
    base = _parameter_search_table()
    # The registered empty diagnostic column is allowed on both sides.
    assert compare_dsa.compare_metric_tables(
        base, base.copy(), table_name="parameter_search"
    )["passed"]
    # One-sided NaN in a statistic fails.
    one_sided = base.copy()
    one_sided.loc[0, "score"] = float("nan")
    result = compare_dsa.compare_metric_tables(base, one_sided, table_name="parameter_search")
    assert not result["passed"]
    assert any("one side only" in problem for problem in result["non_finite_problems"])
    # A NaN in a statistic that must be finite fails even when both sides agree.
    both_nan_left = base.copy()
    both_nan_left.loc[0, "score"] = float("nan")
    result = compare_dsa.compare_metric_tables(
        both_nan_left, both_nan_left.copy(), table_name="parameter_search"
    )
    assert not result["passed"]
    assert any("must be finite" in problem for problem in result["non_finite_problems"])
    # NaN is legitimate on an explicitly failed candidate row.
    failed = base.iloc[:1].copy()
    failed["score"] = [float("nan")]
    failed["status"] = ["failed"]
    failed["error"] = ["LinAlgError: injected"]
    assert compare_dsa.compare_metric_tables(
        failed, failed.copy(), table_name="parameter_search"
    )["passed"]
    # Infinity is never accepted, and dtype mismatches fail explicitly.
    infinite = base.copy()
    infinite.loc[0, "score"] = float("inf")
    result = compare_dsa.compare_metric_tables(base, infinite, table_name="parameter_search")
    assert not result["passed"]
    assert any("infinite value" in problem for problem in result["non_finite_problems"])
    text_score = base.copy()
    text_score["score"] = text_score["score"].astype(str)
    result = compare_dsa.compare_metric_tables(base, text_score, table_name="parameter_search")
    assert not result["passed"]
    assert any("dtype mismatch" in problem for problem in result["non_finite_problems"])


def test_reference_inner_scores_diagnostic_is_validated_not_skipped():
    table = pd.DataFrame(
        {
            "status": ["completed", "failed"],
            "score": [0.5, float("nan")],
            "inner_scores": [json.dumps([0.4, 0.5, 0.6]), "[]"],
        }
    )
    result = compare_dsa.validate_reference_diagnostics(table, expected_inner_folds=3)
    assert result["passed"]
    assert result["detail"]["checked_rows"] == 1
    inconsistent = table.copy()
    inconsistent.loc[0, "inner_scores"] = json.dumps([0.4, 0.5, 0.9])
    assert not compare_dsa.validate_reference_diagnostics(
        inconsistent, expected_inner_folds=3
    )["passed"]
    wrong_length = table.copy()
    wrong_length.loc[0, "inner_scores"] = json.dumps([0.5])
    assert not compare_dsa.validate_reference_diagnostics(
        wrong_length, expected_inner_folds=3
    )["passed"]
    missing_column = table.drop(columns=["inner_scores"])
    assert not compare_dsa.validate_reference_diagnostics(
        missing_column, expected_inner_folds=3
    )["passed"]


def test_shuffled_labels_change_only_the_target_column(tmp_path):
    source = tmp_path / "source.csv"
    rows = [["segment_id", "subject_id", "activity", "x1"]]
    for subject in (2, 1):
        for label in (1, 2, 3):
            rows.append([f"s{subject}_{label}", str(subject), str(label), "0.5"])
    source.write_text("\n".join(",".join(row) for row in rows) + "\n", encoding="utf-8")
    shuffled = tmp_path / "shuffled.csv"
    digest = check_dsa_controls.build_shuffled_labels_csv(
        source,
        shuffled,
        target_column="activity",
        group_column="subject_id",
    )
    assert digest == dsa_case.sha256_file(shuffled)
    assert check_dsa_controls.shuffled_labels_change_only_target(
        source, shuffled, target_column="activity"
    )
    original = pd.read_csv(source, dtype=str)
    permuted = pd.read_csv(shuffled, dtype=str)
    assert original["segment_id"].tolist() == permuted["segment_id"].tolist()
    assert original["subject_id"].tolist() == permuted["subject_id"].tolist()
    assert original["x1"].tolist() == permuted["x1"].tolist()
    for subject in (1, 2):
        before = sorted(original.loc[original["subject_id"] == str(subject), "activity"])
        after = sorted(permuted.loc[permuted["subject_id"] == str(subject), "activity"])
        assert before == after
    # Same seed and same input must reproduce the identical file.
    again = tmp_path / "again.csv"
    assert (
        check_dsa_controls.build_shuffled_labels_csv(
            source, again, target_column="activity", group_column="subject_id"
        )
        == digest
    )
