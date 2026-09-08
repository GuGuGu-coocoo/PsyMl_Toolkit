"""Inference preserves data and fails before predict for incompatible schemas."""
import json
from dataclasses import replace

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LinearRegression

from psyml import ExperimentConfig, run_experiment
from psyml.cli import main
from psyml.data.formats import OUTPUT_SUFFIXES, prediction_output_suffix
from psyml.data.io import load_dataframe, save_dataframe
from psyml.prediction import compatibility_check, load_model, predict_dataframe


@pytest.fixture
def saved(tmp_path):
    frame = pd.DataFrame({'x': range(40), 'category': ['a', 'b'] * 20,
                          'target': [0, 1] * 20})
    config = ExperimentConfig(task='classification', model_name='logistic_regression',
                              target_column='target', output_dir=tmp_path / 'run',
                              figure_types=[])
    result = run_experiment(config, frame)
    path = config.output_dir / result.model_export['model_path']
    return path, frame, config


def test_schema_reordering_extra_target_and_original_values(saved):
    path, frame, _ = saved
    loaded = load_model(path, trusted=True)
    frame = frame[['category', 'target', 'x']].copy()
    frame.insert(0, 'participant_id', range(100, 140))
    frame.index = list(reversed(range(40)))
    check = compatibility_check(loaded, frame)
    assert check['compatible'] and check['feature_order'] == ['x', 'category']
    result, columns = predict_dataframe(loaded, frame)
    pd.testing.assert_frame_equal(result[frame.columns], frame)
    assert columns == ['predicted_class', 'probability_0', 'probability_1']
    np.testing.assert_allclose(result[columns[1:]].sum(axis=1), 1)
    assert not any(name in result for name in ['accuracy', 'rmse'])


@pytest.mark.parametrize('failure', ['missing', 'dtype', 'infinity', 'empty', 'duplicate'])
def test_incompatible_schema_blocks_prediction(saved, failure):
    path, frame, _ = saved
    loaded = load_model(path, trusted=True)
    if failure == 'missing':
        frame = frame.drop(columns='x')
    elif failure == 'dtype':
        frame['x'] = 'twenty'
    elif failure == 'infinity':
        frame['x'] = float('inf')
    elif failure == 'empty':
        frame = frame.iloc[:0]
    else:
        frame = pd.concat([frame, frame[['x']]], axis=1)
    assert not compatibility_check(loaded, frame)['compatible']
    with pytest.raises(ValueError):
        predict_dataframe(loaded, frame)


def test_missing_values_follow_pipeline(saved):
    path, frame, config = saved
    loaded = load_model(path, trusted=True)
    frame.loc[0, 'category'] = None
    frame['x'] = frame['x'].astype(float)
    frame.loc[1, 'x'] = np.nan
    assert compatibility_check(loaded, frame)['compatible']
    assert len(predict_dataframe(loaded, frame)[0]) == len(frame)
    config = replace(config, output_dir=config.output_dir.parent / 'drop', missing_strategy='drop')
    result = run_experiment(config, frame)
    loaded = load_model(config.output_dir / result.model_export['model_path'], trusted=True)
    check = compatibility_check(loaded, frame)
    assert not check['compatible']
    assert {e['code'] for e in check['errors']} == {'missing_values'}


def test_numeric_strings_preserve_original_and_collision_names(saved):
    path, frame, _ = saved
    frame['x'] = frame['x'].astype(str)
    frame['predicted_class'] = 'original'
    frame['probability_0'] = 'original'
    result, columns = predict_dataframe(load_model(path, trusted=True), frame)
    pd.testing.assert_frame_equal(result[frame.columns], frame)
    assert columns[:2] == ['predicted_class_2', 'probability_0_2']


@pytest.mark.parametrize('task,name,classes', [
    ('classification', 'decision_tree', 3), ('classification', 'svm', 2),
    ('regression', 'ridge', 0),
])
def test_native_outputs_only(tmp_path, task, name, classes):
    frame = pd.DataFrame({'x': range(60), 'y': [i % classes for i in range(60)]
                          if classes else range(60)})
    config = ExperimentConfig(task=task, model_name=name, target_column='y',
                              output_dir=tmp_path, figure_types=[])
    result = run_experiment(config, frame)
    loaded = load_model(tmp_path / result.model_export['model_path'], trusted=True)
    predicted, columns = predict_dataframe(loaded, frame)
    if classes == 3:
        assert len(columns) == 4
    else:
        assert columns == ['predicted_class' if classes else 'predicted_value']
    np.testing.assert_array_equal(predicted[columns[0]], result.model.predict(frame[['x']]))


def test_missing_metadata_fallback_and_manual_mapping(saved, tmp_path):
    path, frame, _ = saved
    (path.parent / 'model_metadata.json').unlink()
    loaded = load_model(path, trusted=True)
    assert loaded.notices and compatibility_check(loaded, frame)['compatible']
    del loaded.model.psyml_metadata_
    joblib.dump(loaded.model, path)
    loaded = load_model(path, trusted=True)
    assert loaded.metadata['feature_types']['x'] == 'numeric'
    assert compatibility_check(loaded, frame)['compatible']
    model = LinearRegression().fit(np.array([[1, 5], [2, 8], [3, 7]]), [1, 4, 9])
    fallback = tmp_path / 'manual.pkl'
    joblib.dump(model, fallback)
    loaded = load_model(fallback, trusted=True)
    data = pd.DataFrame({'second': [5, 8], 'first': [1, 2]})
    assert not compatibility_check(loaded, data)['compatible']
    assert not compatibility_check(loaded, data, ['first', 'first'])['compatible']
    result, _ = predict_dataframe(loaded, data, ['first', 'second'])
    np.testing.assert_array_equal(result.predicted_value, model.predict([[1, 5], [2, 8]]))


def test_trust_corruption_metadata_and_versions(saved, tmp_path):
    path, _, _ = saved
    with pytest.raises(ValueError, match='trusted'):
        load_model(path)
    sidecar = path.parent / 'model_metadata.json'
    metadata = json.loads(sidecar.read_text())
    sidecar.write_text('{broken')
    with pytest.raises(ValueError, match='metadata'):
        load_model(path, trusted=True)
    sidecar.write_text(json.dumps({**metadata, 'sklearn_version': '0.0'}))
    with pytest.raises(ValueError, match='version'):
        load_model(path, trusted=True)
    sidecar.write_text(json.dumps({**metadata, 'feature_names': ['x', 'x']}))
    with pytest.raises(ValueError, match='feature names'):
        load_model(path, trusted=True)
    sidecar.write_text(json.dumps(metadata))
    path.write_bytes(b'corrupt')
    with pytest.raises(ValueError, match='match'):
        load_model(path, trusted=True)
    sidecar.unlink()
    with pytest.raises(ValueError, match='Cannot load'):
        load_model(path, trusted=True)
    joblib.dump({'wrong': 'object'}, path)
    with pytest.raises(ValueError, match='supported'):
        load_model(path, trusted=True)
    joblib.dump(LinearRegression(), path)
    with pytest.raises(ValueError, match='not fitted'):
        load_model(path, trusted=True)


@pytest.mark.parametrize('suffix', sorted(OUTPUT_SUFFIXES))
def test_export_roundtrip(tmp_path, suffix):
    frame = pd.DataFrame({'id': [3., 2., 1.], 'predicted_value': [2.5, 5., 7.5]})
    path = tmp_path / ('predictions' + suffix)
    save_dataframe(frame, path)
    pd.testing.assert_frame_equal(load_dataframe(path), frame, check_dtype=False)
    with pytest.raises(FileExistsError):
        save_dataframe(frame, path)
    save_dataframe(frame, path, overwrite=True)
    assert prediction_output_suffix(suffix) == suffix


def test_readonly_format_fallback_and_failed_export_preserves_file(tmp_path):
    assert prediction_output_suffix('.xls') == '.xlsx'
    assert prediction_output_suffix('.sas7bdat') == '.xlsx'
    path = tmp_path / 'out.sav'
    path.write_text('keep')
    with pytest.raises(ValueError):
        save_dataframe(pd.DataFrame({'invalid column!': [1]}), path, overwrite=True)
    assert path.read_text() == 'keep'


def test_cli_check_predict_export(saved, tmp_path, capsys):
    path, frame, _ = saved
    input_path = tmp_path / 'input.csv'
    frame.to_csv(input_path, index=False)
    args = ['predict', '--model', str(path), '--input', str(input_path), '--trust-model']
    assert main([*args, '--check-only']) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload['compatibility']['compatible']
    assert payload['preview']['row_count'] == 40
    output = tmp_path / 'prediction.parquet'
    assert main([*args, '--output', str(output)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload['predictions']['column_count'] == len(frame.columns) + 3
    exported = tmp_path / 'prediction.xlsx'
    assert main(['export-table', '--input', str(output), '--output', str(exported)]) == 0
    capsys.readouterr()
    assert exported.is_file()
    assert main([*args, '--output', str(input_path), '--overwrite']) == 2
    assert 'separate prediction output' in capsys.readouterr().err
