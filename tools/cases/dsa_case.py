"""Shared constants and small helpers for the public DSA conformance case.

The case converts the public UCI *Daily and Sports Activities* archive into a
12-feature table, then checks PsyML's participant-grouped nested procedure
against an independent scikit-learn workflow. Every constant below is a frozen
value recorded when the case was first run; they must only change together with
a new, explicitly versioned protocol.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

CASE_ID = "psyml_dsa_group_nested_v1"
FROZEN_COMMIT = "de33abfe52ccfee67f461a850edd00a14d2fbfaa"

ARCHIVE_URL = "https://archive.ics.uci.edu/static/public/256/daily%2Band%2Bsports%2Bactivities.zip"
ARCHIVE_SHA256 = "f42ad7744ecf14151c9fa3a86dfb5b24de9d7cb7ffe956ef5de242983459c77e"
DERIVED_CSV_SHA256 = "75a5fe87a58f4cfde777d914d674362b5148854a3c7064d8c686c0e25c3a047e"
# Original pre-run template (absolute workspace input); the repository example
# keeps the same science fields with repository-relative example paths.
FROZEN_CONFIG_SHA256 = "a156dee0bde4e65f4e89ceef28320faa6931ded8dc9eccab62b514b2dba69941"
# Within-subject activity shuffle built with one np.random.default_rng(20261002).
SHUFFLED_LABELS_CSV_SHA256 = "e02699c680cfaa6ec91477c79fff68d7229013d7cc9f7c2acb2ddc4b0d961d86"

PLACEBO_SEED = 20261002
PLACEBO_ALARM_THRESHOLD = 0.10

METRIC_ATOL = 1e-12
PROBABILITY_ATOL = 1e-10
PROBABILITY_RTOL = 1e-8
PREPROCESS_ATOL = 1e-12
PREPROCESS_RTOL = 1e-12

CHANNELS = (
    "torso_acc_x",
    "torso_acc_y",
    "torso_acc_z",
    "torso_gyro_x",
    "torso_gyro_y",
    "torso_gyro_z",
)
FEATURES = tuple(
    f"{channel}_{stat}" for channel in CHANNELS for stat in ("mean", "std")
)
ROLE_COLUMNS = ("segment_id", "subject_id", "activity")

REQUIRED_CONFIG_KEYS = (
    "schema_version",
    "task",
    "target_column",
    "input_path",
    "output_dir",
    "feature_columns",
    "model_names",
    "parameter_grids",
    "validation_strategy",
    "primary_validation",
    "n_splits",
    "inner_splits",
    "selection_metric",
    "max_candidates",
)


def sha256_bytes(payload: bytes) -> str:
    """Return the lowercase SHA-256 digest of ``payload``."""
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: str | Path) -> str:
    """Return the lowercase SHA-256 digest of a file, read incrementally."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: str | Path) -> Any:
    """Read a UTF-8 JSON document."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, payload: Any) -> None:
    """Write stable UTF-8 JSON without NaN/Infinity and with a trailing newline."""
    text = json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False)
    Path(path).write_text(text + "\n", encoding="utf-8")


def load_case_config(path: str | Path) -> dict[str, Any]:
    """Read an analysis configuration and require the case-relevant fields."""
    config = read_json(path)
    if not isinstance(config, dict):
        raise TypeError("Analysis configuration must be a JSON object")
    missing = [key for key in REQUIRED_CONFIG_KEYS if key not in config]
    if missing:
        raise ValueError(f"Analysis configuration is missing fields: {', '.join(missing)}")
    return config
