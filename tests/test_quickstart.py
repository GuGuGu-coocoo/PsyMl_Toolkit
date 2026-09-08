"""The complete user kit must work after being copied outside the repository."""
import shutil
from pathlib import Path

import pandas as pd
import pytest

from psyml.gui_config import import_configuration
from psyml.prediction import load_model, predict_dataframe
from psyml.protocol import config_from_dict
from psyml.runner import run_experiment

KIT = Path(__file__).parents[1] / 'examples/quickstart'


@pytest.mark.parametrize('task', ['classification', 'regression'])
def test_portable_quickstart_train_save_predict(tmp_path, monkeypatch, task):
    copied = tmp_path / '用户测试资料'
    shutil.copytree(KIT, copied)
    monkeypatch.chdir(tmp_path)
    imported = import_configuration(copied / f'{task}_config.json')
    assert not imported['needs_data']
    assert imported['config']['input_path'] == str(copied / f'{task}_train.csv')
    assert imported['preview']['row_count'] == 48
    config = config_from_dict({**imported['config'], 'output_dir': str(tmp_path / task)})
    assert config.save_best_model
    result = run_experiment(config)
    model = load_model(config.output_dir / result.model_export['model_path'], trusted=True)
    new = pd.read_csv(copied / f'{task}_predict.csv')
    trained = pd.read_csv(copied / f'{task}_train.csv')
    assert len(new) == 10 and 'target' not in new
    assert set(new.score).isdisjoint(set(trained.score))
    predicted, additions = predict_dataframe(model, new)
    pd.testing.assert_frame_equal(predicted[new.columns], new)
    assert len(predicted) == 10
    assert additions == (['predicted_class', 'probability_0', 'probability_1']
                         if task == 'classification' else ['predicted_value'])
