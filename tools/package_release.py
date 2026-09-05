"""Create the full source ZIP, including the verified Chinese PDFs.

Run after committing the release sources and building PDFs. Excludes legacy code,
private review notes, local environments, generated results and Git history.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import zipfile
from importlib.metadata import version as package_version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=ROOT)


def main() -> None:
    version = package_version("psyml-toolkit")
    if git("status", "--porcelain").strip():
        raise SystemExit("Commit release sources before packaging; working tree is not clean.")
    commit = git("rev-parse", "HEAD").decode().strip()
    source_hashes = json.loads((ROOT / "output/pdf/sources.json").read_text(encoding="utf-8"))
    for name, expected in source_hashes.items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise SystemExit(f"PDF source changed; regenerate PDFs: {name}")
    tracked = [p.decode() for p in git("ls-files", "-z").split(b"\0") if p]
    files = [p for p in tracked if not p.startswith(("legacy/", "docs/internal/"))]
    forbidden = ("/audit-", "/feedback-", "/.venv/", "/.godot/", "/__pycache__/")
    if any(any(part in "/" + p for part in forbidden) for p in files):
        raise SystemExit("Private/generated files found in release inventory")
    prefix = f"PsyML-Toolkit-v{version}/"
    destination = ROOT / "dist" / f"PsyML-Toolkit-v{version}.zip"
    destination.parent.mkdir(exist_ok=True)
    manifest = {"version": version, "commit": commit, "files": {}}
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in files:
            archive.write(ROOT / name, prefix + name)
            manifest["files"][name] = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        for name in ["README_ZH.pdf", "RESEARCHER_GUIDE_ZH.pdf"]:
            path = ROOT / "output/pdf" / name
            target = "docs/pdf/" + name
            archive.write(path, prefix + target)
            manifest["files"][target] = hashlib.sha256(path.read_bytes()).hexdigest()
        archive.writestr(prefix + "RELEASE_MANIFEST.json", json.dumps(manifest, indent=2) + "\n")
    print(destination)


if __name__ == "__main__":
    main()
