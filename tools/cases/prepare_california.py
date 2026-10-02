#!/usr/bin/env python3
"""Convert a checksum-verified official archive, offline and without extraction.

The command performs no download. Source order, capped targets and all rows are
retained. CSV serialization exactly follows the historical preparation script.
"""

from __future__ import annotations

import argparse
import io
import json
import tarfile
from pathlib import Path

import numpy as np
import pandas as pd

if __package__:
    from .california_case import ARCHIVE_SHA256, ARCHIVE_URL, DATA_SHA256, FEATURES, TARGET, sha256
else:
    from california_case import ARCHIVE_SHA256, ARCHIVE_URL, DATA_SHA256, FEATURES, TARGET, sha256

MEMBERS = ("CaliforniaHousing/cal_housing.data", "CaliforniaHousing/cal_housing.domain")
MAX_MEMBER_BYTES = 8_000_000


def convert_archive(
    archive,
    output_dir,
    *,
    expected_sha256=ARCHIVE_SHA256,
    expected_csv_sha256=DATA_SHA256,
    expected_rows=20640,
):
    """Optional expected identities support tiny offline contract fixtures only."""
    archive, output = Path(archive), Path(output_dir)
    if sha256(archive) != expected_sha256:
        raise ValueError("Source archive SHA-256 mismatch")
    with tarfile.open(archive, "r:gz") as bundle:
        members = bundle.getmembers()
        if sorted(m.name for m in members) != sorted(MEMBERS):
            raise ValueError("Archive has missing, duplicate, or unexpected members")
        if any(not m.isfile() or m.size > MAX_MEMBER_BYTES for m in members):
            raise ValueError("Archive members must be bounded regular files")
        raw = np.loadtxt(io.BytesIO(bundle.extractfile(MEMBERS[0]).read()), delimiter=",", ndmin=2)
        domain = bundle.extractfile(MEMBERS[1]).read()
    if raw.shape != (expected_rows, 9) or not np.isfinite(raw).all():
        raise ValueError("Unexpected source shape or nonfinite values")
    if not (raw[:, 6] > 0).all():
        raise ValueError("Household denominator must be positive")
    values = np.column_stack(
        [
            raw[:, 7],
            raw[:, 2],
            raw[:, 3] / raw[:, 6],
            raw[:, 4] / raw[:, 6],
            raw[:, 5],
            raw[:, 5] / raw[:, 6],
            raw[:, 1],
            raw[:, 0],
        ]
    )
    frame = pd.DataFrame(values, columns=FEATURES)
    frame[TARGET] = raw[:, 8] / 100000
    if not np.isfinite(frame.to_numpy()).all():
        raise ValueError("Nonfinite transformed values")
    names = [
        "california_housing.csv",
        "california_predict.csv",
        "california_provenance.json",
        "cal_housing.domain",
    ]
    if any((output / name).exists() for name in names):
        raise FileExistsError("Refusing to overwrite any California case artifact")
    csv = frame.to_csv(index=False, float_format="%.17g", lineterminator="\n").encode("utf-8")
    import hashlib

    digest = hashlib.sha256(csv).hexdigest()
    if expected_csv_sha256 is not None and digest != expected_csv_sha256:
        raise ValueError("Derived CSV SHA-256 mismatch; no files written")
    fixture = frame.loc[:9, list(reversed(FEATURES))].copy()
    fixture.insert(0, "sample_id", [f"CAL{i:05}" for i in range(len(fixture))])
    output.mkdir(parents=True, exist_ok=True)
    (output / names[0]).write_bytes(csv)
    fixture.to_csv(
        output / names[1], index=False, float_format="%.17g", lineterminator="\n", encoding="utf-8"
    )
    (output / names[3]).write_bytes(domain)
    manifest = {
        "raw_sha256": sha256(archive),
        "raw_bytes": archive.stat().st_size,
        "csv_sha256": digest,
        "csv_bytes": len(csv),
        "rows": len(frame),
        "features": FEATURES,
        "target": TARGET,
        "missing": 0,
        "source_url": ARCHIVE_URL,
        "record_url": "https://doi.org/10.6084/m9.figshare.3829992.v2",
        "license": "CC BY 4.0; attribution in examples/public/california_random_nested_v1/ATTRIBUTION.md",
        "target_units": "USD 100000 (1990 census); source cap retained",
        "row_order": "unchanged source order; zero-based row_index",
        "prediction_fixture_sha256": sha256(output / names[1]),
    }
    (output / names[2]).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("examples/public/data"))
    args = parser.parse_args(argv)
    print(json.dumps(convert_archive(args.archive, args.output_dir), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
