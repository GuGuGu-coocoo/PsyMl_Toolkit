"""Single-sample SHAP explanation: codec, support subset, budget and artifacts."""
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression, Ridge
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier

from psyml.explanation import (
    EXPLANATION_SCHEMA_VERSION,
    SEED_MAX,
    ExplanationError,
    ExplanationUnavailableError,
    LosslessCodec,
    _sample_background,
    _value_key,
    build_waterfall_segments,
    explain_row,
    model_support,
    plan_explanation,
    write_explanation,
)
from psyml.prediction import LoadedModel, predict_dataframe
from psyml.preprocessing.pipeline import build_preprocessor

shap = pytest.importorskip("shap", reason="optional explain extra not installed")


def make_loaded(task, estimator, features, target, *, feature_types=None, classes=None):
    preprocessor = build_preprocessor(features, missing_strategy="median", scaling="standard")
    pipeline = Pipeline([("preprocess", preprocessor), ("model", estimator)])
    pipeline.fit(features, target)
    types = feature_types or {
        column: "numeric" if column in features.select_dtypes(include="number") else "categorical"
        for column in features.columns
    }
    metadata = {
        "task": task,
        "feature_names": list(features.columns),
        "feature_types": types,
        "n_features": len(features.columns),
        "classes": classes if classes is not None else (
            list(pipeline.classes_) if task == "classification" else None
        ),
        "estimator_class": f"{type(estimator).__module__}.{type(estimator).__qualname__}",
        "psyml_version": "0.2.0",
        "fit_scope": "all_analyzed_rows",
        "supports_probability": hasattr(pipeline, "predict_proba"),
    }
    return LoadedModel(pipeline, metadata, [])


def classification_frame(rows=60, seed=0):
    rng = np.random.default_rng(seed)
    frame = pd.DataFrame({
        "x": rng.normal(size=rows),
        "y": rng.normal(size=rows),
        "group": (["a", "b", "c"] * (rows // 3 + 1))[:rows],
    })
    frame["target"] = ((frame["x"] + (frame["group"] == "a") * 0.4) > 0).astype(int)
    return frame


# --- codec -----------------------------------------------------------------

def test_value_key_distinguishes_types_and_missing():
    assert _value_key(np.nan) == ("missing",)
    assert _value_key(None) == ("missing",)
    assert _value_key("1") != _value_key(1)
    assert _value_key(1) != _value_key(1.0)
    assert _value_key(True) == ("bool", True)
    # A real string equal to an internal-looking marker stays a string.
    assert _value_key("__missing__") == ("str", "__missing__")
    # Exact float keys do not collapse via np.isclose-like tolerance.
    assert _value_key(0.1) != _value_key(0.10000000000000002)


def test_lossless_codec_round_trip_mixed_values():
    frame = pd.DataFrame({
        "num": [0.1, 0.10000000000000002, np.nan, 2.0],
        "cat": ["1", 1, None, "__missing__"],
        "const": ["k", "k", "k", "k"],
    })
    codec = LosslessCodec.build([frame], ["num", "cat", "const"])
    codes = codec.encode_frame(frame)
    decoded = codec.decode(codes)
    for column in frame.columns:
        assert [_value_key(value) for value in decoded[column]] == [
            _value_key(value) for value in frame[column]
        ]


def test_codec_preserves_background_absent_and_unknown_categories():
    background = pd.DataFrame({"group": ["a", "b"], "x": [0.0, 1.0]})
    sample = pd.DataFrame({"group": ["d"], "x": [2.0]})  # known in training, absent here
    codec = LosslessCodec.build([sample, background], ["group", "x"])
    decoded = codec.decode(codec.encode_frame(sample))
    assert decoded["group"].tolist() == ["d"]
    # Unknown-to-training category also survives exactly.
    unknown = pd.DataFrame({"group": ["never-seen"], "x": [3.0]})
    codec2 = LosslessCodec.build([unknown, background], ["group", "x"])
    assert codec2.decode(codec2.encode_frame(unknown))["group"].tolist() == ["never-seen"]


def test_background_sampling_is_deterministic():
    frame = pd.DataFrame({"x": range(40)})
    first, positions_a = _sample_background(frame, 10, 42)
    second, positions_b = _sample_background(frame, 10, 42)
    assert positions_a == positions_b
    pd.testing.assert_frame_equal(first, second)


# --- support matrix --------------------------------------------------------

@pytest.mark.parametrize(
    "estimator",
    [LogisticRegression(max_iter=500), DecisionTreeClassifier(random_state=0), None],
)
def test_supported_classifiers(estimator):
    frame = classification_frame()
    features, target = frame.drop(columns="target"), frame["target"]
    from sklearn.ensemble import RandomForestClassifier

    estimator = estimator or RandomForestClassifier(n_estimators=10, random_state=0)
    support = model_support(make_loaded("classification", estimator, features, target))
    assert support.supported and support.task == "classification"


@pytest.mark.parametrize(
    "estimator",
    [LinearRegression(), Ridge(alpha=1.0), None],
)
def test_supported_regressors(estimator):
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.linear_model import ElasticNet, Lasso
    from sklearn.tree import DecisionTreeRegressor

    estimator = estimator or Lasso(alpha=0.01)
    rng = np.random.default_rng(0)
    features = pd.DataFrame({"x": rng.normal(size=40), "y": rng.normal(size=40)})
    target = 2 * features["x"] - features["y"]
    support = model_support(make_loaded("regression", estimator, features, target))
    assert support.supported and support.task == "regression"
    for other in (ElasticNet(alpha=0.1), DecisionTreeRegressor(random_state=0),
                  RandomForestRegressor(n_estimators=10, random_state=0)):
        assert model_support(make_loaded("regression", other, features, target)).supported


@pytest.mark.parametrize(
    "task, estimator",
    [
        ("classification", GradientBoostingClassifier(n_estimators=5, random_state=0)),
        ("regression", GradientBoostingRegressor(n_estimators=5, random_state=0)),
    ],
)
def test_unsupported_estimators_are_rejected(task, estimator):
    rng = np.random.default_rng(0)
    features = pd.DataFrame({"x": rng.normal(size=30), "y": rng.normal(size=30)})
    target = (
        (features["x"] > 0).astype(int) if task == "classification"
        else features["x"] - features["y"]
    )
    loaded = make_loaded(task, estimator, features, target)
    support = model_support(loaded)
    assert not support.supported
    assert "subset" in support.reason
    with pytest.raises(ExplanationError):
        explain_row(loaded, features.iloc[[0]], features.iloc[:5], row_position=1,
                    class_index=0 if task == "classification" else None,
                    background_size=5, cycles=1)


# --- explanation behavior --------------------------------------------------

def test_explanation_reconstructs_and_covers_all_predictors():
    frame = classification_frame()
    loaded = make_loaded("classification", DecisionTreeClassifier(max_depth=3, random_state=0),
                         frame.drop(columns="target"), frame["target"])
    background = frame.drop(columns="target").iloc[:20]
    sample = frame.drop(columns="target").iloc[[5]]
    result = explain_row(loaded, sample, background, row_position=1, class_index=1,
                         background_size=12, cycles=3, seed=42)
    assert result["schema_version"] == EXPLANATION_SCHEMA_VERSION
    assert result["approximate"] and not result["exact_shap"]
    assert result["reconstruction_abs_error"] <= 1e-7
    assert len(result["sample_features"]) == outcome_feature_count(loaded)
    assert result["background_size_actual"] == 12
    assert result["model_rows"] <= result["model_row_cap"]


def outcome_feature_count(loaded):
    return loaded.metadata["n_features"]


def test_class_probability_selection_multiclass():
    rng = np.random.default_rng(3)
    frame = pd.DataFrame({"x": rng.normal(size=60), "z": rng.normal(size=60)})
    frame["target"] = np.digitize(frame["x"] + frame["z"], [-0.5, 0.5])
    loaded = make_loaded("classification", LogisticRegression(max_iter=500),
                         frame.drop(columns="target"), frame["target"])
    background = frame.drop(columns="target").iloc[:20]
    sample = frame.drop(columns="target").iloc[[2]]
    seen = []
    for index in range(len(loaded.metadata["classes"])):
        result = explain_row(loaded, sample, background, row_position=1, class_index=index,
                             background_size=8, cycles=2, seed=42)
        assert result["target_class"] == loaded.metadata["classes"][index]
        assert result["output_space"] == "probability"
        seen.append(result["model_output"])
    assert len(set(np.round(seen, 8))) == len(seen)


def test_regression_explains_predicted_value():
    rng = np.random.default_rng(4)
    frame = pd.DataFrame({"x": rng.normal(size=50), "z": rng.normal(size=50)})
    frame["target"] = 3 * frame["x"] - 2 * frame["z"]
    loaded = make_loaded("regression", Ridge(alpha=0.5),
                         frame.drop(columns="target"), frame["target"])
    result = explain_row(loaded, frame.drop(columns="target").iloc[[1]],
                         frame.drop(columns="target").iloc[:20],
                         row_position=1, background_size=8, cycles=2, seed=42)
    assert result["output_space"] == "predicted_value"
    assert result["target_class"] is None
    assert result["reconstruction_abs_error"] <= 1e-6


def test_missing_values_and_unknown_category_are_handled():
    frame = classification_frame()
    features = frame.drop(columns="target").copy()
    features.loc[0, "x"] = np.nan
    features.loc[1, "group"] = "never-seen"
    target = frame["target"]
    loaded = make_loaded("classification", LogisticRegression(max_iter=500), features, target)
    background = features.iloc[:20].copy()
    sample = features.iloc[[0, 1]]
    result_missing = explain_row(loaded, sample, background, row_position=1, class_index=1,
                                 background_size=8, cycles=2, seed=42)
    assert any(record["missing"] for record in result_missing["sample_features"])
    result_unknown = explain_row(loaded, sample, background, row_position=2, class_index=1,
                                 background_size=8, cycles=2, seed=42)
    assert result_unknown["reconstruction_abs_error"] <= 1e-7


def test_no_fit_and_prediction_and_hash_unchanged(tmp_path, monkeypatch):
    frame = classification_frame()
    loaded = make_loaded("classification", LogisticRegression(max_iter=500),
                         frame.drop(columns="target"), frame["target"])
    model_path = tmp_path / "model.joblib"
    import joblib

    joblib.dump(loaded.model, model_path)
    before_hash = hashlib.sha256(model_path.read_bytes()).hexdigest()
    before_prediction = predict_dataframe(loaded, frame)[0]

    from sklearn.pipeline import Pipeline as SkPipeline

    def forbidden_fit(*_args, **_kwargs):
        raise AssertionError("explain must never call fit")

    monkeypatch.setattr(SkPipeline, "fit", forbidden_fit)
    result = explain_row(loaded, frame.drop(columns="target").iloc[[3]],
                         frame.drop(columns="target").iloc[:20], row_position=1,
                         class_index=0, background_size=8, cycles=2, seed=1)
    assert result["no_model_fit"]
    monkeypatch.undo()
    after_hash = hashlib.sha256(model_path.read_bytes()).hexdigest()
    after_prediction = predict_dataframe(loaded, frame)[0]
    pd.testing.assert_frame_equal(before_prediction, after_prediction)
    assert before_hash == after_hash


def test_determinism_same_seed():
    frame = classification_frame()
    loaded = make_loaded("classification", DecisionTreeClassifier(max_depth=2, random_state=0),
                         frame.drop(columns="target"), frame["target"])
    args = {"row_position": 1, "class_index": 0, "background_size": 10, "cycles": 3, "seed": 7}
    background = frame.drop(columns="target").iloc[:20]
    sample = frame.drop(columns="target").iloc[[4]]
    first = explain_row(loaded, sample, background, **args)
    second = explain_row(loaded, sample, background, **args)
    values_a = [record["contribution"] for record in first["sample_features"]]
    values_b = [record["contribution"] for record in second["sample_features"]]
    np.testing.assert_allclose(values_a, values_b, rtol=0, atol=0)


def test_numpy_random_state_is_restored():
    frame = classification_frame()
    loaded = make_loaded("classification", DecisionTreeClassifier(max_depth=2, random_state=0),
                         frame.drop(columns="target"), frame["target"])
    np.random.seed(123)
    expected = np.random.random(3)
    np.random.seed(123)
    explain_row(loaded, frame.drop(columns="target").iloc[[4]],
                frame.drop(columns="target").iloc[:20], row_position=1, class_index=0,
                background_size=8, cycles=2, seed=9)
    np.testing.assert_allclose(np.random.random(3), expected, rtol=0, atol=0)


# --- validation and budget -------------------------------------------------

@pytest.mark.parametrize(
    "kwargs",
    [
        {"background_size": 0},
        {"background_size": 101},
        {"cycles": 0},
        {"cycles": 21},
        {"seed": 1.5},
        {"row_position": 0},
    ],
)
def test_parameter_validation(kwargs):
    frame = classification_frame()
    loaded = make_loaded("classification", LogisticRegression(max_iter=500),
                         frame.drop(columns="target"), frame["target"])
    args = {"row_position": 1, "class_index": 0, "background_size": 8, "cycles": 2, "seed": 42}
    args.update(kwargs)
    with pytest.raises(ExplanationError):
        explain_row(loaded, frame.drop(columns="target").iloc[[0]],
                    frame.drop(columns="target").iloc[:20], **args)


def test_class_index_required_and_bounded():
    frame = classification_frame()
    loaded = make_loaded("classification", LogisticRegression(max_iter=500),
                         frame.drop(columns="target"), frame["target"])
    sample = frame.drop(columns="target").iloc[[0]]
    background = frame.drop(columns="target").iloc[:20]
    with pytest.raises(ExplanationError):
        explain_row(loaded, sample, background, row_position=1, background_size=8, cycles=2)
    with pytest.raises(ExplanationError):
        explain_row(loaded, sample, background, row_position=1, class_index=5,
                    background_size=8, cycles=2)


def test_budget_is_rejected_before_computation():
    rng = np.random.default_rng(5)
    features = pd.DataFrame({
        f"f{index}": rng.normal(size=200) for index in range(100)
    })
    target = (features["f0"] > 0).astype(int)
    loaded = make_loaded("classification", LogisticRegression(max_iter=200), features, target)
    with pytest.raises(ExplanationError, match="row budget"):
        explain_row(loaded, features.iloc[[0]], features.iloc[:100], row_position=1,
                    class_index=0, background_size=100, cycles=20)


def test_feature_limit_is_rejected():
    rng = np.random.default_rng(6)
    features = pd.DataFrame({f"f{index}": rng.normal(size=25) for index in range(101)})
    target = (features["f0"] > 0).astype(int)
    loaded = make_loaded("classification", LogisticRegression(max_iter=200), features, target)
    with pytest.raises(ExplanationError, match="predictor explanation limit"):
        explain_row(loaded, features.iloc[[0]], features.iloc[:10], row_position=1,
                    class_index=0, background_size=5, cycles=1)


def test_missing_optional_dependency_reports_install_hint(monkeypatch):
    frame = classification_frame()
    loaded = make_loaded("classification", LogisticRegression(max_iter=500),
                         frame.drop(columns="target"), frame["target"])

    def unavailable():
        raise ExplanationUnavailableError("install explain extra")

    monkeypatch.setattr("psyml.explanation._import_shap", unavailable)
    with pytest.raises(ExplanationUnavailableError):
        explain_row(loaded, frame.drop(columns="target").iloc[[0]],
                    frame.drop(columns="target").iloc[:20], row_position=1,
                    class_index=0, background_size=8, cycles=2)


def test_plan_explanation_validates_without_shap(monkeypatch):
    frame = classification_frame()
    loaded = make_loaded("classification", LogisticRegression(max_iter=500),
                         frame.drop(columns="target"), frame["target"])

    def unavailable():
        raise AssertionError("plan must not import shap")

    monkeypatch.setattr("psyml.explanation._import_shap", unavailable)
    plan = plan_explanation(loaded, frame.drop(columns="target").iloc[[0]],
                            frame.drop(columns="target").iloc[:20], row_position=1,
                            class_index=0, background_size=10, cycles=4)
    assert plan["supported"] and plan["max_evals"] == 4 * (2 * loaded.metadata["n_features"] + 1)


# --- artifacts -------------------------------------------------------------

def test_write_explanation_creates_only_real_artifacts(tmp_path):
    frame = classification_frame()
    loaded = make_loaded("classification", DecisionTreeClassifier(max_depth=2, random_state=0),
                         frame.drop(columns="target"), frame["target"])
    result = explain_row(loaded, frame.drop(columns="target").iloc[[6]],
                         frame.drop(columns="target").iloc[:20], row_position=1,
                         class_index=1, background_size=8, cycles=2, seed=42)
    out = tmp_path / "explained"
    artifacts = write_explanation(result, out)
    for path in artifacts.values():
        assert Path(path).is_file()
    assert set(json.loads(Path(artifacts["json"]).read_text()).keys()) >= {
        "base_value", "model_output", "reconstruction", "limitations",
    }
    csv_text = Path(artifacts["csv"]).read_text()
    for record in result["sample_features"]:
        assert record["name"] in csv_text


def _sample_result(loaded, frame, class_index=1):
    return explain_row(
        loaded,
        frame.drop(columns="target" if "target" in frame else []).iloc[[6]],
        frame.drop(columns="target" if "target" in frame else []).iloc[:20],
        row_position=1,
        class_index=class_index,
        background_size=8,
        cycles=2,
        seed=42,
    )


def test_waterfall_segments_are_cumulative_and_reconstruct_output():
    frame = classification_frame()
    loaded = make_loaded(
        "classification",
        DecisionTreeClassifier(max_depth=3, random_state=0),
        frame.drop(columns="target"),
        frame["target"],
    )
    result = _sample_result(loaded, frame)
    segments = build_waterfall_segments(result)
    assert segments[0]["start"] == pytest.approx(result["base_value"])
    assert segments[-1]["end"] == pytest.approx(result["model_output"], abs=1e-7)
    for previous, current in itertools.pairwise(segments):
        assert current["start"] == pytest.approx(previous["end"])
        assert current["contribution"] == pytest.approx(current["end"] - current["start"])
    total = sum(segment["contribution"] for segment in segments)
    assert result["base_value"] + total == pytest.approx(result["model_output"], abs=1e-7)


def test_waterfall_keeps_tail_contributions_after_top_n():
    rng = np.random.default_rng(21)
    features = pd.DataFrame({f"f{index}": rng.normal(size=40) for index in range(20)})
    target = (features["f0"] + features["f1"] > 0).astype(int)
    loaded = make_loaded("classification", LogisticRegression(max_iter=300), features, target)
    result = explain_row(
        loaded,
        features.iloc[[3]],
        features.iloc[:20],
        row_position=1,
        class_index=0,
        background_size=6,
        cycles=2,
        seed=42,
    )
    segments = build_waterfall_segments(result, top_n=5)
    assert len(segments) == 6
    assert segments[-1]["label"].startswith("other 15 predictors")
    assert result["base_value"] + sum(s["contribution"] for s in segments) == pytest.approx(
        result["model_output"], abs=1e-7
    )


def test_waterfall_uses_result_tolerance_for_large_scale_outputs(tmp_path):
    """The renderer accepts the same atol/rtol the core used for reconstruction.

    Large-scale regression outputs can pass the core np.isclose check on rtol
    while exceeding bare atol; rendering must not reject them on an inconsistent
    threshold.
    """
    import psyml.explanation as explanation_module

    base = 1.0e10
    result = {
        "base_value": base,
        "model_output": base + 1.0,  # within atol(1e-7) + rtol(1e-6)*|output|
        "output_space": "predicted_value",
        "target_class": None,
        "algorithm": "permutation",
        "cycles": 5,
        "shap_version": "test",
        "tolerance": {"atol": 1e-7, "rtol": 1e-6},
        "sample_features": [
            {
                "name": "big",
                "value": 2.0,
                "missing": False,
                "contribution": 1.0,
                "abs_contribution": 1.0,
                "direction": "positive",
                "rank": 1,
            },
        ],
    }
    png = tmp_path / "waterfall.png"
    explanation_module._render_waterfall(result, png)
    assert png.is_file()

    # Endpoints outside both atol and rtol still abort rendering.
    broken = dict(result, model_output=base + 1.0e6)
    with pytest.raises(ExplanationError):
        explanation_module._render_waterfall(broken, tmp_path / "broken.png")


def test_metadata_records_background_provenance_and_counted_calls():
    frame = classification_frame()
    loaded = make_loaded(
        "classification",
        LogisticRegression(max_iter=500),
        frame.drop(columns="target"),
        frame["target"],
    )
    background = frame.drop(columns="target").iloc[:17]
    result = explain_row(
        loaded,
        frame.drop(columns="target").iloc[[2]],
        background,
        row_position=1,
        class_index=1,
        background_size=10,
        cycles=2,
        seed=5,
    )
    assert result["background_row_count"] == 17
    assert result["background_size_actual"] == 10
    assert result["model_calls"] >= 1 and result["model_rows"] >= 1
    assert result["finite_outputs_verified"] is True
    assert result["seed_supported_range"] == [0, SEED_MAX]
    assert result["feature_mapping"] is None and result["manual_mapping"] is False


def test_seed_range_and_unsupported_value_types_are_rejected():
    frame = classification_frame()
    loaded = make_loaded(
        "classification",
        LogisticRegression(max_iter=500),
        frame.drop(columns="target"),
        frame["target"],
    )
    background = frame.drop(columns="target").iloc[:20]
    sample = frame.drop(columns="target").iloc[[0]]
    for bad_seed in (-1, SEED_MAX + 1):
        with pytest.raises(ExplanationError, match="seed"):
            explain_row(loaded, sample, background, row_position=1, class_index=0,
                        background_size=8, cycles=2, seed=bad_seed)
    unsupported = pd.DataFrame({"cat": [["a"], ["b"]]})
    with pytest.raises(ExplanationError, match="unsupported value type"):
        LosslessCodec.build([unsupported], ["cat"])


def test_bare_or_custom_pipelines_are_rejected_but_prediction_still_works():
    from sklearn.ensemble import RandomForestClassifier

    rng = np.random.default_rng(8)
    features = pd.DataFrame({"x": rng.normal(size=60), "y": rng.normal(size=60)})
    target = (features["x"] + features["y"] > 0).astype(int)
    estimator = RandomForestClassifier(n_estimators=8, random_state=0)

    bare = Pipeline([("model", estimator)])
    bare.fit(features, target)
    bare_loaded = make_loaded("classification", estimator, features, target)
    bare_loaded.model = bare
    support = model_support(bare_loaded)
    assert not support.supported and "layout" in support.reason
    # Ordinary prediction on the same object is untouched by the explanation limit.
    predicted, _ = predict_dataframe(bare_loaded, features)
    assert len(predicted) == len(features)

    custom_preprocessor = build_preprocessor(features, missing_strategy="median", scaling="standard")
    for index, (name, transform, columns) in enumerate(custom_preprocessor.transformers):
        if name == "numeric" and hasattr(transform, "steps"):
            transform.steps = [("custom_scale" if step == "scale" else step, obj)
                               for step, obj in transform.steps]
            custom_preprocessor.transformers[index] = (name, transform, columns)
    custom_pipeline = Pipeline([("preprocess", custom_preprocessor), ("model", estimator)])
    custom_pipeline.fit(features, target)
    custom_loaded = make_loaded("classification", estimator, features, target)
    custom_loaded.model = custom_pipeline
    custom_support = model_support(custom_loaded)
    assert not custom_support.supported
    with pytest.raises(ExplanationError):
        explain_row(custom_loaded, features.iloc[[0]], features.iloc[:5], row_position=1,
                    class_index=0, background_size=5, cycles=1)


def test_missing_provenance_or_fit_scope_is_rejected():
    frame = classification_frame()
    loaded = make_loaded(
        "classification",
        LogisticRegression(max_iter=500),
        frame.drop(columns="target"),
        frame["target"],
    )
    del loaded.metadata["psyml_version"]
    assert not model_support(loaded).supported
    loaded.metadata["psyml_version"] = "0.2.0"
    del loaded.metadata["fit_scope"]
    support = model_support(loaded)
    assert not support.supported and "fit scope" in support.reason


def test_drop_none_identity_passthrough_is_supported_by_shared_structure_check():
    """The shared structure check accepts sklearn's fitted identity passthrough."""
    from psyml.explanation import _pipeline_structure_reason

    rng = np.random.default_rng(11)
    features = pd.DataFrame({
        "x": rng.normal(size=48),
        "y": rng.normal(size=48),
        "group": (["a", "b"] * 24),
    })
    target = 2.0 * features["x"] - features["y"]
    preprocessor = build_preprocessor(features, missing_strategy="drop", scaling="none")
    pipeline = Pipeline([("preprocess", preprocessor), ("model", LinearRegression())])
    pipeline.fit(features, target)
    assert _pipeline_structure_reason(pipeline) is None

    loaded = make_loaded("regression", LinearRegression(), features, target)
    loaded.model = pipeline
    loaded.metadata["estimator_class"] = (
        "sklearn.linear_model._base.LinearRegression"
    )
    support = model_support(loaded)
    assert support.supported, support.reason
    plan = plan_explanation(
        loaded, features.iloc[[0]], features.iloc[:5], row_position=1,
        background_size=5, cycles=1,
    )
    assert plan["supported"] and plan["task"] == "regression"


def test_authentic_saved_psyml_model_is_supported(tmp_path):
    from psyml import ExperimentConfig
    from psyml.prediction import load_model
    from psyml.runner import run_experiment

    rng = np.random.default_rng(7)
    frame = pd.DataFrame({"x": rng.normal(size=60), "y": rng.normal(size=60)})
    frame["target"] = (frame["x"] + frame["y"] > 0).astype(int)
    config = ExperimentConfig(task="classification", model_name="logistic_regression",
                              target_column="target", output_dir=tmp_path / "run",
                              figure_types=[])
    result = run_experiment(config, frame)
    model_path = config.output_dir / result.model_export["model_path"]
    loaded = load_model(model_path, trusted=True)
    support = model_support(loaded)
    assert support.supported and support.fit_scope == "all_analyzed_rows"
    explained = explain_row(
        loaded, frame.drop(columns="target").iloc[[1]], frame.drop(columns="target").iloc[:20],
        row_position=1, class_index=0, background_size=8, cycles=2, seed=42,
    )
    assert explained["reconstruction_abs_error"] <= 1e-7


def test_write_explanation_leaves_no_result_on_render_failure(tmp_path, monkeypatch):
    frame = classification_frame()
    loaded = make_loaded(
        "classification",
        DecisionTreeClassifier(max_depth=2, random_state=0),
        frame.drop(columns="target"),
        frame["target"],
    )
    result = _sample_result(loaded, frame)
    kept = tmp_path / "kept"
    write_explanation(result, kept)
    previous_json = (kept / "shap_explanation.json").read_text()

    import psyml.explanation as explanation_module

    def boom(*_args, **_kwargs):
        raise RuntimeError("simulated render failure")

    monkeypatch.setattr(explanation_module, "_render_waterfall", boom)
    failed = tmp_path / "failed"
    with pytest.raises(RuntimeError):
        write_explanation(result, failed)
    # A failed run publishes no completion marker and clears its own staging.
    assert not (failed / "shap_explanation.json").exists()
    assert not list(failed.glob(".psyml-explanation-staging-*"))
    assert (kept / "shap_explanation.json").read_text() == previous_json


def test_write_explanation_does_not_publish_on_serialization_failure(tmp_path):
    frame = classification_frame()
    loaded = make_loaded(
        "classification",
        DecisionTreeClassifier(max_depth=2, random_state=0),
        frame.drop(columns="target"),
        frame["target"],
    )
    result = _sample_result(loaded, frame)
    kept = tmp_path / "kept"
    write_explanation(result, kept)
    previous_json = (kept / "shap_explanation.json").read_text()
    broken = dict(result)
    broken["limitations"] = [object()]  # not JSON-serializable
    failed = tmp_path / "failed"
    with pytest.raises(TypeError):
        write_explanation(broken, failed)
    # The completion marker is never written and no staging directory survives.
    assert not (failed / "shap_explanation.json").exists()
    assert not list(failed.glob(".psyml-explanation-staging-*"))
    assert (kept / "shap_explanation.json").read_text() == previous_json


def test_write_explanation_rejects_artifact_path_collisions(tmp_path):
    frame = classification_frame()
    loaded = make_loaded(
        "classification",
        DecisionTreeClassifier(max_depth=2, random_state=0),
        frame.drop(columns="target"),
        frame["target"],
    )
    result = _sample_result(loaded, frame)
    out = tmp_path / "explained"
    out.mkdir()
    protected = out / "shap_contributions.csv"
    protected.write_text("participant data")
    with pytest.raises(ExplanationError, match="protected input"):
        write_explanation(result, out, protected_paths=[protected])
    assert protected.read_text() == "participant data"


def test_write_explanation_json_indexes_completed_artifacts(tmp_path):
    frame = classification_frame()
    loaded = make_loaded(
        "classification",
        DecisionTreeClassifier(max_depth=2, random_state=0),
        frame.drop(columns="target"),
        frame["target"],
    )
    result = _sample_result(loaded, frame)
    out = tmp_path / "explained"
    write_explanation(result, out)
    document = json.loads((out / "shap_explanation.json").read_text())
    assert set(document["artifacts"]) == {"json", "csv", "png", "notes"}
    for name in document["artifacts"].values():
        assert (out / name).is_file()


def test_write_explanation_refuses_nonempty_directory(tmp_path):
    frame = classification_frame()
    loaded = make_loaded("classification", DecisionTreeClassifier(max_depth=2, random_state=0),
                         frame.drop(columns="target"), frame["target"])
    result = explain_row(loaded, frame.drop(columns="target").iloc[[6]],
                         frame.drop(columns="target").iloc[:20], row_position=1,
                         class_index=1, background_size=8, cycles=2, seed=42)
    out = tmp_path / "explained"
    out.mkdir()
    (out / "keep.txt").write_text("user data")
    with pytest.raises(ExplanationError, match="not empty"):
        write_explanation(result, out)
    assert (out / "keep.txt").read_text() == "user data"
    assert not (out / "shap_explanation.json").exists()

    # A completed explanation directory is never overwritten either.
    fresh = tmp_path / "fresh"
    write_explanation(result, fresh)
    original = (fresh / "shap_explanation.json").read_text()
    with pytest.raises(ExplanationError, match="not empty"):
        write_explanation(result, fresh)
    assert (fresh / "shap_explanation.json").read_text() == original
