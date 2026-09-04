"""Download and normalize the two license-audited UCI acceptance datasets."""

from __future__ import annotations

import hashlib
import io
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "examples" / "public" / "data"

IRIS_URL = "https://archive.ics.uci.edu/static/public/53/iris.zip"
IRIS_SHA256 = "d11fe30213d36434a0879aab7cb00ce3c812eb7ba2495874438abff7b7b762e9"
CONCRETE_URL = (
    "https://archive.ics.uci.edu/static/public/165/"
    "concrete%2Bcompressive%2Bstrength.zip"
)
CONCRETE_SHA256 = "dad85d14de8aee4e07479daa774e6b569a313715b71a3b92c95a07cf91c2c9a7"


def _download_verified(url: str, expected_sha256: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as response:
        payload = response.read()
    actual = hashlib.sha256(payload).hexdigest()
    if actual != expected_sha256:
        raise RuntimeError(
            f"Checksum mismatch for {url}: expected {expected_sha256}, received {actual}"
        )
    return payload


def _write_iris(payload: bytes) -> None:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        raw = archive.read("iris.data")
    frame = pd.read_csv(
        io.BytesIO(raw),
        header=None,
        names=[
            "sepal_length_cm",
            "sepal_width_cm",
            "petal_length_cm",
            "petal_width_cm",
            "species",
        ],
    ).dropna(how="all")
    frame.to_csv(DATA_DIR / "iris.csv", index=False)


def _write_concrete(payload: bytes) -> None:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        raw = archive.read("Concrete_Data.xls")
    frame = pd.read_excel(io.BytesIO(raw))
    frame.columns = [
        "cement_kg_m3",
        "blast_furnace_slag_kg_m3",
        "fly_ash_kg_m3",
        "water_kg_m3",
        "superplasticizer_kg_m3",
        "coarse_aggregate_kg_m3",
        "fine_aggregate_kg_m3",
        "age_days",
        "compressive_strength_mpa",
    ]
    frame.to_csv(DATA_DIR / "concrete.csv", index=False)


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _write_iris(_download_verified(IRIS_URL, IRIS_SHA256))
    _write_concrete(_download_verified(CONCRETE_URL, CONCRETE_SHA256))
    print(f"Prepared audited public datasets in {DATA_DIR}")


if __name__ == "__main__":
    main()
