"""FR-017: one maintained version constant and the metadata derived from it."""

import importlib.metadata
import importlib.util
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import psyml

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 fallback
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
CORE_MODULE = ROOT / "src" / "psyml" / "__init__.py"
MAINTAINED_VERSION = "0.3.0"
# The development label stays covered even though the source is now a final
# release: the conversion helpers must keep working for the next dev cycle.
DEVELOPMENT_EXAMPLE = "0.3.0.dev0"
MACOS_RELEASE = "0.3.0"
WINDOWS_RELEASE = "0.3.0.0"


def _pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def _load_build_native():
    spec = importlib.util.spec_from_file_location(
        "psyml_build_native", ROOT / "tools" / "build_native.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _export_presets_template() -> str:
    return (ROOT / "gui" / "export_presets.cfg").read_text(encoding="utf-8")


def _temporary_gui_project(name: str) -> Path:
    """A disposable project tree with the tracked export presets copied into it."""
    project = ROOT / "tmp" / "phase-E-round2" / "test_version" / name
    if project.exists():
        shutil.rmtree(project)
    (project / "gui").mkdir(parents=True)
    (project / "gui" / "export_presets.cfg").write_text(
        _export_presets_template(), encoding="utf-8"
    )
    return project


def test_single_maintained_version_constant():
    assignments = re.findall(
        r'^__version__\s*=\s*"([^"]+)"\s*$',
        CORE_MODULE.read_text(encoding="utf-8"),
        flags=re.MULTILINE,
    )
    assert assignments == [MAINTAINED_VERSION]
    assert psyml.__version__ == MAINTAINED_VERSION
    assert re.fullmatch(r"\d+(?:\.\d+)+", MAINTAINED_VERSION)
    # Dev-version parsing/formatting stays covered for the next development cycle.
    assert re.fullmatch(r"\d+(?:\.\d+)+\.dev\d+", DEVELOPMENT_EXAMPLE)


def test_pyproject_declares_the_dynamic_version_from_the_core_module():
    pyproject = _pyproject()
    assert "version" not in pyproject["project"]
    assert pyproject["project"]["dynamic"] == ["version"]
    assert pyproject["build-system"]["build-backend"] == "hatchling.build"
    assert pyproject["tool"]["hatch"]["version"]["path"] == "src/psyml/__init__.py"


def test_installed_metadata_matches_the_core_constant():
    # Real evidence of what the build backend produced: the synced development
    # environment installs this project, so importlib.metadata reads the
    # version hatch resolved from the core module. This is the same metadata
    # tests/smoke_test.py, model save files and research reports consume, so a
    # stale dist-info fails here instead of hiding behind a regex copy.
    distribution = importlib.metadata.distribution("psyml-toolkit")
    assert distribution.version == psyml.__version__ == MAINTAINED_VERSION
    metadata = distribution.read_text("METADATA") or ""
    assert f"Version: {MAINTAINED_VERSION}" in metadata
    direct_url = distribution.read_text("direct_url.json") or ""
    if '"dir_info"' in direct_url:
        assert json.loads(direct_url)["dir_info"]["editable"] is True


def test_locked_environment_has_no_stale_project_version():
    lock_text = (ROOT / "uv.lock").read_text(encoding="utf-8")
    assert "0.2.0" not in lock_text
    assert DEVELOPMENT_EXAMPLE not in lock_text
    packages = [
        package
        for package in tomllib.loads(lock_text)["package"]
        if package["name"] == "psyml-toolkit"
    ]
    assert len(packages) == 1
    assert packages[0].get("version", MAINTAINED_VERSION) == MAINTAINED_VERSION


def test_build_native_derives_defaults_from_the_core_constant():
    module = _load_build_native()
    assert module.CORE_VERSION == MAINTAINED_VERSION
    assert module.default_label() == MAINTAINED_VERSION
    assert not module.is_development_version(MAINTAINED_VERSION)
    assert module.is_development_version(DEVELOPMENT_EXAMPLE)


def test_build_native_derives_native_export_versions_from_the_core_constant():
    module = _load_build_native()
    fields = module.export_version_fields()
    assert fields == {
        module.MACOS_VERSION_TOKEN: MACOS_RELEASE,
        module.WINDOWS_VERSION_TOKEN: WINDOWS_RELEASE,
    }
    assert module.export_version_fields(module.CORE_VERSION) == fields
    # A final release keeps the same numeric fields; dev stays in GUI/BUILD only.
    assert module.export_version_fields("0.3.0") == fields
    assert module.export_version_fields(DEVELOPMENT_EXAMPLE) == fields
    for unusable in ["", "dev", "v0.3.0", "unreleased"]:
        with pytest.raises(ValueError):
            module.export_version_fields(unusable)


def test_gui_export_presets_carry_placeholders_not_version_numbers():
    text = _export_presets_template()
    for key in ["application/short_version", "application/version"]:
        assert f'{key}="@PSYML_MACOS_VERSION@"' in text
    for key in ["application/file_version", "application/product_version"]:
        assert f'{key}="@PSYML_WINDOWS_VERSION@"' in text
    assert "0.2.0" not in text


def test_prepared_export_presets_renders_core_versions_and_restores():
    module = _load_build_native()
    target = _temporary_gui_project("prepared") / "gui" / "export_presets.cfg"
    try:
        with module.prepared_export_presets(path=target):
            rendered = target.read_text(encoding="utf-8")
        assert f'application/short_version="{MACOS_RELEASE}"' in rendered
        assert f'application/version="{MACOS_RELEASE}"' in rendered
        assert f'application/file_version="{WINDOWS_RELEASE}"' in rendered
        assert f'application/product_version="{WINDOWS_RELEASE}"' in rendered
        assert target.read_text(encoding="utf-8") == _export_presets_template()
        with pytest.raises(RuntimeError), module.prepared_export_presets(path=target):
            raise RuntimeError("export failed")
        assert target.read_text(encoding="utf-8") == _export_presets_template()
    finally:
        shutil.rmtree(target.parent.parent)


def test_export_gui_generates_presets_for_the_mocked_export_and_restores():
    module = _load_build_native()
    project = _temporary_gui_project("export-gui")
    original_root = module.ROOT
    observed = {}
    try:
        def recording_run(*args):
            observed["command"] = [str(arg) for arg in args]
            observed["presets"] = (
                project / "gui" / "export_presets.cfg"
            ).read_text(encoding="utf-8")

        module.ROOT = project
        module.run = recording_run
        output = project / "out" / "PsyML Toolkit.app"
        module.export_gui("/usr/bin/godot", "macOS", output)
        assert f'application/short_version="{MACOS_RELEASE}"' in observed["presets"]
        assert f'application/file_version="{WINDOWS_RELEASE}"' in observed["presets"]
        assert observed["command"] == [
            "/usr/bin/godot", "--headless", "--path", str(project / "gui"),
            "--export-release", "macOS", str(output),
        ]
        presets = project / "gui" / "export_presets.cfg"
        assert presets.read_text(encoding="utf-8") == _export_presets_template()

        def failing_run(*args):
            raise subprocess.CalledProcessError(1, args)

        module.run = failing_run
        with pytest.raises(subprocess.CalledProcessError):
            module.export_gui("/usr/bin/godot", "Windows", project / "PsyML Toolkit.exe")
        assert presets.read_text(encoding="utf-8") == _export_presets_template()
    finally:
        module.ROOT = original_root
        shutil.rmtree(project)


def test_tracked_version_sources_do_not_hardcode_the_old_release():
    offenders = [
        path.relative_to(ROOT).as_posix()
        for path in sorted((ROOT / "src").rglob("*.py"))
        if "0.2.0" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []
    for relative in [
        "pyproject.toml",
        "tools/build_native.py",
        "tools/NATIVE_START_HERE.txt",
        "gui/export_presets.cfg",
    ]:
        assert "0.2.0" not in (ROOT / relative).read_text(encoding="utf-8")


def test_metadata_and_persistence_use_the_distribution_version():
    for relative in ["src/psyml/models/persistence.py", "src/psyml/reporting/research.py"]:
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "from importlib.metadata import" in text
        assert "psyml-toolkit" in text
