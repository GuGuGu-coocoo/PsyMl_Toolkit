# PsyML Toolkit Completed Phases

本文件归档开发计划中已完成的阶段，避免当前计划混入已经结束的工作。今后每完成一个阶段，必须先补充其完成证据与验证记录，再在本文件增加对应条目，并从 `docs/PSYML_TOOLKIT_DEVELOPMENT_PLAN.md` 移除该阶段的详细待办。

## Phase 0 — Legacy Asset Inventory

目标是盘点遗留的机器学习、数据分析和辅助脚本，并记录模型、预处理、验证、评价与输出能力。完成记录见 `docs/legacy_inventory.md`。

## Phase 1 — Legacy Version Archaeology

目标是保留原始目录名称、比较历史版本差异，并标注 Latest Candidate、Superseded、Experimental Branch、Unique Component 或 Unknown。完成记录见 `docs/legacy_versions.md`。

## Phase 2 — Backup and Privacy / IP Audit

目标是先保留历史代码，再移除或替换真实被试数据、身份信息、机密配置、绝对路径和未经确认可公开的内容；同时记录源码归属与保密风险。审计记录见 `docs/privacy_ip_audit.md`，数据处理记录见 `docs/data_sanitization_manifest.json` 与 `docs/csv_sanitization_manifest.json`。

## Phase 3 — Git Repository Initialization

仓库已初始化；遗留代码保存在 `legacy/original/program/`，并建立了 `legacy-v0.1` 标签。此后不再用复制目录的方式管理版本，而使用 Git commit、branch 和 tag。

## Phase 4 — Initial README

已建立根目录 `README.md`，说明项目背景、现有回归与分类模型、实验性 RNN NLP 代码，以及当前现代化状态。

## Phase 5 — uv Migration

已建立 `pyproject.toml` 与 `uv.lock`，并可用 `uv sync` 创建可复现的开发环境。

## Phase 6 — Current State Baseline

已建立 `docs/current_state.md`，记录遗留资产可运行、失效和待确认状态，以及输入、输出和人工配置情况。

## Phase 7 — Legacy Read-Only Review

已完成对 `legacy/original/program/` 的只读统计、机器学习与工程审查；72 个 Python 文件均能解析。发现的 P0/P1/P2 风险、迁移建议与 Core Candidate / Specialized / Archive Only 分类见 `docs/legacy_code_review.md`。Legacy 源文件未被修改。

## Phase 8 — First Round Fixes

已在新的 PsyML Core 中完成，不修改 legacy 代码。训练集内预处理、防硬编码路径、统一随机种子、验证、评价、输出、输入校验和未弃用的 SVM 评分路径均已落实。完成证据与自动化验证见 `docs/phase_8_9_completion.md`。

## Phase 9 — Create Modern PsyML Core

已建立 `src/psyml/`、命令行入口、统一的分类/回归流程、group-aware 切分、留出集评价和结果导出。完成证据与自动化验证见 `docs/phase_8_9_completion.md`。

## Phase 10 — Scientific Core Completion

已完成九种表格格式、23 个回归/分类模型、四种缺失值策略、三种缩放策略、五种验证策略、完整评价指标、逐 fold 与汇总结果导出，以及目标/分组变量隔离。57 项自动化测试通过；完成范围、限制和验证证据见 `docs/phase_10_completion.md`。

## Phase 11 — Research Methods & Reproducibility Output

每次分析会按真实配置生成分析清单、Methods 参考说明、可复现性报告和回归/分类图，支持可选 SHA-256 数据指纹并避免在报告中复制路径和数据值。59 项测试与人工图形检查通过；完成证据见 `docs/phase_11_completion.md`。

## Phase 12 — Stable Core Interface and Packaging

已冻结 version 1.0 的分析配置、结果和 JSONL event Schema，增加配置运行、数据预览、能力与 Schema 查询、本地子进程错误/取消协议、显式特征选择和 wheel 构建。66 项本地测试与隔离安装通过；GitHub Actions 在 Windows、macOS、Linux 全部成功。完整证据见 `docs/phase_12_completion.md`，接口说明见 `docs/core_interface.md`。

## Phase 13 — Trilingual Godot GUI

已建立默认中文并支持英文、法文的 Godot 4 图形界面，通过稳定 JSON/JSONL 接口完成数据预览、配置、运行/取消、warning、指标、预测、图形和结果目录流程。真实 GUI 自动化测试已完成分类与回归分析；完整证据见 `docs/phase_13_completion.md`。
