"""Read-only configuration import for the desktop application."""

from pathlib import Path

from psyml.models.catalog import supported_models
from psyml.protocol import config_to_dict, load_config, preview_payload


def import_configuration(path: Path, input_override: Path | None = None) -> dict:
    """Validate before changing the GUI; resolve portable paths from the config location."""
    path = path.absolute()
    config = load_config(path)
    unknown_models = set(config.selected_models()) - set(supported_models(config.task))
    if unknown_models:
        raise ValueError("Unsupported models: " + ", ".join(sorted(unknown_models)))
    for name in ["random_seed", "n_splits", "inner_splits", "max_candidates"]:
        value = getattr(config, name)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or int(value) != value:
            raise ValueError(f"{name} must be an integer")
    if not 0 <= config.random_seed <= 4294967295:
        raise ValueError("random_seed must be between 0 and 4294967295")
    payload = config_to_dict(config)
    source = input_override or config.input_path
    candidates = []
    if source is not None:
        if source.is_absolute():
            candidates = [source]
        else:
            # Config-relative is preferred; ancestors support repository-style example paths.
            candidates = [parent / source for parent in [path.parent, *path.parent.parents]]
    resolved = next((candidate for candidate in candidates if candidate.is_file()), None)
    if resolved is None:
        return {"config": payload, "needs_data": True}
    preview = preview_payload(resolved, rows=5, include_sample=True)
    columns = {column["name"] for column in preview["columns"]}
    required = {config.target_column}
    if config.group_column:
        required.add(config.group_column)
    if config.feature_columns:
        required.update(config.feature_columns)
    missing = required - columns
    if missing:
        raise ValueError("Data is missing configured columns: " + ", ".join(sorted(missing)))
    payload["input_path"] = str(resolved.absolute())
    payload["model_names"] = config.selected_models()
    payload["validation_strategies"] = config.selected_validations()
    payload["primary_validation"] = config.resolved_primary_validation()
    return {"config": payload, "preview": preview, "needs_data": False}
