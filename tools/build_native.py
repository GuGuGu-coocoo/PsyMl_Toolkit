"""Build a self-contained desktop app on its target OS; never publish a release."""

import argparse
import contextlib
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from psyml import __version__ as CORE_VERSION

ROOT = Path(__file__).absolute().parents[1]

# gui/export_presets.cfg keeps these tokens instead of version numbers: the
# numeric fields Godot writes into the macOS bundle and the Windows executable
# are generated from CORE_VERSION for the duration of one export and the
# original file is restored afterwards.
MACOS_VERSION_TOKEN = "@PSYML_MACOS_VERSION@"
WINDOWS_VERSION_TOKEN = "@PSYML_WINDOWS_VERSION@"
EXPORT_PRESETS = Path("gui") / "export_presets.cfg"


def default_label() -> str:
    """The default build label is the single maintained core version."""
    return CORE_VERSION


def is_development_version(version: str) -> bool:
    """PEP 440-style development release, for example ``0.3.0.dev0``."""
    return ".dev" in version


def export_version_fields(version: str = CORE_VERSION) -> dict:
    """Numeric GUI export versions derived from the single core version.

    The macOS bundle takes ``X.Y.Z`` (bounded to three components by the
    plist format) and the Windows executable takes four numeric components, so
    the development release ``0.3.0.dev0`` becomes ``0.3.0`` / ``0.3.0.0``.
    The ``dev`` suffix stays in the GUI label and in BUILD.json only.
    """
    match = re.match(r"^(\d+(?:\.\d+)*)", version.strip())
    if match is None:
        raise ValueError(f"cannot derive numeric export versions from {version!r}")
    release = [int(part) for part in match.group(1).split(".")]
    mac = ".".join(str(part) for part in release[:3])
    windows_parts = release[:4] + [0] * max(0, 4 - len(release))
    windows = ".".join(str(part) for part in windows_parts)
    return {MACOS_VERSION_TOKEN: mac, WINDOWS_VERSION_TOKEN: windows}


def render_export_presets(version: str, template: str) -> str:
    """Replace the version tokens of one export preset document."""
    rendered = template
    for token, value in export_version_fields(version).items():
        if token not in rendered:
            raise ValueError(f"export presets template is missing {token}")
        rendered = rendered.replace(token, value)
    return rendered


@contextlib.contextmanager
def prepared_export_presets(version: str = CORE_VERSION, path=None):
    """Generate export preset versions for one export, then restore the file.

    The tracked configuration stays token-based and is restored in ``finally``,
    so neither a successful export nor a failure leaves a modified GUI file.
    """
    target = Path(path) if path is not None else ROOT / EXPORT_PRESETS
    original = target.read_text(encoding="utf-8")
    target.write_text(render_export_presets(version, original), encoding="utf-8")
    try:
        yield target
    finally:
        target.write_text(original, encoding="utf-8")


def export_gui(godot: str, platform_name: str, output: Path) -> None:
    """Export one GUI preset with versions generated from the core constant."""
    with prepared_export_presets():
        run(godot, "--headless", "--path", ROOT / "gui", "--export-release",
            platform_name, output)


def run(*args):
    subprocess.run([str(arg) for arg in args], cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--godot", default="godot")
    parser.add_argument("--reuse-core", action="store_true",
                        help="Local GUI-only rebuild using the existing frozen runtime")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist",
                        help="Directory that receives the package (default: dist/)")
    parser.add_argument("--label", default=default_label(),
                        help="Build label for the package name and BUILD.json; "
                             "defaults to the single core version")
    parser.add_argument("--permutation-smoke", action="store_true",
                        help="Run bundled-core permutation classification/regression smoke")
    parser.add_argument("--explain-smoke", action="store_true",
                        help="Run bundled-core single-sample explanation classification/regression smoke")
    parser.add_argument("--coefficients-smoke", action="store_true",
                        help="Run bundled-core fitted-coefficient classification/regression smoke")
    args = parser.parse_args()
    if not args.output_dir.is_absolute():
        args.output_dir = ROOT / args.output_dir
    source_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    source_changes = subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=ROOT, text=True).splitlines()
    candidate = os.environ.get("GODOT", args.godot) if args.godot == "godot" else args.godot
    args.godot = str(Path(shutil.which(candidate) or candidate).resolve())
    run(args.godot, "--version")
    mac = sys.platform == "darwin"
    if not mac and sys.platform != "win32":
        raise SystemExit("Build on Apple Silicon macOS or Windows x64")
    architecture = "macOS-arm64" if mac else "Windows-x64"
    destination = args.output_dir / f"PsyML-Toolkit-{args.label}-{architecture}"
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)
    frozen = ROOT / "tmp" / "native" / "frozen"
    # Keep transitive dependency versions and bundled license files, too
    # (for example joblib, threadpoolctl, Pillow and python-dateutil).
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir",
               "--name", "psyml-core", "--distpath", str(frozen),
               "--workpath", str(ROOT / "tmp/native/build"),
               "--specpath", str(ROOT / "tmp/native"), "--paths", str(ROOT / "src"),
               "--collect-submodules", "psyml", "--collect-data", "psyml",
               "--recursive-copy-metadata", "psyml-toolkit",
               "--collect-all", "pyreadstat", "--collect-all", "numba",
               "--collect-all", "llvmlite", "--collect-all", "shap",
               "--hidden-import", "openpyxl",
               "--hidden-import", "xlrd", "--hidden-import", "pyarrow.parquet"]
    for package in ["psyml-toolkit", "numpy", "pandas", "matplotlib", "scikit-learn",
                    "scipy", "pyarrow", "pyreadstat", "openpyxl", "xlrd",
                    "shap", "numba", "llvmlite", "slicer", "tqdm"]:
        command.extend(["--copy-metadata", package])
    command.append(str(ROOT / "tools/frozen_core.py"))
    if not args.reuse_core:
        run(*command)
    run(args.godot, "--headless", "--editor", "--path", ROOT / "gui", "--quit")
    if mac:
        app = destination / "PsyML Toolkit.app"
        export_gui(args.godot, "macOS", app)
        binary_dir = app / "Contents/MacOS"
    else:
        binary_dir = destination
        export_gui(args.godot, "Windows", destination / "PsyML Toolkit.exe")
    resource_dir = app / "Contents/Resources" if mac else binary_dir
    shutil.copytree(frozen / "psyml-core", resource_dir / "core", dirs_exist_ok=True)
    shutil.copytree(ROOT / "examples/synthetic", destination / "examples/synthetic",
                    dirs_exist_ok=True)
    if mac:
        shutil.copytree(ROOT / "examples/synthetic", resource_dir / "examples/synthetic",
                        dirs_exist_ok=True)
    shutil.copytree(ROOT / "examples/quickstart", destination / "examples/quickstart",
                    dirs_exist_ok=True)
    if mac:
        shutil.copytree(ROOT / "examples/quickstart", resource_dir / "examples/quickstart",
                        dirs_exist_ok=True)
    shutil.copy2(ROOT / "LICENSE", destination / "LICENSE")
    shutil.copy2(ROOT / "tools/NATIVE_START_HERE.txt", destination / "START_HERE.txt")
    shutil.copytree(ROOT / "tools/licenses", destination / "licenses", dirs_exist_ok=True)
    (destination / "BUILD.json").write_text(json.dumps({
        "version": CORE_VERSION, "label": args.label,
        "development_label": is_development_version(CORE_VERSION) or args.label != CORE_VERSION,
        "published": False,
        "platform": architecture,
        "python": platform.python_version(),
        "commit": source_commit,
        "working_tree_modified": bool(source_changes),
        "source_changes": source_changes,
        "post_build_changes": subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=ROOT, text=True).splitlines(),
    }, indent=2), encoding="utf-8")
    if mac:
        run("codesign", "--force", "--deep", "--sign", "-", app)
        run("codesign", "--verify", "--deep", "--strict", app)
    core = resource_dir / "core" / ("psyml-core" if mac else "psyml-core.exe")
    # Clear development configuration: this must run with the embedded interpreter.
    environment = dict(os.environ)
    for key in ["PYTHONPATH", "PYTHONHOME", "PSYML_PYTHON"]:
        environment.pop(key, None)
    smoke = subprocess.run([str(core), "import-config", "--config",
                            str(destination / "examples/synthetic/classification_config.json")],
                           cwd=destination, env=environment, check=True, capture_output=True,
                           text=True, timeout=300)
    assert json.loads(smoke.stdout)["needs_data"] is False
    executable = next(path for path in binary_dir.iterdir()
                      if path.is_file() and (path.suffix == ".exe" if not mac
                                             else os.access(path, os.X_OK)))
    report_path = ROOT / "tmp/native/smoke-report.txt"
    report_path.unlink(missing_ok=True)
    environment["PSYML_SMOKE_REPORT"] = str(report_path)
    gui_smoke = subprocess.run(
        [str(executable), "--headless", "--verbose", "--", "--psyml-smoke-test"], cwd=destination,
        env=environment, check=True, capture_output=True, text=True, timeout=420)
    if not report_path.exists() or report_path.read_text() != "PSYML_NATIVE_BUNDLE_OK":
        raise RuntimeError(gui_smoke.stdout + gui_smoke.stderr)
    (destination / "SMOKE_TEST.txt").write_text(report_path.read_text(), encoding="utf-8")
    print(gui_smoke.stdout)
    if args.permutation_smoke:
        schema = subprocess.run(
            [str(core), "schema", "analysis_config"], cwd=destination, env=environment,
            check=True, capture_output=True, text=True, timeout=120)
        assert "permutation_importance" in schema.stdout and "permutation_repeats" in schema.stdout
        quickstart = destination / "examples/quickstart"
        for task in ["classification", "regression"]:
            run_dir = quickstart / f"results/quickstart_{task}_permutation"
            shutil.rmtree(run_dir, ignore_errors=True)
            subprocess.run(
                [str(core), "run", "--config", f"{task}_permutation_config.json"],
                cwd=quickstart, env=environment, check=True, capture_output=True,
                text=True, timeout=600)
            interpretation = run_dir / "interpretations/group_k_fold"
            for name in ["permutation_raw.csv", "permutation_folds.csv",
                         "permutation_summary.csv", "permutation.json",
                         "permutation_importance.png"]:
                if not (interpretation / name).is_file():
                    raise RuntimeError(f"missing bundled-core permutation artefact: {name}")
        print("PSYML_PERMUTATION_BUNDLE_OK")
    if args.explain_smoke:
        quickstart = destination / "examples/quickstart"
        for task in ["classification", "regression"]:
            run_dir = quickstart / f"results/quickstart_{task}"
            shutil.rmtree(run_dir, ignore_errors=True)
            subprocess.run(
                [str(core), "run", "--config", f"{task}_config.json"],
                cwd=quickstart, env=environment, check=True, capture_output=True,
                text=True, timeout=600)
            models = sorted((run_dir / "model").glob("best_*.joblib"))
            if len(models) != 1:
                raise RuntimeError(f"expected one saved {task} model, found {models}")
            data = quickstart / f"{task}_predict.csv"
            out = quickstart / f"results/quickstart_{task}_explain"
            shutil.rmtree(out, ignore_errors=True)
            arguments = [str(core), "explain", "--model", str(models[0]),
                         "--input", str(data), "--background", str(data),
                         "--row", "1", "--background-size", "20", "--cycles", "3",
                         "--trust-model", "--output-dir", str(out)]
            if task == "classification":
                arguments.extend(["--class-index", "0"])
            subprocess.run(arguments, cwd=quickstart, env=environment, check=True,
                           capture_output=True, text=True, timeout=600)
            for name in ["shap_explanation.json", "shap_contributions.csv",
                         "shap_waterfall.png", "shap_explanation_notes.md"]:
                if not (out / name).is_file():
                    raise RuntimeError(f"missing bundled-core explanation artefact: {name}")
            explanation = json.loads((out / "shap_explanation.json").read_text(encoding="utf-8"))
            if explanation["reconstruction_abs_error"] > 1e-6:
                raise RuntimeError("bundled-core explanation reconstruction failed")
        print("PSYML_EXPLANATION_BUNDLE_OK")
    if args.coefficients_smoke:
        quickstart = destination / "examples/quickstart"
        expected = {
            "classification": "logistic_regression",
            "regression": "ridge",
        }
        for task in ["classification", "regression"]:
            run_dir = quickstart / f"results/quickstart_{task}_coefficients"
            shutil.rmtree(run_dir, ignore_errors=True)
            subprocess.run(
                [str(core), "run", "--config", f"{task}_coefficients_config.json"],
                cwd=quickstart, env=environment, check=True, capture_output=True,
                text=True, timeout=600)
            models = sorted((run_dir / "model").glob("best_*.joblib"))
            if len(models) != 1:
                raise RuntimeError(f"expected one saved {task} model, found {models}")
            if expected[task] not in models[0].name:
                raise RuntimeError(f"unexpected {task} coefficient model: {models[0].name}")
            data = quickstart / f"{task}_predict.csv"
            out = run_dir / "coefficient_export"
            report = run_dir / "coefficients"
            if not (report / "coefficients.json").is_file():
                raise RuntimeError("runner did not write final-model coefficients")
            document = json.loads((report / "coefficients.json").read_text(encoding="utf-8"))
            if document.get("status") != "available" or not document["verification"]["verified"]:
                raise RuntimeError("runner coefficient reconstruction failed")
            exported = subprocess.run(
                [str(core), "coefficients", "--model", str(models[0]), "--input", str(data),
                 "--trust-model", "--output-dir", str(out)],
                cwd=quickstart, env=environment, check=True, capture_output=True, text=True,
                timeout=600)
            payload = json.loads(exported.stdout.strip().splitlines()[-1])
            if not payload["coefficients"]["verification"]["verified"]:
                raise RuntimeError("bundled-core coefficient reconstruction failed")
            for name in ["coefficients.csv", "coefficients.json", "coefficients_notes.md"]:
                if not (out / name).is_file():
                    raise RuntimeError(f"missing bundled-core coefficient artefact: {name}")
        print("PSYML_COEFFICIENTS_BUNDLE_OK")
    archive = Path(str(destination) + ".zip")
    if mac:
        run("ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", destination, archive)
    else:
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
            for file in destination.rglob("*"):
                if file.is_file():
                    output.write(file, file.relative_to(destination.parent))
    archive.with_suffix(".zip.sha256").write_text(
        hashlib.sha256(archive.read_bytes()).hexdigest() + "  " + archive.name + "\n")
    print(archive)


if __name__ == "__main__":
    main()
