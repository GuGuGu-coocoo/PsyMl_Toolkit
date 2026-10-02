"""Fail-closed checks for the specifically authorized original release withdrawal."""

import copy
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("withdraw_v031", ROOT / "tools/withdraw_v031.py")
withdrawal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(withdrawal)


def original():
    return {"id": withdrawal.RELEASE_ID, "tag_name": "v0.3.1",
            "target_commitish": withdrawal.OLD_COMMIT, "draft": False,
            "immutable": False, "prerelease": False,
            "assets": [{"name": name, "id": identifier, "size": size,
                        "digest": "sha256:" + digest, "state": "uploaded"}
                       for name, (identifier, size, digest) in withdrawal.ASSETS.items()]}


@pytest.mark.parametrize("field,value", [("id", 1), ("tag_name", "v0.3.2"),
    ("target_commitish", "a" * 40), ("draft", True), ("immutable", True),
    ("immutable", None), ("prerelease", True), ("assets", [])])
def test_requires_exact_original_release(field, value):
    data = original()
    withdrawal.check_release(data, draft=False)
    data[field] = value
    with pytest.raises(SystemExit):
        withdrawal.check_release(data, draft=False)


@pytest.mark.parametrize("field,value", [("id", 1), ("size", 1), ("state", "new"),
                                       ("digest", "sha256:" + "a" * 64), ("name", "other.zip")])
def test_requires_exact_original_assets(field, value):
    data = original()
    data["assets"][0][field] = value
    with pytest.raises(SystemExit):
        withdrawal.check_release(data, draft=False)


def test_withdrawal_only_mutates_after_backup_and_remote_checks(monkeypatch, tmp_path):
    events = []
    monkeypatch.setattr(withdrawal, "check_archive", lambda directory: events.append("backup"))
    monkeypatch.setattr(withdrawal, "check_context", lambda: events.append("context"))
    state = original()

    def api(path, *args):
        assert path == f"releases/{withdrawal.RELEASE_ID}"
        if args:
            assert events == ["backup", "context", "get"]
            assert args == ("--method", "PATCH", "-F", "draft=true")
            state["draft"] = True
            events.append("patch")
        else:
            events.append("get")
        return copy.deepcopy(state)

    monkeypatch.setattr(withdrawal, "api", api)
    withdrawal.withdraw(tmp_path)
    assert events == ["backup", "context", "get", "patch", "get"]


def test_failed_backup_never_reads_or_mutates_remote(monkeypatch, tmp_path):
    monkeypatch.setattr(withdrawal, "api", lambda *args: pytest.fail("No remote action allowed"))
    with pytest.raises(FileNotFoundError):
        withdrawal.withdraw(tmp_path)
