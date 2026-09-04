# Phase 12 Completion — Stable Core Interface and Packaging

Phase 12 于 2026-09-04 完成。Python Core 与未来 Godot GUI 之间的本地接口冻结为 schema version `1.0`。

## 稳定接口

- `analysis_config.json`：显式任务、目标、特征、分组、模型、预处理、验证、随机种子、数据指纹选项和路径。
- `result.json`：完成状态、任务、汇总指标、warning 和相对产物路径。
- JSONL event：`started`、`completed`、`failed`、`cancelled`，包含进度与结构化错误。
- 三份 JSON Schema 随 Python wheel 一同发布，可通过 `psyml schema ...` 查询。
- `psyml capabilities` 提供格式、模型、预处理和验证能力。
- `psyml preview` 默认只返回列级元数据；仅显式 `--include-sample` 时返回本地样例。
- `psyml run --config ... --events` 是 Godot 使用的本地子进程协议。

详细协议和错误码见 `docs/core_interface.md`。无子命令的旧 CLI 参数暂时保留兼容。

## 可靠性与隐私

- 中文和空格路径通过配置运行、预览、结果写入和确定性重跑测试。
- SIGTERM 取消产生 `cancelled` 事件和状态码 130；`result.json` 最后写入，未完成目录不会被标记成功。
- 失败以稳定错误码和消息返回，不向 GUI 输出 traceback。
- 特征列必须显式传递；自动化测试证明未选择列、目标列和分组列不会进入 Pipeline。
- 能力查询与科学运行时已解耦，约 0.35 秒返回，不会无条件加载 scikit-learn/SciPy。
- 移除了现代核心未使用的 Torch、jieba、Graphviz 等直接依赖，减少安装体积与供应链范围。

## 构建与验证

本地验证：

```text
ruff check src tests
All checks passed!

pytest -q
66 passed in 21.58s

uv build
source distribution and wheel built successfully

isolated wheel smoke test
passed
```

wheel 内容检查确认包含 `analysis_config.schema.json`、`event.schema.json` 和 `result.schema.json`。

GitHub Actions `Core CI #3`（commit `90bf425`）在 `windows-latest`、`macos-latest` 与 `ubuntu-latest` 全部成功，三平台均执行锁定环境安装、lint、测试、sdist/wheel 构建和隔离 wheel 冒烟测试。第一次运行发现 Windows PowerShell 不展开 wheel glob；工作流切换该步骤到 Bash 后，后续两次运行均成功。
