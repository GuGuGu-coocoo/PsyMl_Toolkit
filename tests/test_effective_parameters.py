"""Actual defaults, factory overrides and selected parameters must be inspectable."""
import json

import pandas as pd
import pytest

from psyml import ExperimentConfig, run_experiment
from psyml.models.factory import build_model
from psyml.models.parameters import effective_parameters


@pytest.mark.parametrize('name,params', [
    ('linear_regression', {}), ('ridge', {'alpha': 2.5}),
    ('random_forest', {'n_estimators': 3}),
])
def test_final_parameter_record(tmp_path, name, params):
    frame = pd.DataFrame({'x': range(30), 'y': range(30)})
    result = run_experiment(ExperimentConfig(
        task='regression', target_column='y', model_name=name, model_params=params,
        random_seed=13, output_dir=tmp_path, figure_types=[],
    ), frame)
    saved = json.loads((tmp_path / 'best_parameters.json').read_text())
    assert saved == result.model.named_steps['model'].get_params(deep=False)
    assert saved == result.effective_params
    assert result.best_params == params
    assert 'coef_' not in saved
    if name == 'random_forest':
        assert saved['random_state'] == 13


def test_nested_estimators_record_all_defaults():
    model = build_model('classification', 'stacking', 17, {})
    saved = effective_parameters(model)
    assert saved['estimators'][1][1]['parameters']['random_state'] == 17
    assert saved['final_estimator']['parameters']['max_iter'] == 500
    json.dumps(saved, allow_nan=False)
