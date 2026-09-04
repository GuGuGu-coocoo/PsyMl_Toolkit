# PsyML Toolkit Development Plan

## Project direction

PsyML Toolkit 将本科研究与应用项目遗留的 Python 机器学习脚本，逐步整理为可运行、可复现、可维护、能避免常见数据泄漏，且对非程序研究者友好的研究工具。

已完成的 Phase 0–11 已移至 [completed_phases.md](completed_phases.md)。遗留代码继续原样保存在 `legacy/original/program/`；新的实现只放在 `src/psyml/`。

完成规则：每个阶段完成时，先在 `docs/` 写入可核验的完成记录，再追加到 `docs/completed_phases.md`，并从本计划移除该阶段的详细待办。

当前不在范围内：AutoML、Transformer、LLM、云服务、数据库、SHAP、高级模型搜索、大规模深度学习、Web SaaS 与商业化。

## Phase 12 — Stable Core Interface and Packaging

在 GUI 前冻结 Python Core 接口：

- 定义版本化 `analysis_config.json` schema、结果 schema、状态事件和错误结构。
- CLI 支持配置文件运行、数据预览与能力查询。
- 提供本地子进程接口；Godot 只传递 JSON 和读取结果，不嵌入或复制科学计算逻辑。
- 验证中文路径、含空格路径、取消运行、错误返回与确定性重跑。
- 建立 Windows 与 macOS 的自动化测试和可安装包构建。

## Phase 13 — Trilingual Godot GUI

GUI 默认中文，同时支持英文和法文，并调用 Phase 12 的稳定接口。

流程：导入数据 → 预览变量与缺失值 → 选择任务/特征/目标/分组 → 设置预处理与验证 → 选择模型 → 检查配置 → 运行及取消 → 查看 warning、指标、预测与图 → 导出完整结果。

Godot 不训练模型、不拟合预处理、不计算指标。三种语言必须覆盖界面、状态、验证提示和错误信息。

## Phase 14 — Cross-Platform Acceptance and Researcher Documentation

- 在 Windows 与 macOS 分别完成回归和分类端到端验证；Linux 作为次级支持。
- 使用有清晰来源与许可的标准公开数据完成可复查示例，并同时保留随机合成数据用于结构测试。
- README 以中文、英文、法文提供图文操作流程；每种语言使用对应语言界面的真实截图。
- 验证安装、中文/空格路径、配置重跑、结果导出、Methods 与 reproducibility 报告。
- 发布前再次执行隐私、许可证、依赖、安全与产物大小审查。

## Current development finish line

Phase 10–14 的每项完成标准均有代码、自动化测试、报告或平台运行证据；Windows 与 macOS 用户可通过三语 GUI 完成规范的回归和分类分析并导出可复现结果。达到该点后暂停扩展功能，邀请真实研究者试用，再依据反馈决定后续工作。
