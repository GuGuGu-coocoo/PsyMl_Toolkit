# PsyML Toolkit Development Plan

## Project direction

PsyML Toolkit 将本科研究与应用项目遗留的 Python 机器学习脚本，逐步整理为可运行、可复现、可维护、能避免常见数据泄漏，且对非程序研究者友好的研究工具。

已完成的 Phase 0–6 已移至 [docs/completed_phases.md](docs/completed_phases.md)。遗留代码继续原样保存在 `legacy/original/program/`；新的实现只放在 `src/psyml/`。

当前不在范围内：AutoML、Transformer、LLM、云服务、数据库、SHAP、高级模型搜索、大规模深度学习、Web SaaS 与商业化。

## Phase 7 — Legacy Read-Only Review

在不修改 legacy 代码的前提下，生成 `docs/legacy_code_review.md`。

审查内容：

- 数据切分、缺失值填补、标准化、特征选择、调参和 stacking 是否发生数据泄漏；是否存在 participant-level leakage。
- KNN、SVM、Lasso、MLP、RF、Stacking、Decision Tree 和 RNN 的建模与评价是否合理。
- Accuracy、Precision、Recall、F1、AUC、R²、MAE、RMSE 的计算是否正确。
- 重复代码、硬编码路径与参数、全局变量、输出管理、异常处理、弃用 API、依赖、可维护性与可测试性。

将遗留代码归类为 Core Candidate、Specialized / Experimental 或 Archive Only。

## Phase 8 — First Round Fixes

状态：已完成（新核心实现；legacy 保持不修改）。

已解决的优先事项：

- 使用训练集内拟合的预处理 Pipeline，防止标准化、填补和编码泄漏。
- 以显式配置替代硬编码输入和输出路径。
- 统一随机种子、数据读取、验证、评价与结果导出。
- 采用未弃用的 SVM 评分接口。
- 对 CSV/XLSX 输入、目标列、分组列和模型选项进行早期校验。

## Phase 9 — Create Modern PsyML Core

状态：已完成。

新核心位于 `src/psyml/`：

```text
src/psyml/
├── data/
├── models/
│   ├── classification/
│   └── regression/
├── preprocessing/
├── validation/
├── evaluation/
├── reporting/
└── utils/
```

已提供：

- 可序列化的分析配置，以及 `psyml` 命令行入口。
- CSV/XLSX 读取和数据结构校验。
- 分类与回归的统一预处理、训练/测试切分，以及可选的 group-aware split。
- KNN、Lasso、MLP、Random Forest、SVR、SVM、Stacking 和 Decision Tree 的基础运行入口。
- 仅以留出集预测计算的分类与回归指标。
- `metrics.csv`、`predictions.csv` 和 `config.json` 的统一导出。
- 覆盖数据读取、分组切分、泄漏保护、输出和 CLI 的自动化测试。

## Phase 10 — Basic Model Completion

在现有基础模型上补齐科研常用 baseline；不引入 XGBoost、LightGBM 或 Transformer。

- Regression：Linear Regression、Ridge Regression、Dummy Regressor；可选 Decision Tree Regression。
- Classification：Logistic Regression、Dummy Classifier。

## Phase 11 — Research Methods & Reproducibility Output

每次分析在真实配置基础上生成下列文件，且不得写入被试姓名、学号、手机号等直接身份信息：

- `analysis_manifest.json`：PsyML/Python/OS 与实际使用库版本；按需记录 PyTorch、TensorFlow、CUDA 和 GPU。
- `methods_summary.md`：根据真实模型、预处理、验证、分组和指标生成可供论文 Methods 参考的说明。
- `reproducibility_report.md`：环境、数据维度与可选 hash、预处理、验证、模型超参数、指标、警告与已发现的泄漏风险。

标准结果目录：

```text
results/run_xxx/
├── metrics.csv
├── predictions.csv
├── config.json
├── analysis_manifest.json
├── methods_summary.md
├── reproducibility_report.md
└── figures/
```

## Phase 12 — Godot GUI

Godot 只负责选择数据、变量和配置，启动 Python Core，显示状态、警告、结果与导出选项；不得重复训练、预处理、验证或指标计算。

v0.1 流程：CSV/XLSX 导入 → 任务与变量选择 → 预处理与验证选择 → 模型选择 → 配置确认 → 执行 → 回归或分类结果展示 → 导出。

优先使用本地进程或本地 API 传递 `analysis_config.json` 和结果文件；不使用复杂 Python embedding。第一阶段支持 Windows 与 macOS，Linux 后续测试；Web 不在当前范围。

核心必须先验证：回归和分类 Pipeline、交叉验证、group-aware validation、无泄漏预处理、指标、结果导出、中文和含空格路径，以及 Godot 与 Python 的配置和错误传递。

## Current development finish line

当前阶段完成标准：Legacy review 完成；P0 问题修复；Core、基础模型、统一预处理与验证、group-aware 支持、泄漏保护、指标、结果导出与分析配置完成；Godot 能完成一次回归和一次分类分析，并在 Windows 与 macOS 基础流程可用；分析清单、Methods Summary 和 reproducibility report 自动生成。达到该点后暂停扩展功能，邀请真实研究者试用，再依据反馈决定后续工作。
