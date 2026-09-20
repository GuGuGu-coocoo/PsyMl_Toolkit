"""Verify built release artifacts by inspecting the real files.

Structural verification of the platform ZIPs, their SHA-256 sidecars and, in
``all`` mode, the Chinese distribution PDFs and the release checksum manifest.
Entry names, sizes, ``BUILD.json`` fields, archive safety and hashes are read
from the artifacts themselves; a success string in a log is never enough.

Usage::

    .venv/bin/python tools/verify_release_artifacts.py --directory dist/v0.3.0 --platform all

``all`` requires both platform ZIPs, non-empty ``docs/README_ZH.pdf`` and
``docs/RESEARCHER_GUIDE_ZH.pdf`` generated from the current sources, and a
``SHA256SUMS`` (or ``SHA256SUMS.txt``) manifest listing the two ZIPs and the
two PDFs with matching hashes. A single-platform run verifies only that ZIP and
its sidecar, so F02 can gate the macOS build before the Windows artifact exists.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import zipfile
from pathlib import Path

from psyml import __version__ as CORE_VERSION

ROOT = Path(__file__).resolve().parents[1]
PLATFORM_SUFFIXES = {"macOS": "macOS-arm64", "Windows": "Windows-x64"}
PDF_NAMES = ("README_ZH.pdf", "RESEARCHER_GUIDE_ZH.pdf")
PDF_SOURCES = ("README.md", "docs/RESEARCHER_GUIDE_ZH.md")
MANIFEST_NAMES = ("SHA256SUMS", "SHA256SUMS.txt")
SMOKE_MARKER = "PSYML_NATIVE_BUNDLE_OK"
_HEX = re.compile(r"^[0-9a-f]{64}$")


class VerificationError(Exception):
    """Raised with every structural failure found in the requested artifacts."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_sidecar(path: Path) -> tuple[str, str | None]:
    """Return ``(digest, name)`` from a ``sha256sum``-style sidecar file."""
    parts = path.read_text(encoding="utf-8").split()
    if not parts or not _HEX.fullmatch(parts[0].lower()):
        raise VerificationError(f"malformed SHA-256 sidecar: {path}")
    name = parts[1].lstrip("*") if len(parts) > 1 else None
    return parts[0].lower(), name


def parse_manifest(path: Path) -> dict[str, str]:
    """Return ``{name: digest}`` from a ``SHA256SUMS`` manifest."""
    entries: dict[str, str] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2 or not _HEX.fullmatch(parts[0].lower()):
            raise VerificationError(f"malformed manifest line {number}: {path}: {line!r}")
        name = " ".join(parts[1:]).lstrip("*")
        if name in entries:
            raise VerificationError(f"duplicate manifest entry {name!r}: {path}")
        entries[name] = parts[0].lower()
    if not entries:
        raise VerificationError(f"empty checksum manifest: {path}")
    return entries


def check_member_safety(archive: zipfile.ZipFile, root: str, errors: list[str]) -> None:
    """Reject absolute, escaping, duplicated or symlinked archive members."""
    seen: set[str] = set()
    for info in archive.infolist():
        name = info.filename
        if name in seen:
            errors.append(f"duplicate archive entry: {name}")
            continue
        seen.add(name)
        if not name or name.startswith("/") or re.match(r"^[A-Za-z]:", name):
            errors.append(f"unsafe absolute archive entry: {name!r}")
            continue
        if "\\" in name:
            errors.append(f"unsafe backslash archive entry: {name!r}")
            continue
        parts = name.split("/")
        if name.endswith("/"):
            parts = parts[:-1]
        if any(part in ("", ".", "..") for part in parts):
            errors.append(f"unsafe archive entry path: {name!r}")
            continue
        if not name.startswith((root + "/", "__MACOSX/")):
            errors.append(f"archive entry outside the package root: {name!r}")
            continue
        mode = (info.external_attr >> 16) & 0o170000
        if mode == 0o120000:
            errors.append(f"archive entry is a symlink: {name!r}")


def check_required_members(names: set[str], required: list[str], errors: list[str]) -> None:
    for name in required:
        if name not in names:
            errors.append(f"missing required archive member: {name}")


def check_build_json(archive: zipfile.ZipFile, member: str, version: str,
                     commit: str, suffix: str, errors: list[str]) -> None:
    try:
        document = json.loads(archive.read(member).decode("utf-8"))
    except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as error:
        errors.append(f"unreadable {member}: {error}")
        return
    if not isinstance(document, dict):
        errors.append(f"{member}: expected a JSON object, found {type(document).__name__}")
        return
    expected = {
        "version": version,
        "commit": commit,
        "platform": suffix,
    }
    for key, value in expected.items():
        if document.get(key) != value:
            errors.append(
                f"{member}: {key} is {document.get(key)!r}, expected {value!r}"
            )
    if document.get("label", version) != version:
        errors.append(
            f"{member}: label is {document.get('label')!r}, expected the release {version!r}"
        )
    if document.get("working_tree_modified") is not False:
        errors.append(
            f"{member}: working_tree_modified is not false; the build did not start "
            "from a clean source tree"
        )
    if document.get("published", False) is not False:
        errors.append(f"{member}: published is not false; a local build must not claim release")


def verify_platform(directory: Path, platform: str, version: str, commit: str) -> list[str]:
    """Verify one platform ZIP, its sidecar and its BUILD.json; return failures."""
    suffix = PLATFORM_SUFFIXES[platform]
    archive_name = f"PsyML-Toolkit-{version}-{suffix}.zip"
    archive_path = directory / archive_name
    errors: list[str] = []
    if not archive_path.is_file():
        return [f"missing platform archive: {archive_path}"]
    sidecar = archive_path.with_name(archive_name + ".sha256")
    if not sidecar.is_file():
        errors.append(f"missing SHA-256 sidecar: {sidecar}")
    else:
        try:
            digest, name = parse_sidecar(sidecar)
        except VerificationError as error:
            errors.append(str(error))
        else:
            actual = sha256_file(archive_path)
            if digest != actual:
                errors.append(
                    f"{sidecar.name}: digest {digest} does not match the archive {actual}"
                )
            if name is not None and name != archive_name:
                errors.append(f"{sidecar.name}: names {name!r}, expected {archive_name!r}")
    if errors:
        return errors

    root = f"PsyML-Toolkit-{version}-{suffix}"
    required = [
        f"{root}/BUILD.json",
        f"{root}/SMOKE_TEST.txt",
        f"{root}/START_HERE.txt",
        f"{root}/LICENSE",
        f"{root}/examples/quickstart/README.md",
        f"{root}/examples/quickstart/classification_config.json",
        f"{root}/examples/quickstart/regression_config.json",
        f"{root}/examples/quickstart/classification_train.csv",
        f"{root}/examples/quickstart/regression_train.csv",
        f"{root}/examples/quickstart/classification_predict.csv",
        f"{root}/examples/quickstart/regression_predict.csv",
        f"{root}/examples/synthetic/classification.csv",
        f"{root}/licenses/SHAP_LICENSE.txt",
        f"{root}/licenses/NUMBA_LICENSE.txt",
        f"{root}/licenses/LLVMLITE_LICENSE.txt",
    ]
    if platform == "macOS":
        app = f"{root}/PsyML Toolkit.app/Contents"
        required.extend([
            f"{app}/Info.plist",
            f"{app}/MacOS/PsyML Toolkit",
            f"{app}/Resources/core/psyml-core",
        ])
        core_prefix = f"{app}/Resources/core/"
        binary_dir = f"{app}/MacOS/"
    else:
        required.extend([f"{root}/PsyML Toolkit.exe", f"{root}/core/psyml-core.exe"])
        core_prefix = f"{root}/core/"
        binary_dir = f"{root}/"

    try:
        archive = zipfile.ZipFile(archive_path)
    except (zipfile.BadZipFile, OSError) as error:
        errors.append(f"unreadable archive {archive_name}: {error}")
        return errors
    with archive:
        names = {info.filename for info in archive.infolist()}
        check_member_safety(archive, root, errors)
        check_required_members(names, required, errors)
        if not any(name.startswith(core_prefix + "_internal/") for name in names):
            errors.append(f"missing bundled core runtime: {core_prefix}_internal/")
        if not any(
            name.startswith(f"{root}/licenses/") and not name.endswith("/")
            for name in names
        ):
            errors.append(f"missing bundled licenses: {root}/licenses/")
        if not any(
            name.startswith(binary_dir) and not name.endswith("/") and name != binary_dir
            for name in names
        ):
            errors.append(f"missing application binary under: {binary_dir}")
        build_member = f"{root}/BUILD.json"
        if build_member in names:
            check_build_json(archive, build_member, version, commit, suffix, errors)
        smoke_member = f"{root}/SMOKE_TEST.txt"
        if smoke_member in names:
            smoke = archive.read(smoke_member).decode("utf-8").strip()
            if smoke != SMOKE_MARKER:
                errors.append(
                    f"{smoke_member}: {smoke!r} is not the expected {SMOKE_MARKER!r}"
                )
    return errors


def verify_pdfs(directory: Path) -> list[str]:
    """Require non-empty PDFs generated from the current sources."""
    errors: list[str] = []
    docs = directory / "docs"
    for name in PDF_NAMES:
        path = docs / name
        if not path.is_file():
            errors.append(f"missing distribution PDF: {path}")
            continue
        if path.stat().st_size <= 0:
            errors.append(f"empty distribution PDF: {path}")
        elif path.read_bytes()[:5] != b"%PDF-":
            errors.append(f"not a PDF file: {path}")
    sources = docs / "sources.json"
    if not sources.is_file():
        errors.append(f"missing PDF source manifest: {sources}")
        return errors
    try:
        recorded = json.loads(sources.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        errors.append(f"unreadable {sources}: {error}")
        return errors
    if not isinstance(recorded, dict):
        errors.append(f"{sources}: expected a JSON object of source hashes")
        return errors
    for relative in PDF_SOURCES:
        if relative not in recorded:
            errors.append(f"{sources}: no source hash recorded for {relative}")
    for relative, expected in recorded.items():
        source = ROOT / relative
        if not source.is_file():
            errors.append(f"{sources}: recorded source is missing: {relative}")
        elif sha256_file(source) != expected:
            errors.append(f"{sources}: recorded source changed: {relative}")
    return errors


def verify_manifest(directory: Path, expected: dict[str, str]) -> list[str]:
    """Verify the release checksum manifest lists every artifact with its hash."""
    errors: list[str] = []
    path = next(
        (directory / name for name in MANIFEST_NAMES if (directory / name).is_file()),
        None,
    )
    if path is None:
        wanted = ", ".join(sorted(expected)) or "the release artifacts"
        message = (
            f"missing release checksum manifest in {directory}: expected "
            f"{MANIFEST_NAMES[0]} listing {wanted}"
        )
        return [message]
    try:
        listed = parse_manifest(path)
    except VerificationError as error:
        return [str(error)]
    for name, digest in expected.items():
        if name not in listed:
            errors.append(f"{path.name}: missing artifact entry {name}")
        elif listed[name] != digest:
            errors.append(
                f"{path.name}: {name} is listed as {listed[name]}, actual {digest}"
            )
    for name in listed:
        artifact = directory / name
        if not artifact.is_file():
            errors.append(f"{path.name}: listed artifact does not exist: {name}")
        elif sha256_file(artifact) != listed[name]:
            errors.append(f"{path.name}: {name} does not match its listed digest")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True,
                        help="Directory holding the release artifacts, for example dist/v0.3.0")
    parser.add_argument("--platform", choices=[*PLATFORM_SUFFIXES, "all"], default="all",
                        help="Verify one platform ZIP or the complete release candidate")
    parser.add_argument("--version", default=CORE_VERSION,
                        help="Release version the artifacts must carry (default: core version)")
    parser.add_argument("--commit", default=None,
                        help="Source commit the artifacts must carry (default: git HEAD)")
    args = parser.parse_args()
    directory = args.directory if args.directory.is_absolute() else ROOT / args.directory
    if not directory.is_dir():
        raise SystemExit(f"FAILED: artifact directory does not exist: {directory}")
    commit = args.commit
    if commit is None:
        try:
            commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        except (OSError, subprocess.CalledProcessError) as error:
            raise SystemExit(f"FAILED: cannot read git HEAD for --commit: {error}") from error

    platforms = list(PLATFORM_SUFFIXES) if args.platform == "all" else [args.platform]
    errors: list[str] = []
    verified: list[str] = []
    for platform in platforms:
        suffix = PLATFORM_SUFFIXES[platform]
        platform_errors = verify_platform(directory, platform, args.version, commit)
        if platform_errors:
            errors.extend(f"[{platform}] {message}" for message in platform_errors)
        else:
            verified.append(f"PsyML-Toolkit-{args.version}-{suffix}.zip")
    if args.platform == "all":
        errors.extend(f"[all] {message}" for message in verify_pdfs(directory))
        expected = {
            f"PsyML-Toolkit-{args.version}-{suffix}.zip": sha256_file(
                directory / f"PsyML-Toolkit-{args.version}-{suffix}.zip")
            for suffix in PLATFORM_SUFFIXES.values()
            if (directory / f"PsyML-Toolkit-{args.version}-{suffix}.zip").is_file()
        }
        for name in PDF_NAMES:
            path = directory / "docs" / name
            if path.is_file():
                expected[f"docs/{name}"] = sha256_file(path)
        if len(expected) != 4:
            errors.append(
                "[all] incomplete artifact set; the release candidate needs two platform "
                "ZIPs and two distribution PDFs"
            )
        errors.extend(f"[all] {message}" for message in verify_manifest(directory, expected))
    if errors:
        raise SystemExit("FAILED: release artifacts did not verify:\n- " + "\n- ".join(errors))
    print(f"PSYML_RELEASE_ARTIFACTS_OK version={args.version} commit={commit} "
          f"platform={args.platform}")
    for name in verified:
        print(f"verified {name} ({sha256_file(directory / name)})")
    if args.platform == "all":
        for name in PDF_NAMES:
            path = directory / "docs" / name
            print(f"verified docs/{name} ({path.stat().st_size} bytes)")
        print("verified SHA256SUMS")


if __name__ == "__main__":
    main()
