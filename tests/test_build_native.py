"""Build, PDF-label and release-artifact tooling regression tests.

The synthetic archives below are structurally valid stand-ins for the real
platform packages, so the verifier is exercised against ZIP contents, hashes
and ``BUILD.json`` fields instead of a success string.
"""

import hashlib
import importlib.util
import io
import json
import shutil
import struct
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
FIXTURE_ROOT = ROOT / "tmp" / "test_build_native"
VERSION = "0.3.1"
COMMIT = "a" * 40
PLATFORM_SUFFIXES = {"macOS": "macOS-arm64", "Windows": "Windows-x64"}


def _mach_executable(cpu=0x0100000C, endian="<") -> bytes:
    """Tiny structurally valid 64-bit Mach-O; never executed by these tests."""
    header = struct.pack(endian + "8I", 0xFEEDFACF, cpu, 0, 2, 1, 72, 0, 0)
    segment = struct.pack(endian + "II16sQQQQIIII", 0x19, 72, b"__TEXT", 0, 108,
                          0, 108, 7, 5, 0, 0)
    return header + segment + b"code"


def _pe_executable(cpu=0x8664) -> bytes:
    """Tiny structurally valid PE32+ application with one nonempty section."""
    dos = bytearray(64)
    dos[:2] = b"MZ"
    struct.pack_into("<I", dos, 60, 64)
    coff = b"PE\0\0" + struct.pack("<HHIIIHH", cpu, 1, 0, 0, 0, 112, 0x0002)
    optional = b"\x0b\x02" + bytes(110)
    section = bytearray(40)
    struct.pack_into("<II", section, 16, 4, 240)
    return bytes(dos) + coff + optional + bytes(section) + b"code"


def _fat_executable(*cpus, wide=False) -> bytes:
    entries, slices = [], []
    position = 8 + len(cpus) * (32 if wide else 20)
    for cpu in cpus:
        executable = _mach_executable(cpu)
        if wide:
            entries.append(struct.pack(">IIQQII", cpu, 0, position, len(executable), 0, 0))
        else:
            entries.append(struct.pack(">5I", cpu, 0, position, len(executable), 0))
        position += len(executable)
        slices.append(executable)
    return (struct.pack(">II", 0xCAFEBABF if wide else 0xCAFEBABE, len(cpus))
            + b"".join(entries) + b"".join(slices))


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"psyml_{name}", TOOLS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def fixture_dir(request):
    # Parametrized binary headers and archive paths are not valid directory names.
    identifier = hashlib.sha256(request.node.nodeid.encode()).hexdigest()[:16]
    directory = FIXTURE_ROOT / identifier
    if directory.exists():
        shutil.rmtree(directory)
    directory.mkdir(parents=True)
    yield directory
    shutil.rmtree(directory, ignore_errors=True)


def _write_package(directory: Path, platform: str, *, build_overrides: dict | None = None,
                   extra_members: dict | None = None) -> Path:
    """Write one structurally valid package ZIP plus its SHA-256 sidecar."""
    suffix = PLATFORM_SUFFIXES[platform]
    root = f"PsyML-Toolkit-{VERSION}-{suffix}"
    build = {
        "version": VERSION,
        "label": VERSION,
        "published": False,
        "platform": suffix,
        "python": "3.12.13",
        "commit": COMMIT,
        "lock_sha256": hashlib.sha256((ROOT / "uv.lock").read_bytes()).hexdigest(),
        "working_tree_modified": False,
        "source_changes": [],
        "post_build_changes": [],
    }
    build.update(build_overrides or {})
    members = {
        f"{root}/BUILD.json": json.dumps(build, indent=2).encode(),
        f"{root}/SMOKE_TEST.txt": b"PSYML_NATIVE_BUNDLE_OK\n",
        f"{root}/START_HERE.txt": b"start here\n",
        f"{root}/LICENSE": b"license\n",
        f"{root}/licenses/SHAP_LICENSE.txt": b"shap\n",
        f"{root}/licenses/NUMBA_LICENSE.txt": b"numba\n",
        f"{root}/licenses/LLVMLITE_LICENSE.txt": b"llvmlite\n",
        f"{root}/examples/quickstart/README.md": b"quickstart\n",
        f"{root}/examples/quickstart/classification_config.json": b"{}\n",
        f"{root}/examples/quickstart/regression_config.json": b"{}\n",
        f"{root}/examples/quickstart/classification_train.csv": b"a,b\n1,2\n",
        f"{root}/examples/quickstart/regression_train.csv": b"a,b\n1,2\n",
        f"{root}/examples/quickstart/classification_predict.csv": b"a\n1\n",
        f"{root}/examples/quickstart/regression_predict.csv": b"a\n1\n",
        f"{root}/examples/synthetic/classification.csv": b"a,b\n1,2\n",
    }
    if platform == "macOS":
        app = f"{root}/PsyML Toolkit.app/Contents"
        members.update({
            f"{app}/Info.plist": b"plist\n",
            f"{app}/MacOS/PsyML Toolkit": _mach_executable(),
            f"{app}/Resources/core/psyml-core": _mach_executable(),
            f"{app}/Resources/core/_internal/runtime.txt": b"runtime\n",
        })
    else:
        members.update({
            f"{root}/PsyML Toolkit.exe": _pe_executable(),
            f"{root}/core/psyml-core.exe": _pe_executable(),
            f"{root}/core/_internal/runtime.txt": b"runtime\n",
        })
    members.update(extra_members or {})
    archive = directory / f"{root}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
        for name, payload in members.items():
            output.writestr(name, payload)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_name(archive.name + ".sha256").write_text(
        f"{digest}  {archive.name}\n", encoding="utf-8"
    )
    return archive


def _write_pdfs(directory: Path) -> None:
    docs = directory / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    module = _load("verify_release_artifacts")
    for name in module.PDF_NAMES:
        (docs / name).write_bytes(b"%PDF-1.4\n% synthetic fixture\n%%EOF\n")
    sources = {
        relative: hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        for relative in module.PDF_SOURCES
    }
    (docs / "sources.json").write_text(json.dumps(sources, indent=2), encoding="utf-8")


def _write_manifest(directory: Path) -> None:
    listed = {}
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path.name.endswith(".sha256") or path.name == "SHA256SUMS":
            continue
        listed[path.relative_to(directory).as_posix()] = hashlib.sha256(
            path.read_bytes()).hexdigest()
    (directory / "SHA256SUMS").write_text(
        "".join(f"{digest}  {name}\n" for name, digest in sorted(listed.items())),
        encoding="utf-8",
    )


def _run_verifier(directory: Path, platform: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TOOLS / "verify_release_artifacts.py"),
         "--directory", str(directory), "--platform", platform,
         "--version", VERSION, "--commit", COMMIT],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )


def test_release_metadata_follows_the_single_core_version():
    module = _load("release_metadata")
    import psyml

    assert module.CORE_VERSION == psyml.__version__
    assert module.default_label() == "v" + psyml.__version__
    assert module.notice_for_label(module.default_label()) is None
    development = module.notice_for_label("v0.3.0.dev1")
    assert development is not None and "开发版 QA 文档" in development
    historical = module.notice_for_label("v0.2.0")
    assert historical is not None and "历史版本文档" in historical
    assert module.is_development_label("v0.3.0.dev0")
    assert not module.is_development_label("v0.3.0")


def test_pdf_builder_derives_its_label_from_the_core_version():
    text = (TOOLS / "build_release_pdfs.py").read_text(encoding="utf-8")
    assert "0.2.0" not in text
    assert "from release_metadata import CURRENT_LABEL, default_label, notice_for_label" in text
    assert "default=default_label()" in text
    assert "notice_for_label(label)" in text
    assert "releases/tag/{label}" in text


def test_pdf_builder_preamble_matches_the_standalone_apps():
    """The frozen README PDF must describe the real per-platform packages.

    The old wording assumed a Windows-only researcher share kit with TestData/
    and Documents/ folders, a bundled best_ridge.joblib and a save-as
    prediction export; none of that exists in the standalone ZIPs.
    """
    text = (TOOLS / "build_release_pdfs.py").read_text(encoding="utf-8")
    for obsolete in ["分享包", "TestData", "Documents", "另存", "predictions.parquet"]:
        assert obsolete not in text
    for required in [
        "PsyML Toolkit.app",
        "PsyML Toolkit.exe",
        "examples/quickstart/classification_config.json",
        "classification_predict.csv",
        "regression_predict.csv",
        "model_metadata.json",
        "best_decision_tree.joblib",
        "打开预测结果文件夹",
        "predictions.csv",
    ]:
        assert required in text


def test_build_native_and_workflow_keep_explain_and_all_three_smokes():
    build_native = (TOOLS / "build_native.py").read_text(encoding="utf-8")
    for package in ["shap", "numba", "llvmlite"]:
        assert f'"--collect-all", "{package}"' in build_native
    flags = ["--permutation-smoke", "--explain-smoke", "--coefficients-smoke"]
    for flag in flags:
        assert f'"{flag}"' in build_native
    workflow = (ROOT / ".github/workflows/native-test-build.yml").read_text(encoding="utf-8")
    assert "uv sync --locked --group dev --group build --extra explain" in workflow
    assert "--directory dist --platform Windows" in workflow
    for flag in flags:
        assert flag in workflow


def test_verify_release_artifacts_accepts_a_complete_candidate(fixture_dir):
    for platform in PLATFORM_SUFFIXES:
        _write_package(fixture_dir, platform)
    _write_pdfs(fixture_dir)
    _write_manifest(fixture_dir)
    result = _run_verifier(fixture_dir, "all")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PSYML_RELEASE_ARTIFACTS_OK" in result.stdout


def test_verify_release_artifacts_single_platform_needs_only_its_zip(fixture_dir):
    _write_package(fixture_dir, "macOS")
    result = _run_verifier(fixture_dir, "macOS")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PSYML_RELEASE_ARTIFACTS_OK" in result.stdout


def test_verify_release_artifacts_rejects_a_wrong_build_version(fixture_dir):
    module = _load("verify_release_artifacts")
    _write_package(fixture_dir, "macOS", build_overrides={"version": "0.2.0"})
    errors = module.verify_platform(fixture_dir, "macOS", VERSION, COMMIT)
    assert any("version" in error and "0.2.0" in error for error in errors), errors


def test_verify_release_artifacts_rejects_a_dirty_source_build(fixture_dir):
    module = _load("verify_release_artifacts")
    _write_package(fixture_dir, "macOS", build_overrides={"working_tree_modified": True})
    errors = module.verify_platform(fixture_dir, "macOS", VERSION, COMMIT)
    assert any("working_tree_modified" in error for error in errors), errors


def test_verify_release_artifacts_rejects_a_tampered_sidecar(fixture_dir):
    module = _load("verify_release_artifacts")
    archive = _write_package(fixture_dir, "macOS")
    archive.with_name(archive.name + ".sha256").write_text(
        f"{'0' * 64}  {archive.name}\n", encoding="utf-8"
    )
    errors = module.verify_platform(fixture_dir, "macOS", VERSION, COMMIT)
    assert any("does not match the archive" in error for error in errors), errors


def test_verify_release_artifacts_rejects_unsafe_archive_members(fixture_dir):
    module = _load("verify_release_artifacts")
    _write_package(fixture_dir, "macOS", extra_members={"../escape.txt": b"x"})
    errors = module.verify_platform(fixture_dir, "macOS", VERSION, COMMIT)
    assert any("unsafe archive entry path" in error for error in errors), errors


def test_verify_release_artifacts_rejects_a_missing_core_runtime(fixture_dir):
    module = _load("verify_release_artifacts")
    archive = _write_package(fixture_dir, "Windows")
    # Rewrite the archive without its bundled runtime but keep the sidecar honest.
    with zipfile.ZipFile(archive) as source:
        payload = {
            info.filename: source.read(info.filename)
            for info in source.infolist()
            if "_internal/" not in info.filename
        }
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
        for name, data in payload.items():
            output.writestr(name, data)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_name(archive.name + ".sha256").write_text(
        f"{digest}  {archive.name}\n", encoding="utf-8"
    )
    errors = module.verify_platform(fixture_dir, "Windows", VERSION, COMMIT)
    assert any("missing bundled core runtime" in error for error in errors), errors


def test_verify_release_artifacts_rejects_stale_pdf_sources(fixture_dir):
    module = _load("verify_release_artifacts")
    _write_pdfs(fixture_dir)
    docs = fixture_dir / "docs"
    sources = json.loads((docs / "sources.json").read_text(encoding="utf-8"))
    sources["README.md"] = "0" * 64
    (docs / "sources.json").write_text(json.dumps(sources), encoding="utf-8")
    errors = module.verify_pdfs(fixture_dir)
    assert any("recorded source changed: README.md" in error for error in errors), errors


def test_verify_release_artifacts_all_mode_fails_without_the_pdf_set(fixture_dir):
    for platform in PLATFORM_SUFFIXES:
        _write_package(fixture_dir, platform)
    result = _run_verifier(fixture_dir, "all")
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "missing distribution PDF" in combined
    assert "missing release checksum manifest" in combined


@pytest.mark.parametrize("platform,machine,bits", [
    ("darwin", "x86_64", 64), ("win32", "ARM64", 64),
    ("win32", "AMD64", 32), ("linux", "aarch64", 64),
])
def test_build_target_rejects_unsupported_or_emulated_python(monkeypatch, platform, machine, bits):
    module = _load("build_native")
    monkeypatch.setattr(module.sys, "platform", platform)
    monkeypatch.setattr(module.platform, "machine", lambda: machine)
    monkeypatch.setattr(module.struct, "calcsize", lambda _: bits // 8)
    with pytest.raises(SystemExit, match="native 64-bit Python"):
        module.build_target()


@pytest.mark.parametrize("platform,machine,expected", [
    ("darwin", "arm64", "macOS-arm64"), ("darwin", "aarch64", "macOS-arm64"),
    ("win32", "AMD64", "Windows-x64"), ("win32", "x86_64", "Windows-x64"),
])
def test_build_target_accepts_supported_python(monkeypatch, platform, machine, expected):
    module = _load("build_native")
    monkeypatch.setattr(module.sys, "platform", platform)
    monkeypatch.setattr(module.platform, "machine", lambda: machine)
    monkeypatch.setattr(module.struct, "calcsize", lambda _: 8)
    assert module.build_target() == expected


def test_build_rejects_wrong_target_before_invoking_any_tools(monkeypatch):
    module = _load("build_native")
    monkeypatch.setattr(module.sys, "platform", "linux")
    monkeypatch.setattr(module.sys, "argv", ["build_native.py"])
    monkeypatch.setattr(module, "run", lambda *args: pytest.fail("tool ran before preflight"))
    monkeypatch.setattr(module.subprocess, "check_output",
                        lambda *args, **kwargs: pytest.fail("git ran before preflight"))
    with pytest.raises(SystemExit, match="native 64-bit Python"):
        module.main()


@pytest.mark.parametrize("payload,expected", [
    (_mach_executable(), {"macOS-arm64"}),
    (_mach_executable(0x01000007, ">"), {"macOS-x86_64"}),
    (_pe_executable(), {"Windows-x64"}),
    (_pe_executable(0xAA64), {"Windows-arm64"}),
    (_fat_executable(0x0100000C, 0x01000007), {"macOS-arm64", "macOS-x86_64"}),
    (_fat_executable(0x0100000C, wide=True), {"macOS-arm64"}),
])
def test_executable_targets_reads_real_headers(payload, expected):
    module = _load("verify_release_artifacts")
    assert module.executable_targets(io.BytesIO(payload), len(payload)) == expected


@pytest.mark.parametrize("payload", [
    b"", b"binary\n", b"\xcf\xfa\xed\xfe" + bytes(28),
    _mach_executable()[:-1], _pe_executable()[:-1],
    b"MZ" + bytes(62), _fat_executable(0x0100000C)[:-1],
])
def test_executable_targets_rejects_fake_or_truncated_binaries(payload):
    module = _load("verify_release_artifacts")
    with pytest.raises(module.VerificationError):
        module.executable_targets(io.BytesIO(payload), len(payload))


def test_universal_python_is_allowed_but_universal_package_is_not(fixture_dir):
    module = _load("verify_release_artifacts")
    executable = fixture_dir / "Python"
    executable.write_bytes(_fat_executable(0x0100000C, 0x01000007))
    module.check_file_architecture(executable, "macOS-arm64", allow_universal=True)
    with pytest.raises(module.VerificationError, match="executable architecture"):
        module.check_file_architecture(executable, "macOS-arm64")


@pytest.mark.parametrize("platform,relative,payload", [
    ("macOS", "PsyML Toolkit.app/Contents/MacOS/PsyML Toolkit", _mach_executable(0x01000007)),
    ("macOS", "PsyML Toolkit.app/Contents/Resources/core/psyml-core", _mach_executable(0x01000007)),
    ("Windows", "PsyML Toolkit.exe", _pe_executable(0xAA64)),
    ("Windows", "core/psyml-core.exe", _pe_executable(0xAA64)),
    ("Windows", "core/psyml-core.exe", _mach_executable()),
])
def test_release_rejects_wrong_executable_architecture(fixture_dir, platform, relative, payload):
    module = _load("verify_release_artifacts")
    root = f"PsyML-Toolkit-{VERSION}-{PLATFORM_SUFFIXES[platform]}"
    _write_package(fixture_dir, platform, extra_members={f"{root}/{relative}": payload})
    errors = module.verify_platform(fixture_dir, platform, VERSION, COMMIT)
    assert any("executable architecture" in error for error in errors), errors


@pytest.mark.parametrize("relative", [
    "BUILD.json", "SMOKE_TEST.txt", "START_HERE.txt", "LICENSE", "licenses/SHAP_LICENSE.txt",
    "licenses/NUMBA_LICENSE.txt", "licenses/LLVMLITE_LICENSE.txt", "PsyML Toolkit.exe",
    "core/psyml-core.exe", "examples/quickstart/classification_train.csv",
])
def test_release_rejects_empty_required_member(fixture_dir, relative):
    module = _load("verify_release_artifacts")
    root = f"PsyML-Toolkit-{VERSION}-Windows-x64"
    _write_package(fixture_dir, "Windows", extra_members={f"{root}/{relative}": b""})
    errors = module.verify_platform(fixture_dir, "Windows", VERSION, COMMIT)
    assert any("empty or non-file required" in error for error in errors), errors


def test_release_rejects_empty_and_directory_only_runtime(fixture_dir):
    module = _load("verify_release_artifacts")
    root = f"PsyML-Toolkit-{VERSION}-Windows-x64"
    _write_package(fixture_dir, "Windows", extra_members={
        f"{root}/core/_internal/runtime.txt": b"",
        f"{root}/core/_internal/": b"",
    })
    errors = module.verify_platform(fixture_dir, "Windows", VERSION, COMMIT)
    assert any("missing bundled core runtime" in error for error in errors), errors


@pytest.mark.parametrize("changes", [
    [" M src/psyml/runner.py"], [" M gui/project.godot"],
    [" M gui/assets/psyml-icon.png.import"], ["?? src/psyml/new.py"],
    ["?? dist/unreviewed.bin"], "", None, [None],
])
def test_release_rejects_dirty_or_unknown_post_build_source(fixture_dir, changes):
    module = _load("verify_release_artifacts")
    _write_package(fixture_dir, "Windows", build_overrides={"post_build_changes": changes})
    errors = module.verify_platform(fixture_dir, "Windows", VERSION, COMMIT)
    assert any("post_build_changes" in error for error in errors), errors


@pytest.mark.parametrize("overrides,expected", [
    ({"source_changes": [" M src/psyml/runner.py"]}, "source_changes"),
    ({"reused_core": True}, "reused_core"),
    ({"lock_sha256": "b" * 64}, "lock_sha256"),
    ({"lock_sha256": None}, "lock_sha256"),
])
def test_release_rejects_inconsistent_provenance(fixture_dir, overrides, expected):
    module = _load("verify_release_artifacts")
    _write_package(fixture_dir, "Windows", build_overrides=overrides)
    errors = module.verify_platform(fixture_dir, "Windows", VERSION, COMMIT)
    assert any(expected in error for error in errors), errors


@pytest.mark.parametrize("language", ["EN", "ZH", "FR"])
def test_developer_build_commands_keep_explain_smokes_and_current_destinations(language):
    text = (ROOT / "docs" / f"DEVELOPMENT_{language}.md").read_text(encoding="utf-8")
    assert "uv sync --locked --group dev --group build --extra explain" in text
    assert "uv run --locked --group build --extra explain python tools/build_native.py" in text
    for flag in ["--permutation-smoke", "--explain-smoke", "--coefficients-smoke"]:
        assert flag in text
    assert "--output-dir dist/v0.3.1/docs" in text
    assert "--output-dir output/pdf" in text
    assert "--windows-zip dist/v0.3.1/PsyML-Toolkit-0.3.1-Windows-x64.zip" in text
    assert "PsyML-Toolkit-Researcher-Share-v0.2.0.zip" not in text
    assert "`tools/licenses/`" in text and "`licenses/`" in text


@pytest.mark.parametrize("final_changes", [[], [" M src/psyml/runner.py"]])
def test_native_build_records_final_status_after_smoke_and_blocks_new_source_changes(
        fixture_dir, monkeypatch, final_changes):
    """Exercise finalization order without running native executables on Linux."""
    monkeypatch.syspath_prepend(str(TOOLS))
    import verify_release_artifacts

    module = _load("build_native")
    monkeypatch.setattr(module, "ROOT", fixture_dir)
    monkeypatch.setattr(module, "build_target", lambda: "Windows-x64")
    monkeypatch.setattr(module.sys, "platform", "win32")
    monkeypatch.setattr(module.sys, "argv", ["build_native.py", "--reuse-core"])
    monkeypatch.setattr(verify_release_artifacts, "check_file_architecture", lambda *a, **k: None)
    for relative, data in {
        "uv.lock": b"locked dependencies",
        "LICENSE": b"license",
        "tools/NATIVE_START_HERE.txt": b"start",
        "tools/licenses/SHAP_LICENSE.txt": b"notice",
        "examples/synthetic/classification_config.json": b"{}",
        "examples/quickstart/README.md": b"examples",
        "tmp/native/frozen/psyml-core/psyml-core.exe": _pe_executable(),
    }.items():
        path = fixture_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    calls = []

    def status():
        calls.append("source_status")
        return [] if calls.count("source_status") == 1 else final_changes

    def run(*args, **kwargs):
        if "import-config" in args[0]:
            return subprocess.CompletedProcess(args[0], 0, stdout='{"needs_data": false}')
        calls.append("gui_smoke")
        (fixture_dir / "tmp/native/smoke-report.txt").write_text("PSYML_NATIVE_BUNDLE_OK")
        package = fixture_dir / f"dist/PsyML-Toolkit-{VERSION}-Windows-x64"
        assert json.loads((package / "BUILD.json").read_text())["post_build_changes"] is None
        return subprocess.CompletedProcess(args[0], 0, stdout="native smoke", stderr="")

    monkeypatch.setattr(module, "source_status", status)
    monkeypatch.setattr(module, "run", lambda *args: None)
    monkeypatch.setattr(module.shutil, "which", lambda candidate: candidate)
    monkeypatch.setattr(module, "export_gui", lambda godot, platform, output:
                        output.write_bytes(_pe_executable()))
    monkeypatch.setattr(module.subprocess, "check_output", lambda *a, **k: COMMIT)
    monkeypatch.setattr(module.subprocess, "run", run)
    if final_changes:
        with pytest.raises(RuntimeError, match="Build changed source files"):
            module.main()
        assert not list((fixture_dir / "dist").glob("*.zip"))
    else:
        module.main()
        archive = next((fixture_dir / "dist").glob("*.zip"))
        with zipfile.ZipFile(archive) as package:
            name = next(name for name in package.namelist() if name.endswith("/BUILD.json"))
            document = json.loads(package.read(name))
        assert document["post_build_changes"] == []
        assert document["lock_sha256"] == hashlib.sha256(b"locked dependencies").hexdigest()
        assert document["reused_core"] is True
    assert calls == ["source_status", "gui_smoke", "source_status"]


def test_release_rejects_corruption_in_unchecked_runtime_member(fixture_dir):
    module = _load("verify_release_artifacts")
    path = _write_package(fixture_dir, "Windows")
    member = f"PsyML-Toolkit-{VERSION}-Windows-x64/core/_internal/runtime.txt"
    with zipfile.ZipFile(path) as archive:
        info = archive.getinfo(member)
        offset = info.header_offset + 30 + len(info.filename.encode()) + len(info.extra)
    payload = bytearray(path.read_bytes())
    payload[offset] ^= 0xFF
    path.write_bytes(payload)
    path.with_name(path.name + ".sha256").write_text(
        hashlib.sha256(payload).hexdigest() + "  " + path.name + "\n")
    errors = module.verify_platform(fixture_dir, "Windows", VERSION, COMMIT)
    assert any("CRC/decompression integrity failure" in error for error in errors), errors
