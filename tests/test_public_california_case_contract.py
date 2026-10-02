"""Contract fault injections only; never fits on the acceptance data."""

import ast
import io
import tarfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from tools.cases import california_case as case
from tools.cases import check_california_controls, prepare_california, reference_california
from tools.cases.compare_california import Audit


class ComparatorContractTests(unittest.TestCase):
    def test_integer_parameter_types_are_exact(self):
        a = Audit()
        a.equal("params", {"verbose": 0.0}, {"verbose": 0})
        self.assertFalse(a.checks[-1]["passed"])

    def test_effective_default_omission_passes(self):
        a = Audit()
        a.resolve_parameter_defaults = True
        left = pd.DataFrame({"model": ["random_forest"], "candidate": [1], "parameters": ["{}"]})
        right = pd.DataFrame(
            {"model": ["random_forest"], "candidate": [1], "parameters": ['{"verbose":0}']}
        )
        a.frame(
            "params",
            left,
            right,
            ["model", "candidate", "parameters"],
            ["candidate"],
            ["model", "candidate", "parameters"],
        )
        self.assertTrue(all(c["passed"] for c in a.checks))

    def test_effective_resolution_does_not_hide_invalid_float(self):
        a = Audit()
        a.resolve_parameter_defaults = True
        left = pd.DataFrame(
            {"model": ["random_forest"], "candidate": [1], "parameters": ['{"verbose":0.0}']}
        )
        right = pd.DataFrame(
            {"model": ["random_forest"], "candidate": [1], "parameters": ['{"verbose":0}']}
        )
        a.frame(
            "params",
            left,
            right,
            ["model", "candidate", "parameters"],
            ["candidate"],
            ["model", "candidate", "parameters"],
        )
        self.assertTrue(any(not c["passed"] for c in a.checks))

    def test_exact_identity_passes(self):
        a = Audit()
        f = pd.DataFrame({"row_index": [0, 1], "predicted": [1.0, 2.0]})
        a.frame("sample", f, f.copy(), ["row_index", "predicted"], ["row_index"], ["row_index"])
        self.assertTrue(all(c["passed"] for c in a.checks))

    def test_both_sides_missing_required_column_fails(self):
        a = Audit()
        f = pd.DataFrame({"row_index": [0, 1]})
        a.frame("sample", f, f.copy(), ["row_index", "predicted"], ["row_index"], ["row_index"])
        self.assertEqual(sum(not c["passed"] for c in a.checks), 2)

    def test_one_sided_nan_fails(self):
        a = Audit()
        a.close("nan", [1.0, np.nan], [1.0, 2.0])
        self.assertFalse(a.checks[-1]["passed"])

    def test_both_sides_nan_fail(self):
        a = Audit()
        a.close("nan", [np.nan], [np.nan])
        self.assertFalse(a.checks[-1]["passed"])

    def test_infinity_fails(self):
        a = Audit()
        a.close("inf", [np.inf], [np.inf])
        self.assertFalse(a.checks[-1]["passed"])

    def test_exact_fold_mismatch_fails(self):
        a = Audit()
        f = pd.DataFrame({"row_index": [0, 1], "fold": [1, 2], "predicted": [1.0, 2.0]})
        other = f.copy()
        other.loc[0, "fold"] = 2
        a.frame(
            "sample",
            other,
            f,
            ["row_index", "fold", "predicted"],
            ["row_index"],
            ["row_index", "fold"],
        )
        self.assertTrue(any(not c["passed"] for c in a.checks))

    def test_beyond_frozen_tolerance_fails(self):
        a = Audit()
        a.close("big", [1.0 + 1e-8], [1.0])
        self.assertFalse(a.checks[-1]["passed"])

    def test_roundoff_within_frozen_tolerance_passes(self):
        a = Audit()
        a.close("small", [1.0 + 1e-12], [1.0])
        self.assertTrue(a.checks[-1]["passed"])

    def test_duplicate_keys_fail(self):
        a = Audit()
        f = pd.DataFrame({"row_index": [0, 0], "predicted": [1.0, 2.0]})
        a.frame("sample", f, f.copy(), ["row_index", "predicted"], ["row_index"], ["row_index"])
        self.assertTrue(any(not c["passed"] for c in a.checks))

    def test_extra_production_column_fails(self):
        a = Audit()
        f = pd.DataFrame({"row_index": [0], "predicted": [1.0]})
        other = f.assign(extra=1)
        a.frame("sample", other, f, ["row_index", "predicted"], ["row_index"], ["row_index"])
        self.assertTrue(any(not c["passed"] for c in a.checks))

    def test_parameter_dict_key_order_irrelevant(self):
        a = Audit()
        f = pd.DataFrame({"candidate": [1], "parameters": ['{"a":1,"b":2}']})
        other = f.copy()
        other["parameters"] = '{"b":2,"a":1}'
        a.frame(
            "sample",
            other,
            f,
            ["candidate", "parameters"],
            ["candidate"],
            ["candidate", "parameters"],
        )
        self.assertTrue(all(c["passed"] for c in a.checks))

    def test_only_empty_error_text_nan_permitted(self):
        a = Audit()
        f = pd.DataFrame({"candidate": [1], "error": [np.nan]})
        other = f.copy()
        other["error"] = ""
        a.frame("sample", other, f, ["candidate", "error"], ["candidate"], ["candidate", "error"])
        self.assertTrue(all(c["passed"] for c in a.checks))


ROOT = Path(__file__).resolve().parents[1]


def _archive(path, raw=None, extra=None, duplicate=False):
    if raw is None:
        raw = np.array(
            [
                [-122.0, 37.0, 30.0, 120.0, 24.0, 80.0, 20.0, 5.0, 500001.0],
                [-121.0, 36.0, 20.0, 100.0, 20.0, 60.0, 10.0, 4.0, 200000.0],
            ]
        )
    content = io.StringIO()
    np.savetxt(content, raw, delimiter=",", fmt="%.17g")
    members = [
        (prepare_california.MEMBERS[0], content.getvalue().encode()),
        (prepare_california.MEMBERS[1], b"test domain\n"),
    ]
    if extra:
        members.append((extra, b"not data"))
    if duplicate:
        members.append(members[0])
    with tarfile.open(path, "w:gz") as tar:
        for name, data in members:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return raw


def test_historical_protocol_and_config_bytes_are_unchanged():
    assert case.sha256(case.EXPECTED_DIR / "PROTOCOL_FROZEN.json") == case.FROZEN_PROTOCOL_SHA256
    assert case.sha256(case.EXPECTED_DIR / "california_config.json") == case.FROZEN_CONFIG_SHA256
    assert (
        case.sha256(case.EXPECTED_DIR / "california_config_v1_1.json") == case.AMENDED_CONFIG_SHA256
    )
    protocol = case.read_json(case.EXPECTED_DIR / "PROTOCOL_FROZEN.json")
    assert protocol["numeric_acceptance"]["atol"] == protocol["numeric_acceptance"]["rtol"] == 1e-10
    summary = case.read_json(case.EXPECTED_DIR / "historical_summary.json")
    assert summary["original_v1_failure"]["status"] == "failed"
    assert summary["original_v1_failure"]["n_failed"] == 32
    assert (
        summary["v1_1_observed_scope"]["n_checks"]
        == summary["v1_1_observed_scope"]["n_passed"]
        == 270
    )
    assert summary["scope"]["production_per_fit_instrumentation"] is False


def test_portable_configs_only_relocate_paths_and_v11_only_removes_verbose():
    for variant, name in [
        ("v1", "california_config.json"),
        ("v1.1", "california_config_v1_1.json"),
    ]:
        value = case.read_json(case.CASE_DIR / name)
        assert case.config_identity(value) == variant
        assert value["input_path"] == "examples/public/data/california_housing.csv"
        assert value["output_dir"].startswith("examples/public/results/")
        assert case.science_sha256(value) == case.science_sha256(case.frozen_config(variant))
    original = case.frozen_config("v1")
    del original["parameter_grids"]["random_forest"]["verbose"]
    assert case.typed_json(original) == case.typed_json(case.frozen_config("v1.1"))


@pytest.mark.parametrize(
    "mutation", ["seed", "float_verbose", "extra", "schema", "candidate_order", "fractional_leaf"]
)
def test_frozen_science_identity_is_fail_closed(mutation):
    value = case.frozen_config()
    if mutation == "seed":
        value["random_seed"] += 1
    elif mutation == "float_verbose":
        value["parameter_grids"]["random_forest"]["verbose"] = [0.0]
    elif mutation == "extra":
        value["extra_unregistered_field"] = True
    elif mutation == "schema":
        value["schema_version"] = "2.0"
    elif mutation == "candidate_order":
        value["parameter_grids"]["ridge"]["alpha"].reverse()
    else:
        value["parameter_grids"]["random_forest"]["min_samples_leaf"] = [1.0]
    with pytest.raises(ValueError):
        reference_california.validate_config(value)


def test_prepare_mini_archive_transformation_and_order(tmp_path):
    archive = tmp_path / "source.tgz"
    _archive(archive)
    out = tmp_path / "out"
    manifest = prepare_california.convert_archive(
        archive,
        out,
        expected_sha256=case.sha256(archive),
        expected_csv_sha256=None,
        expected_rows=2,
    )
    frame = pd.read_csv(out / "california_housing.csv")
    assert list(frame.columns) == case.FEATURES + [case.TARGET]
    np.testing.assert_allclose(
        frame.iloc[0], [5.0, 30.0, 6.0, 1.2, 80.0, 4.0, 37.0, -122.0, 5.00001]
    )
    assert frame[case.TARGET].tolist() == [5.00001, 2.0]
    fixture = pd.read_csv(out / "california_predict.csv")
    assert list(fixture.columns) == ["sample_id"] + list(reversed(case.FEATURES))
    assert fixture.sample_id.tolist() == ["CAL00000", "CAL00001"]
    np.testing.assert_array_equal(fixture[case.FEATURES], frame[case.FEATURES])
    assert manifest["csv_sha256"] == case.sha256(out / "california_housing.csv")
    assert b"\r" not in (out / "california_housing.csv").read_bytes()
    with pytest.raises(FileExistsError):
        prepare_california.convert_archive(
            archive,
            out,
            expected_sha256=case.sha256(archive),
            expected_csv_sha256=None,
            expected_rows=2,
        )


@pytest.mark.parametrize(
    "bad",
    [
        "hash",
        "extra",
        "duplicate",
        "shape",
        "nonfinite",
        "zero_households",
        "derived_hash",
        "symlink",
    ],
)
def test_prepare_rejects_invalid_archives_without_outputs(tmp_path, bad):
    archive = tmp_path / "bad.tgz"
    raw = np.ones((2, 9))
    kwargs = {}
    if bad == "extra":
        kwargs["extra"] = "../outside"
    elif bad == "duplicate":
        kwargs["duplicate"] = True
    elif bad == "shape":
        raw = np.ones((2, 8))
    elif bad == "nonfinite":
        raw[0, 0] = np.nan
    elif bad == "zero_households":
        raw[0, 6] = 0
    _archive(archive, raw=raw, **kwargs)
    if bad == "symlink":
        with tarfile.open(archive, "w:gz") as tar:
            for name in prepare_california.MEMBERS:
                member = tarfile.TarInfo(name)
                member.type = tarfile.SYMTYPE
                member.linkname = "/etc/passwd"
                tar.addfile(member)
    with pytest.raises(ValueError):
        prepare_california.convert_archive(
            archive,
            tmp_path / "out",
            expected_sha256="0" * 64 if bad == "hash" else case.sha256(archive),
            expected_csv_sha256="0" * 64 if bad == "derived_hash" else None,
            expected_rows=2,
        )
    assert not (tmp_path / "out").exists()


def test_reference_never_imports_production_and_candidates_keep_order():
    for name in ["reference_california.py", "california_case.py"]:
        tree = ast.parse((ROOT / "tools/cases" / name).read_text())
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports += [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                imports.append((node.module or "").split(".")[0])
        assert "psyml" not in imports
    candidates = reference_california.validate_config(case.frozen_config())
    assert list(candidates) == ["dummy", "ridge", "random_forest"]
    assert [c["alpha"] for c in candidates["ridge"]] == [0.1, 1.0, 10.0]
    assert sum(map(len, candidates.values())) == 5
    before = [
        reference_california.estimator(f, p).get_params()
        for f, ps in candidates.items()
        for p in ps
    ]
    amended = reference_california.validate_config(case.frozen_config("v1.1"))
    after = [
        reference_california.estimator(f, p).get_params() for f, ps in amended.items() for p in ps
    ]
    assert case.typed_json(before) == case.typed_json(after)


def test_strict_minimum_ties_and_nonfinite_rejection():
    first = {"score": 1.0, "model": "first"}
    tied = {"score": 1.0, "model": "second"}
    better = {"score": 0.5, "model": "third"}
    assert reference_california.first_minimum(None, first) is first
    assert reference_california.first_minimum(first, tied) is first
    assert reference_california.first_minimum(first, better) is better
    with pytest.raises(ValueError):
        reference_california.first_minimum(first, {"score": float("nan")})


def test_direct_residual_metrics_match_sklearn():
    observed = np.array([1.0, 2.0, 4.0, 6.0])
    predicted = np.array([1.2, 2.1, 4.3, 5.5])
    assert reference_california.direct_metrics(observed, predicted) == pytest.approx(
        reference_california.metrics(observed, predicted)
    )


def test_synthetic_controls_are_bounded_and_pass():
    report = check_california_controls.run_controls()
    assert report["passed"] is True
    assert report["n_checks"] == 13
    assert report["real_data_fits"] == 0
    assert report["synthetic_reference_fits"] == 1
