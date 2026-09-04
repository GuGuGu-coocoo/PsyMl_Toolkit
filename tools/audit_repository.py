"""Fail if the tracked legacy fixtures regain likely personal or secret data."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import openpyxl
import pandas as pd
import pyreadstat

ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / "legacy" / "original" / "program"

SENSITIVE_PATTERNS = {
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "Chinese mobile": re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    "Chinese national ID": re.compile(
        r"(?<!\d)[1-9]\d{5}(?:18|19|20)\d{2}(?:0[1-9]|1[0-2])"
        r"(?:0[1-9]|[12]\d|3[01])\d{3}[0-9Xx](?!\d)"
    ),
}
SECRET_PATTERNS = {
    "AWS access key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "GitHub token": re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    "private key": re.compile(r"BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY"),
}


def _check_value(value: object, location: str, findings: list[str]) -> None:
    if not isinstance(value, str):
        return
    for label, pattern in SENSITIVE_PATTERNS.items():
        for match in pattern.finditer(value):
            if match.group(0).endswith("@example.invalid"):
                continue
            findings.append(f"{label}: {location}")


def _scan_data() -> tuple[int, int, int, list[str]]:
    findings: list[str] = []
    workbooks = sorted(LEGACY.rglob("*.xlsx"))
    csv_files = sorted(path for path in LEGACY.rglob("*") if path.suffix.lower() == ".csv")
    sav_files = sorted(LEGACY.rglob("*.sav"))
    for path in workbooks:
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=False)
        for sheet in workbook.worksheets:
            for row_index, row in enumerate(sheet.iter_rows(values_only=True), start=1):
                for column_index, value in enumerate(row, start=1):
                    _check_value(
                        value,
                        f"{path.relative_to(ROOT)}:{sheet.title}!R{row_index}C{column_index}",
                        findings,
                    )
        workbook.close()
    for path in csv_files:
        frame = pd.read_csv(path, dtype=str, keep_default_na=False)
        for column in frame.columns:
            for row_index, value in enumerate(frame[column], start=2):
                _check_value(value, f"{path.relative_to(ROOT)}:{row_index}:{column}", findings)
    for path in sav_files:
        frame, _ = pyreadstat.read_sav(path)
        for column in frame.columns:
            for row_index, value in enumerate(frame[column], start=1):
                _check_value(value, f"{path.relative_to(ROOT)}:{row_index}:{column}", findings)
    return len(workbooks), len(csv_files), len(sav_files), findings


def _scan_tracked_text() -> list[str]:
    findings: list[str] = []
    tracked = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout.split(b"\0")
    for raw_path in tracked:
        if not raw_path:
            continue
        path = ROOT / raw_path.decode()
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{label}: {path.relative_to(ROOT)}")
    return findings


def main() -> None:
    workbook_count, csv_count, sav_count, findings = _scan_data()
    findings.extend(_scan_tracked_text())
    expected = (39, 2, 1)
    actual = (workbook_count, csv_count, sav_count)
    if actual != expected:
        findings.append(f"legacy data inventory changed: expected {expected}, received {actual}")
    if findings:
        raise SystemExit("Repository privacy audit failed:\n" + "\n".join(findings))
    print(
        "PSYML_PRIVACY_AUDIT_OK "
        f"workbooks={workbook_count} csv={csv_count} sav={sav_count}"
    )


if __name__ == "__main__":
    main()
