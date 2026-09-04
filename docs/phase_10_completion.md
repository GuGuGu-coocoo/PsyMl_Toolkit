# Phase 10 Completion — Scientific Core

Phase 10 于 2026-09-04 完成。该阶段扩展的是新的 `src/psyml/` 核心，未修改只读的 legacy Python 源码，也未恢复任何原始研究数据。

## 已实现能力

- 数据格式：CSV、TSV、XLSX、XLS、SPSS SAV、Stata DTA、SAS7BDAT、XPT 与 Parquet。
- 回归模型：Dummy、Linear、Ridge、Lasso、Elastic Net、KNN、SVR、Decision Tree、Random Forest、Gradient Boosting 与 MLP。
- 分类模型：Dummy、Logistic Regression、Gaussian Naive Bayes、LDA、QDA、KNN、SVM、Decision Tree、Random Forest、Gradient Boosting、MLP 与 Stacking。
- 预处理：Drop/Mean/Median/Mode 缺失值策略，None/Standard/MinMax 缩放和分类变量 One-Hot；所有拟合型转换均位于训练 Pipeline 内。
- 验证：Holdout、K-Fold、Stratified K-Fold、Group K-Fold 与 Leave-One-Group-Out。
- 评价与导出：逐 fold 指标、均值/标准差/极值汇总、预测、配置、warning，以及分类混淆矩阵。
- 风险防护：空数据、重复列、缺失目标/分组、单一分类、分层样本不足和错误 group 配置会提前失败；提供 group 未隔离、类别不平衡和 Drop 行数 warning。

目标列和分组列会在构建特征 Pipeline 前移除。自动化测试直接检查最终 Pipeline 的输入列，证明两者没有进入模型特征。

## 输出文件

一次分析可产生：

- `metrics.csv`
- `fold_metrics.csv`
- `metrics_summary.csv`
- `predictions.csv`
- `confusion_matrix.csv`（分类任务）
- `warnings.json`
- `config.json`

Phase 11 将在这些真实执行结果上生成分析清单、Methods 说明、可复现性报告和图形。

## 验证记录

在 macOS arm64、Python 3.12.13 环境执行：

```text
ruff check src tests
All checks passed!

pytest -q
57 passed in 3.18s
```

测试覆盖所有 23 个模型、所有约定格式的真实读写或读取器分派、九种预处理组合、五种验证策略、中文与空格路径、泄漏隔离、指标和导出。SAS7BDAT 因测试工具没有写入器，采用读取器分派测试；公开样例文件的端到端验收留在 Phase 14。Windows 真机与安装包验证同样按计划留在 Phase 14，不在本阶段做未经验证的平台声明。

本次验证的关键库版本为 pandas 3.0.5、scikit-learn 1.9.0、pyarrow 23.0.1 与 pyreadstat 1.3.6。
