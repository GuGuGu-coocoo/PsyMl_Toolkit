"""Build a self-contained desktop app on its target OS; never publish a release."""

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).absolute().parents[1]


def run(*args):
    subprocess.run([str(arg) for arg in args], cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--godot", default="godot")
    parser.add_argument("--reuse-core", action="store_true",
                        help="Local GUI-only rebuild using the existing frozen runtime")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist",
                        help="Directory that receives the package (default: dist/)")
    parser.add_argument("--label", default="0.2.0",
                        help="Version label for the package name and BUILD.json")
    parser.add_argument("--permutation-smoke", action="store_true",
                        help="Run bundled-core permutation classification/regression smoke")
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
               "--collect-all", "pyreadstat", "--hidden-import", "openpyxl",
               "--hidden-import", "xlrd", "--hidden-import", "pyarrow.parquet"]
    for package in ["psyml-toolkit", "numpy", "pandas", "matplotlib", "scikit-learn",
                    "scipy", "pyarrow", "pyreadstat", "openpyxl", "xlrd"]:
        command.extend(["--copy-metadata", package])
    command.append(str(ROOT / "tools/frozen_core.py"))
    if not args.reuse_core:
        run(*command)
    run(args.godot, "--headless", "--editor", "--path", ROOT / "gui", "--quit")
    if mac:
        app = destination / "PsyML Toolkit.app"
        run(args.godot, "--headless", "--path", ROOT / "gui", "--export-release", "macOS", app)
        binary_dir = app / "Contents/MacOS"
    else:
        binary_dir = destination
        run(args.godot, "--headless", "--path", ROOT / "gui", "--export-release", "Windows",
            destination / "PsyML Toolkit.exe")
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
        "version": args.label, "label": args.label,
        "development_label": args.label != "0.2.0", "published": False,
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
