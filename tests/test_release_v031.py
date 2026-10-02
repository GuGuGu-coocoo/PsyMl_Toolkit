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
    names = [*release.NATIVE_NAMES, *(f"docs/{n}" for n in release.PDF_NAMES)]
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
    assert len((tmp_path / "SHA256SUMS").read_text(encoding="utf-8").splitlines()) == 4


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
    assert "branches: [release/v0.3.1, publish/v0.3.1]" in text
    assert text.count("contents: write") == 1
    assert "contents: write" not in text.split("  publish:")[0]
    assert "needs: [quality, native, documents]" in text
    assert "uses: ./.github/workflows/ci.yml" in text
    assert '"draft=false"' in (ROOT / "tools/release_v031.py").read_text(encoding="utf-8")
    for flag in ("--permutation-smoke", "--explain-smoke", "--coefficients-smoke"):
        assert flag in text
    assert "id-token:" not in text
    assert "secrets:" not in text


def test_pdf_sources_use_split_chinese_readme_and_complete_guide():
    builder = (ROOT / "tools/build_release_pdfs.py").read_text(encoding="utf-8")
    assert 'readme = ROOT / "README_ZH.md"' in builder
    assert 'guide = ROOT / "docs/RESEARCHER_GUIDE_ZH.md"' in builder
    assert '.split(\'<a id="chinese"></a>\')' not in builder


@pytest.mark.parametrize("mutation", ["extra_field", "extra_asset", "missing_asset", "path", "digest",
                                      "version", "commit", "run", "lock", "public_assets"])
def test_candidate_manifest_rejects_mismatches(release, tmp_path, monkeypatch, mutation):
    monkeypatch.setenv("GITHUB_RUN_ID", "42")
    monkeypatch.setattr(release, "verify", lambda *args: None)
    for name in [*release.NATIVE_NAMES, *(f"docs/{n}" for n in release.PDF_NAMES)]:
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
    for name in [*release.NATIVE_NAMES, *(f"docs/{n}" for n in release.PDF_NAMES)]:
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


def _pdf_text_module():
    spec = importlib.util.spec_from_file_location("psyml_pdf_text", ROOT / "tools/pdf_text.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pdf_math_symbols_have_readable_font_safe_equivalents():
    module = _pdf_text_module()
    result = module.supported_glyphs("MAE = Σ |yᵢ − ŷᵢ|; R² = 1 − Σ(yᵢ − ŷᵢ)² / Σ(yᵢ − ȳ)²")
    assert "−" not in result and "ŷ" not in result
    assert result.count("y_hat") == 2 and "y_mean" in result
    assert "y<sub>i</sub> - y_hat<sub>i</sub>" in result


def test_pdf_paragraph_rejects_missing_visible_font_glyphs():
    module = _pdf_text_module()
    widths = {ord(c): 10 for c in "y_hat -012<>sub/"}
    assert module.font_safe_text("ŷ − 1", widths) == "y_hat - 1"
    with pytest.raises(ValueError, match="font lacks visible characters"):
        module.font_safe_text("missing ♞", widths)
