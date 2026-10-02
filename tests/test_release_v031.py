"""No-network checks for the one-version release gate."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "a" * 40


@pytest.fixture()
def release(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "tools"))
    spec = importlib.util.spec_from_file_location("release_v031", ROOT / "tools/release_v031.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setenv("GITHUB_REPOSITORY", module.REPOSITORY)
    monkeypatch.setenv("GITHUB_REF", "refs/heads/publish/v0.3.1")
    return module


def test_candidate_records_source_and_exact_public_assets(release, tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_RUN_ID", "42")
    names = list(release.NATIVE_NAMES)
    for name in names:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(name.encode())
    calls = []
    monkeypatch.setattr(release, "verify", lambda *args: calls.append(args))
    release.candidate(tmp_path, COMMIT)
    recorded = json.loads((tmp_path / "CANDIDATE.json").read_text(encoding="utf-8"))
    assert calls == [(tmp_path, COMMIT)]
    assert recorded["commit"] == COMMIT
    assert recorded["version"] == "0.3.1"
    assert recorded["workflow_run_id"] == "42"
    assert recorded["public_assets"] == list(release.NATIVE_NAMES)
    assert set(recorded["assets"]) == set(names)
    assert len((tmp_path / "SHA256SUMS").read_text(encoding="utf-8").splitlines()) == 2


@pytest.mark.parametrize("name,value", [
    ("GITHUB_REPOSITORY", "someone/else"),
    ("GITHUB_REF", "refs/heads/release/v0.3.1"),
])
def test_publish_requires_explicit_repository_and_branch(release, tmp_path, monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    monkeypatch.setattr(release, "api", lambda *args: pytest.fail("No remote access expected"))
    with pytest.raises(SystemExit):
        release.publish(tmp_path, COMMIT)


def test_publish_refuses_changed_main(release, tmp_path, monkeypatch):
    monkeypatch.setattr(release, "api", lambda path: {"object": {"sha": "b" * 40}})
    with pytest.raises(SystemExit, match="current main"):
        release.publish(tmp_path, COMMIT)


def test_publish_refuses_existing_tag(release, tmp_path, monkeypatch):
    def api(path):
        if path == "git/ref/heads/main":
            return {"object": {"sha": COMMIT}}
        assert path == "git/matching-refs/tags/v0.3.1"
        return [{"ref": "refs/tags/v0.3.1"}]
    monkeypatch.setattr(release, "api", api)
    monkeypatch.setattr(release, "run", lambda *args: pytest.fail("Must not write or download"))
    with pytest.raises(SystemExit, match="existing tag"):
        release.publish(tmp_path, COMMIT)


def test_publish_refuses_existing_draft_or_release(release, tmp_path, monkeypatch):
    monkeypatch.setattr(release, "api", lambda path:
                        {"object": {"sha": COMMIT}} if path == "git/ref/heads/main" else [])
    monkeypatch.setattr(release, "run", lambda *args:
                        json.dumps([[{"tag_name": "v0.3.1", "draft": True}]]))
    with pytest.raises(SystemExit, match="existing release"):
        release.publish(tmp_path, COMMIT)


@pytest.mark.parametrize("result", [[], [{"head_sha": COMMIT, "path": "other.yml",
                                        "status": "completed", "conclusion": "success"}],
    [{"head_sha": "b" * 40, "path": ".github/workflows/release-v0.3.1.yml",
      "status": "completed", "conclusion": "success"}],
    [{"head_sha": COMMIT, "path": ".github/workflows/release-v0.3.1.yml",
      "status": "completed", "conclusion": "failure"}],
])
def test_publish_requires_successful_exact_candidate(release, tmp_path, monkeypatch, result):
    def api(path):
        if path == "git/ref/heads/main":
            return {"object": {"sha": COMMIT}}
        if path.startswith("git/matching-"):
            return []
        assert path.startswith("actions/runs?")
        return {"workflow_runs": result}
    monkeypatch.setattr(release, "api", api)
    monkeypatch.setattr(release, "run", lambda *args: "[[]]")
    with pytest.raises(SystemExit, match="No successful candidate"):
        release.publish(tmp_path, COMMIT)


@pytest.mark.parametrize("failure", [None, "missing", "extra", "size", "digest", "state"])
def test_uploaded_assets_require_exact_names_sizes_and_digests(release, tmp_path, failure):
    assets = []
    for name in release.NATIVE_NAMES:
        path = tmp_path / name
        path.write_bytes(b"release zip")
        assets.append({"name": name, "size": path.stat().st_size, "state": "uploaded",
                       "digest": "sha256:" + release.sha256_file(path)})
    if failure == "missing":
        assets.pop()
    elif failure == "extra":
        assets.append({"name": "unwanted.zip"})
    elif failure == "size":
        assets[0]["size"] += 1
    elif failure == "digest":
        assets[0]["digest"] = "sha256:" + "f" * 64
    elif failure == "state":
        assets[0]["state"] = "new"
    if failure:
        with pytest.raises(SystemExit):
            release.verify_downloads(tmp_path, assets)
    else:
        release.verify_downloads(tmp_path, assets)


def test_workflow_scopes_writes_to_publication_and_current_version():
    text = (ROOT / ".github/workflows/release-v0.3.1.yml").read_text(encoding="utf-8")
    assert "branches: [release/v0.3.1, publish/v0.3.1, republish/v0.3.1]" in text
    assert text.count("contents: write") == 1
    assert "contents: write" not in text.split("  publish:")[0]
    assert "needs: [quality, native]" in text
    assert "uses: ./.github/workflows/ci.yml" in text
    assert '"draft=false"' in (ROOT / "tools/release_v031.py").read_text(encoding="utf-8")
    for flag in ("--permutation-smoke", "--explain-smoke", "--coefficients-smoke"):
        assert flag in text
    assert "id-token:" not in text
    assert "secrets:" not in text


@pytest.mark.parametrize("failure", [None, "backup", "changed_main", "archive_tag", "archive_release"])
def test_replacement_preserves_original_before_nonforced_tag_move(
        release, tmp_path, monkeypatch, failure):
    from withdraw_v031 import ASSETS, OLD_COMMIT, RELEASE_ID

    events = []
    old = {"id": RELEASE_ID, "tag_name": "v0.3.1", "target_commitish": OLD_COMMIT,
           "draft": True, "immutable": False, "prerelease": False,
           "assets": [{"name": name, "id": identifier, "size": size,
                       "digest": "sha256:" + digest, "state": "uploaded"}
                      for name, (identifier, size, digest) in ASSETS.items()]}
    monkeypatch.setattr(release, "check_original_release", lambda: dict(old))

    def download(directory, assets):
        events.append("download_original")
        directory.mkdir()
        if failure == "backup":
            raise OSError("Download failed")

    monkeypatch.setattr(release, "download_assets", download)
    monkeypatch.setattr(release, "verify_downloads", lambda *args: events.append("verify_original"))

    def api(path):
        if path == "git/ref/heads/main":
            return {"object": {"sha": "b" * 40 if failure == "changed_main" else COMMIT}}
        if path == "git/ref/tags/v0.3.1-withdrawn-2d2308e":
            return {"object": {"sha": "b" * 40 if failure == "archive_tag" else OLD_COMMIT}}
        assert path == f"releases/{RELEASE_ID}"
        return {**old, "tag_name": "v0.3.1-withdrawn-2d2308e",
                "draft": failure != "archive_release"}

    def run(*args):
        if args[:3] == ("git", "merge-base", "--is-ancestor"):
            assert args[3:] == (OLD_COMMIT, COMMIT)
            events.append("ancestry")
        elif "POST" in args:
            assert events == ["ancestry", "download_original", "verify_original", "verify_original"]
            assert "ref=refs/tags/v0.3.1-withdrawn-2d2308e" in args
            assert f"sha={OLD_COMMIT}" in args
            events.append("archive_tag")
        elif f"repos/{release.REPOSITORY}/releases/{RELEASE_ID}" in args:
            assert "draft=true" in args
            assert "tag_name=v0.3.1-withdrawn-2d2308e" in args
            events.append("archive_release")
        else:
            assert "force=false" in args and "force=true" not in args
            assert "verify_original" == events[-2] and events[-1] == "require_old"
            events.append("move_tag")
        assert "DELETE" not in args and "--clobber" not in args
        return ""

    monkeypatch.setattr(release, "run", run)
    monkeypatch.setattr(release, "api", api)
    monkeypatch.setattr(release, "require_tag", lambda sha:
                        events.append("require_old" if sha == OLD_COMMIT else "require_new"))
    if failure:
        with pytest.raises((SystemExit, OSError)):
            release.preserve_original_and_move_tag(tmp_path, COMMIT)
        assert "move_tag" not in events
    else:
        release.preserve_original_and_move_tag(tmp_path, COMMIT)
        assert events[-2:] == ["move_tag", "require_new"]
        assert json.loads((tmp_path / "original-v031/release.json").read_text()) == old


def test_replacement_refuses_original_commit(release, tmp_path, monkeypatch):
    from withdraw_v031 import OLD_COMMIT
    monkeypatch.setattr(release, "run", lambda *args: pytest.fail("No remote action expected"))
    with pytest.raises(SystemExit, match="corrected source"):
        release.preserve_original_and_move_tag(tmp_path, OLD_COMMIT)


def test_replacement_requires_distinct_explicit_branch(release, tmp_path, monkeypatch):
    monkeypatch.setattr(release, "api", lambda *args: pytest.fail("No remote action expected"))
    with pytest.raises(SystemExit):
        release.publish(tmp_path, COMMIT, replace_original=True)


@pytest.mark.parametrize("mutation", ["extra_field", "extra_asset", "missing_asset", "path", "digest",
                                      "version", "commit", "run", "lock", "public_assets"])
def test_candidate_manifest_rejects_mismatches(release, tmp_path, monkeypatch, mutation):
    monkeypatch.setenv("GITHUB_RUN_ID", "42")
    monkeypatch.setattr(release, "verify", lambda *args: None)
    for name in list(release.NATIVE_NAMES):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"candidate")
    release.candidate(tmp_path, COMMIT)
    document = json.loads((tmp_path / "CANDIDATE.json").read_text(encoding="utf-8"))
    release.verify_candidate_document(document, tmp_path, COMMIT, 42)
    if mutation == "extra_field":
        document["unexpected"] = True
    elif mutation == "extra_asset":
        document["assets"]["extra.zip"] = "a" * 64
    elif mutation == "missing_asset":
        document["assets"].pop(release.NATIVE_NAMES[0])
    elif mutation == "path":
        document["assets"]["../../outside"] = document["assets"].pop(release.NATIVE_NAMES[0])
    elif mutation == "digest":
        document["assets"][release.NATIVE_NAMES[0]] = "f" * 64
    elif mutation == "version":
        document["version"] = "0.3.0"
    elif mutation == "commit":
        document["commit"] = "b" * 40
    elif mutation == "run":
        document["workflow_run_id"] = "99"
    elif mutation == "lock":
        document["lock_sha256"] = "b" * 64
    elif mutation == "public_assets":
        document["public_assets"].append("extra.zip")
    with pytest.raises(SystemExit):
        release.verify_candidate_document(document, tmp_path, COMMIT, 42)


@pytest.mark.parametrize("failure", [None, "download", "digest", "tag", "main", "draft"])
def test_publish_order_and_fail_closed_before_publication(release, tmp_path, monkeypatch, failure):
    import shutil

    source = tmp_path / "source"
    source.mkdir()
    (source / "uv.lock").write_text("locked")
    monkeypatch.setattr(release, "ROOT", source)
    monkeypatch.setenv("GITHUB_RUN_ID", "42")
    ready = tmp_path / "ready"
    destination = tmp_path / "downloaded"
    for name in list(release.NATIVE_NAMES):
        path = ready / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"candidate")
    events = []
    monkeypatch.setattr(release, "verify", lambda *args: events.append("verify"))
    release.candidate(ready, COMMIT)
    events.clear()
    assets = [{"id": i, "name": name, "state": "uploaded",
               "size": (ready / name).stat().st_size,
               "digest": "sha256:" + release.sha256_file(ready / name)}
              for i, name in enumerate(release.NATIVE_NAMES, 1)]

    def api(path):
        if path == "git/ref/heads/main":
            return {"object": {"sha": "b" * 40 if failure == "main" and "roundtrip" in events
                               else COMMIT}}
        if path.startswith("git/matching-"):
            return []
        if path.startswith("actions/runs?"):
            return {"workflow_runs": [{"id": 42, "head_sha": COMMIT,
                                       "path": release.WORKFLOW_PATH,
                                       "status": "completed", "conclusion": "success"}]}
        if path == "actions/runs/42/artifacts":
            return {"artifacts": [{"name": release.ARTIFACT, "expired": False}]}
        if path == "git/ref/tags/v0.3.1":
            events.append("check-tag")
            return {"object": {"sha": "b" * 40 if failure == "tag" and "roundtrip" in events
                               else COMMIT}}
        assert path == "releases/123", "Drafts must be read by immutable ID"
        events.append("get-id")
        published = "publish" in events
        return {"id": 123, "draft": not published,
                "target_commitish": "b" * 40 if failure == "draft" and "roundtrip" in events
                else COMMIT, "tag_name": release.TAG, "assets": assets, "prerelease": False,
                "published_at": "today" if published else None, "html_url": "release-url"}

    def run(*args):
        if args[:4] == ("gh", "api", "--paginate", "--slurp"):
            return "[[]]"
        if args[:3] == ("gh", "run", "download"):
            shutil.copytree(ready, destination)
            events.append("download-candidate")
        elif args[:4] == ("gh", "api", "--method", "POST"):
            if args[4].endswith("git/refs"):
                events.append("create-tag")
            else:
                events.append("create-draft")
                return json.dumps({"id": 123, "draft": True, "tag_name": release.TAG})
        elif args[:3] == ("gh", "release", "upload"):
            assert "--clobber" not in args
            events.append("upload")
        elif args[:4] == ("gh", "api", "--method", "PATCH"):
            assert args[4].endswith("releases/123")
            events.append("publish")
        else:
            pytest.fail(f"Unexpected command: {args}")
        return "{}"

    def download(directory, uploaded):
        events.append("roundtrip")
        if failure == "download":
            raise RuntimeError("download failed")
        directory.mkdir(parents=True)
        for asset in uploaded:
            shutil.copy2(ready / asset["name"], directory / asset["name"])
        if failure == "digest":
            (directory / release.NATIVE_NAMES[0]).write_bytes(b"corrupted")

    monkeypatch.setattr(release, "api", api)
    monkeypatch.setattr(release, "run", run)
    monkeypatch.setattr(release, "download_assets", download)
    def public_download(directory, uploaded):
        events.append("public-roundtrip")
        directory.mkdir(parents=True)
        for asset in uploaded:
            shutil.copy2(ready / asset["name"], directory / asset["name"])
    monkeypatch.setattr(release, "download_public_assets", public_download)
    if failure:
        with pytest.raises((SystemExit, RuntimeError)):
            release.publish(destination, COMMIT)
        assert "publish" not in events
    else:
        release.publish(destination, COMMIT)
        assert events == ["download-candidate", "verify", "create-tag", "check-tag",
                          "create-draft", "upload", "get-id", "roundtrip", "check-tag", "get-id",
                          "publish", "get-id", "check-tag", "public-roundtrip"]


def test_release_workflow_has_no_document_generation_or_pdf_gate():
    workflow = (ROOT / ".github/workflows/release-v0.3.1.yml").read_text(encoding="utf-8")
    publisher = (ROOT / "tools/release_v031.py").read_text(encoding="utf-8")
    for text in (workflow, publisher):
        for forbidden in ("build_release_pdfs", "reportlab", "v0.3.1-documents", "PDF_NAMES"):
            assert forbidden not in text
    assert "  documents:" not in workflow
