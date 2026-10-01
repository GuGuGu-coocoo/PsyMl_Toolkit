"""Convert the official UCI DSA archive into the frozen 12-feature CSV.

This is a data-only transform: it never imports PsyML, fits a model or runs any
code contained in the archive. The archive is read member by member and only
the small derived CSV, a manifest and per-member hashes are written.

Expected input is the official archive from :data:`dsa_case.ARCHIVE_URL` with
SHA-256 :data:`dsa_case.ARCHIVE_SHA256`; the archive is verified before any
member is read. Folder names follow the upstream layout
``data/a01..a19/p1..p8/s01..s60.txt``; each member holds 125 comma-separated
rows of 45 numeric columns. The first six columns (torso acceleration x/y/z and
torso angular rate x/y/z) are reduced per segment to mean and population
standard deviation (``ddof=0``), giving 12 predictors.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import platform
import re
import sys
from collections import Counter
from collections.abc import Iterable, Sequence
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd

if __package__ in {None, ""}:  # direct script execution
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.cases import dsa_case

SOURCE_ROWS = 125
SOURCE_COLUMNS = 45
STAT_CHANNELS = 6
ACTIVITY_VALUES = tuple(range(1, 20))
PARTICIPANT_VALUES = tuple(range(1, 9))
SEGMENT_VALUES = tuple(range(1, 61))
MEMBER_PATTERN = re.compile(r"^data/a(\d{2})/p(\d)/s(\d{2})\.txt$")
CSV_NAME = "dsa_torso_mean_std.csv"


def member_name(activity: int, participant: int, segment: int) -> str:
    """Return the upstream member name for one segment."""
    return f"data/a{activity:02d}/p{participant}/s{segment:02d}.txt"


def expected_members(
    activities: Sequence[int] = ACTIVITY_VALUES,
    participants: Sequence[int] = PARTICIPANT_VALUES,
    segments: Sequence[int] = SEGMENT_VALUES,
) -> list[str]:
    """Enumerate the required members in activity, participant, segment order."""
    return [
        member_name(activity, participant, segment)
        for activity in activities
        for participant in participants
        for segment in segments
    ]


def validate_member_names(actual: Iterable[str], expected: Sequence[str]) -> None:
    """Reject missing, duplicated or extra members instead of filtering silently."""
    names = list(actual)
    counts = Counter(names)
    duplicates = sorted(name for name, count in counts.items() if count > 1)
    actual_set = set(names)
    expected_set = set(expected)
    missing = sorted(expected_set - actual_set)
    extra = sorted(actual_set - expected_set)
    if duplicates or missing or extra:
        details = []
        if duplicates:
            details.append(f"duplicate members: {duplicates[:5]}")
        if missing:
            details.append(f"missing members: {missing[:5]}")
        if extra:
            details.append(f"unexpected members: {extra[:5]}")
        raise ValueError("Archive member set does not match the frozen layout: " + "; ".join(details))
    if len(names) != len(expected):
        raise ValueError(f"Archive member count mismatch: {len(names)} != {len(expected)}")


def read_segment_values(
    raw: bytes,
    name: str,
    *,
    rows: int = SOURCE_ROWS,
    columns: int = SOURCE_COLUMNS,
    channels: int = STAT_CHANNELS,
) -> np.ndarray:
    """Parse one member and return its first ``channels`` columns as float64."""
    try:
        values = np.loadtxt(io.BytesIO(raw), delimiter=",", dtype=np.float64)
    except ValueError as error:
        raise ValueError(f"{name}: cannot parse as comma-separated float64 ({error})") from error
    if values.shape != (rows, columns):
        raise ValueError(f"{name}: shape {values.shape} != expected {(rows, columns)}")
    if not np.isfinite(values).all():
        raise ValueError(f"{name}: source values contain NaN or infinity")
    return values[:, :channels]


def segment_features(values: np.ndarray) -> np.ndarray:
    """Return per-channel mean then population std, in the frozen feature order."""
    means = values.mean(axis=0)
    deviations = values.std(axis=0, ddof=0)
    return np.column_stack([means, deviations]).ravel()


def convert_archive(
    archive: str | Path,
    output_dir: str | Path,
    *,
    expected_sha256: str = dsa_case.ARCHIVE_SHA256,
    expected_csv_sha256: str | None = dsa_case.DERIVED_CSV_SHA256,
    activities: Sequence[int] = ACTIVITY_VALUES,
    participants: Sequence[int] = PARTICIPANT_VALUES,
    segments: Sequence[int] = SEGMENT_VALUES,
    rows: int = SOURCE_ROWS,
    columns: int = SOURCE_COLUMNS,
    channels: int = STAT_CHANNELS,
    features: Sequence[str] = dsa_case.FEATURES,
) -> dict:
    """Verify, convert and describe the archive; return the data manifest."""
    archive_path = Path(archive)
    output_path = Path(output_dir)
    archive_sha = dsa_case.sha256_file(archive_path)
    if archive_sha != expected_sha256:
        raise ValueError(
            f"Archive SHA-256 mismatch: expected {expected_sha256}, received {archive_sha}"
        )
    expected = expected_members(activities, participants, segments)
    records: list[list[object]] = []
    member_hashes: dict[str, str] = {}
    with ZipFile(archive_path) as bundle:
        actual = [name for name in bundle.namelist() if not name.endswith("/")]
        validate_member_names(actual, expected)
        for activity in activities:
            for participant in participants:
                for segment in segments:
                    name = member_name(activity, participant, segment)
                    raw = bundle.read(name)
                    member_hashes[name] = hashlib.sha256(raw).hexdigest()
                    values = read_segment_values(
                        raw, name, rows=rows, columns=columns, channels=channels
                    )
                    records.append(
                        [
                            f"a{activity:02d}_p{participant}_s{segment:02d}",
                            participant,
                            activity,
                            *segment_features(values).tolist(),
                        ]
                    )
    frame = pd.DataFrame(records, columns=[*dsa_case.ROLE_COLUMNS, *features])
    _validate_frame(frame, activities, participants, segments, features)
    output_path.mkdir(parents=True, exist_ok=True)
    csv_path = output_path / CSV_NAME
    frame.to_csv(csv_path, index=False, float_format="%.17g", lineterminator="\n")
    csv_sha = dsa_case.sha256_file(csv_path)
    if expected_csv_sha256 is not None and csv_sha != expected_csv_sha256:
        raise ValueError(
            f"Derived CSV SHA-256 mismatch: expected {expected_csv_sha256}, received {csv_sha}"
        )
    manifest = {
        "dataset": "UCI Daily and Sports Activities",
        "uci_id": 256,
        "doi": "10.24432/C5C59F",
        "download_url": dsa_case.ARCHIVE_URL,
        "archive_sha256": archive_sha,
        "archive_bytes": archive_path.stat().st_size,
        "derived_csv_sha256": csv_sha,
        "derived_csv_bytes": csv_path.stat().st_size,
        "rows": len(frame),
        "participants": len(participants),
        "activities": len(activities),
        "segments_per_participant_activity": len(segments),
        "source_shape_per_segment": [rows, columns],
        "feature_columns": list(features),
        "source_column_indices_zero_based": list(range(channels)),
        "feature_std_ddof": 0,
        "row_order": "activity ascending; subject ascending; segment ascending",
        "dropped_rows": 0,
        "transformer_sha256": dsa_case.sha256_file(Path(__file__)),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
    }
    dsa_case.write_json(output_path / "data_manifest.json", manifest)
    dsa_case.write_json(output_path / "member_sha256.json", member_hashes)
    return manifest


def _validate_frame(
    frame: pd.DataFrame,
    activities: Sequence[int],
    participants: Sequence[int],
    segments: Sequence[int],
    features: Sequence[str],
) -> None:
    """Assert the frozen row/participant/activity/feature structure."""
    if frame["segment_id"].duplicated().any():
        raise ValueError("segment_id values are not unique")
    if sorted(frame["subject_id"].unique().tolist()) != sorted(participants):
        raise ValueError("subject_id values do not match the frozen participant set")
    if sorted(frame["activity"].unique().tolist()) != sorted(activities):
        raise ValueError("activity values do not match the frozen activity set")
    counts = frame.groupby(["subject_id", "activity"]).size()
    if not counts.eq(len(segments)).all():
        raise ValueError("Every participant x activity must contribute the same segment count")
    if list(frame.columns) != [*dsa_case.ROLE_COLUMNS, *features]:
        raise ValueError("Derived CSV column order does not match the frozen layout")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--archive", type=Path, required=True, help="Official DSA ZIP file")
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory for the derived CSV, manifest and member hashes",
    )
    args = parser.parse_args(argv)
    if sys.flags.optimize:
        raise SystemExit("Do not use python -O or PYTHONOPTIMIZE; checks must stay enabled.")
    manifest = convert_archive(args.archive, args.output_dir)
    print(
        f"Wrote {manifest['rows']} rows to {Path(args.output_dir) / CSV_NAME} "
        f"(sha256 {manifest['derived_csv_sha256']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
