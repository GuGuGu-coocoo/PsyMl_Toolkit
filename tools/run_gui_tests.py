"""Run the headless Godot GUI test groups with timeouts and completion markers.

A group passes only when the Godot process exits with 0, prints its expected
completion marker and logs no ``SCRIPT ERROR`` or test failure marker. Exit
codes alone are not enough: Godot can print script errors and still exit 0.
Raw output is streamed so CI keeps the diagnostics for failures.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUI = ROOT / "gui"
DEFAULT_TIMEOUT = 600.0
DEFAULT_LOG_DIR = ROOT / "tmp" / "ci-gui"

Group = tuple[str, str, str]

# (group name, script under gui/tests, completion marker)
GROUPS: tuple[Group, ...] = (
    ("bridge", "test_bridge.gd", "PSYML_GODOT_BRIDGE_OK"),
    ("ui_flow", "test_ui_flow.gd", "PSYML_GODOT_UI_FLOW_OK"),
    ("feedback", "test_feedback.gd", "PSYML_FEEDBACK_OK"),
    ("parameter_context", "test_parameter_context.gd", "PSYML_PARAMETER_CONTEXT_OK"),
    ("independent_results", "test_independent_results.gd", "PSYML_INDEPENDENT_RESULTS_OK"),
    ("config_import", "test_config_import.gd", "PSYML_CONFIG_IMPORT_OK"),
    ("prediction", "test_prediction.gd", "PSYML_PREDICTION_UI_OK"),
    ("permutation", "test_permutation.gd", "PSYML_PERMUTATION_OK"),
    ("data_check", "test_data_check.gd", "PSYML_DATA_CHECK_OK"),
    ("interpretation", "test_interpretation_results.gd", "PSYML_INTERPRETATION_OK"),
    ("explanation", "test_explanation.gd", "PSYML_EXPLANATION_UI_OK"),
    ("coefficients", "test_coefficients.gd", "PSYML_COEFFICIENTS_UI_OK"),
)


@dataclass
class GodotChoice:
    path: Path | None
    origin: str
    tried: list[str]


def resolve_executable(
    value: str,
    *,
    environ: Mapping[str, str] | None = None,
    which: Callable[[str], str | None] = shutil.which,
) -> Path | None:
    """Resolve a Godot path or command name to the real executable file.

    ``shutil.which`` only expands ``PATHEXT`` suffixes on Windows, so it misses
    the extensionless ``godot`` link that setup-godot creates there; the exact
    name is also checked in every PATH directory. Links are resolved to the file
    they point at, so the Windows link ends up as the real ``.exe``.
    """
    name = value.strip().strip('"')
    if not name:
        return None
    candidate = Path(os.path.expandvars(os.path.expanduser(name)))
    if candidate.is_file():
        return candidate.resolve()
    found = which(name)
    if found and Path(found).is_file():
        return Path(found).resolve()
    if os.path.dirname(name):
        return None
    path_value = (environ if environ is not None else os.environ).get("PATH", "")
    for directory in path_value.split(os.pathsep):
        if not directory:
            continue
        entry = Path(directory) / name
        # On Windows any existing file is executable; elsewhere require +x.
        if entry.is_file() and (os.name == "nt" or os.access(entry, os.X_OK)):
            return entry.resolve()
    return None


def select_godot(
    explicit: str | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    which: Callable[[str], str | None] = shutil.which,
) -> GodotChoice:
    """Pick the Godot executable: --godot, then GODOT/GODOT4, then PATH."""
    env = environ if environ is not None else os.environ
    if explicit:
        tried = [f"--godot={explicit}"]
        resolved = resolve_executable(explicit, environ=env, which=which)
        return GodotChoice(resolved, "--godot", tried)
    tried: list[str] = []
    for variable in ("GODOT", "GODOT4"):
        value = env.get(variable, "").strip()
        if not value:
            continue
        tried.append(f"{variable}={value}")
        resolved = resolve_executable(value, environ=env, which=which)
        if resolved is not None:
            return GodotChoice(resolved, variable, tried)
    tried.append("PATH command 'godot'")
    resolved = resolve_executable("godot", environ=env, which=which)
    return GodotChoice(resolved, "PATH", tried)


def missing_godot_message(tried: list[str]) -> str:
    return (
        "Godot executable not found (tried: " + ", ".join(tried) + "); "
        "pass --godot <path-or-command> or set GODOT to a Godot 4.7.2 executable"
    )


@dataclass
class GroupResult:
    name: str
    passed: bool
    duration: float
    returncode: int | None
    problems: list[str] = field(default_factory=list)
    output: str = ""


def build_command(godot: str, script: str) -> list[str]:
    return [godot, "--headless", "--path", str(GUI), "--script", f"res://tests/{script}"]


def evaluate_group(returncode: int, output: str, marker: str) -> list[str]:
    """Return the reasons a group must not be treated as successful."""
    problems: list[str] = []
    if returncode != 0:
        problems.append(f"exit code {returncode}")
    if marker not in output:
        problems.append(f"missing completion marker {marker}")
    if "SCRIPT ERROR" in output:
        problems.append("SCRIPT ERROR in Godot output")
    for line in output.splitlines():
        if "_FAILURE" in line:
            problems.append(f"failure marker: {line.strip()[:160]}")
            break
    return problems


def build_validate_command(godot: str) -> list[str]:
    return [godot, "--headless", "--editor", "--path", str(GUI), "--quit"]


def evaluate_validate(returncode: int, output: str) -> list[str]:
    """Return the reasons an editor validation run must not be trusted."""
    problems: list[str] = []
    if returncode != 0:
        problems.append(f"exit code {returncode}")
    if "Godot Engine v" not in output:
        problems.append("missing Godot version banner in output")
    if "SCRIPT ERROR" in output:
        problems.append("SCRIPT ERROR in Godot output")
    for line in output.splitlines():
        if "_FAILURE" in line:
            problems.append(f"failure marker: {line.strip()[:160]}")
            break
    return problems


def validate_project(
    godot: str,
    timeout: float,
    *,
    run=subprocess.run,
    stream=sys.stdout,
) -> int:
    """Load the project with the resolved executable and wait for it to exit."""
    command = build_validate_command(godot)
    print("$ " + " ".join(command))
    started = time.monotonic()
    try:
        completed = run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as error:
        output = _text(error.stdout) + _text(error.stderr)
        _stream_output(stream, output)
        print(f"PSYML_GODOT_VALIDATE_FAILED problems=timeout after {timeout:g}s", file=sys.stderr)
        return 1
    output = _text(completed.stdout) + _text(completed.stderr)
    _stream_output(stream, output)
    problems = evaluate_validate(completed.returncode, output)
    if problems:
        print("PSYML_GODOT_VALIDATE_FAILED problems=" + "; ".join(problems), file=sys.stderr)
        return 1
    print(f"PSYML_GODOT_VALIDATE_OK ({time.monotonic() - started:.1f}s)")
    return 0


def _text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def run_group(
    godot: str,
    group: Group,
    timeout: float,
    *,
    run=subprocess.run,
    stream=sys.stdout,
) -> GroupResult:
    name, script, marker = group
    started = time.monotonic()
    try:
        completed = run(
            build_command(godot, script),
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as error:
        output = _text(error.stdout) + _text(error.stderr)
        _stream_output(stream, output)
        return GroupResult(
            name=name,
            passed=False,
            duration=time.monotonic() - started,
            returncode=None,
            problems=[f"timeout after {timeout:g}s"],
            output=output,
        )
    output = _text(completed.stdout) + _text(completed.stderr)
    _stream_output(stream, output)
    problems = evaluate_group(completed.returncode, output, marker)
    return GroupResult(
        name=name,
        passed=not problems,
        duration=time.monotonic() - started,
        returncode=completed.returncode,
        problems=problems,
        output=output,
    )


def _stream_output(stream, output: str) -> None:
    if not output:
        return
    stream.write(output)
    if not output.endswith("\n"):
        stream.write("\n")
    stream.flush()


def _pump_lines(source, sink: Callable[[str], None]) -> None:
    """Forward every line as it arrives; a hung child still shows progress."""
    try:
        for line in source:
            sink(line)
    finally:
        source.close()


def run_group_streaming(
    godot: str,
    group: Group,
    timeout: float,
    *,
    stream=sys.stdout,
    log_path: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> GroupResult:
    """Run one group while streaming output to the console and a log file.

    The capture-based ``run_group`` keeps an injectable runner for tests; this
    path is what ``main`` uses so a timed-out or crashing group still leaves its
    diagnostics in ``log_path`` instead of losing everything buffered in memory.
    """
    name, script, marker = group
    command = build_command(godot, script)
    env = dict(os.environ if environ is None else environ)
    log_file = None
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        env["PSYML_GUI_LOG_DIR"] = str(log_path.parent)
        log_file = log_path.open("w", encoding="utf-8", errors="replace")

    collected: list[str] = []

    def sink(text: str) -> None:
        collected.append(text)
        stream.write(text)
        stream.flush()
        if log_file is not None:
            log_file.write(text)
            log_file.flush()

    if log_file is not None:
        log_file.write("$ " + " ".join(command) + "\n")
        log_file.flush()
    started = time.monotonic()
    try:
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            env=env,
        )
    except OSError as error:
        if log_file is not None:
            log_file.write(f"failed to start: {error}\n")
            log_file.close()
        return GroupResult(
            name=name,
            passed=False,
            duration=time.monotonic() - started,
            returncode=None,
            problems=[f"could not start Godot: {error}"],
        )
    reader = threading.Thread(target=_pump_lines, args=(process.stdout, sink), daemon=True)
    reader.start()
    timed_out = False
    try:
        returncode: int | None = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        process.wait()
        returncode = None
    reader.join(timeout=30.0)
    if log_file is not None:
        log_file.close()
    output = "".join(collected)
    if timed_out:
        return GroupResult(
            name=name,
            passed=False,
            duration=time.monotonic() - started,
            returncode=None,
            problems=[f"timeout after {timeout:g}s"],
            output=output,
        )
    problems = evaluate_group(returncode, output, marker)
    return GroupResult(
        name=name,
        passed=not problems,
        duration=time.monotonic() - started,
        returncode=returncode,
        problems=problems,
        output=output,
    )


def resolve_log_dir(value: str | None) -> Path:
    if value:
        return Path(value).expanduser().absolute()
    configured = os.environ.get("PSYML_GUI_LOG_DIR", "").strip()
    if configured:
        return Path(configured).expanduser().absolute()
    return DEFAULT_LOG_DIR


def _clear_stale_logs(directory: Path) -> None:
    if not directory.is_dir():
        return
    stale = list(directory.glob("[0-9][0-9]-*.log"))
    stale.append(directory / "ui_flow_failure.txt")
    for path in stale:
        if path.is_file():
            path.unlink()


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description="Run the headless Godot GUI test groups.")
    parser.add_argument(
        "--godot",
        default=None,
        help=(
            "Godot 4.7.2 executable path or command; overrides GODOT/GODOT4 "
            "(default: GODOT, then GODOT4, then godot on PATH)"
        ),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help=f"seconds allowed per Godot run (default: {DEFAULT_TIMEOUT:g})",
    )
    parser.add_argument(
        "--group",
        action="append",
        default=[],
        metavar="NAME",
        help="run only this group (repeatable; see --list-groups)",
    )
    parser.add_argument(
        "--log-dir",
        default=None,
        help=(
            "directory for per-group logs (default: PSYML_GUI_LOG_DIR, then "
            f"{DEFAULT_LOG_DIR})"
        ),
    )
    parser.add_argument(
        "--list-groups",
        action="store_true",
        help="print the group names, scripts and markers, then exit",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="only load the Godot project with --editor --quit, then exit",
    )
    args = parser.parse_args(argv)

    if args.list_groups:
        for name, script, marker in GROUPS:
            print(f"{name}\t{script}\t{marker}")
        return 0

    requested: set[str] = set()
    if not args.validate:
        known = {name for name, _, _ in GROUPS}
        unknown = [name for name in args.group if name not in known]
        if unknown:
            print(f"Unknown group(s): {', '.join(unknown)}", file=sys.stderr)
            return 2
        requested = set(args.group)
    selected = [group for group in GROUPS if not requested or group[0] in requested]

    choice = select_godot(args.godot)
    if choice.path is None:
        print(missing_godot_message(choice.tried), file=sys.stderr)
        return 2
    godot = str(choice.path)
    print(f"Godot: {godot} (from {choice.origin})")
    if args.validate:
        print(f"Timeout: {args.timeout:g}s")
        return validate_project(godot, args.timeout)
    missing = [script for _, script, _ in selected if not (GUI / "tests" / script).is_file()]
    if missing:
        print(f"Missing GUI test script(s): {', '.join(missing)}", file=sys.stderr)
        return 2

    print(f"PSYML_PYTHON: {os.environ.get('PSYML_PYTHON', '<unset>')}")
    print(f"Timeout per group: {args.timeout:g}s")
    log_dir = resolve_log_dir(args.log_dir)
    _clear_stale_logs(log_dir)
    print(f"Per-group logs: {log_dir}")

    failures: list[GroupResult] = []
    for index, group in enumerate(selected, start=1):
        name, script, _ = group
        print(f"\n[{index}/{len(selected)}] {name}")
        print("$ " + " ".join(build_command(godot, script)))
        log_path = log_dir / f"{index:02d}-{name}.log"
        result = run_group_streaming(godot, group, args.timeout, log_path=log_path)
        status = "PASS" if result.passed else "FAIL"
        print(f"[{index}/{len(selected)}] {name}: {status} ({result.duration:.1f}s)")
        if not result.passed:
            failures.append(result)
            for problem in result.problems:
                print(f"  - {problem}")
            print(f"  log: {log_path}")
        sys.stdout.flush()

    if failures:
        summary = "; ".join(f"{result.name}: {'; '.join(result.problems)}" for result in failures)
        print(f"\nPSYML_GUI_SUITE_FAILED groups={len(failures)}/{len(selected)}")
        print(f"  {summary}")
        return 1
    print(f"\nPSYML_GUI_SUITE_OK groups={len(selected)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
