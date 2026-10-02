"""Frozen identities for the public California Housing workflow case.

Only input/output relocation is operational. Protocol/config byte hashes refer
explicitly to historical originals, never to relocated repository templates.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

CASE_DIR = Path(__file__).resolve().parents[2] / "examples/public/california_random_nested_v1"
EXPECTED_DIR = CASE_DIR / "expected"
FEATURES = [
    "MedInc",
    "HouseAge",
    "AveRooms",
    "AveBedrms",
    "Population",
    "AveOccup",
    "Latitude",
    "Longitude",
]
TARGET = "MedHouseVal"
ARCHIVE_URL = "https://ndownloader.figshare.com/files/5976036"
ARCHIVE_SHA256 = "aaa5c9a6afe2225cc2aed2723682ae403280c4a3695a2ddda4ffb5d8215ea681"
DATA_SHA256 = "157b6c0d3acd6d93a50c411d0cd4130d8c719ce5eb17b61f1c45300f2af6fc85"
FROZEN_PROTOCOL_SHA256 = "8c421185c4171fc8f8f17822043a2b3616f9c890163fb953a306e80c3e2db0e0"
FROZEN_CONFIG_SHA256 = "6545958eadc8a20ed56e267f37ad2a6925ae18d95c2455ac18ca80fae8d935ce"
AMENDED_CONFIG_SHA256 = "9c463398d4d5dd388502be1d8dd1140d727f6c7ae6e2732ec63835c331f132d8"
OPERATIONAL_FIELDS = frozenset({"input_path", "output_dir"})


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def typed_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def science(config):
    return {key: value for key, value in config.items() if key not in OPERATIONAL_FIELDS}


def science_sha256(config):
    return hashlib.sha256(typed_json(science(config)).encode()).hexdigest()


def frozen_config(variant="v1"):
    if variant not in {"v1", "v1.1"}:
        raise ValueError(f"Unknown frozen variant: {variant}")
    name = "california_config.json" if variant == "v1" else "california_config_v1_1.json"
    expected = FROZEN_CONFIG_SHA256 if variant == "v1" else AMENDED_CONFIG_SHA256
    path = EXPECTED_DIR / name
    if sha256(path) != expected:
        raise ValueError(f"Historical config bytes changed: {name}")
    return read_json(path)


def config_identity(config):
    """Accept exact scientific fields and types; permit only path relocation."""
    for variant in ("v1", "v1.1"):
        if typed_json(science(config)) == typed_json(science(frozen_config(variant))):
            return variant
    raise ValueError("Configuration differs from frozen v1/v1.1 science fields or JSON types")
