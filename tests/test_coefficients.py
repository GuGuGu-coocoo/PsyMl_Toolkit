"""Fitted coefficient/intercept extraction, mapping and reconstruction checks."""

import hashlib
import json

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import ElasticNet, Lasso, LinearRegression, LogisticRegression, Ridge
from sklearn.pipeline import Pipeline
from sklearn.svm import SVC, SVR

from psyml import ExperimentConfig, run_experiment
from psyml.models.coefficients import (
    CoefficientError,
    build_coefficient_report,
    coefficient_support,
    extract_coefficients,
    verify_reconstruction,
    write_coefficients,
)
from psyml.models.parameters import effective_parameters
from psyml.prediction import LoadedModel
from psyml.preprocessing.pipeline import build_preprocessor


def _mixed_frame(n: int = 90, seed: int = 3) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    frame = pd.DataFrame(
        {
            "num_a": rng.normal(size=n),
            "num_b": rng.normal(size=n),
            "cat": rng.choice(["a_b", "a", "b"], size=n),
            "const": np.ones(n),
            "all_missing_num": np.full(n, np.nan),
            "all_missing_cat": pd.Series([None] * n, dtype=object),
        }
    )
    frame.loc[:: 7, "num_a"] = np.nan
    frame.loc[:: 11, "cat"] = np.nan
    return frame


def _pipeline(frame, estimator, *, missing="median", scaling="standard") -> Pipeline:
    return Pipeline([
        ("preprocess", build_preprocessor(frame, missing_strategy=missing, scaling=scaling)),
        ("model", estimator),
    ])


def _report(frame, pipeline, target, task, **kwargs):
    pipeline.fit(frame, target)
    return build_coefficient_report(
        pipeline,
        task=task,
        feature_names=list(frame.columns),
        feature_dtypes={column: str(dtype) for column, dtype in frame.dtypes.items()},
        verify_frame=frame,
        **kwargs,
    )


@pytest.mark.parametrize(
    "estimator",
    [
        LinearRegression(),
        Ridge(alpha=0.5),
        Lasso(alpha=0.01),
        ElasticNet(alpha=0.01),
        SVR(kernel="linear"),
    ],
)
@pytest.mark.parametrize("scaling", ["standard", "minmax", "none"])
def test_regression_families_reconstruct(estimator, scaling):
    frame = _mixed_frame()
    target = frame["num_a"].fillna(0) * 2 + frame["num_b"]
    report = _report(frame, _pipeline(frame, estimator, scaling=scaling), target, "regression")
    assert report["status"] == "available"
    assert report["verification"]["verified"] is True
    assert report["verification"]["max_abs_error"] <= 1e-7
    sources = [feature["source"] for feature in report["features"]]
    assert "all_missing_num" not in sources
    assert "all_missing_cat" not in sources


def test_classification_families_and_axes():
    frame = _mixed_frame()
    binary = (frame["num_a"].fillna(0) + frame["num_b"] > 0).astype(int)
    binary_report = _report(
        frame, _pipeline(frame, LogisticRegression(max_iter=1000)), binary, "classification"
    )
    assert binary_report["verification"]["verified"] is True
    row = binary_report["output"]["rows"][0]
    assert row["class_index"] == 1 and row["class_label"] == 1
    assert "log-odds" in row["unit"]

    lda_frame = frame.drop(columns=["all_missing_num", "all_missing_cat"])
    from sklearn.discriminant_analysis import LinearDiscriminantAnalysis

    lda_report = _report(
        lda_frame, _pipeline(lda_frame, LinearDiscriminantAnalysis()), binary, "classification"
    )
    assert lda_report["verification"]["verified"] is True
    lda_unit = lda_report["output"]["rows"][0]["unit"]
    assert "log-odds" in lda_unit and "sigmoid" in lda_unit
    # Independent check of the axis semantics: for two classes the LDA decision
    # score is the log-odds used by predict_proba (not an arbitrary "not log-odds").
    lda_pipeline = _pipeline(lda_frame, LinearDiscriminantAnalysis()).fit(lda_frame, binary)
    decision = lda_pipeline.decision_function(lda_frame)
    probability = lda_pipeline.predict_proba(lda_frame)[:, 1]
    assert np.max(np.abs(1.0 / (1.0 + np.exp(-decision)) - probability)) < 1e-9

    svc_report = _report(
        lda_frame, _pipeline(lda_frame, SVC(kernel="linear")), binary, "classification"
    )
    assert svc_report["verification"]["verified"] is True
    assert "margin" in svc_report["output"]["rows"][0]["unit"]

    multiclass = np.digitize(frame["num_a"].fillna(0), [-1, 1])
    multi_report = _report(
        frame, _pipeline(frame, LogisticRegression(max_iter=1000)), multiclass, "classification"
    )
    assert multi_report["verification"]["verified"] is True
    assert multi_report["n_output_rows"] == len(set(multiclass))
    kinds = {row["kind"] for row in multi_report["output"]["rows"]}
    assert kinds == {"class_logit"}
    # Each multiclass row is the softmax logit for that class: softmax(decision_function)
    # must match predict_proba and the argmax must match predict, proving the axis order.
    multi_pipeline = _pipeline(frame, LogisticRegression(max_iter=1000)).fit(frame, multiclass)
    decision = multi_pipeline.decision_function(frame)
    probability = multi_pipeline.predict_proba(frame)
    softmax = np.exp(decision - decision.max(axis=1, keepdims=True))
    softmax = softmax / softmax.sum(axis=1, keepdims=True)
    assert np.max(np.abs(softmax - probability)) < 1e-9
    assert np.array_equal(probability.argmax(axis=1), multi_pipeline.predict(frame))
    for row in multi_report["output"]["rows"]:
        assert row["class_label"] == multi_report["classes"][row["class_index"]]


def test_category_values_and_type_preserved_without_name_parsing():
    frame = pd.DataFrame({"cat": ["a_b", "a", "ab"] * 20, "num": np.arange(60.0)})
    target = (pd.Categorical(frame["cat"]).codes).astype(int)
    report = _report(frame, _pipeline(frame, LogisticRegression(max_iter=1000)), target,
                     "classification")
    onehot = [feature for feature in report["features"] if feature["kind"] == "onehot"]
    assert {feature["category"] for feature in onehot} == {"a_b", "a", "ab"}
    assert all(feature["source"] == "cat" for feature in onehot)
    assert report["verification"]["verified"] is True


def test_numeric_all_missing_and_imputer_statistics_are_recorded():
    frame = _mixed_frame()
    target = frame["num_b"]
    report = _report(frame, _pipeline(frame, LinearRegression()), target, "regression")
    numeric = {feature["source"]: feature for feature in report["features"]
               if feature["kind"] == "numeric"}
    assert set(numeric) == {"num_a", "num_b", "const"}
    assert numeric["num_a"]["imputed"] is True
    assert numeric["num_a"]["imputer_fill_value"] is not None
    assert numeric["const"]["scaler"]["scale"] == pytest.approx(1.0, abs=1e-12)


def test_unsupported_estimators_return_specific_reasons():
    frame = _mixed_frame().drop(columns=["all_missing_num", "all_missing_cat"])
    target = (frame["num_a"].fillna(0) > 0).astype(int)
    from sklearn.ensemble import RandomForestClassifier

    rf = _report(frame, _pipeline(frame, RandomForestClassifier(n_estimators=5)), target,
                 "classification")
    assert rf["status"] == "unsupported"
    assert "RandomForestClassifier" in rf["reason"]

    nonlinear = _report(frame, _pipeline(frame, SVC(kernel="rbf")), target, "classification")
    assert nonlinear["status"] == "unsupported"
    assert "kernel='rbf'" in nonlinear["reason"]

    svr = _report(frame, _pipeline(frame, SVR(kernel="rbf")), frame["num_b"], "regression")
    assert svr["status"] == "unsupported"

    three = np.digitize(frame["num_a"].fillna(0), [-1, 1])
    multiclass_svc = _report(frame, _pipeline(frame, SVC(kernel="linear")), three,
                             "classification")
    assert multiclass_svc["status"] == "unsupported"
    assert "pairwise" in multiclass_svc["reason"]


def test_extraction_never_fits_and_does_not_change_the_model(monkeypatch):
    frame = _mixed_frame().drop(columns=["all_missing_num", "all_missing_cat"])
    target = frame["num_a"].fillna(0) * 1.5 + frame["num_b"]
    pipeline = _pipeline(frame, Ridge(alpha=0.3))
    pipeline.fit(frame, target)
    before_params = effective_parameters(pipeline.named_steps["model"])
    before_predictions = pipeline.predict(frame)

    def fail_fit(*args, **kwargs):  # pragma: no cover - must never be called
        raise AssertionError("coefficient extraction must not fit")

    monkeypatch.setattr(Ridge, "fit", fail_fit)
    monkeypatch.setattr(Pipeline, "fit", fail_fit)
    report = build_coefficient_report(
        pipeline,
        task="regression",
        feature_names=list(frame.columns),
        verify_frame=frame,
    )
    assert report["verification"]["verified"] is True
    assert effective_parameters(pipeline.named_steps["model"]) == before_params
    assert np.array_equal(pipeline.predict(frame), before_predictions)


def test_write_coefficients_is_atomic_and_protects_existing_output(tmp_path):
    frame = _mixed_frame().drop(columns=["all_missing_num", "all_missing_cat"])
    target = frame["num_b"]
    report = _report(frame, _pipeline(frame, LinearRegression()), target, "regression")
    target_dir = tmp_path / "coefficients"
    artifacts = write_coefficients(report, target_dir)
    assert {path.name for path in target_dir.iterdir()} == {
        "coefficients.csv", "coefficients.json", "coefficients_notes.md"
    }
    document = json.loads((target_dir / "coefficients.json").read_text(encoding="utf-8"))
    assert document["artifacts"]["json"] == "coefficients.json"
    assert set(artifacts) == {"csv", "json", "notes"}
    with pytest.raises(CoefficientError):
        write_coefficients(report, target_dir)
    with pytest.raises(CoefficientError):
        write_coefficients(report, tmp_path / "other", protected_paths=(
            tmp_path / "other" / "coefficients.json",))


def test_loaded_model_support_and_verification():
    frame = _mixed_frame().drop(columns=["all_missing_num", "all_missing_cat"])
    target = (frame["num_a"].fillna(0) > 0).astype(int)
    pipeline = _pipeline(frame, LogisticRegression(max_iter=1000))
    pipeline.fit(frame, target)
    pipeline.psyml_metadata_ = {
        "psyml_version": "0.2.0",
        "task": "classification",
        "feature_names": list(frame.columns),
        "feature_types": {},
        "n_features": len(frame.columns),
        "estimator_class": f"{type(pipeline.named_steps['model']).__module__}."
                           f"{type(pipeline.named_steps['model']).__qualname__}",
        "fit_scope": "all_analyzed_rows",
    }
    loaded = LoadedModel(pipeline, dict(pipeline.psyml_metadata_), [])
    support = coefficient_support(loaded)
    assert support.supported and support.task == "classification"

    from psyml.models.coefficients import build_loaded_coefficient_report

    report = build_loaded_coefficient_report(loaded, frame)
    assert report["status"] == "available"
    assert report["verification"]["verified"] is True

    unverified = build_loaded_coefficient_report(loaded)
    assert unverified["verification"]["performed"] is False
    assert unverified["verification"]["verified"] is False


def test_report_is_json_serializable_and_records_limits():
    frame = _mixed_frame().drop(columns=["all_missing_num", "all_missing_cat"])
    target = frame["num_b"]
    report = _report(frame, _pipeline(frame, LinearRegression()), target, "regression")
    encoded = json.dumps(report, allow_nan=False)
    assert "p-values" in encoded
    assert report["coefficient_space"] == "preprocessed_feature_space"
    assert verify_reconstruction(
        _pipeline(frame, LinearRegression()).fit(frame, target), frame, report
    )["verified"] is True


def test_model_hash_and_outputs_unchanged_before_after(tmp_path):
    frame = _mixed_frame().drop(columns=["all_missing_num", "all_missing_cat"])
    target = frame["num_b"]
    pipeline = _pipeline(frame, LinearRegression()).fit(frame, target)
    digest_before = hashlib.sha256(np.asarray(pipeline.predict(frame)).tobytes()).hexdigest()
    extract_coefficients(pipeline, task="regression", feature_names=list(frame.columns))
    digest_after = hashlib.sha256(np.asarray(pipeline.predict(frame)).tobytes()).hexdigest()
    assert digest_before == digest_after


def test_runner_writes_final_model_coefficients_even_without_saving_model(tmp_path):
    rng = np.random.default_rng(9)
    frame = pd.DataFrame({
        "score": rng.normal(size=80),
        "category": rng.choice(["a", "b"], size=80),
    })
    frame["target"] = (frame["score"] + (frame["category"] == "a") > 0).astype(int)
    config = ExperimentConfig(
        task="classification", target_column="target", model_name="logistic_regression",
        output_dir=tmp_path / "run", random_seed=2, save_best_model=False,
    )
    result = run_experiment(config, frame)
    assert result.coefficient_report["status"] == "available"
    assert result.model_export["status"] == "disabled"
    target_dir = config.output_dir / "coefficients"
    assert (target_dir / "coefficients.json").is_file()
    payload = json.loads((config.output_dir / "result.json").read_text(encoding="utf-8"))
    assert payload["coefficients"]["status"] == "available"
    assert payload["coefficients"]["verification"]["verified"] is True
    assert sorted(key for key in payload["artifacts"] if "coefficient" in key) == [
        "coefficients_csv", "coefficients_json", "coefficients_notes",
    ], sorted(payload["artifacts"])
    document = json.loads((target_dir / "coefficients.json").read_text(encoding="utf-8"))
    assert document["model"]["fit_scope"] == "all_analyzed_rows"


def test_runner_independent_mode_exposes_per_validation_coefficients(tmp_path):
    rng = np.random.default_rng(10)
    frame = pd.DataFrame({
        "score": rng.normal(size=90),
        "category": rng.choice(["a", "b", "c"], size=90),
    })
    frame["target"] = 2 * frame["score"] + (frame["category"] == "a")
    config = ExperimentConfig(
        task="regression", target_column="target", model_name="ridge",
        output_dir=tmp_path / "independent", random_seed=3,
        validation_strategies=["holdout", "k_fold"], primary_validation=None, n_splits=3,
    )
    result = run_experiment(config, frame)
    assert set(result.validation_results) == {"holdout", "k_fold"}
    for validation in ("holdout", "k_fold"):
        child = config.output_dir / "validations" / validation / "coefficients"
        assert (child / "coefficients.json").is_file()
    payload = json.loads((config.output_dir / "result.json").read_text(encoding="utf-8"))
    assert payload["model_export"]["status"] == "independent_validations"
    assert set(payload["coefficients"]["validations"]) == {"holdout", "k_fold"}
    assert payload["coefficients"]["data_scope"] == "final_all_analyzed_rows_model"
    assert "coefficients_holdout_csv" in payload["artifacts"]


def test_drop_none_standard_pipeline_is_supported():
    """missing_strategy='drop' + scaling='none' fits an identity numeric passthrough."""
    frame = pd.DataFrame({
        "num_a": np.arange(20.0),
        "num_b": np.linspace(-1.0, 1.0, 20),
        "category": (["x", "y"] * 10),
    })
    target = 2.0 * frame["num_a"] - frame["num_b"]
    pipeline = Pipeline([
        ("preprocess", build_preprocessor(frame, missing_strategy="drop", scaling="none")),
        ("model", LinearRegression()),
    ]).fit(frame, target)
    report = build_coefficient_report(
        pipeline, task="regression", feature_names=list(frame.columns), verify_frame=frame
    )
    assert report["status"] == "available", report.get("reason")
    assert report["verification"]["verified"] is True
    assert report["scaling"]["numeric_mode"] == "none"
    numeric = [feature for feature in report["features"] if feature["kind"] == "numeric"]
    assert {feature["source"] for feature in numeric} == {"num_a", "num_b"}
    assert all(feature["scaling"] == "none" for feature in numeric)

    numeric_only = frame[["num_a", "num_b"]]
    numeric_pipeline = Pipeline([
        ("preprocess", build_preprocessor(numeric_only, missing_strategy="drop", scaling="none")),
        ("model", LinearRegression()),
    ]).fit(numeric_only, target)
    numeric_report = build_coefficient_report(
        numeric_pipeline, task="regression", feature_names=list(numeric_only.columns),
        verify_frame=numeric_only,
    )
    assert numeric_report["status"] == "available", numeric_report.get("reason")
    assert numeric_report["verification"]["verified"] is True


def test_failed_reconstruction_blocks_successful_delivery(tmp_path, monkeypatch):
    frame = _mixed_frame().drop(columns=["all_missing_num", "all_missing_cat"])
    target = frame["num_b"]
    pipeline = _pipeline(frame, LinearRegression()).fit(frame, target)
    original_predict = pipeline.predict
    pipeline.predict = lambda data: np.asarray(original_predict(data)) + 1.0
    report = build_coefficient_report(
        pipeline, task="regression", feature_names=list(frame.columns), verify_frame=frame
    )
    assert report["status"] == "error"
    assert report["verification"]["verified"] is False
    assert "Reconstruction" in report["reason"]
    with pytest.raises(CoefficientError):
        write_coefficients(report, tmp_path / "failed")
    assert not (tmp_path / "failed").exists()


def test_nonfinite_and_shape_mismatch_block_delivery():
    frame = _mixed_frame().drop(columns=["all_missing_num", "all_missing_cat"])
    binary = (frame["num_a"].fillna(0) > 0).astype(int)
    pipeline = _pipeline(frame, LogisticRegression(max_iter=1000)).fit(frame, binary)

    def non_finite(_data):
        return np.full(len(frame), np.inf)

    original_decision = pipeline.decision_function
    pipeline.decision_function = non_finite
    report = build_coefficient_report(
        pipeline, task="classification", feature_names=list(frame.columns), verify_frame=frame
    )
    assert report["status"] == "error"
    assert report["verification"]["finite"] is False

    pipeline.decision_function = lambda data: np.column_stack(
        [np.asarray(original_decision(data)), np.asarray(original_decision(data))]
    )
    report = build_coefficient_report(
        pipeline, task="classification", feature_names=list(frame.columns), verify_frame=frame
    )
    assert report["status"] == "error"
    assert report["verification"]["shape_ok"] is False
    assert "shape" in report["reason"].lower()


def test_dropped_features_and_training_dtype_source_are_recorded():
    frame = _mixed_frame()
    target = frame["num_b"]
    pipeline = _pipeline(frame, LinearRegression()).fit(frame, target)
    report = build_coefficient_report(
        pipeline, task="regression", feature_names=list(frame.columns),
        feature_dtypes={column: str(dtype) for column, dtype in frame.dtypes.items()},
        feature_dtypes_source="training_frame",
        verify_frame=frame,
    )
    mapping = {entry["name"]: entry for entry in report["input_features"]}
    assert set(mapping) == set(frame.columns)
    assert mapping["all_missing_num"]["retained"] is False
    assert "all values are missing" in mapping["all_missing_num"]["drop_reason"]
    assert mapping["all_missing_cat"]["retained"] is False
    assert mapping["num_a"]["retained"] is True and mapping["num_a"]["transformed_indices"]
    dropped = {entry["name"]: entry for entry in report["dropped_features"]}
    assert set(dropped) == {"all_missing_num", "all_missing_cat"}
    # Original column positions, not block-local positions.
    assert dropped["all_missing_num"]["index"] == 4
    assert dropped["all_missing_cat"]["index"] == 5
    assert report["training_dtype_source"] == "training_frame"
    numeric = {feature["source"]: feature for feature in report["features"]
               if feature["kind"] == "numeric"}
    assert numeric["num_a"]["training_dtype"]


def test_encoding_records_drop_idx_and_per_source_mapping():
    frame = pd.DataFrame({
        "cat": ["a_b", "a", "b"] * 20,
        "num": np.arange(60.0),
    })
    target = pd.Categorical(frame["cat"]).codes.astype(int)
    pipeline = _pipeline(frame, LogisticRegression(max_iter=1000)).fit(frame, target)
    report = build_coefficient_report(
        pipeline, task="classification", feature_names=list(frame.columns), verify_frame=frame
    )
    encoding = report["encoding"]
    assert encoding["drop"] is None
    assert encoding["drop_idx_"] is None
    assert len(encoding["per_source"]) == 1
    source = encoding["per_source"][0]
    assert source["source"] == "cat"
    assert source["source_index"] == 0
    assert source["categories"] == ["a", "a_b", "b"]
    assert len(source["transformed_names"]) == len(source["categories"])
    onehot = [feature for feature in report["features"] if feature["kind"] == "onehot"]
    assert [feature["category"] for feature in onehot] == source["categories"]


def test_loaded_model_without_psyml_provenance_is_unsupported():
    frame = _mixed_frame().drop(columns=["all_missing_num", "all_missing_cat"])
    target = frame["num_b"]
    pipeline = _pipeline(frame, LinearRegression()).fit(frame, target)
    loaded = LoadedModel(pipeline, {"task": "regression", "feature_names": list(frame.columns)}, [])
    support = coefficient_support(loaded)
    assert not support.supported
    assert "PsyML" in support.reason
    loaded.metadata["psyml_version"] = "0.2.0"
    assert not coefficient_support(loaded).supported
    loaded.metadata["fit_scope"] = "all_analyzed_rows"
    assert coefficient_support(loaded).supported
