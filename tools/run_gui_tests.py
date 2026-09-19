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
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUI = ROOT / "gui"
DEFAULT_TIMEOUT = 600.0

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


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description="Run the headless Godot GUI test groups.")
    parser.add_argument(
        "--godot",
        default="godot",
        help="Godot 4.7.2 executable (default: godot on PATH)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help=f"seconds allowed per group (default: {DEFAULT_TIMEOUT:g})",
    )
    parser.add_argument(
        "--group",
        action="append",
        default=[],
        metavar="NAME",
        help="run only this group (repeatable; see --list-groups)",
    )
    parser.add_argument(
        "--list-groups",
        action="store_true",
        help="print the group names, scripts and markers, then exit",
    )
    args = parser.parse_args(argv)

    if args.list_groups:
        for name, script, marker in GROUPS:
            print(f"{name}\t{script}\t{marker}")
        return 0

    known = {name for name, _, _ in GROUPS}
    unknown = [name for name in args.group if name not in known]
    if unknown:
        print(f"Unknown group(s): {', '.join(unknown)}", file=sys.stderr)
        return 2
    requested = set(args.group)
    selected = [group for group in GROUPS if not requested or group[0] in requested]

    godot = shutil.which(args.godot) or args.godot
    if not Path(godot).exists():
        print(f"Godot executable not found: {args.godot}", file=sys.stderr)
        return 2
    missing = [script for _, script, _ in selected if not (GUI / "tests" / script).is_file()]
    if missing:
        print(f"Missing GUI test script(s): {', '.join(missing)}", file=sys.stderr)
        return 2

    print(f"Godot: {godot}")
    print(f"PSYML_PYTHON: {os.environ.get('PSYML_PYTHON', '<unset>')}")
    print(f"Timeout per group: {args.timeout:g}s")

    failures: list[GroupResult] = []
    for index, group in enumerate(selected, start=1):
        name, script, _ = group
        print(f"\n[{index}/{len(selected)}] {name}")
        print("$ " + " ".join(build_command(godot, script)))
        result = run_group(godot, group, args.timeout)
        status = "PASS" if result.passed else "FAIL"
        print(f"[{index}/{len(selected)}] {name}: {status} ({result.duration:.1f}s)")
        if not result.passed:
            failures.append(result)
            for problem in result.problems:
                print(f"  - {problem}")

    if failures:
        summary = "; ".join(f"{result.name}: {'; '.join(result.problems)}" for result in failures)
        print(f"\nPSYML_GUI_SUITE_FAILED groups={len(failures)}/{len(selected)}")
        print(f"  {summary}")
        return 1
    print(f"\nPSYML_GUI_SUITE_OK groups={len(selected)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
