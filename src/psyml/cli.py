"""Command-line entry point for a reproducible PsyML experiment."""

import argparse
import json
from pathlib import Path

from psyml.config import ExperimentConfig
from psyml.runner import run_experiment


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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a leakage-safe PsyML experiment.")
    parser.add_argument("--input", required=True, type=Path, help="CSV or Excel dataset path")
    parser.add_argument("--task", required=True, choices=["classification", "regression"])
    parser.add_argument("--target", required=True, help="Target-column name")
    parser.add_argument("--model", required=True, help="Model name")
    parser.add_argument("--output", required=True, type=Path, help="Directory for result files")
    parser.add_argument("--group", help="Optional grouping column for group-aware splitting")
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--param", action="append", default=[], type=_parameter, metavar="KEY=VALUE")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = ExperimentConfig(
        task=args.task,
        target_column=args.target,
        model_name=args.model,
        input_path=args.input,
        output_dir=args.output,
        group_column=args.group,
        test_size=args.test_size,
        random_seed=args.seed,
        model_params=dict(args.param),
    )
    result = run_experiment(config)
    print(json.dumps(result.metrics, indent=2, sort_keys=True))
