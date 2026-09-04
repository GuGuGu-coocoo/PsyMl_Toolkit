"""Command-line and JSONL subprocess interface for PsyML."""

import argparse
import json
import signal
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from psyml.config import ExperimentConfig
from psyml.protocol import (
    capabilities_payload,
    error_payload,
    event_payload,
    load_config,
    preview_payload,
    schema_text,
)

COMMANDS = {"capabilities", "preview", "run", "schema"}


class CancellationRequested(Exception):
    """Raised when the local subprocess receives a cancellation signal."""


def _parameter(value: str) -> tuple[str, object]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("Parameters must use key=value syntax")
    key, raw_value = value.split("=", 1)
    if not key:
        raise argparse.ArgumentTypeError("Parameter name cannot be empty")
    try:
        return key, json.loads(raw_value)
    except json.JSONDecodeError:
        return key, raw_value


def build_legacy_parser() -> argparse.ArgumentParser:
    """Build the pre-1.0 flag parser retained for compatibility."""
    parser = argparse.ArgumentParser(description="Run a leakage-safe PsyML experiment.")
    parser.add_argument("--input", required=True, type=Path, help="Supported research dataset path")
    parser.add_argument("--task", required=True, choices=["classification", "regression"])
    parser.add_argument("--target", required=True, help="Target-column name")
    parser.add_argument("--model", required=True, help="Model name")
    parser.add_argument("--output", required=True, type=Path, help="Directory for result files")
    parser.add_argument("--group", help="Optional grouping column for group-aware splitting")
    parser.add_argument(
        "--feature", action="append", dest="feature_columns", help="Feature column (repeatable)"
    )
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--validation",
        default="holdout",
        choices=[
            "holdout",
            "k_fold",
            "stratified_k_fold",
            "group_k_fold",
            "stratified_group_k_fold",
            "leave_one_group_out",
        ],
    )
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--missing", default="median", choices=["drop", "mean", "median", "mode"])
    parser.add_argument("--scaling", default="standard", choices=["none", "standard", "minmax"])
    parser.add_argument(
        "--no-data-hash",
        action="store_false",
        dest="include_data_hash",
        help="Do not calculate a SHA-256 fingerprint for the input data",
    )
    parser.add_argument(
        "--param", action="append", default=[], type=_parameter, metavar="KEY=VALUE"
    )
    return parser


def build_parser() -> argparse.ArgumentParser:
    """Build the stable command-oriented CLI parser."""
    parser = argparse.ArgumentParser(description="PsyML local analysis interface.")
    commands = parser.add_subparsers(dest="command", required=True)

    run_parser = commands.add_parser("run", help="Run a versioned analysis configuration")
    run_parser.add_argument("--config", required=True, type=Path)
    run_parser.add_argument("--events", action="store_true", help="Emit JSONL status events")

    preview_parser = commands.add_parser("preview", help="Inspect local tabular metadata")
    preview_parser.add_argument("--input", required=True, type=Path)
    preview_parser.add_argument("--rows", type=int, default=5)
    preview_parser.add_argument("--include-sample", action="store_true")

    commands.add_parser("capabilities", help="List models, formats, and strategies")
    schema_parser = commands.add_parser("schema", help="Print a bundled JSON schema")
    schema_parser.add_argument("name", choices=["analysis_config", "event", "result"])
    return parser


def _legacy_config(args: argparse.Namespace) -> ExperimentConfig:
    return ExperimentConfig(
        task=args.task,
        target_column=args.target,
        model_name=args.model,
        input_path=args.input,
        output_dir=args.output,
        group_column=args.group,
        feature_columns=args.feature_columns,
        test_size=args.test_size,
        random_seed=args.seed,
        validation_strategy=args.validation,
        n_splits=args.folds,
        missing_strategy=args.missing,
        scaling=args.scaling,
        include_data_hash=args.include_data_hash,
        model_params=dict(args.param),
    )


def _print_json(payload: object, *, stream=None) -> None:
    print(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str),
        file=stream or sys.stdout,
        flush=True,
    )


@contextmanager
def _cancellation_handler() -> Iterator[None]:
    can_handle = (
        hasattr(signal, "SIGTERM") and threading.current_thread() is threading.main_thread()
    )
    previous = signal.getsignal(signal.SIGTERM) if can_handle else None

    def cancel(_signum, _frame):
        raise CancellationRequested("Analysis cancelled by the caller")

    if can_handle:
        signal.signal(signal.SIGTERM, cancel)
    try:
        yield
    finally:
        if can_handle:
            signal.signal(signal.SIGTERM, previous)


def _run_versioned(args: argparse.Namespace) -> int:
    try:
        config = load_config(args.config)
        if args.events:
            _print_json(event_payload("started", 0.0))
        def report_progress(details: dict) -> None:
            progress = float(details.pop("progress"))
            _print_json(event_payload("progress", progress, details=details))

        with _cancellation_handler():
            _execute(config, progress_callback=report_progress if args.events else None)
        result_path = Path(config.output_dir) / "result.json"
        if args.events:
            _print_json(event_payload("completed", 1.0, result_path=str(result_path)))
        else:
            _print_json(json.loads(result_path.read_text(encoding="utf-8")))
        return 0
    except (CancellationRequested, KeyboardInterrupt) as error:
        payload = {"code": "cancelled", "type": type(error).__name__, "message": str(error)}
        if args.events:
            _print_json(event_payload("cancelled", 0.0, error=payload))
        else:
            _print_json({"schema_version": "1.0", "error": payload}, stream=sys.stderr)
        return 130
    except Exception as error:  # noqa: BLE001 - protocol boundary must return structured errors
        payload = error_payload(error)
        if args.events:
            _print_json(event_payload("failed", 0.0, error=payload))
        else:
            _print_json({"schema_version": "1.0", "error": payload}, stream=sys.stderr)
        return 2


def _run_legacy(args: argparse.Namespace) -> int:
    config = _legacy_config(args)
    result = _execute(config)
    _print_json(result.metrics)
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run a command and return a process exit code."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments or arguments[0] not in COMMANDS:
        return _run_legacy(build_legacy_parser().parse_args(arguments))
    args = build_parser().parse_args(arguments)
    if args.command == "run":
        return _run_versioned(args)
    try:
        if args.command == "capabilities":
            _print_json(capabilities_payload())
        elif args.command == "preview":
            _print_json(
                preview_payload(args.input, rows=args.rows, include_sample=args.include_sample)
            )
        else:
            print(schema_text(args.name), end="")
        return 0
    except Exception as error:  # noqa: BLE001 - CLI boundary must return structured errors
        _print_json({"schema_version": "1.0", "error": error_payload(error)}, stream=sys.stderr)
        return 2


def entrypoint() -> None:
    """Console-script wrapper that propagates the returned status code."""
    raise SystemExit(main())


def _execute(config: ExperimentConfig, progress_callback=None):
    """Import the scientific runtime only for an actual analysis."""
    from psyml.runner import run_experiment

    return run_experiment(config, progress_callback=progress_callback)
