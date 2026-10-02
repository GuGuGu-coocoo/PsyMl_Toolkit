"""Prepare or publish the explicitly scoped v0.3.1 native release.

Candidate creation is read-only outside the workspace. Publishing is invoked
only by the separate publish/v0.3.1 branch, after candidate review. Existing
releases and tags are refused by default. The separately authorized replacement
mode preserves the known original release as a draft archive. Public assets stay
limited to two ZIPs.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from urllib.request import urlopen

from verify_release_artifacts import PLATFORM_SUFFIXES, ROOT, sha256_file

from psyml import __version__

VERSION = "0.3.1"
TAG = "v" + VERSION
REPOSITORY = "GuGuGu-coocoo/PsyMl_Toolkit"
ARTIFACT = "PsyML-v0.3.1-release-candidate"
WORKFLOW_PATH = ".github/workflows/release-v0.3.1.yml"
NATIVE_NAMES = tuple(f"PsyML-Toolkit-{VERSION}-{p}.zip" for p in PLATFORM_SUFFIXES.values())


def run(*args: str) -> str:
    return subprocess.check_output(list(args), cwd=ROOT, text=True).strip()


def api(path: str) -> dict | list:
    return json.loads(run("gh", "api", f"repos/{REPOSITORY}/{path}"))


def check_source() -> str:
    if __version__ != VERSION:
        raise SystemExit(f"This one-version workflow requires {VERSION}, got {__version__}")
    if run("git", "status", "--porcelain", "--untracked-files=all"):
        raise SystemExit("Release operation requires a clean source checkout")
    commit = run("git", "rev-parse", "HEAD")
    if os.environ.get("GITHUB_SHA", commit) != commit:
        raise SystemExit("Workflow commit differs from checked-out source")
    return commit


def verify(directory: Path, commit: str) -> None:
    import sys
    subprocess.run(
        [sys.executable, str(ROOT / "tools/verify_release_artifacts.py"),
         "--directory", str(directory), "--platform", "all", "--version", VERSION,
         "--commit", commit], cwd=ROOT, check=True,
    )


def candidate(directory: Path, commit: str) -> None:
    names = NATIVE_NAMES
    manifest = {name: sha256_file(directory / name) for name in names}
    (directory / "SHA256SUMS").write_text(
        "".join(f"{digest}  {name}\n" for name, digest in sorted(manifest.items())),
        encoding="utf-8",
    )
    verify(directory, commit)
    (directory / "CANDIDATE.json").write_text(json.dumps({
        "version": VERSION,
        "commit": commit,
        "lock_sha256": sha256_file(ROOT / "uv.lock"),
        "workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
        "assets": manifest,
        "public_assets": list(NATIVE_NAMES),
    }, indent=2) + "\n", encoding="utf-8")
    print(f"PSYML_RELEASE_CANDIDATE_OK version={VERSION} commit={commit}")


def verify_downloads(directory: Path, assets: list[dict]) -> None:
    expected = set(NATIVE_NAMES)
    if len(assets) != len(expected) or {item["name"] for item in assets} != expected:
        raise SystemExit("Release must have exactly the two native application ZIPs")
    for asset in assets:
        path = directory / asset["name"]
        if asset["state"] != "uploaded" or asset["size"] != path.stat().st_size:
            raise SystemExit(f"Incomplete uploaded asset: {asset['name']}")
        if asset.get("digest") != "sha256:" + sha256_file(path):
            raise SystemExit(f"Uploaded digest differs: {asset['name']}")


def verify_candidate_document(document: dict, directory: Path, commit: str, run_id: int) -> None:
    expected_names = set(NATIVE_NAMES)
    expected_keys = {"version", "commit", "lock_sha256", "workflow_run_id", "assets", "public_assets"}
    if not isinstance(document, dict) or set(document) != expected_keys:
        raise SystemExit("Candidate manifest has unexpected fields")
    if (document["version"] != VERSION or document["commit"] != commit
            or document["lock_sha256"] != sha256_file(ROOT / "uv.lock")
            or document["workflow_run_id"] != str(run_id)
            or document["public_assets"] != list(NATIVE_NAMES)):
        raise SystemExit("Candidate provenance differs from release source or build run")
    assets = document["assets"]
    if not isinstance(assets, dict) or set(assets) != expected_names:
        raise SystemExit("Candidate manifest must describe exactly the two native ZIPs")
    for name, digest in assets.items():
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise SystemExit(f"Invalid candidate digest: {name}")
        if sha256_file(directory / name) != digest:
            raise SystemExit(f"Candidate digest differs: {name}")


def download_assets(directory: Path, assets: list[dict]) -> None:
    directory.mkdir(parents=True, exist_ok=False)
    for asset in assets:
        with (directory / asset["name"]).open("wb") as handle:
            subprocess.run(["gh", "api", "-H", "Accept: application/octet-stream",
                            f"repos/{REPOSITORY}/releases/assets/{asset['id']}"],
                           cwd=ROOT, stdout=handle, check=True)


def download_public_assets(directory: Path, assets: list[dict]) -> None:
    directory.mkdir(parents=True, exist_ok=False)
    for asset in assets:
        url = f"https://github.com/{REPOSITORY}/releases/download/{TAG}/{asset['name']}"
        if asset["browser_download_url"] != url:
            raise SystemExit("Unexpected public download URL")
        # No GitHub token is sent: the published files must be publicly readable.
        with urlopen(url, timeout=120) as response, (directory / asset["name"]).open("wb") as out:
            shutil.copyfileobj(response, out)


def require_tag(commit: str) -> None:
    if api(f"git/ref/tags/{TAG}")["object"]["sha"] != commit:
        raise SystemExit("Release tag differs from verified source commit")


def check_original_release() -> dict:
    from withdraw_v031 import OLD_COMMIT, RELEASE_ID, check_release

    require_tag(OLD_COMMIT)
    original = api(f"releases/{RELEASE_ID}")
    check_release(original, draft=True)
    archive_tag = "v0.3.1-withdrawn-2d2308e"
    if any(item["ref"] == f"refs/tags/{archive_tag}"
           for item in api(f"git/matching-refs/tags/{archive_tag}")):
        raise SystemExit("Original archive tag already exists; inspect state before retrying")
    return original


def preserve_original_and_move_tag(directory: Path, commit: str) -> None:
    from withdraw_v031 import OLD_COMMIT, RELEASE_ID, check_release

    if commit == OLD_COMMIT:
        raise SystemExit("Replacement must contain the corrected source")
    run("git", "merge-base", "--is-ancestor", OLD_COMMIT, commit)
    original = check_original_release()
    backup = directory / "original-v031"
    download_assets(backup, original["assets"])
    verify_downloads(backup, original["assets"])
    (backup / "release.json").write_text(json.dumps(original, indent=2) + "\n", encoding="utf-8")
    original = check_original_release()
    verify_downloads(backup, original["assets"])
    if api("git/ref/heads/main")["object"]["sha"] != commit:
        raise SystemExit("Main changed before the original release was archived")
    archive_tag = "v0.3.1-withdrawn-2d2308e"
    # Preserve the original tag target and every original asset. No DELETE or
    # asset-clobber operation is used anywhere in this one-time transition.
    run("gh", "api", "--method", "POST", f"repos/{REPOSITORY}/git/refs",
        "-f", f"ref=refs/tags/{archive_tag}", "-f", f"sha={OLD_COMMIT}")
    if api(f"git/ref/tags/{archive_tag}")["object"]["sha"] != OLD_COMMIT:
        raise SystemExit("Archive tag differs from original source")
    run("gh", "api", "--method", "PATCH", f"repos/{REPOSITORY}/releases/{RELEASE_ID}",
        "-f", f"tag_name={archive_tag}", "-f", f"target_commitish={OLD_COMMIT}",
        "-f", "name=PsyML Toolkit v0.3.1 — withdrawn original", "-F", "draft=true")
    archived = api(f"releases/{RELEASE_ID}")
    if archived["tag_name"] != archive_tag:
        raise SystemExit("Original release was not preserved under its archive tag")
    # Validate every immutable original identity after the tag-name change.
    check_release({**archived, "tag_name": TAG}, draft=True)
    verify_downloads(backup, archived["assets"])
    require_tag(OLD_COMMIT)
    # The new source is a descendant of the old source, so this specific ref
    # move uses force=false. It never rewrites main or removes the old commit.
    run("gh", "api", "--method", "PATCH", f"repos/{REPOSITORY}/git/refs/tags/{TAG}",
        "-f", f"sha={commit}", "-F", "force=false")
    require_tag(commit)


def publish(directory: Path, commit: str, *, replace_original: bool = False) -> None:
    if os.environ.get("GITHUB_REPOSITORY") != REPOSITORY:
        raise SystemExit("Publishing is restricted to the intended repository")
    expected_branch = "republish/v0.3.1" if replace_original else "publish/v0.3.1"
    if os.environ.get("GITHUB_REF") != "refs/heads/" + expected_branch:
        raise SystemExit("Publishing requires the separately created publish/v0.3.1 branch")
    if api("git/ref/heads/main")["object"]["sha"] != commit:
        raise SystemExit("Release candidate must equal current main")
    # Collection reads fail closed on API errors. Never interpret a generic
    # failed request as evidence that a tag or release does not exist.
    tags = api(f"git/matching-refs/tags/{TAG}")
    if replace_original:
        check_original_release()
    elif any(item["ref"] == f"refs/tags/{TAG}" for item in tags):
        raise SystemExit(f"Refusing to replace existing tag {TAG}")
    releases = json.loads(run("gh", "api", "--paginate", "--slurp",
                             f"repos/{REPOSITORY}/releases?per_page=100"))
    matching_releases = [item for page in releases for item in page if item["tag_name"] == TAG]
    if replace_original:
        from withdraw_v031 import RELEASE_ID
        if len(matching_releases) != 1 or matching_releases[0]["id"] != RELEASE_ID:
            raise SystemExit("Replacement requires exactly the known original draft")
    elif matching_releases:
        raise SystemExit(f"Refusing to replace existing release {TAG}")
    runs = api(f"actions/runs?branch=release/v0.3.1&event=push&head_sha={commit}&per_page=100")
    successful = [item for item in runs["workflow_runs"]
                  if item["head_sha"] == commit and item["path"] == WORKFLOW_PATH
                  and item["status"] == "completed" and item["conclusion"] == "success"]
    if not successful:
        raise SystemExit("No successful candidate workflow exists for this exact commit")
    run_id = successful[0]["id"]
    artifacts = api(f"actions/runs/{run_id}/artifacts")["artifacts"]
    matches = [item for item in artifacts if item["name"] == ARTIFACT and not item["expired"]]
    if len(matches) != 1:
        raise SystemExit("Expected one unexpired, successfully verified candidate artifact")
    run("gh", "run", "download", str(run_id), "--repo", REPOSITORY,
        "--name", ARTIFACT, "--dir", str(directory))
    document = json.loads((directory / "CANDIDATE.json").read_text(encoding="utf-8"))
    verify_candidate_document(document, directory, commit, run_id)
    verify(directory, commit)
    # Ordinary publication atomically creates a new ref. Only the separately
    # authorized replacement mode preserves and advances the exact original tag.
    if replace_original:
        preserve_original_and_move_tag(directory, commit)
    else:
        run("gh", "api", "--method", "POST", f"repos/{REPOSITORY}/git/refs",
            "-f", f"ref=refs/tags/{TAG}", "-f", f"sha={commit}")
    require_tag(commit)
    created = json.loads(run(
        "gh", "api", "--method", "POST", f"repos/{REPOSITORY}/releases",
        "-f", f"tag_name={TAG}", "-f", f"target_commitish={commit}",
        "-f", "name=PsyML Toolkit v0.3.1", "-F", "draft=true",
        "-F", f"body=@{ROOT / 'docs/RELEASE_NOTES_0.3.1.md'}"))
    release_id = created["id"]
    if not created["draft"] or created["tag_name"] != TAG:
        raise SystemExit("Created release has unexpected tag or publication state")
    run("gh", "release", "upload", TAG, *(str(directory / n) for n in NATIVE_NAMES),
        "--repo", REPOSITORY)
    # Drafts are retrieved by the immutable ID returned by creation, not the
    # published-release-by-tag endpoint. No overwrite/clobber flags are used.
    draft = api(f"releases/{release_id}")
    if not draft["draft"] or draft["target_commitish"] != commit or draft["tag_name"] != TAG:
        raise SystemExit("Created draft release has unexpected target or publication state")
    verify_downloads(directory, draft["assets"])
    downloaded = ROOT / "tmp/release-v031-roundtrip"
    download_assets(downloaded, draft["assets"])
    verify_downloads(downloaded, draft["assets"])
    require_tag(commit)
    if api("git/ref/heads/main")["object"]["sha"] != commit:
        raise SystemExit("Main changed during release preparation")
    refreshed = api(f"releases/{release_id}")
    if (not refreshed["draft"] or refreshed["target_commitish"] != commit
            or refreshed["tag_name"] != TAG):
        raise SystemExit("Draft changed during release preparation")
    verify_downloads(downloaded, refreshed["assets"])
    run("gh", "api", "--method", "PATCH", f"repos/{REPOSITORY}/releases/{release_id}",
        "-F", "draft=false", "-f", "make_latest=true")
    released = api(f"releases/{release_id}")
    if released["draft"] or released["prerelease"] or not released["published_at"]:
        raise SystemExit("Release did not become publicly published")
    require_tag(commit)
    verify_downloads(downloaded, released["assets"])
    public_download = ROOT / "tmp/release-v031-public"
    download_public_assets(public_download, released["assets"])
    verify_downloads(public_download, released["assets"])
    if replace_original:
        from withdraw_v031 import RELEASE_ID, check_release
        archived = api(f"releases/{RELEASE_ID}")
        if archived["tag_name"] != "v0.3.1-withdrawn-2d2308e":
            raise SystemExit("Original archive changed during replacement")
        check_release({**archived, "tag_name": TAG}, draft=True)
        verify_downloads(directory / "original-v031", archived["assets"])
    print(f"PSYML_RELEASE_PUBLISHED {released['html_url']} commit={commit}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["candidate", "publish", "replace"])
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    directory = args.directory.resolve()
    commit = check_source()
    if args.mode == "candidate":
        candidate(directory, commit)
    else:
        publish(directory, commit, replace_original=args.mode == "replace")


if __name__ == "__main__":
    main()
