# Phase 11 Completion — Research Methods and Reproducibility Output

Phase 11 于 2026-09-04 完成。每次核心分析现在会基于真实执行配置与 held-out 结果，自动生成科研报告和任务对应图形。

## 新增产物

- `analysis_manifest.json`：schema 版本、生成时间、PsyML/Python/系统版本、实际核心依赖版本、输入与分析维度，以及可选 SHA-256 数据指纹。
- `methods_summary.md`：任务、样本与特征数、目标/分组、缺失值、缩放、One-Hot、模型、参数、验证、随机种子和实际指标。
- `reproducibility_report.md`：环境、数据指纹、去路径配置、逐 fold 指标、warning、泄漏保护和重跑说明。
- `figures/observed_vs_predicted.png`：回归 held-out 观察值与预测值图。
- `figures/confusion_matrix.png`：分类 held-out 混淆矩阵图。

报告不会复制输入数据行或分组值。本地路径在 Markdown 报告中替换为占位符；分类图使用匿名 `Class 1…` 标签，避免将潜在敏感类别值写入图片。可重跑所需的输入路径仍只保存在机器可读的 `config.json`。数据指纹仅记录 SHA-256，可通过 `include_data_hash=False` 或 CLI 的 `--no-data-hash` 关闭。

对于文件输入，指纹基于源文件字节；对于直接传入 API 的 dataframe，指纹基于规范化 CSV 表示。报告会明确区分可直接从文件配置重跑和需要先补充输入路径的内存运行，不声称未执行的步骤。

## 验证记录

```text
ruff check src tests
All checks passed!

pytest -q
59 passed in 21.10s
```

专门测试核对了源文件 SHA-256、环境与数据维度、模型参数与验证描述、哈希关闭行为、姓名/手机号/被试值/类别值不进入报告文本，以及两种 PNG 的有效文件头。另对分类和回归图进行了人工视觉检查，确认标签、参考线、色阶和文字对比可读。
