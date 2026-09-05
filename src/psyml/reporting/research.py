"""Research-facing, privacy-conscious reproducibility artefacts."""

from __future__ import annotations

import hashlib
import json
import platform
from dataclasses import asdict, replace
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import pandas as pd

from psyml.config import ExperimentConfig


def _package_version(distribution: str) -> str:
    try:
        return version(distribution)
    except PackageNotFoundError:
        return "unknown"


def _sha256(config: ExperimentConfig, frame: pd.DataFrame) -> tuple[str, str] | None:
    if not config.include_data_hash:
        return None
    digest = hashlib.sha256()
    if config.input_path is not None and Path(config.input_path).is_file():
        with Path(config.input_path).open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest(), "source_file_bytes"
    digest.update(frame.to_csv(index=False, lineterminator="\n").encode("utf-8"))
    return digest.hexdigest(), "canonical_in_memory_csv"


def _loader_dependency(config: ExperimentConfig) -> tuple[str, str] | None:
    if config.input_path is None:
        return None
    suffix = Path(config.input_path).suffix.lower()
    distribution = {
        ".xlsx": "openpyxl",
        ".xls": "xlrd",
        ".sav": "pyreadstat",
        ".dta": "pyreadstat",
        ".sas7bdat": "pyreadstat",
        ".xpt": "pyreadstat",
        ".parquet": "pyarrow",
    }.get(suffix)
    if distribution is None:
        return None
    return distribution, _package_version(distribution)


def _manifest(
    config: ExperimentConfig,
    frame: pd.DataFrame,
    analyzed_rows: int,
    feature_columns: int,
) -> dict[str, Any]:
    dependencies = {
        "matplotlib": _package_version("matplotlib"),
        "numpy": _package_version("numpy"),
        "pandas": _package_version("pandas"),
        "scikit-learn": _package_version("scikit-learn"),
    }
    loader_dependency = _loader_dependency(config)
    if loader_dependency is not None:
        dependencies[loader_dependency[0]] = loader_dependency[1]
    fingerprint = _sha256(config, frame)
    return {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "psyml_version": _package_version("psyml-toolkit"),
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
        },
        "operating_system": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "dependencies": dependencies,
        "data": {
            "source_kind": "file" if config.input_path is not None else "in_memory",
            "input_rows": len(frame),
            "input_columns": len(frame.columns),
            "analyzed_rows": analyzed_rows,
            "feature_columns": feature_columns,
            "sha256": fingerprint[0] if fingerprint else None,
            "hash_basis": fingerprint[1] if fingerprint else None,
        },
    }


def _display(value: str | None) -> str:
    if value is None:
        return "not used"
    return value.replace("|", "\\|").replace("\n", " ")


def _validation_description(config: ExperimentConfig) -> str:
    if config.validation_strategy == "holdout":
        return f"a holdout split with {config.test_size:.0%} assigned to evaluation"
    if config.validation_strategy == "leave_one_group_out":
        return "leave-one-group-out cross-validation"
    labels = {
        "k_fold": "cross-validation",
        "stratified_k_fold": "stratified cross-validation",
        "group_k_fold": "group cross-validation",
        "stratified_group_k_fold": "stratified group cross-validation",
    }
    return f"{config.n_splits}-fold {labels[config.validation_strategy]}"


def _methods_summary(
    config: ExperimentConfig,
    analyzed_rows: int,
    feature_columns: int,
    metric_names: list[str],
) -> str:
    group_sentence = (
        f"The grouping variable `{_display(config.group_column)}` was excluded from predictors and "
        + (
            "used by the configured outer split."
            if config.validation_strategy not in {"k_fold", "stratified_k_fold"}
            else "NOT used to isolate groups by the configured outer split."
        )
        if config.group_column
        else "No grouping variable was configured."
    )
    parameters = json.dumps(config.model_params, ensure_ascii=False, sort_keys=True)
    metrics = ", ".join(metric_names)
    selected_models = ", ".join(f"`{name}`" for name in config.selected_models())
    selected_validations = ", ".join(f"`{name}`" for name in config.selected_validations())
    family_search = len(config.selected_models()) > 1
    selection_text = (
        f"Candidate models ({selected_models}) and validation strategies ({selected_validations}) "
        f"used `{config.resolved_selection_metric()}`. Parameter mode was `{config.tuning_mode}` "
        f"with at most {config.max_candidates} candidates per model. "
        f"Inner selection used up to {config.inner_splits} folds restricted to each outer training partition; "
        "groups were isolated in inner splits whenever a group column was configured. "
        + (
            "Model-family selection and parameter selection were jointly nested: even in no-parameter-search "
            "mode, all families were compared within inner CV. Each outer test fold evaluated only the "
            "family/parameters selected without that test fold. Primary metrics evaluate this complete "
            "selection procedure, whose chosen family can differ by fold; they do NOT evaluate the final "
            "full-data fitted model. `selection_trace.csv` records these choices. Final family and parameters "
            "were selected afresh by inner CV on all analyzed data, without using outer scores. "
            "`model_comparison.csv` is an exploratory per-family leaderboard; selecting its top score and "
            "reporting that score as independent performance still introduces selection bias. "
            if family_search else
            "The model family was prespecified. Parameters were selected within inner CV when multiple "
            "candidates existed, and reselected on all analyzed rows for the final fit. A single fixed "
            "candidate requires no inner search. "
        )
        + f"The designated primary validation is `{config.resolved_primary_validation()}`; others are sensitivity analyses, summarized "
        "separately in `validation_summary.csv`. Neither sensitivity results nor outer family ranks "
        "select the final model. Ties follow configured family/candidate order. Candidates with any "
        "failed inner fold are ineligible; if the inner-selected family fails outer evaluation, the "
        "procedure fails that validation rather than substituting a family using test outcomes. "
        "Nested evaluation is internal validation at the outer training sample size, not proof of "
        "transportability to new populations, centres or times. It also does not protect against "
        "researchers revising the design after inspecting results."
    )
    evaluated_subject = "complete model-family/parameter selection procedure" if family_search else f"`{config.model_name}` model"
    stacking_text = (
        "Stacking cross-fits complete base pipelines, including preprocessing, using group-aware "
        "splits when groups are configured. Its internal fold count is up to cv (default 5), "
        "subject to available classes/groups; its split seed is the configured seed. "
        "With passthrough, original features are preprocessed within the meta-estimator fit."
        if "stacking" in config.selected_models()
        else ""
    )
    return f"""# Methods Summary

PsyML analyzed {analyzed_rows} rows with {feature_columns} predictor columns for a {config.task} task. The outcome column was `{_display(config.target_column)}`. {group_sentence}

Missing predictor values used the `{config.missing_strategy}` strategy. Numeric scaling was `{config.scaling}`, and categorical predictors were one-hot encoded. All learned preprocessing steps were fitted within each training partition only.

The {evaluated_subject} was evaluated using {_validation_description(config)} with random seed {config.random_seed}. The final full-data family was `{config.model_name}`. Final full-data parameter overrides were `{parameters}`; outer folds may use different families/parameters recorded in `selection_trace.csv` and `parameter_search.csv`. Performance was calculated only from held-out predictions using: {metrics}.

{selection_text}

{stacking_text}

The final model was fitted on all analyzed rows. Reported metrics remain held-out evaluation metrics, not final-fit training scores. Fold means are unweighted; standard deviations are descriptive (ddof=0), not confidence intervals. Undefined secondary metrics are excluded and their available fold counts are in `metrics_summary.csv`. Binary AUC treats estimator `classes_[1]` as positive; multiclass AUC uses matching probability columns and is omitted when class sets differ. Figures use Class 1, Class 2, etc. in the same order as `confusion_matrix.csv`.

`config.json`, `analysis_config.json`, and `study_config.json` retain the original search design for reruns; `best_parameters.json` records final parameter overrides. The configured seed controls splits and seeded estimators; inner split seeds add the outer fold number (zero for final tuning), and explicit estimator random_state overrides take precedence.

This summary is generated offline by local rules and is not guaranteed to be correct. Researchers must check the data, design, warnings and results. This text describes the executed configuration and is intended as a starting point for a manuscript Methods section; researchers remain responsible for study-specific justification and reporting.
"""


def _markdown_table(frame: pd.DataFrame) -> str:
    columns = [str(column) for column in frame.columns]
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    rows = []
    for values in frame.itertuples(index=False, name=None):
        cells = []
        for value in values:
            if isinstance(value, float):
                cells.append(f"{value:.6g}")
            else:
                cells.append(_display(str(value)))
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join([header, separator, *rows])


def _safe_configuration(config: ExperimentConfig) -> dict[str, Any]:
    serialized = asdict(config)
    serialized["input_path"] = "<redacted-local-path>" if config.input_path else None
    serialized["output_dir"] = "<redacted-local-path>"
    return serialized


def _reproducibility_report(
    config: ExperimentConfig,
    manifest: dict[str, Any],
    fold_metrics: pd.DataFrame,
    warnings: list[str],
) -> str:
    environment = manifest["operating_system"]
    data = manifest["data"]
    warning_lines = "\n".join(f"- {warning}" for warning in warnings) or "- None recorded."
    fingerprint = data["sha256"] or "disabled"
    rerun_note = (
        "The saved `config.json` contains the original study design and source path for a CLI rerun; change output_dir to a new empty directory first."
        if config.input_path is not None
        else "This run used an in-memory dataframe; attach an input path before a CLI rerun."
    )
    safe_config = json.dumps(
        _safe_configuration(config), indent=2, ensure_ascii=False, sort_keys=True, default=str
    )
    group_safeguard = (
        "- The configured group column was removed from predictors before fitting."
        if config.group_column
        else "- No group column was configured for this run."
    )
    return f"""# Reproducibility Report

## Run and environment

- PsyML: {manifest["psyml_version"]}
- Python: {manifest["python"]["version"]} ({manifest["python"]["implementation"]})
- OS: {environment["system"]} {environment["release"]} ({environment["machine"]})
- Data shape: {data["input_rows"]} input rows × {data["input_columns"]} columns; {data["analyzed_rows"]} analyzed rows and {data["feature_columns"]} predictors
- Data SHA-256: `{fingerprint}`

## Executed configuration

```json
{safe_config}
```

## Best parameters

Final family: `{config.model_name}`. Final full-data parameter overrides (best_parameters):

```json
{json.dumps(config.model_params, ensure_ascii=False, indent=2)}
```

Use `best_parameters_configure.json` for a fixed-parameter run. This is not a rerun of the original nested search; its evaluation reuses data involved in parameter selection and is not independent validation.

## Fold metrics

{_markdown_table(fold_metrics)}

## Warnings

{warning_lines}

## Leakage safeguards

- The target column was removed before preprocessing and model fitting.
{group_safeguard}
- Imputation, scaling and one-hot encoding were fitted inside each training partition.
- Reported metrics use only predictions from held-out partitions.

## Review suggestions

Check warnings, fold variability and systematic errors in held-out predictions and task-specific figures. Assess practical relevance using the research question. These rule-based suggestions run offline and are not guaranteed to be correct; researcher review is required.

## Re-running and artefacts

{rerun_note} The result directory contains the executed configuration, fold and summary metrics, predictions, warnings, this report, a Methods summary, the analysis manifest and task-specific figures. Local paths are intentionally redacted from this report to reduce disclosure risk.
"""


def _write_figure(
    figures_dir: Path,
    config: ExperimentConfig,
    predictions: pd.DataFrame,
    confusion: pd.DataFrame | None,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    figures_dir.mkdir(parents=True, exist_ok=True)
    selected = config.figure_types if config.figure_types is not None else [
        "confusion_matrix" if config.task == "classification" else "observed_vs_predicted"
    ]
    residual = predictions["observed"] - predictions["predicted"] if config.task == "regression" else None
    for name in selected:
        if name not in {"residuals", "residual_distribution", "class_distribution"}:
            continue
        figure, axis = plt.subplots(figsize=(6.4, 5.2))
        if name == "residuals":
            axis.scatter(predictions["predicted"], residual, alpha=0.7)
            axis.axhline(0, linestyle="--", color="black")
            axis.set(xlabel="Predicted", ylabel="Observed - predicted", title="Held-out residuals")
        elif name == "residual_distribution":
            axis.hist(residual, bins="auto", edgecolor="white")
            axis.set(xlabel="Observed - predicted", ylabel="Count", title="Held-out residual distribution")
        elif confusion is not None:
            values = confusion.to_numpy()
            positions = list(range(len(values)))
            axis.bar([x - .2 for x in positions], values.sum(axis=1), .4, label="Observed")
            axis.bar([x + .2 for x in positions], values.sum(axis=0), .4, label="Predicted")
            axis.set_xticks(positions, [f"Class {x + 1}" for x in positions])
            axis.set(ylabel="Count", title="Held-out class distribution")
            axis.legend()
        figure.tight_layout()
        figure.savefig(figures_dir / f"{name}.png", dpi=160)
        plt.close(figure)
    if "observed_vs_predicted" in selected:
        figure, axis = plt.subplots(figsize=(6.4, 5.2))
        axis.scatter(predictions["observed"], predictions["predicted"], alpha=0.7)
        lower = min(predictions["observed"].min(), predictions["predicted"].min())
        upper = max(predictions["observed"].max(), predictions["predicted"].max())
        axis.plot([lower, upper], [lower, upper], linestyle="--", color="black", linewidth=1)
        axis.set(xlabel="Observed", ylabel="Predicted", title="Observed vs predicted")
        figure.tight_layout()
        figure.savefig(figures_dir / "observed_vs_predicted.png", dpi=160)
        plt.close(figure)
        return

    if confusion is None or "confusion_matrix" not in selected:
        return
    values = confusion.to_numpy()
    figure, axis = plt.subplots(figsize=(6.0, 5.2))
    image = axis.imshow(values, cmap="Blues")
    labels = [f"Class {index + 1}" for index in range(len(values))]
    axis.set_xticks(range(len(labels)), labels=labels, rotation=30, ha="right")
    axis.set_yticks(range(len(labels)), labels=labels)
    axis.set(xlabel="Predicted", ylabel="Observed", title="Confusion matrix")
    for row in range(values.shape[0]):
        for column in range(values.shape[1]):
            text_color = "white" if values[row, column] > values.max() / 2 else "black"
            axis.text(
                column,
                row,
                str(values[row, column]),
                ha="center",
                va="center",
                color=text_color,
            )
    figure.colorbar(image, ax=axis)
    figure.tight_layout()
    figure.savefig(figures_dir / "confusion_matrix.png", dpi=160)
    plt.close(figure)


def write_research_outputs(
    output_dir: Path,
    config: ExperimentConfig,
    source_frame: pd.DataFrame,
    analyzed_rows: int,
    feature_columns: int,
    fold_metrics: pd.DataFrame,
    predictions: pd.DataFrame,
    warnings: list[str],
    confusion: pd.DataFrame | None,
) -> None:
    """Write manifest, faithful narrative reports, and privacy-conscious figures."""
    manifest = _manifest(config, source_frame, analyzed_rows, feature_columns)
    (output_dir / "analysis_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    metric_names = [
        column for column in fold_metrics.columns if column not in {"fold", "model", "validation"}
    ]
    (output_dir / "methods_summary.md").write_text(
        _methods_summary(config, analyzed_rows, feature_columns, metric_names),
        encoding="utf-8",
    )
    (output_dir / "reproducibility_report.md").write_text(
        _reproducibility_report(config, manifest, fold_metrics, warnings),
        encoding="utf-8",
    )
    _write_companion_outputs(output_dir, config, manifest, fold_metrics, warnings)
    _write_figure(output_dir / "figures", config, predictions, confusion)


CONFIG_HELP = {
    "schema_version": "配置格式版本 / Configuration schema version",
    "task": "分类或回归 / Classification or regression",
    "target_column": "预测目标列 / Outcome column",
    "model_name": "单模型或最终模型名称 / Single or final model name",
    "model_names": "候选模型，顺序用于并列裁决 / Candidate families; order breaks ties",
    "input_path": "本地数据路径 / Local input data path",
    "output_dir": "新建空结果目录 / New empty output directory",
    "group_column": "分组列，不作为预测变量 / Group identifier excluded from predictors",
    "feature_columns": "预测变量；null 表示排除目标和分组后的所有列 / Predictors; null selects remaining columns",
    "test_size": "留出法测试集比例 / Holdout test fraction",
    "random_seed": "可复现随机种子 / Reproducible random seed",
    "validation_strategy": "单一验证的兼容字段 / Legacy single-validation field",
    "primary_validation": "null 不指定；策略名显式指定；first_selected 兼容旧配置 / null for independent outputs, strategy name for explicit primary, first_selected for legacy configs",
    "validation_strategies": "已选验证列表；主要项由 primary_validation 决定 / Selected validations; primary_validation determines priority",
    "n_splits": "外层折数 / Outer fold count",
    "missing_strategy": "预测变量缺失处理 / Predictor missing-value strategy",
    "scaling": "数值缩放 / Numeric scaling",
    "include_data_hash": "是否保存数据指纹 / Save data fingerprint",
    "model_params": "固定参数覆盖 / Fixed parameter overrides",
    "tuning_mode": "none 固定、quick 快速、custom 自定义 / Fixed, quick or custom search",
    "parameter_grids": "训练集内部搜索候选值 / Inner-training search candidates",
    "selection_metric": "内层模型及参数选择指标 / Inner model and parameter selection metric",
    "inner_splits": "内层折数 / Inner fold count",
    "max_candidates": "每模型候选数上限 / Candidate limit per family",
    "selection_protocol": "嵌套模型家族选择协议 / Nested family selection protocol",
    "figure_types": "图形列表；null 默认图，[] 不输出图 / Figures; null for default, [] for none",
}


def _write_companion_outputs(output_dir, config, manifest, fold_metrics, warnings):
    from psyml.protocol import config_to_dict

    # A fixed-parameter recipe must not retain other families or restart a search.
    recipe = replace(
        config, model_names=[config.model_name], tuning_mode="none", parameter_grids={},
        validation_strategies=[config.validation_strategy],
        output_dir=output_dir / "best_parameters_run",
    )
    (output_dir / "best_parameters_configure.json").write_text(
        json.dumps(config_to_dict(recipe), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    guide = "# 配置字段说明 / Configuration guide\n\nJSON 不支持注释，因此解释单独保存，配置可直接运行。 / JSON comments are kept in this companion file so configurations remain runnable.\n\n"
    guide += "\n".join(f"- `{key}`: {description}" for key, description in CONFIG_HELP.items())
    guide += "\n\n`config.json` 复现原始搜索设计；`best_parameters_configure.json` 固定最终参数重新运行，不复现原始搜索。后者使用曾参与选参的数据，不能视作独立验证。 / config.json reruns the original search; best_parameters_configure.json reruns fixed parameters on previously used data, not independent validation.\n"
    (output_dir / "configuration_guide.md").write_text(guide, encoding="utf-8")
    data = manifest["data"]
    parameters = json.dumps(config.model_params, ensure_ascii=False, indent=2)
    grouped = (
        "已设置分组列并从预测变量中排除。内层搜索隔离分组；外层是否隔离取决于所选验证。"
        if config.group_column else "未设置分组变量；请确认数据不存在未处理的重复测量或聚类结构。"
    )
    methods = f"""# 方法摘要（中文）

本次为 {config.task} 任务，共分析 {data['analyzed_rows']} 行、{data['feature_columns']} 个预测变量。目标列为 `{_display(config.target_column)}`。{grouped}

缺失处理为 `{config.missing_strategy}`，数值缩放为 `{config.scaling}`，类别预测变量使用独热编码。所有预处理仅在各训练分区拟合。

主要验证为 `{config.validation_strategy}`，K 折类策略的外层折数为 {config.n_splits}，留出比例为 {config.test_size}，随机种子为 {config.random_seed}。内层最多 {config.inner_splits} 折，按 `{config.resolved_selection_metric()}` 选择，每个家族最多 {config.max_candidates} 个候选。候选模型：{', '.join(config.selected_models())}；验证：{', '.join(config.selected_validations())}；搜索模式：`{config.tuning_mode}`。

多家族比较时，家族与参数联合嵌套选择；单一家族固定时，仅在存在多个参数候选时进行内层搜索。外层测试分数不参与最终模型选择。主要指标评估选择流程，不代表最终全数据拟合模型的独立性能。其他验证为敏感性分析，不能根据最高分事后更换主要验证。并列时按配置候选顺序决定；内层任一折失败的候选不参与选择。

最终全数据模型为 `{config.model_name}`，best_parameters 为：

```json
{parameters}
```

每折选择可不同，见 `selection_trace.csv` 和 `parameter_search.csv`。最终模型使用全部分析行拟合，报告指标来自样本外预测。折均值未按样本量加权，标准差（ddof=0）为描述性统计，不是置信区间。不可定义的次要指标不计入其均值，有效折数见 `metrics_summary.csv`。分类图中 Class 编号顺序对应 `confusion_matrix.csv`；二分类 AUC 的正类为估计器 classes_[1]。

{'堆叠模型在内部交叉拟合完整基础流水线，设置分组时采用分组切分；passthrough 的原始变量在元估计器内预处理。' if 'stacking' in config.selected_models() else ''}

本摘要由本地规则离线生成，不保证绝对正确，也不替代科学判断。研究者应核对数据、研究设计、缺失处理、分组、参数、警告和结果后再用于论文。内部验证不证明可推广至新群体、中心或时间，也不能防止查看结果后修改设计造成的偏差。
"""
    (output_dir / "methods_summary_zh.md").write_text(methods, encoding="utf-8")
    warning_text = "\n".join(f"- {warning}" for warning in warnings) or "- 无记录。"
    report = f"""# 可复现性报告（中文）

## 优先检查

先查看 `warnings.json` 和下方警告，再查看 `metrics.csv`、`metrics_summary.csv`、`validation_summary.csv`。模型排行榜仅供探索，不能把排序最高的分数当作独立验证。

## 环境与数据

PsyML {manifest['psyml_version']}；Python {manifest['python']['version']}；系统 {manifest['operating_system']['system']}。输入 {data['input_rows']} 行，分析 {data['analyzed_rows']} 行。数据 SHA-256：`{data['sha256'] or '未启用'}`。依赖版本详见 `analysis_manifest.json`。

## 最佳参数 best_parameters

最终模型：`{config.model_name}`。

```json
{parameters}
```

`best_parameters_configure.json` 可以直接用于固定参数运行；它使用曾参与选择的数据，不能作为独立验证。复现原始搜索请使用 `config.json`，先把 output_dir 改为新空目录。内存数据运行需补充 input_path。

## 配置（本地路径已隐藏）

```json
{json.dumps(_safe_configuration(config), ensure_ascii=False, indent=2, default=str)}
```

## 逐折指标

{_markdown_table(fold_metrics)}

## 警告（保留核心原始信息）

{warning_text}

## 核查与建议

{grouped} 目标列在预处理前排除。请检查样本外预测与残差/混淆矩阵是否存在系统性错误，检查折间波动，并结合研究问题判断性能是否有实际意义。自动建议仅由本地规则生成，无需网络，不保证绝对正确，请研究者逐项复核。完整方法与指标限制见 `methods_summary_zh.md`；英文版见 `methods_summary.md` 和 `reproducibility_report.md`。
"""
    (output_dir / "reproducibility_report_zh.md").write_text(report, encoding="utf-8")
