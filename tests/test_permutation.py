"""Behavioral tests for permutation importance computation and its config."""

import json

import jsonschema
import numpy as np
import pandas as pd
import pytest
from sklearn.compose import ColumnTransformer
from sklearn.exceptions import NotFittedError
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.tree import DecisionTreeClassifier

from psyml import ExperimentConfig, runner
from psyml.evaluation.permutation import (
    NonFiniteScoreError,
    PermutationImportanceError,
    default_score,
    extract_feature_encoding,
    permutation_importance,
)
from psyml.preprocessing.pipeline import build_preprocessor
from psyml.protocol import config_from_dict, config_to_dict, schema_text

CONTEXT = {"validation": "holdout", "fold": 0, "model_family": "logistic_regression"}


def _base_config(tmp_path):
    return ExperimentConfig(
        task="classification",
        target_column="target",
        model_name="logistic_regression",
        output_dir=tmp_path / "run",
    )


def classification_setup(seed=0, n=240):
    rng = np.random.default_rng(seed)
    signal = rng.normal(size=n)
    noise = rng.normal(size=n)
    category = rng.choice(["alpha", "beta", "gamma"], size=n)
    target = ((signal + 0.2 * rng.normal(size=n)) > 0).astype(int)
    features = pd.DataFrame(
        {"signal": signal, "noise": noise, "category": pd.Categorical(category)}
    )
    observed = pd.Series(target)
    model = Pipeline(
        [
            ("preprocess", build_preprocessor(features, "median", "standard")),
            ("model", LogisticRegression(max_iter=1000)),
        ]
    ).fit(features, observed)
    return model, features, observed


def regression_setup(seed=1, n=240):
    rng = np.random.default_rng(seed)
    signal = rng.normal(size=n)
    noise = rng.normal(size=n)
    target = 2.0 * signal + 0.1 * noise + 0.1 * rng.normal(size=n)
    features = pd.DataFrame({"signal": signal, "noise": noise})
    observed = pd.Series(target)
    model = Pipeline(
        [
            ("preprocess", build_preprocessor(features, "median", "standard")),
            ("model", LinearRegression()),
        ]
    ).fit(features, observed)
    return model, features, observed


# --- configuration and schema -------------------------------------------------


def test_config_defaults_and_round_trip(tmp_path):
    config = _base_config(tmp_path)
    assert config.permutation_importance is False
    assert config.permutation_repeats == 10

    schema = json.loads(schema_text("analysis_config"))
    assert schema["properties"]["permutation_importance"]["default"] is False
    assert schema["properties"]["permutation_repeats"] == {
        "type": "integer",
        "minimum": 1,
        "maximum": 100,
        "default": 10,
    }

    payload = config_to_dict(config)
    jsonschema.validate(payload, schema)
    assert payload["permutation_importance"] is False
    assert payload["permutation_repeats"] == 10
    assert config_from_dict(payload) == config


def test_config_accepts_integral_float_repeats_and_normalises(tmp_path):
    config = ExperimentConfig(
        **{
            **_base_config(tmp_path).__dict__,
            "permutation_importance": True,
            "permutation_repeats": 10.0,
        }
    )
    assert config.permutation_importance is True
    assert config.permutation_repeats == 10
    assert isinstance(config.permutation_repeats, int)

    payload = config_to_dict(config)
    jsonschema.validate(payload, json.loads(schema_text("analysis_config")))
    assert payload["permutation_repeats"] == 10
    # A GUI-style JSON document with 10.0 must load back as an int.
    restored = config_from_dict({**payload, "permutation_repeats": 10.0})
    assert restored.permutation_repeats == 10
    assert isinstance(restored.permutation_repeats, int)


@pytest.mark.parametrize(
    ("value", "error"),
    [
        (True, TypeError),
        (False, TypeError),
        (10.5, ValueError),
        (float("nan"), ValueError),
        (0, ValueError),
        (-1, ValueError),
        (101, ValueError),
        ("10", TypeError),
        (None, TypeError),
    ],
)
def test_config_rejects_invalid_repeats(tmp_path, value, error):
    with pytest.raises(error):
        ExperimentConfig(**{**_base_config(tmp_path).__dict__, "permutation_repeats": value})


def test_config_rejects_non_boolean_switch(tmp_path):
    for value in [1, 0, "yes", None]:
        with pytest.raises(TypeError):
            ExperimentConfig(
                **{**_base_config(tmp_path).__dict__, "permutation_importance": value}
            )


def test_legacy_config_without_new_fields_still_loads(tmp_path):
    payload = config_to_dict(_base_config(tmp_path))
    del payload["permutation_importance"]
    del payload["permutation_repeats"]
    jsonschema.validate(payload, json.loads(schema_text("analysis_config")))
    restored = config_from_dict(payload)
    assert restored.permutation_importance is False
    assert restored.permutation_repeats == 10


# --- scoring definitions ------------------------------------------------------


def test_default_score_matches_runner_for_all_metrics():
    observed = pd.Series([0, 1, 0, 1])
    predicted = np.array([0, 0, 1, 1])
    for metric in ["accuracy", "balanced_accuracy", "f1_macro"]:
        assert default_score(metric, observed, predicted) == pytest.approx(
            runner._selection_score(metric, observed, predicted)
        )

    observed_reg = pd.Series([1.0, 2.0, 3.0, 4.0])
    predicted_reg = np.array([1.5, 2.0, 2.5, 5.0])
    for metric in ["r2", "mae", "rmse"]:
        assert default_score(metric, observed_reg, predicted_reg) == pytest.approx(
            runner._selection_score(metric, observed_reg, predicted_reg)
        )

    with pytest.raises(PermutationImportanceError):
        default_score("roc_auc", observed, predicted)


def _expected_importance(model, features, observed, metric, seed, variable):
    order = np.random.default_rng(seed).permutation(len(features))
    baseline = runner._selection_score(metric, observed, model.predict(features))
    permuted = features.copy(deep=True)
    permuted[variable] = features[variable].array.take(order)
    after = runner._selection_score(metric, observed, model.predict(permuted))
    if metric in {"mae", "rmse"}:
        return after - baseline
    return baseline - after


def test_all_six_metrics_match_runner_definition_and_direction():
    model, features, observed = classification_setup()
    for metric in ["accuracy", "balanced_accuracy", "f1_macro"]:
        result = permutation_importance(
            model, features, observed, metric=metric, context=CONTEXT, seed=7, repeats=1
        )
        assert result["direction"] == "higher_is_better"
        assert result["baseline_score"] == pytest.approx(
            runner._selection_score(metric, observed, model.predict(features))
        )
        variable = next(v for v in result["variables"] if v["name"] == "signal")
        assert variable["importances"][0] == pytest.approx(
            _expected_importance(model, features, observed, metric, 7, "signal")
        )

    model_reg, features_reg, observed_reg = regression_setup()
    for metric in ["r2", "mae", "rmse"]:
        result = permutation_importance(
            model_reg, features_reg, observed_reg, metric=metric, context=CONTEXT, seed=7, repeats=1
        )
        assert result["direction"] == (
            "lower_is_better" if metric in {"mae", "rmse"} else "higher_is_better"
        )
        variable = next(v for v in result["variables"] if v["name"] == "signal")
        assert variable["importances"][0] == pytest.approx(
            _expected_importance(model_reg, features_reg, observed_reg, metric, 7, "signal")
        )


# --- engine behavior ----------------------------------------------------------


def test_signal_outweighs_noise_reproducible_and_no_mutation():
    model, features, observed = classification_setup()
    original_features = features.copy(deep=True)
    params_before = model.get_params(deep=True)

    first = permutation_importance(
        model, features, observed, metric="balanced_accuracy", context=CONTEXT, seed=3, repeats=4
    )
    second = permutation_importance(
        model, features, observed, metric="balanced_accuracy", context=CONTEXT, seed=3, repeats=4
    )
    assert first == second

    means = {v["name"]: v["mean"] for v in first["variables"]}
    assert means["signal"] > means["noise"]
    pd.testing.assert_frame_equal(features, original_features)
    assert model.get_params(deep=True) == params_before

    different = permutation_importance(
        model, features, observed, metric="balanced_accuracy", context=CONTEXT, seed=4, repeats=4
    )
    assert any(
        v["importances"] != w["importances"] for v, w in zip(first["variables"], different["variables"])
    )


def test_repeat_records_mean_and_ddof0_std():
    model, features, observed = classification_setup()
    result = permutation_importance(
        model, features, observed, metric="f1_macro", context=CONTEXT, seed=5, repeats=5
    )
    for variable in result["variables"]:
        values = np.asarray(variable["importances"])
        assert len(values) == 5
        assert variable["mean"] == pytest.approx(values.mean())
        assert variable["std"] == pytest.approx(values.std(ddof=0))

    single = permutation_importance(
        model, features, observed, metric="f1_macro", context=CONTEXT, seed=5, repeats=1
    )
    assert all(variable["std"] == 0.0 for variable in single["variables"])
    assert all(len(variable["importances"]) == 1 for variable in single["variables"])


class _RecordingModel:
    def __init__(self, inner):
        self.inner = inner
        self.frames = []

    def predict(self, frame):
        self.frames.append(frame.copy(deep=True))
        return self.inner.predict(frame)


def test_permutes_original_category_column_preserving_dtype_and_index():
    inner, features, observed = classification_setup()
    features.index = np.arange(1000, 1000 + len(features))
    original = features.copy(deep=True)
    spy = _RecordingModel(inner)

    permutation_importance(
        spy, features, observed, metric="accuracy", context=CONTEXT, seed=0, repeats=1
    )

    baseline = spy.frames[0]
    assert baseline.equals(features)
    permutations = spy.frames[1:]
    assert len(permutations) == features.shape[1]
    for index, column in enumerate(features.columns):
        permuted = permutations[index]
        assert list(permuted.columns) == list(features.columns)
        assert permuted.index.equals(features.index)
        assert permuted[column].dtype == features[column].dtype
        for other in features.columns:
            if other == column:
                assert sorted(map(str, permuted[other])) == sorted(map(str, features[other]))
            else:
                assert permuted[other].equals(features[other])
    category_column = list(features.columns).index("category")
    category_frame = permutations[category_column]
    assert category_frame["category"].dtype == features["category"].dtype
    assert set(category_frame["category"].cat.categories) == set(features["category"].cat.categories)
    assert not category_frame["category"].equals(features["category"])
    pd.testing.assert_frame_equal(features, original)


class _StubModel:
    def predict(self, frame):
        return frame["x"].to_numpy()


def test_negative_importance_is_retained():
    order = np.random.default_rng(0).permutation(4)
    features = pd.DataFrame({"x": [0, 1, 0, 1]})
    observed = pd.Series(features["x"].to_numpy()[order])
    result = permutation_importance(
        _StubModel(), features, observed, metric="accuracy", context=CONTEXT, seed=0, repeats=1
    )
    variable = result["variables"][0]
    assert variable["importances"][0] < 0
    assert variable["mean"] == pytest.approx(-0.5)


def test_unknown_metric_is_rejected_not_treated_as_rmse():
    model, features, observed = regression_setup()
    with pytest.raises(PermutationImportanceError, match="Unsupported"):
        permutation_importance(
            model, features, observed, metric="roc_auc", context=CONTEXT
        )


def test_non_finite_score_raises_instead_of_zero_filling():
    model, features, observed = regression_setup()
    with pytest.raises(NonFiniteScoreError):
        permutation_importance(
            model,
            features,
            observed,
            metric="rmse",
            context=CONTEXT,
            score=lambda _observed, _predicted: float("nan"),
        )

    def infinite_score(_observed, _predicted):
        return float("inf")

    model2, features2, observed2 = regression_setup()
    # Force a non-finite baseline by scoring before any permutation.
    with pytest.raises(NonFiniteScoreError):
        permutation_importance(
            model2, features2, observed2, metric="rmse", context=CONTEXT, score=infinite_score
        )


@pytest.mark.parametrize("permuted_value", [float("nan"), float("inf"), float("-inf")])
def test_permuted_non_finite_score_raises_after_finite_baseline(permuted_value):
    model, features, observed = regression_setup()
    calls = {"count": 0}

    def scorer(_observed, _predicted):
        calls["count"] += 1
        if calls["count"] == 1:
            return 1.0  # finite baseline so the failure comes from the permutation
        return permuted_value

    with pytest.raises(NonFiniteScoreError):
        permutation_importance(
            model,
            features,
            observed,
            metric="rmse",
            context=CONTEXT,
            seed=0,
            repeats=1,
            score=scorer,
        )
    # Baseline plus the first permuted score, then abort: no zero-filled result.
    assert calls["count"] == 2


def test_callback_exception_propagates():
    model, features, observed = regression_setup()

    def boom(_payload):
        raise RuntimeError("cancelled")

    with pytest.raises(RuntimeError, match="cancelled"):
        permutation_importance(
            model, features, observed, metric="rmse", context=CONTEXT, progress_callback=boom
        )


def test_progress_callback_reports_every_permutation():
    model, features, observed = regression_setup()
    events = []
    permutation_importance(
        model,
        features,
        observed,
        metric="rmse",
        context=CONTEXT,
        seed=0,
        repeats=3,
        progress_callback=events.append,
    )
    assert len(events) == 3 * features.shape[1]
    assert [event["permutation"] for event in events] == list(range(1, len(events) + 1))
    assert events[-1]["total"] == len(events)
    assert set(events[0]) == {"permutation", "total", "variable", "repeat"}


def test_engine_does_not_fit_and_requires_a_fitted_model():
    model, features, observed = classification_setup()

    def _forbidden_fit(*_args, **_kwargs):
        raise AssertionError("the engine must never fit")

    model.fit = _forbidden_fit
    result = permutation_importance(
        model, features, observed, metric="accuracy", context=CONTEXT, seed=0, repeats=1
    )
    assert result["variables"]

    fresh = Pipeline(
        [
            ("preprocess", build_preprocessor(features, "median", "standard")),
            ("model", LogisticRegression()),
        ]
    )
    with pytest.raises(NotFittedError):
        permutation_importance(fresh, features, observed, metric="accuracy", context=CONTEXT)


def test_context_and_metadata_document_scope_and_limits():
    model, features, observed = regression_setup()
    context = {
        "validation": "group_k_fold",
        "fold": 2,
        "model_family": "linear_regression",
        "extra": "kept",
    }
    result = permutation_importance(
        model, features, observed, metric="mae", context=context, seed=11, repeats=2
    )
    recorded = result["context"]
    assert recorded["validation"] == "group_k_fold"
    assert recorded["fold"] == 2
    assert recorded["model_family"] == "linear_regression"
    assert recorded["extra"] == "kept"
    assert recorded["data_scope"] == "outer_test"
    assert recorded["random_seed"] == 11
    assert recorded["repeats"] == 2
    assert recorded["metric"] == "mae"
    assert recorded["direction"] == "lower_is_better"
    assert recorded["n_rows"] == len(features)
    assert recorded["permutation_scheme"] == "rowwise_marginal"
    assert result["permutation_scheme"] == "rowwise_marginal"

    notes = " ".join(result["metadata"]["notes"])
    assert "block or group permutation" in notes
    assert "confidence interval" in notes
    assert "within-group dependence" in notes
    assert "not a causal effect" in notes
    assert result["metadata"]["not_a_confidence_interval"] is True


def test_context_missing_required_fields_is_rejected():
    model, features, observed = regression_setup()
    with pytest.raises(ValueError, match="missing required fields"):
        permutation_importance(
            model, features, observed, metric="mae", context={"fold": 0}
        )


# --- encoding extraction ------------------------------------------------------


def test_extract_feature_encoding_maps_mixed_pipeline_without_guessing():
    rng = np.random.default_rng(2)
    n = 80
    features = pd.DataFrame(
        {
            "signal_x": rng.normal(size=n),
            "grp_code": pd.Categorical(rng.choice(["x_y", "plain"], size=n)),
        }
    )
    observed = pd.Series((features["signal_x"] > 0).astype(int))
    model = Pipeline(
        [
            ("preprocess", build_preprocessor(features, "median", "standard")),
            ("model", LogisticRegression(max_iter=1000)),
        ]
    ).fit(features, observed)

    mapping = extract_feature_encoding(model, features)
    assert mapping["status"] == "available"
    assert set(mapping["original_features"]) == {"signal_x", "grp_code"}
    assert mapping["mapping"]["signal_x"]["kind"] == "numeric"
    assert mapping["mapping"]["signal_x"]["transformed_features"] == ["numeric__signal_x"]

    categorical = mapping["mapping"]["grp_code"]
    assert categorical["kind"] == "categorical"
    assert "categorical__grp_code_x_y" in mapping["transformed_features"]
    assert {entry["category"] for entry in categorical["categories"]} == {"x_y", "plain"}
    for entry in categorical["categories"]:
        assert entry["feature"] in mapping["transformed_features"]


def test_extract_feature_encoding_unavailable_without_preprocessor():
    _, features, observed = classification_setup()
    plain = LogisticRegression(max_iter=1000).fit(features[["signal", "noise"]], observed)
    assert extract_feature_encoding(plain)["status"] == "unavailable"


def test_extract_feature_encoding_unavailable_when_raw_columns_mismatch():
    model, features, _ = classification_setup()
    renamed = features.rename(columns={"signal": "signal_renamed"})
    assert extract_feature_encoding(model, renamed)["status"] == "unavailable"


@pytest.mark.filterwarnings("ignore:Skipping features without any observed values")
def test_extract_feature_encoding_unavailable_for_all_missing_column():
    rng = np.random.default_rng(6)
    n = 60
    features = pd.DataFrame(
        {
            "a": rng.normal(size=n),
            "b": [np.nan] * n,
        }
    )
    observed = pd.Series((features["a"] > 0).astype(int))
    model = Pipeline(
        [
            ("preprocess", build_preprocessor(features, "median", "standard")),
            ("model", DecisionTreeClassifier()),
        ]
    ).fit(features, observed)
    assert extract_feature_encoding(model, features)["status"] == "unavailable"


def test_extract_feature_encoding_unavailable_for_generated_template():
    rng = np.random.default_rng(8)
    n = 60
    generated = pd.DataFrame({f"column_{i}": rng.normal(size=n) for i in range(2)})
    observed = pd.Series((generated["column_0"] > 0).astype(int))
    model = Pipeline(
        [
            ("preprocess", build_preprocessor(generated, "median", "standard")),
            ("model", LogisticRegression(max_iter=1000)),
        ]
    ).fit(generated, observed)
    raw = pd.DataFrame({"signal": rng.normal(size=n), "noise": rng.normal(size=n)})
    result = extract_feature_encoding(model, raw)
    assert result["status"] == "unavailable"


def _fit_ohe_pipeline(features, observed, encoder):
    preprocess = ColumnTransformer(
        [("categorical", encoder, list(features.columns))], remainder="drop"
    )
    return Pipeline(
        [("preprocess", preprocess), ("model", LogisticRegression(max_iter=1000))]
    ).fit(features, observed)


def test_extract_feature_encoding_unavailable_for_drop_first_two_columns():
    rng = np.random.default_rng(11)
    n = 80
    features = pd.DataFrame(
        {
            "a": pd.Categorical(rng.choice(["a0", "a1"], size=n)),
            "b": pd.Categorical(rng.choice(["b0", "b1"], size=n)),
        }
    )
    observed = pd.Series(rng.integers(0, 2, size=n))
    encoder = OneHotEncoder(drop="first", sparse_output=False, handle_unknown="ignore")
    model = _fit_ohe_pipeline(features, observed, encoder)

    result = extract_feature_encoding(model, features)
    # Two categories per column but one dropped output each must not be
    # re-split by category count, which would misassign features across columns.
    assert result["status"] == "unavailable"
    assert "reason" in result
    assert "mapping" not in result


def test_extract_feature_encoding_unavailable_for_infrequent_categories():
    rng = np.random.default_rng(12)
    n = 80
    values = ["common"] * (n - 4) + ["rare1", "rare2", "rare3", "rare4"]
    features = pd.DataFrame({"grp": pd.Categorical(values)})
    observed = pd.Series(rng.integers(0, 2, size=n))
    encoder = OneHotEncoder(
        min_frequency=10, sparse_output=False, handle_unknown="ignore"
    )
    model = _fit_ohe_pipeline(features, observed, encoder)

    result = extract_feature_encoding(model, features)
    assert result["status"] == "unavailable"
    assert "reason" in result
    assert "mapping" not in result
