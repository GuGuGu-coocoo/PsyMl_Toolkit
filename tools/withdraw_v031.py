"""Archive and reversibly withdraw only the originally published v0.3.1."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

REPOSITORY = "GuGuGu-coocoo/PsyMl_Toolkit"
RELEASE_ID = 401742317
OLD_COMMIT = "2d2308e5fcb9e3876d3dd9ab94737e0018ea4833"
ASSETS = {
    "PsyML-Toolkit-0.3.1-macOS-arm64.zip": (
        605413663, 230458873, "cc68b7c15dd8222ef8e380624c383282be730485a009e4a830f3a54a8f9bb45f"),
    "PsyML-Toolkit-0.3.1-Windows-x64.zip": (
        605413659, 223570587, "7cdd7da52b84e0cc05a30984c8c558ba335b1478ef2b71c1388c63af7fc51fae"),
}


def api(path: str, *args: str) -> dict:
    return json.loads(subprocess.check_output(
        ["gh", "api", f"repos/{REPOSITORY}/{path}", *args], text=True))


def check_release(release: dict, *, draft: bool) -> None:
    if (release["id"] != RELEASE_ID or release["tag_name"] != "v0.3.1"
            or release["target_commitish"] != OLD_COMMIT or release["draft"] is not draft
            or release.get("immutable") is not False or release["prerelease"]):
        raise SystemExit("Original release identity or state changed; refusing withdrawal")
    assets = release["assets"]
    if len(assets) != 2 or {a["name"] for a in assets} != set(ASSETS):
        raise SystemExit("Original asset inventory changed")
    for asset in assets:
        identifier, size, digest = ASSETS[asset["name"]]
        if (asset["id"] != identifier or asset["size"] != size
                or asset["digest"] != "sha256:" + digest or asset["state"] != "uploaded"):
            raise SystemExit("Original asset provenance changed")


def check_archive(directory: Path) -> None:
    check_release(json.loads((directory / "release.json").read_text(encoding="utf-8")), draft=False)
    for name, (_, size, digest) in ASSETS.items():
        path = directory / name
        if path.stat().st_size != size:
            raise SystemExit("Archived asset size mismatch")
        with path.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != digest:
                raise SystemExit("Archived asset SHA-256 mismatch")


def check_context() -> None:
    if (os.environ.get("GITHUB_REPOSITORY") != REPOSITORY
            or os.environ.get("GITHUB_REF") != "refs/heads/withdraw/v0.3.1"):
        raise SystemExit("Withdrawal requires the intended repository and one-time branch")
    if api("git/ref/tags/v0.3.1")["object"]["sha"] != OLD_COMMIT:
        raise SystemExit("Original release tag changed")


def archive(directory: Path) -> None:
    check_context()
    release = api(f"releases/{RELEASE_ID}")
    check_release(release, draft=False)
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "release.json").write_text(json.dumps(release, indent=2) + "\n", encoding="utf-8")
    for name, (identifier, _, _) in ASSETS.items():
        with (directory / name).open("wb") as stream:
            subprocess.run(["gh", "api", "-H", "Accept: application/octet-stream",
                            f"repos/{REPOSITORY}/releases/assets/{identifier}"],
                           stdout=stream, check=True)
    check_archive(directory)
    print("PSYML_ORIGINAL_V031_ARCHIVED " + OLD_COMMIT)


def withdraw(directory: Path) -> None:
    check_archive(directory)
    check_context()
    check_release(api(f"releases/{RELEASE_ID}"), draft=False)
    result = api(f"releases/{RELEASE_ID}", "--method", "PATCH", "-F", "draft=true")
    check_release(result, draft=True)
    check_release(api(f"releases/{RELEASE_ID}"), draft=True)
    print(f"PSYML_V031_WITHDRAWN release_id={RELEASE_ID} original_commit={OLD_COMMIT}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["archive", "withdraw"])
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    {"archive": archive, "withdraw": withdraw}[args.mode](args.directory)
