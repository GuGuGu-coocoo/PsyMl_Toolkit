"""Build, PDF-label and release-artifact tooling regression tests.

The synthetic archives below are structurally valid stand-ins for the real
platform packages, so the verifier is exercised against ZIP contents, hashes
and ``BUILD.json`` fields instead of a success string.
"""

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
FIXTURE_ROOT = ROOT / "tmp" / "test_build_native"
VERSION = "0.3.0"
COMMIT = "a" * 40
PLATFORM_SUFFIXES = {"macOS": "macOS-arm64", "Windows": "Windows-x64"}


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"psyml_{name}", TOOLS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def fixture_dir(request):
    directory = FIXTURE_ROOT / request.node.name
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
            f"{app}/MacOS/PsyML Toolkit": b"binary\n",
            f"{app}/Resources/core/psyml-core": b"core\n",
            f"{app}/Resources/core/_internal/runtime.txt": b"runtime\n",
        })
    else:
        members.update({
            f"{root}/PsyML Toolkit.exe": b"binary\n",
            f"{root}/core/psyml-core.exe": b"core\n",
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
