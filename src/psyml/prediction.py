"""Local batch inference, separate from scientific evaluation and model selection."""

import hashlib
import json
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.base import is_classifier, is_regressor
from sklearn.exceptions import InconsistentVersionWarning
from sklearn.pipeline import Pipeline
from sklearn.utils.validation import check_is_fitted

from psyml.models.parameters import effective_parameters, parameter_value
from psyml.models.persistence import safe_name


@dataclass
class LoadedModel:
    model: object
    metadata: dict
    notices: list[str]


@dataclass
class PredictionFrame:
    """Appended prediction columns plus their original-label provenance."""

    frame: pd.DataFrame
    additions: list[str]
    columns: list[dict]


def _validate_metadata(metadata):
    if not isinstance(metadata, dict):
        raise TypeError("Model metadata must be a JSON object.")
    names = metadata.get('feature_names')
    if names is not None and (not isinstance(names, list) or not names
                             or any(not isinstance(n, str) or not n for n in names)
                             or len(names) != len(set(names))):
        raise ValueError("Model metadata contains invalid feature names.")
    types = metadata.get('feature_types', {})
    if not isinstance(types, dict) or any(v not in ('numeric', 'categorical', 'unknown')
                                         for v in types.values()):
        raise ValueError("Model metadata contains invalid feature types.")
    count = metadata.get('n_features')
    if count is not None and (type(count) is not int or count < 1):
        raise ValueError("Model metadata contains an invalid feature count.")
    if names and count and len(names) != count:
        raise ValueError("Model metadata feature names and count disagree.")
    if metadata.get('task') not in (None, 'classification', 'regression'):
        raise ValueError("Model metadata contains an invalid task.")


def load_model(path, *, trusted=False) -> LoadedModel:
    """Unpickling executes code: callers must explicitly trust the source first."""
    if not trusted:
        raise ValueError("Only load models from a trusted source. Joblib/pickle files can execute "
                         "code. Confirm trust before loading (--trust-model in the CLI).")
    path = Path(path)
    if path.suffix.lower() not in ('.joblib', '.pkl'):
        raise ValueError("Select a PsyML-exported .joblib or .pkl model.")
    if not path.is_file():
        raise FileNotFoundError(f"Model file does not exist: {path}")
    sidecar = path.parent / 'model_metadata.json'
    metadata, notices = {}, []
    if sidecar.is_file():
        try:
            metadata = json.loads(sidecar.read_text(encoding='utf-8'))
        except (ValueError, UnicodeError) as error:
            raise ValueError("Model metadata is unreadable or invalid JSON.") from error
        _validate_metadata(metadata)
        if metadata.get('sha256') and hashlib.sha256(path.read_bytes()).hexdigest() != metadata['sha256']:
            raise ValueError("Model file does not match its metadata. Select the matching pair.")
        if metadata.get('sklearn_version', sklearn.__version__) != sklearn.__version__:
            raise ValueError("Model was saved with a different scikit-learn version "
                             f"({metadata['sklearn_version']}); use that environment to load it.")
    else:
        notices.append('Metadata sidecar is missing; using information retained in the model.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', InconsistentVersionWarning)
            model = joblib.load(path)
    except InconsistentVersionWarning as error:
        raise ValueError("Model uses an incompatible scikit-learn version; use its original "
                         "environment.") from error
    except Exception as error:
        raise ValueError("Cannot load model: the file may be corrupt, or its estimator class or "
                         "Python environment is unavailable.") from error
    if not callable(getattr(model, 'predict', None)) or not (is_classifier(model) or is_regressor(model)):
        raise ValueError("This file does not contain a supported fitted sklearn model.")
    try:
        check_is_fitted(model)
    except Exception as error:
        raise ValueError("This model is not fitted. Select a final PsyML-exported model.") from error
    embedded = getattr(model, 'psyml_metadata_', {})
    _validate_metadata(embedded)
    if not metadata:
        metadata = dict(embedded)
    if metadata.get('sklearn_version', sklearn.__version__) != sklearn.__version__:
        raise ValueError("Model metadata reports an incompatible scikit-learn version.")
    task = 'classification' if is_classifier(model) else 'regression'
    if metadata.get('task', task) != task:
        raise ValueError("Model task does not match its metadata.")
    names = getattr(model, 'feature_names_in_', None)
    if names is not None:
        names = list(names)
        if metadata.get('feature_names') is not None and metadata['feature_names'] != names:
            raise ValueError("Model predictors do not match its metadata.")
        metadata['feature_names'] = names
    count = getattr(model, 'n_features_in_', metadata.get('n_features'))
    if count is None:
        raise ValueError("Cannot determine the model's required predictor count.")
    count = int(count)
    if metadata.get('n_features', count) != count:
        raise ValueError("Model predictor count does not match its metadata.")
    if metadata.get('feature_names') and len(metadata['feature_names']) != count:
        raise ValueError("Model feature names do not match its predictor count.")
    estimator = model.steps[-1][1] if isinstance(model, Pipeline) else model
    types = metadata.get('feature_types', {})
    # Recover the existing PsyML preprocessor's original column types when possible.
    if isinstance(model, Pipeline) and 'preprocess' in model.named_steps:
        for kind, _, columns in model.named_steps['preprocess'].transformers_:
            if kind in ('numeric', 'categorical'):
                for column in columns:
                    if isinstance(column, str):
                        types[column] = kind
    metadata.update(task=task, n_features=count, feature_types=types,
                    supports_probability=hasattr(model, 'predict_proba'),
                    classes=parameter_value(getattr(model, 'classes_', None)))
    metadata.setdefault('estimator_class', f'{type(estimator).__module__}.{type(estimator).__qualname__}')
    metadata.setdefault('pipeline_steps', [name for name, _ in model.steps]
                        if isinstance(model, Pipeline) else [])
    metadata.setdefault('best_parameters', effective_parameters(estimator))
    return LoadedModel(model, metadata, notices)


def _accepts_missing(model):
    """Conservative fallback based on fitted PsyML preprocessors, never a new imputer."""
    if isinstance(model, Pipeline):
        if 'preprocess' in model.named_steps:
            transforms = model.named_steps['preprocess'].transformers_
            return all(isinstance(transform, Pipeline) and 'impute' in transform.named_steps
                       for name, transform, _ in transforms if name != 'remainder')
        final = model.steps[-1][1]
        bases = getattr(final, 'estimators_', None)
        if bases:
            return all(_accepts_missing(base) for base in bases)
    return False


def compatibility_check(loaded: LoadedModel, frame: pd.DataFrame, mapping=None) -> dict:
    """Check schema immediately; additional original columns and ordering are harmless."""
    metadata = loaded.metadata
    names = metadata.get('feature_names')
    errors, required = [], []
    manual = not names
    if manual:
        names = mapping or []
        if (len(names) != metadata['n_features'] or len(set(names)) != len(names)
                or any(not isinstance(name, str) for name in names)):
            errors.append({'code': 'mapping_required', 'message':
                           f"Confirm {metadata['n_features']} distinct predictors in model order."})
    if frame.empty:
        errors.append({'code': 'empty_data', 'message': 'Prediction data contains no rows.'})
    if frame.columns.duplicated().any():
        errors.append({'code': 'duplicate_columns', 'message': 'Prediction data has duplicate columns.'})
    missing_allowed = _accepts_missing(loaded.model)
    for name in names:
        kind = metadata.get('feature_types', {}).get(name, 'unknown')
        status = 'ready'
        message = ''
        if name not in frame.columns:
            status, message = 'missing_feature', f'Missing required feature: {name}'
        elif not frame.columns.duplicated().any():
            series = frame[name]
            if kind == 'numeric':
                numeric = pd.to_numeric(series, errors='coerce')
                if (series.notna() & numeric.isna()).any():
                    status, message = 'incompatible_type', f'Feature {name} requires numeric values.'
                elif np.isinf(numeric.to_numpy(dtype=float, na_value=np.nan)).any():
                    status, message = 'nonfinite', f'Feature {name} contains infinite values.'
            if not message and series.isna().any() and not missing_allowed:
                status, message = 'missing_values', f'Feature {name} has missing values; this pipeline cannot impute them.'
        if message:
            errors.append({'code': status, 'feature': name, 'message': message})
        required.append({'name': name, 'expected_type': kind, 'status': status})
    return {'compatible': not errors, 'errors': errors, 'required_features': required,
            'feature_order': names, 'manual_mapping': manual,
            'warnings': loaded.notices, 'n_features': metadata['n_features']}


def model_input(loaded: LoadedModel, frame: pd.DataFrame, mapping=None, *, check=None):
    """Build the exact object passed to ``model.predict`` for a checked frame.

    Single source of truth for the inference input path (column order, numeric
    coercion, manual-mapping conversion) so explanation and plain prediction
    cannot drift apart.
    """
    if check is None:
        check = compatibility_check(loaded, frame, mapping)
    if not check['compatible']:
        raise ValueError(' '.join(error['message'] for error in check['errors']))
    features = frame.loc[:, check['feature_order']].copy()
    for name in features:
        if loaded.metadata.get('feature_types', {}).get(name) == 'numeric':
            features[name] = pd.to_numeric(features[name])
    if check['manual_mapping']:
        features = features.to_numpy()
    return features


def predict_frame(loaded, frame, mapping=None) -> PredictionFrame:
    """Append native predictions and keep per-column provenance for the manifest."""
    check = compatibility_check(loaded, frame, mapping)
    features = model_input(loaded, frame, mapping, check=check)
    try:
        predicted = np.asarray(loaded.model.predict(features))
        probabilities = (np.asarray(loaded.model.predict_proba(features))
                         if loaded.metadata['task'] == 'classification'
                         and loaded.metadata['supports_probability'] else None)
    except Exception as error:
        raise ValueError('Prediction failed. Check predictor types and the original model '
                         f'environment. {str(error)[:250]}') from error
    if predicted.ndim != 1 or len(predicted) != len(frame):
        raise ValueError('Model returned an unsupported prediction shape.')
    result = frame.copy()
    additions: list[str] = []
    columns: list[dict] = []

    def append(base, values, *, kind, class_index=None, class_label=None):
        name, number = base, 2
        while name in result.columns:
            name = f'{base}_{number}'
            number += 1
        result[name] = values
        additions.append(name)
        entry = {'column': name, 'base': base, 'kind': kind}
        if class_index is not None:
            entry.update(class_index=class_index, class_label=class_label,
                         class_type=type(class_label).__name__)
        columns.append(entry)

    append('predicted_class' if loaded.metadata['task'] == 'classification' else 'predicted_value',
           predicted, kind='prediction')
    if probabilities is not None:
        classes = loaded.metadata['classes']
        if probabilities.shape != (len(frame), len(classes)):
            raise ValueError('Model returned an unsupported probability shape.')
        for index, label in enumerate(classes):
            append('probability_' + safe_name(str(label)), probabilities[:, index],
                   kind='probability', class_index=index, class_label=label)
    return PredictionFrame(result, additions, columns)


def predict_dataframe(loaded, frame, mapping=None):
    """Append native predictions, keeping original values, target, row order and index."""
    prediction = predict_frame(loaded, frame, mapping)
    return prediction.frame, prediction.additions


def build_prediction_manifest(
    loaded: LoadedModel,
    prediction: PredictionFrame,
    *,
    model_path,
    input_path,
    output_path,
    rows: int,
    feature_order: list[str],
    manual_mapping: bool,
    created: datetime | None = None,
) -> dict:
    """Machine-readable provenance for one prediction file.

    The prediction table keeps its sanitized column names; this manifest is the
    durable mapping from every appended column back to the original class label,
    its position in ``classes_`` and the exact files the prediction used.
    """
    from importlib.metadata import version

    return {
        'schema_version': '1.0',
        'created_time': (created or datetime.now(timezone.utc)).isoformat(),
        'psyml_version': version('psyml-toolkit'),
        'sklearn_version': sklearn.__version__,
        'task': loaded.metadata.get('task'),
        'model_path': str(model_path),
        'model_sha256': hashlib.sha256(Path(model_path).read_bytes()).hexdigest(),
        'input_path': str(input_path),
        'input_sha256': hashlib.sha256(Path(input_path).read_bytes()).hexdigest(),
        'output_path': str(output_path),
        'rows': int(rows),
        'feature_order': list(feature_order),
        'manual_mapping': bool(manual_mapping),
        'classes': loaded.metadata.get('classes'),
        'columns': prediction.columns,
    }


def write_prediction_manifest(manifest: dict, output_path, *, overwrite: bool = False) -> Path:
    """Write ``prediction_manifest.json`` next to the prediction file."""
    path = Path(output_path).parent / 'prediction_manifest.json'
    if path.exists() and not overwrite:
        raise ValueError('A prediction manifest already exists for this output; use a new '
                         'prediction folder or --overwrite.')
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n',
                    encoding='utf-8')
    return path
