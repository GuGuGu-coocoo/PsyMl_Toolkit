"""Verify built release artifacts by inspecting the real files.

Structural verification of the platform ZIPs, their SHA-256 sidecars and, in
``all`` mode, the Chinese distribution PDFs and the release checksum manifest.
Entry names, sizes, ``BUILD.json`` fields, archive safety and hashes are read
from the artifacts themselves; a success string in a log is never enough.

Usage::

    .venv/bin/python tools/verify_release_artifacts.py --directory dist/v0.3.1 --platform all

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
import posixpath
import re
import struct
import subprocess
import zipfile
import zlib
from pathlib import Path
from typing import BinaryIO

from psyml import __version__ as CORE_VERSION

ROOT = Path(__file__).resolve().parents[1]
PLATFORM_SUFFIXES = {"macOS": "macOS-arm64", "Windows": "Windows-x64"}
PDF_NAMES = ("README_ZH.pdf", "RESEARCHER_GUIDE_ZH.pdf")
PDF_SOURCES = ("README_ZH.md", "docs/RESEARCHER_GUIDE_ZH.md",
               "tools/build_release_pdfs.py", "tools/pdf_text.py",
               "tools/release_metadata.py", "src/psyml/__init__.py")
MANIFEST_NAMES = ("SHA256SUMS", "SHA256SUMS.txt")
SMOKE_MARKER = "PSYML_NATIVE_BUNDLE_OK"
_HEX = re.compile(r"^[0-9a-f]{64}$")
# Build outputs/caches live in ignored dist/, tmp/ and gui/.godot/. No tracked
# source or untracked source addition is a justified packaging side effect.
# Keep this explicit and fail closed; do not allow whole source directories.
ALLOWED_POST_BUILD_CHANGES: frozenset[str] = frozenset()


class VerificationError(Exception):
    """Raised with every structural failure found in the requested artifacts."""


def executable_targets(stream: BinaryIO, size: int, *, offset: int = 0) -> set[str]:
    """Read Mach-O/PE headers and payload bounds, without executing the file.

    This is an architecture/structural check, not a substitute for native smoke
    tests. Universal Mach-O slices are inspected individually, not just trusted
    from the outer table. Reads are bounded, including for untrusted ZIP members.
    """
    def read(position: int, length: int) -> bytes:
        if position < 0 or length < 0 or position + length > size:
            raise VerificationError("truncated executable header or payload")
        stream.seek(offset + position)
        data = stream.read(length)
        if len(data) != length:
            raise VerificationError("truncated executable header or payload")
        return data

    magic = read(0, 4)
    fat_formats = {b"\xca\xfe\xba\xbe": (">", False), b"\xbe\xba\xfe\xca": ("<", False),
                   b"\xca\xfe\xba\xbf": (">", True), b"\xbf\xba\xfe\xca": ("<", True)}
    if magic in fat_formats:
        endian, wide = fat_formats[magic]
        count = struct.unpack(endian + "I", read(4, 4))[0]
        if not 1 <= count <= 16:
            raise VerificationError("invalid universal Mach-O architecture count")
        entry_size = 32 if wide else 20
        table = read(8, count * entry_size)
        targets: set[str] = set()
        spans = []
        for index in range(count):
            entry = table[index * entry_size:(index + 1) * entry_size]
            cpu, _, start, length = struct.unpack(endian + ("IIQQ" if wide else "IIII"),
                                                 entry[:24 if wide else 16])
            if start < 8 + len(table) or length < 32 or start + length > size:
                raise VerificationError("invalid universal Mach-O slice bounds")
            if any(start < end and start + length > begin for begin, end in spans):
                raise VerificationError("overlapping universal Mach-O slices")
            spans.append((start, start + length))
            slice_magic = read(start, 4)
            if slice_magic not in (b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf"):
                raise VerificationError("universal Mach-O slice is not a 64-bit executable")
            slice_endian = "<" if slice_magic == b"\xcf\xfa\xed\xfe" else ">"
            if struct.unpack(slice_endian + "I", read(start + 4, 4))[0] != cpu:
                raise VerificationError("universal Mach-O CPU table disagrees with slice")
            targets.update(executable_targets(stream, length, offset=offset + start))
        return targets
    if magic in (b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf"):
        endian = "<" if magic == b"\xcf\xfa\xed\xfe" else ">"
        _, cpu, _, file_type, commands, command_size, _, _ = struct.unpack(
            endian + "8I", read(0, 32))
        if file_type != 2 or commands == 0 or commands > command_size // 8:
            raise VerificationError("Mach-O is not an executable with load commands")
        if 32 + command_size > size:
            raise VerificationError("truncated Mach-O load commands")
        position, has_payload = 32, False
        for _ in range(commands):
            command, length = struct.unpack(endian + "II", read(position, 8))
            if length < 8 or length % 8 or position + length > 32 + command_size:
                raise VerificationError("invalid Mach-O load command")
            if command == 0x19:  # LC_SEGMENT_64
                if length < 72:
                    raise VerificationError("truncated Mach-O segment")
                start, payload_size = struct.unpack(endian + "QQ", read(position + 40, 16))
                if start + payload_size > size:
                    raise VerificationError("Mach-O segment exceeds executable bounds")
                has_payload |= payload_size > 0 and start + payload_size > 32 + command_size
            position += length
        if position != 32 + command_size or not has_payload:
            raise VerificationError("Mach-O has no executable payload or inconsistent load commands")
        target = {0x0100000C: "macOS-arm64", 0x01000007: "macOS-x86_64"}.get(cpu)
        if target is None:
            raise VerificationError(f"unsupported Mach-O CPU type: {cpu:#x}")
        return {target}
    if magic[:2] == b"MZ":
        pe_offset = struct.unpack("<I", read(60, 4))[0]
        if pe_offset < 64:
            raise VerificationError("invalid PE header offset")
        header = read(pe_offset, 24)
        if header[:4] != b"PE\0\0":
            raise VerificationError("invalid PE signature")
        cpu, sections, _, _, _, optional_size, flags = struct.unpack("<HHIIIHH", header[4:])
        if not flags & 0x0002 or flags & 0x2000 or not 1 <= sections <= 96:
            raise VerificationError("PE is not an application executable")
        optional = read(pe_offset + 24, optional_size)
        if optional_size < 112 or optional[:2] != b"\x0b\x02":
            raise VerificationError("PE is not a 64-bit executable")
        table = read(pe_offset + 24 + optional_size, sections * 40)
        has_payload = False
        for index in range(sections):
            length, start = struct.unpack_from("<II", table, index * 40 + 16)
            if length and (start < pe_offset + 24 + optional_size + len(table)
                           or start + length > size):
                raise VerificationError("PE section exceeds executable payload bounds")
            has_payload |= length > 0
        if not has_payload:
            raise VerificationError("PE has no executable payload")
        target = {0x8664: "Windows-x64", 0xAA64: "Windows-arm64"}.get(cpu)
        if target is None:
            raise VerificationError(f"unsupported PE machine type: {cpu:#x}")
        return {target}
    raise VerificationError("not a supported Mach-O or PE executable")


def check_file_architecture(path: Path, target: str, *, allow_universal: bool = False) -> None:
    """Fail early on a wrong-architecture build tool or frozen executable."""
    with path.open("rb") as stream:
        actual = executable_targets(stream, path.stat().st_size)
    if actual != {target} and not (allow_universal and target in actual):
        raise VerificationError(f"{path}: executable architecture {sorted(actual)}, expected {target}")


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


def check_required_members(archive: zipfile.ZipFile, required: list[str],
                           errors: list[str]) -> None:
    for name in required:
        try:
            info = archive.getinfo(name)
        except KeyError:
            errors.append(f"missing required archive member: {name}")
            continue
        mode = (info.external_attr >> 16) & 0o170000
        if info.is_dir() or mode not in (0, 0o100000) or info.file_size <= 0:
            errors.append(f"empty or non-file required archive member: {name}")


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
        "lock_sha256": sha256_file(ROOT / "uv.lock"),
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
    if document.get("source_changes") != []:
        errors.append(f"{member}: source_changes must record an empty initial source tree")
    changes = document.get("post_build_changes")
    if not isinstance(changes, list) or any(not isinstance(line, str) for line in changes):
        errors.append(f"{member}: post_build_changes must be a list of git status records")
    else:
        unexpected = [line for line in changes if line not in ALLOWED_POST_BUILD_CHANGES]
        if unexpected:
            errors.append(f"{member}: unexpected post_build_changes: {unexpected!r}")
    if document.get("reused_core", False) is not False:
        errors.append(f"{member}: reused_core must be false for a release build")
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
        executables = [f"{app}/MacOS/PsyML Toolkit", f"{core_prefix}psyml-core"]
    else:
        required.extend([f"{root}/PsyML Toolkit.exe", f"{root}/core/psyml-core.exe"])
        core_prefix = f"{root}/core/"
        executables = [f"{root}/PsyML Toolkit.exe", f"{core_prefix}psyml-core.exe"]

    try:
        archive = zipfile.ZipFile(archive_path)
    except (zipfile.BadZipFile, OSError) as error:
        errors.append(f"unreadable archive {archive_name}: {error}")
        return errors
    with archive:
        try:
            bad_member = archive.testzip()
        except (OSError, RuntimeError, zipfile.BadZipFile, zlib.error) as error:
            return [f"archive CRC/decompression integrity failure: {error}"]
        if bad_member is not None:
            return [f"archive CRC/decompression integrity failure: {bad_member}"]
        names = {info.filename for info in archive.infolist()}
        check_member_safety(archive, root, errors)
        check_required_members(archive, required, errors)
        quickstart = f"{root}/examples/quickstart/README.md"
        if quickstart in names:
            try:
                text = archive.read(quickstart).decode("utf-8")
                for target in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text):
                    if "://" in target:
                        continue
                    resolved = posixpath.normpath(posixpath.join(posixpath.dirname(quickstart), target))
                    if not resolved.startswith(root + "/"):
                        errors.append(f"quickstart image escapes package: {target}")
                    else:
                        check_required_members(archive, [resolved], errors)
            except UnicodeDecodeError:
                errors.append("quickstart README is not valid UTF-8")
        runtime = [info for info in archive.infolist()
                   if info.filename.startswith(core_prefix + "_internal/") and not info.is_dir()
                   and (info.external_attr >> 16) & 0o170000 in (0, 0o100000)]
        if not runtime or not any(info.file_size > 0 for info in runtime):
            errors.append(f"missing bundled core runtime: {core_prefix}_internal/")
        for member in executables:
            if member not in names:
                continue
            try:
                with archive.open(member) as stream:
                    actual = executable_targets(stream, archive.getinfo(member).file_size)
                if actual != {suffix}:
                    errors.append(f"{member}: executable architecture {sorted(actual)}, "
                                  f"expected {suffix}")
            except (VerificationError, OSError, zipfile.BadZipFile) as error:
                errors.append(f"{member}: {error}")
        build_member = f"{root}/BUILD.json"
        if build_member in names:
            check_build_json(archive, build_member, version, commit, suffix, errors)
        smoke_member = f"{root}/SMOKE_TEST.txt"
        if smoke_member in names:
            try:
                smoke = archive.read(smoke_member).decode("utf-8").strip()
            except UnicodeDecodeError:
                smoke = None
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
                        help="Directory holding the release artifacts, for example dist/v0.3.1")
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
