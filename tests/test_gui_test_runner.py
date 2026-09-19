"""Tests for the GUI test runner: groups, markers, timeouts and Godot resolution."""

import io
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tools import run_gui_tests as runner

MARKER = "PSYML_FAKE_OK"
BANNER = "Godot Engine v4.7.2.stable.official.ed1daf0bf - https://godotengine.org\n"


def _fake_executable(directory: Path, name: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(0o755)
    return path


def _completed(returncode: int = 0, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess(args=["godot"], returncode=returncode,
                                       stdout=stdout, stderr=stderr)



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


def _streaming_fake(tmp_path, monkeypatch, body, **kwargs):
    script = tmp_path / "fake_godot.py"
    script.write_text(body, encoding="utf-8")
    monkeypatch.setattr(runner, "build_command", lambda godot, gd: [sys.executable, str(script)])
    group = ("fake", "test_bridge.gd", MARKER)
    stream = io.StringIO()
    log_path = tmp_path / "01-fake.log"
    result = runner.run_group_streaming(
        "fake-godot",
        group,
        kwargs.pop("timeout", 30.0),
        stream=stream,
        log_path=log_path,
        **kwargs,
    )
    return result, stream.getvalue(), log_path


def test_streaming_group_writes_log_and_exports_log_dir(tmp_path, monkeypatch):
    body = (
        "import os\n"
        "print('LOGDIR=' + os.environ.get('PSYML_GUI_LOG_DIR', 'unset'))\n"
        f"print('{MARKER}')\n"
    )
    result, streamed, log_path = _streaming_fake(tmp_path, monkeypatch, body)

    assert result.passed is True
    assert MARKER in streamed
    logged = log_path.read_text(encoding="utf-8")
    assert MARKER in logged
    assert "$ " in logged.splitlines()[0]
    assert f"LOGDIR={tmp_path}" in logged


def test_streaming_timeout_keeps_partial_diagnostics_in_log(tmp_path, monkeypatch):
    body = "import sys, time\nprint('early diagnostic', flush=True)\ntime.sleep(30)\n"
    result, _streamed, log_path = _streaming_fake(
        tmp_path, monkeypatch, body, timeout=0.5
    )

    assert result.passed is False
    assert result.problems == ["timeout after 0.5s"]
    assert result.duration < 15.0
    assert "early diagnostic" in log_path.read_text(encoding="utf-8")


def test_main_writes_per_group_logs_and_clears_stale_ones(tmp_path, monkeypatch):
    script = tmp_path / "fake_godot.py"
    script.write_text("print('PSYML_GODOT_BRIDGE_OK')\n", encoding="utf-8")
    monkeypatch.setattr(runner, "build_command", lambda godot, gd: [sys.executable, str(script)])
    monkeypatch.setenv("GODOT", sys.executable)
    stale = tmp_path / "01-bridge.log"
    stale.write_text("old run\n", encoding="utf-8")
    failure_note = tmp_path / "ui_flow_failure.txt"
    failure_note.write_text("old failure\n", encoding="utf-8")

    assert runner.main(["--group", "bridge", "--log-dir", str(tmp_path)]) == 0

    logged = stale.read_text(encoding="utf-8")
    assert "PSYML_GODOT_BRIDGE_OK" in logged
    assert "old run" not in logged
    assert not failure_note.exists()


def test_list_groups_and_unknown_group_are_handled(capsys):
    assert runner.main(["--list-groups"]) == 0
    listed = capsys.readouterr().out
    assert "coefficients\ttest_coefficients.gd" in listed
    assert runner.main(["--group", "does-not-exist"]) == 2
    assert "Unknown group" in capsys.readouterr().err


def test_explicit_godot_argument_wins_over_environment(tmp_path):
    explicit = _fake_executable(tmp_path / "Godot 4.7.2 with spaces", "Godot_v4.7.2.exe")
    environment = {"GODOT": str(tmp_path / "installer" / "godot")}

    choice = runner.select_godot(str(explicit), environ=environment, which=lambda _: None)

    assert choice.path == explicit.resolve()
    assert choice.origin == "--godot"
    assert choice.tried == [f"--godot={explicit}"]


def test_extensionless_godot_link_resolves_to_the_real_executable(tmp_path):
    install = tmp_path / "Godot 4.7.2 win64"
    target = _fake_executable(install, "Godot_v4.7.2-stable_win64.exe")
    link = install / "godot"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlinks are not available in this environment")

    choice = runner.select_godot(environ={"GODOT": str(link)}, which=lambda _: None)

    assert choice.path == target.resolve()
    assert choice.path.suffix == ".exe"
    assert choice.origin == "GODOT"
    assert choice.tried == [f"GODOT={link}"]


def test_godot4_is_used_when_godot_is_not_set(tmp_path):
    executable = _fake_executable(tmp_path / "godot4", "godot.exe")

    choice = runner.select_godot(environ={"GODOT4": str(executable)}, which=lambda _: None)

    assert choice.path == executable.resolve()
    assert choice.origin == "GODOT4"


def test_path_fallback_accepts_extensionless_command(tmp_path):
    directory = tmp_path / "bin"
    executable = _fake_executable(directory, "godot")

    # shutil.which misses the extensionless entry on Windows (PATHEXT only).
    choice = runner.select_godot(environ={"PATH": str(directory)}, which=lambda _: None)

    assert choice.path == executable.resolve()
    assert choice.origin == "PATH"
    assert choice.tried == ["PATH command 'godot'"]


@pytest.mark.skipif(os.name == "nt", reason="Windows os.access ignores the executable bit")
def test_path_fallback_rejects_non_executable_file(tmp_path):
    directory = tmp_path / "bin"
    directory.mkdir()
    (directory / "godot").write_text("not executable", encoding="utf-8")

    choice = runner.select_godot(environ={"PATH": str(directory)}, which=lambda _: None)

    assert choice.path is None


def test_missing_candidates_report_where_they_were_tried(tmp_path, capsys):
    missing = str(tmp_path / "Godot_v4.7.2-stable_win64.exe")

    assert runner.main(["--validate", "--godot", missing, "--timeout", "1"]) == 2
    stderr = capsys.readouterr().err

    assert "Godot executable not found" in stderr
    assert missing in stderr
    assert f"--godot={missing}" in stderr


def test_no_candidates_reports_all_locations():
    choice = runner.select_godot(environ={"PATH": ""}, which=lambda _: None)

    assert choice.path is None
    message = runner.missing_godot_message(choice.tried)
    assert "PATH command 'godot'" in message


def test_broken_link_is_not_accepted(tmp_path):
    link = tmp_path / "godot"
    try:
        link.symlink_to(tmp_path / "missing.exe")
    except OSError:
        pytest.skip("symlinks are not available in this environment")

    choice = runner.select_godot(str(link), environ={}, which=lambda _: None)

    assert choice.path is None


def test_validate_mode_uses_resolved_executable(tmp_path, monkeypatch, capsys):
    directory = tmp_path / "bin"
    executable = _fake_executable(directory, "godot")
    seen = {}

    def fake_validate(godot, timeout):
        seen["godot"] = godot
        seen["timeout"] = timeout
        return 0

    monkeypatch.setattr(runner, "validate_project", fake_validate)
    monkeypatch.setenv("PATH", str(directory))
    monkeypatch.delenv("GODOT", raising=False)
    monkeypatch.delenv("GODOT4", raising=False)

    assert runner.main(["--validate", "--timeout", "1"]) == 0
    assert seen == {"godot": str(executable.resolve()), "timeout": 1.0}
    assert str(executable.resolve()) in capsys.readouterr().out


def test_validate_accepts_a_real_editor_run(capsys):
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        return _completed(stdout=BANNER + "[ DONE ] first_scan_filesystem\n")

    assert runner.validate_project("godot", 30.0, run=fake_run, stream=io.StringIO()) == 0
    assert calls[0] == runner.build_validate_command("godot")
    assert "PSYML_GODOT_VALIDATE_OK" in capsys.readouterr().out


def test_validate_rejects_a_silent_stub(capsys):
    def fake_run(command, **kwargs):
        return _completed(stdout="", stderr="")

    assert runner.validate_project("godot", 30.0, run=fake_run, stream=io.StringIO()) == 1
    assert "PSYML_GODOT_VALIDATE_FAILED" in capsys.readouterr().err


def test_validate_rejects_script_error_with_exit_zero(capsys):
    def fake_run(command, **kwargs):
        return _completed(stdout=BANNER + "SCRIPT ERROR: fake\n")

    assert runner.validate_project("godot", 30.0, run=fake_run, stream=io.StringIO()) == 1
    assert "SCRIPT ERROR" in capsys.readouterr().err


def test_validate_timeout_is_not_success(capsys):
    def fake_run(command, **kwargs):
        raise subprocess.TimeoutExpired(command, 30.0)

    assert runner.validate_project("godot", 30.0, run=fake_run, stream=io.StringIO()) == 1
    assert "timeout" in capsys.readouterr().err
