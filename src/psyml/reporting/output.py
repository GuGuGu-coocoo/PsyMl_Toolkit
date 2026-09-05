"""Write consistent, explicit experiment outputs."""

import json
from pathlib import Path

import pandas as pd

from psyml.config import ExperimentConfig
from psyml.protocol import config_to_dict, result_payload


def write_results(
    output_dir: Path,
    config: ExperimentConfig,
    metrics: dict[str, float],
    predictions: pd.DataFrame,
    fold_metrics: pd.DataFrame | None = None,
    metric_summary: pd.DataFrame | None = None,
    warnings: list[str] | None = None,
    confusion: pd.DataFrame | None = None,
) -> None:
    """Persist evaluation, warnings, and configuration in one output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([metrics]).to_csv(output_dir / "metrics.csv", index=False)
    predictions.to_csv(output_dir / "predictions.csv", index=False)
    if fold_metrics is not None:
        fold_metrics.to_csv(output_dir / "fold_metrics.csv", index=False)
    if metric_summary is not None:
        metric_summary.to_csv(output_dir / "metrics_summary.csv", index=False)
    if confusion is not None:
        confusion.to_csv(output_dir / "confusion_matrix.csv", index=True)
    (output_dir / "warnings.json").write_text(
        json.dumps(warnings or [], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    serialized = (
        json.dumps(
            config_to_dict(config), indent=2, ensure_ascii=False, sort_keys=True, default=str
        )
        + "\n"
    )
    (output_dir / "analysis_config.json").write_text(serialized, encoding="utf-8")
    (output_dir / "config.json").write_text(serialized, encoding="utf-8")


def write_result_summary(
    output_dir: Path,
    config: ExperimentConfig,
    metrics: dict[str, float],
    warnings: list[str],
    study_summary: dict | None = None,
) -> None:
    """Write the stable result summary after every other artefact succeeds."""
    (output_dir / ".result.json.tmp").write_text(
        json.dumps(
            result_payload(config, metrics, warnings, study_summary=study_summary),
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    (output_dir / ".result.json.tmp").replace(output_dir / "result.json")


def write_study_outputs(
    output_dir: Path,
    config: ExperimentConfig,
    leaderboard: pd.DataFrame,
    tuning_results: pd.DataFrame,
    best_parameters: dict,
) -> None:
    """Persist the complete comparison and parameter-selection evidence."""
    leaderboard.to_csv(output_dir / "model_comparison.csv", index=False)
    tuning_results.to_csv(output_dir / "parameter_search.csv", index=False)
    (output_dir / "best_parameters.json").write_text(
        json.dumps(best_parameters, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "study_config.json").write_text(
        json.dumps(
            config_to_dict(config), indent=2, ensure_ascii=False, sort_keys=True, default=str
        )
        + "\n",
        encoding="utf-8",
    )


def write_independent_outputs(
    output_dir: Path,
    config: ExperimentConfig,
    summary: pd.DataFrame,
    entries: dict,
    warnings: list[str],
    results: dict,
) -> None:
    """Write an index of peer validations, never global metrics or a winning validation."""
    from psyml.reporting.research import CONFIG_HELP

    serialized = json.dumps(config_to_dict(config), indent=2, ensure_ascii=False) + "\n"
    for name in ["analysis_config.json", "config.json", "study_config.json"]:
        (output_dir / name).write_text(serialized, encoding="utf-8")
    summary.to_csv(output_dir / "validation_summary.csv", index=False)
    (output_dir / "warnings.json").write_text(
        json.dumps(warnings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    artifacts = {
        "analysis_config": "analysis_config.json", "study_config": "study_config.json",
        "validation_summary": "validation_summary.csv", "warnings": "warnings.json",
        "reproducibility_report": "reproducibility_report.md",
        "reproducibility_report_zh": "reproducibility_report_zh.md",
        "configuration_guide": "configuration_guide.md",
    }
    for attribute, name in [
        ("leaderboard", "model_comparison.csv"), ("tuning_results", "parameter_search.csv"),
        ("selection_trace", "selection_trace.csv"),
    ]:
        frames = [getattr(result, attribute) for result in results.values()]
        if frames:
            pd.concat(frames, ignore_index=True).to_csv(output_dir / name, index=False)
            artifacts[name.removesuffix(".csv")] = name
    for validation, entry in entries.items():
        if entry["status"] == "failed":
            directory = output_dir / "validations" / validation
            directory.mkdir(parents=True, exist_ok=True)
            (directory / "error.json").write_text(
                json.dumps(entry["error"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )

    for language, title, introduction in [
        ("", "Independent validation results", (
            "No primary validation was designated. Each validation has its own complete metrics, "
            "predictions, figures, reports and fixed-parameter recipe in validations/<strategy>/. "
            "No global score or winning validation is selected. Model ranks are exploratory within "
            "each validation only. Open result.json in a successful child folder for its file index. "
            "The word 'primary' in a child report refers only to that folder's single validation, "
            "not priority over its peers. Reproduce the entire design with the root config.json and "
            "a new empty output_dir. A failed validation is recorded, not silently replaced. "
            "Reports run offline, are not guaranteed correct and require researcher review."
        )),
        ("_zh", "独立验证结果", (
            "未指定主要验证。每种验证的完整指标、预测、图形、报告和最佳参数运行配置分别保存在 "
            "validations/<策略名>/。不计算跨验证总分，也不选择获胜验证。模型排名只在每种验证内供探索使用。"
            "成功子目录的 result.json 提供其完整文件索引。子报告中的“主要验证”仅指该子目录内部的单一验证，"
            "不表示相对于其他验证更重要。复现全部设计请使用总目录的 config.json，并改用新空 output_dir。"
            "失败验证保留错误记录，不会被其他验证悄悄替代。报告离线生成，不保证绝对正确，需研究者复核。"
        )),
    ]:
        lines = [f"# {title}", "", introduction, "", "| Validation | Status | Files |", "| --- | --- | --- |"]
        for validation, entry in entries.items():
            filename = "result.json" if entry["status"] == "completed" else "error.json"
            link = f"validations/{validation}/{filename}"
            lines.append(f"| {validation} | {entry['status']} | [{filename}]({link}) |")
        lines.extend(["", "## Warnings / 警告", "", *[f"- {warning}" for warning in warnings]])
        (output_dir / f"reproducibility_report{language}.md").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )
    (output_dir / "configuration_guide.md").write_text(
        "# 配置字段 / Configuration fields\n\n"
        + "\n".join(f"- `{key}`: {value}" for key, value in CONFIG_HELP.items()) + "\n",
        encoding="utf-8",
    )
    if not results:
        return  # All-failed output must not have a successful result marker.
    payload = {
        "schema_version": "1.0", "selection_protocol": config.selection_protocol,
        "status": "completed" if len(results) == len(entries) else "completed_with_errors",
        "task": config.task, "metrics": {}, "warnings": warnings, "artifacts": artifacts,
        "evaluation_scope": "independent_validations", "primary_validation": None,
        "selection_metric": config.resolved_selection_metric(), "validation_results": entries,
    }
    temporary = output_dir / ".result.json.tmp"
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(output_dir / "result.json")
