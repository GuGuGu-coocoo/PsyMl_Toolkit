"""Only the final full-data Pipeline is exported, without altering validation."""
import json
from dataclasses import replace

import joblib
import numpy as np
import pandas as pd
import pytest
from jsonschema import validate

from psyml import ExperimentConfig, run_experiment
from psyml.protocol import config_from_dict, config_to_dict, schema_text


@pytest.mark.parametrize('task,name', [('classification', 'logistic_regression'),
                                       ('regression', 'linear_regression')])
def test_pipeline_roundtrip_and_metadata(tmp_path, task, name):
    frame = pd.DataFrame({'x': range(40), 'category': ['a', 'b'] * 20,
                          'y': [0, 1] * 20 if task == 'classification' else range(40)})
    frame.loc[0, 'y'] = np.nan
    config = ExperimentConfig(task=task, target_column='y', model_name=name,
                              output_dir=tmp_path, figure_types=[])
    result = run_experiment(config, frame)
    path = tmp_path / result.model_export['model_path']
    loaded = joblib.load(path)
    features = frame.drop(columns='y')
    np.testing.assert_array_equal(result.model.predict(features), loaded.predict(features))
    metadata = json.loads((path.parent / 'model_metadata.json').read_text())
    assert metadata['analyzed_row_count'] == 39
    assert metadata['feature_names'] == ['x', 'category']
    assert metadata['feature_types'] == {'x': 'numeric', 'category': 'categorical'}
    assert metadata['best_parameters'] == result.effective_params
    assert metadata['fit_scope'] == 'all_analyzed_rows'
    assert metadata['supports_probability'] == (task == 'classification')
    scaler = loaded.named_steps['preprocess'].named_transformers_['numeric']['scale']
    assert scaler.mean_[0] == frame.loc[1:, 'x'].mean()
    payload = json.loads((tmp_path / 'result.json').read_text())
    validate(payload, json.loads(schema_text('result')))
    assert payload['artifacts']['saved_model'] == result.model_export['model_path']


def test_disabled_and_independent_never_save(tmp_path):
    frame = pd.DataFrame({'x': range(30), 'y': range(30)})
    config = ExperimentConfig(task='regression', target_column='y', model_name='ridge',
                              output_dir=tmp_path / 'disabled', save_best_model=False,
                              figure_types=[])
    run_experiment(config, frame)
    assert not list(tmp_path.rglob('*.joblib'))
    independent = replace(config, output_dir=tmp_path / 'independent', save_best_model=True,
                          primary_validation=None, validation_strategies=['holdout', 'k_fold'])
    result = run_experiment(independent, frame)
    assert result.model is None
    assert not list(tmp_path.rglob('*.joblib'))
    summary = json.loads((independent.output_dir / 'result.json').read_text())
    assert summary['model_export']['status'] == 'independent_validations'


def test_old_config_default_and_toggle_validation(tmp_path):
    config = ExperimentConfig(task='regression', target_column='y', model_name='ridge')
    payload = config_to_dict(config)
    del payload['save_best_model']
    assert config_from_dict(payload).save_best_model is True
    assert config_from_dict({**payload, 'save_best_model': False}).save_best_model is False
    with pytest.raises(ValueError, match='boolean'):
        config_from_dict({**payload, 'save_best_model': 'false'})
