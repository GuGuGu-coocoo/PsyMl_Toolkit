"""Tests for the GUI test runner: group configuration, markers and timeouts."""

import io
import sys

from tools import run_gui_tests as runner

MARKER = "PSYML_FAKE_OK"


def test_group_list_covers_every_headless_suite_with_unique_markers():
    assert len(runner.GROUPS) == 12
    listed = {script for _, script, _ in runner.GROUPS}
    on_disk = {
        path.name
        for path in (runner.GUI / "tests").glob("test_*.gd")
        if path.name not in {"test_paths.gd", "test_native_bundle.gd"}
    }
    assert listed == on_disk

    markers = [marker for _, _, marker in runner.GROUPS]
    assert len(set(markers)) == len(markers)
    for name, script, marker in runner.GROUPS:
        text = (runner.GUI / "tests" / script).read_text(encoding="utf-8")
        assert marker in text, name


def _run_fake(tmp_path, monkeypatch, body, *, timeout=30.0):
    script = tmp_path / "fake_godot.py"
    script.write_text(body, encoding="utf-8")
    monkeypatch.setattr(runner, "build_command", lambda godot, gd: [sys.executable, str(script)])
    group = ("fake", "test_bridge.gd", MARKER)
    stream = io.StringIO()
    result = runner.run_group("fake-godot", group, timeout, stream=stream)
    return result, stream.getvalue()


def test_success_requires_exit_zero_marker_and_no_error(tmp_path, monkeypatch):
    result, streamed = _run_fake(
        tmp_path, monkeypatch, f"print('{MARKER}')\n"
    )
    assert result.passed is True
    assert result.problems == []
    assert result.returncode == 0
    assert MARKER in result.output
    assert MARKER in streamed


def test_script_error_with_exit_zero_is_not_a_success(tmp_path, monkeypatch):
    body = "print('SCRIPT ERROR: fake')\n" f"print('{MARKER}')\n"
    result, _ = _run_fake(tmp_path, monkeypatch, body)
    assert result.passed is False
    assert any("SCRIPT ERROR" in problem for problem in result.problems)


def test_missing_completion_marker_is_not_a_success(tmp_path, monkeypatch):
    result, _ = _run_fake(tmp_path, monkeypatch, "print('no marker here')\n")
    assert result.passed is False
    assert any("missing completion marker" in problem for problem in result.problems)


def test_non_zero_exit_is_not_a_success(tmp_path, monkeypatch):
    body = "import sys\n" f"print('{MARKER}')\n" "sys.exit(3)\n"
    result, _ = _run_fake(tmp_path, monkeypatch, body)
    assert result.passed is False
    assert any("exit code 3" in problem for problem in result.problems)


def test_failure_marker_is_not_a_success_even_with_exit_zero(tmp_path, monkeypatch):
    body = "print('PSYML_FAKE_UI_FAILURE: boom')\n" f"print('{MARKER}')\n"
    result, _ = _run_fake(tmp_path, monkeypatch, body)
    assert result.passed is False
    assert any("failure marker" in problem for problem in result.problems)


def test_timeout_is_reported_instead_of_hanging(tmp_path, monkeypatch):
    result, _ = _run_fake(tmp_path, monkeypatch, "import time\ntime.sleep(30)\n", timeout=0.5)
    assert result.passed is False
    assert result.problems == ["timeout after 0.5s"]
    assert result.duration < 15.0


def test_list_groups_and_unknown_group_are_handled(capsys):
    assert runner.main(["--list-groups"]) == 0
    listed = capsys.readouterr().out
    assert "coefficients\ttest_coefficients.gd" in listed
    assert runner.main(["--group", "does-not-exist"]) == 2
    assert "Unknown group" in capsys.readouterr().err
