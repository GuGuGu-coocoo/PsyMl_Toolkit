"""Bind every analysis to an immutable input byte/row snapshot."""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

import pandas as pd

from psyml.config import ExperimentConfig

SNAPSHOT_KEY = "psyml_input_snapshot_v1"


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bind_input_snapshot(config: ExperimentConfig, frame: pd.DataFrame | None, *, loader):
    """Hash the exact private temporary bytes parsed, then remove the snapshot.

    No raw participant-data copy is placed in the result directory. Source row
    positions are assigned before missing-value removal and are stable for files
    and DataFrames, including nonunique or named pandas indexes.
    """
    if frame is None:
        if config.input_path is None:
            raise ValueError("input_path is required when frame is not supplied")
        path = Path(config.input_path)
        digest = hashlib.sha256()
        with tempfile.TemporaryDirectory(prefix="psyml-input-") as directory:
            snapshot = Path(directory) / ("input" + path.suffix)
            with path.open("rb") as source, snapshot.open("wb") as destination:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
                    destination.write(chunk)
            frame = loader(snapshot)
        fingerprint = digest.hexdigest()
        basis = "source_file_bytes"
    else:
        frame = frame.copy(deep=True)
        fingerprint = hashlib.sha256(
            frame.to_csv(index=False, lineterminator="\n").encode("utf-8")
        ).hexdigest()
        basis = "canonical_in_memory_csv"
    frame = frame.reset_index(drop=True)
    frame.attrs[SNAPSHOT_KEY] = {
        "sha256": fingerprint,
        "hash_basis": basis,
        "row_identity": "zero_based_input_position_before_filtering",
        "pandas_index_policy": "ignored; input row position is authoritative",
    }
    return frame


def source_change_warning(config: ExperimentConfig, frame: pd.DataFrame) -> str | None:
    """Record late source changes without replacing the fitted snapshot's hash."""
    snapshot = frame.attrs.get(SNAPSHOT_KEY, {})
    if config.input_path is None or snapshot.get("hash_basis") != "source_file_bytes":
        return None
    try:
        current = hash_file(Path(config.input_path))
    except OSError:
        status = "unavailable"
    else:
        status = "unchanged" if current == snapshot.get("sha256") else "changed"
    snapshot["source_status_at_export"] = status
    if status == "unchanged":
        return None
    return (
        f"The input source file is {status} since its analysis snapshot was read. "
        "The analysis manifest hash remains bound to the exact bytes used for fitting."
    )
