# Phase 13 Completion — Trilingual Godot GUI

## 完成范围

Phase 13 已建立 Godot 4 图形界面，并且只通过 Phase 12 的 version 1.0 JSON/JSONL 接口调用 Python 核心。Godot 不训练模型、不拟合预处理，也不自行计算指标。

界面默认使用中文，同时完整支持英文和法文。四个连续页面覆盖：

1. 导入 CSV、TSV、XLSX、XLS、SAV、DTA、SAS7BDAT、XPT 或 Parquet，并预览变量、类型、缺失数和样本；
2. 选择回归或分类任务、目标、分组、特征、缺失值策略、缩放、验证策略、折数和模型；
3. 审核 version 1.0 JSON 配置，选择输出目录，运行或取消分析；
4. 查看本地化 warning、指标、预测预览和核心生成的真实分析图，并打开完整结果目录。

界面状态、字段、选项、已知 warning 与稳定错误码均有中、英、法三语文本。临时分析配置写入操作系统临时目录，并在完成、失败或取消后删除。

## 自动化证据

- Godot 编辑器无脚本解析错误；
- `gui/tests/test_bridge.gd` 验证能力查询、数据预览和错误协议，输出 `PSYML_GODOT_BRIDGE_OK`；
- `gui/tests/test_ui_flow.gd` 使用随机合成 TSV，通过真实 GUI 控件连续执行分类和回归，验证结果、指标、图形与法语界面，输出 `PSYML_GODOT_UI_FLOW_OK`；
- Python 回归套件：66 项通过；
- macOS 上使用 Godot 4.7.2 的真实 Metal 渲染人工检查中文和法文界面，未发现溢出或遮挡。

跨平台打包、三语图文操作流程和 Windows/macOS/Linux 验收属于 Phase 14。
