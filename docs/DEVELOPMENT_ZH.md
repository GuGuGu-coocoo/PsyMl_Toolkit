# 开发者指南

[README](../README.md#chinese) · [English](DEVELOPMENT_EN.md) · [Français](DEVELOPMENT_FR.md)

本文面向修改代码、参与维护或构建应用的开发者。研究者直接使用 GUI，无需安装开发工具或执行本文命令。当前代码版本见 [pyproject.toml](../pyproject.toml)，已发布版本以 Releases 为准。

## 环境与启动

需要 Git、Python 3.10–3.12、[uv](https://docs.astral.sh/uv/) 和 [Godot 4.7.2](https://godotengine.org/download/archive/4.7.2-stable/)。独立应用构建使用 Python 3.12.13。克隆完整仓库后，在根目录运行：

```bash
uv sync --locked --group dev
uv run python tools/launch_gui.py
```

启动器会使用当前虚拟环境并设置 `PSYML_PYTHON`。Godot 不在 PATH 时，可设置 `PSYML_GODOT` 为完整可执行文件路径。macOS 配置好环境后，也可双击根目录的 `Launch PsyML.command`。不要把 `.venv/bin/python` 的符号链接解析成环境外的解释器路径，否则可能丢失项目依赖。

## 先读哪些文件

| 位置 | 职责 |
| --- | --- |
| `src/psyml/config.py`、`protocol.py`、`schemas/` | 配置校验、版本化 JSON 协议与结构 |
| `src/psyml/runner.py` | 分析编排、嵌套模型/参数选择、独立验证 |
| `src/psyml/data/`、`preprocessing/`、`validation/` | 文件读取、训练内预处理、数据切分 |
| `src/psyml/models/catalog.py`、`factory.py`、`evaluation/metrics.py` | 模型/参数目录、估计器构造、指标 |
| `src/psyml/reporting/` | 指标、预测、图形、报告和环境版本记录 |
| `src/psyml/gui_config.py` | 配置导入的数据路径解析与列校验 |
| `gui/main.tscn`、`gui/scripts/main.gd` | 界面结构和交互 |
| `gui/scripts/core_bridge.gd`、`configuration_io.gd` | 核心子进程通信、配置导入与保存 |
| `gui/scripts/i18n.gd`、`light_theme.gd` | 中英法文案、交互状态颜色 |
| `tests/`、`gui/tests/`、`examples/synthetic/` | 核心测试、界面测试、合成数据与配置 |
| `tools/`、`.github/workflows/` | 启动、构建、检查与 CI |

`legacy/` 仅保留历史代码与合成夹具，不是当前运行入口。`dist/`、`tmp/`、`output/` 和 `.venv/` 为本地产物；不要把它们或真实研究数据提交到仓库。

## 核心接口

GUI 通过本机子进程调用 Python 核心；开发模式使用虚拟环境，独立应用使用包内 `psyml-core`。不要把分析逻辑复制到界面脚本中。

```bash
uv run psyml --help
uv run psyml capabilities
uv run psyml preview --input examples/synthetic/classification.csv
uv run psyml import-config --config examples/synthetic/classification_config.json
uv run psyml schema analysis_config
uv run psyml run --config examples/synthetic/classification_config.json --events
uv run psyml run --config examples/synthetic/regression_config.json --events
```

`capabilities` 返回支持的模型、格式、指标和验证；`preview` 默认仅返回元数据，添加 `--include-sample` 才返回样本行。`schema` 支持 `analysis_config`、`event`、`result`。`run --events` 输出 JSONL 进度与终止事件；保持传输为合法 JSON，不混入日志。Python API 可从 `psyml` 导入 `ExperimentConfig`、`run_experiment`，用 `psyml.protocol.load_config` 读取配置。

CLI 的相对路径基于运行目录，按配置的 `output_dir` 写入且拒绝覆盖已有结果；重复运行前须换新空目录。GUI 导入优先从配置目录解析数据，兼容示例路径；找不到时让用户重新关联，缺列时报错。GUI 始终使用本机选定目录的新子目录，不沿用导入的输出路径。保存配置时，仅数据与配置同目录的情况保存相对文件名。

配置中 `primary_validation: null` 表示各验证分别输出；策略名表示显式主要项；省略该字段时保留旧配置的首项语义。 Python API 此模式返回 `validation_results[策略名]`；顶层 `model=None`、`metrics={}`，调用者需明确选择验证。

## 修改时必须保留的行为

- 编码、填补、缩放只在相应训练分区拟合；模型家族与参数在内层选择，不用外层排行榜挑最终模型。科研方法变化需在贡献说明中解释，不能只以测试通过代替科学论证。
- `primary_validation: null` 表示分别输出；根目录没有全局最佳模型或统一指标。每种验证保留完整结果或失败记录，不自动挑最高分。
- 修改配置字段时，同时检查配置类、schema、协议、GUI 导入/保存与测试，兼容既有配置。不得静默丢失固定参数、搜索候选、变量顺序或图形选择。
- 数据、配置、保存与目录选择均使用系统原生文件窗口。自绘控件需检查悬停、焦点、选中和禁用状态的对比度。
- 修改可见功能时同步三语文案、README、研究者指南和对应语言截图；语言切换不能改变分析配置。导出图形和底层错误的语言边界见 README。
- `analysis_manifest.json` 记录运行版本；新增运行依赖时同步检查报告记录及独立包的元数据和许可证。更新依赖须同步 `uv.lock`。

## 测试与提交

具体命令和人工核查见 [TESTING.md](TESTING.md)。它是开发者回归检查清单，不是 GUI 用户的安装或使用步骤。按改动范围选择检查；界面修改需实际打开核对，方法修改需用可核查的小数据验证。只用合成数据或可公开分享的最小示例。

提交 PR 时说明解决的问题、行为变化、验证结果和已知限制。避免无关重构；涉及科学行为、协议兼容性或依赖变动时明确说明影响。贡献遵循 [Apache-2.0 许可证](../LICENSE)，不上传参与者数据、未公开研究资料或凭据。不要将开发者说明误写为“研究者必须运行命令”。

## 构建与发布维护

[build_native.py](../tools/build_native.py) 在目标操作系统构建独立应用，使用 PyInstaller 打包核心、Godot 导出 GUI；需要匹配的 Godot 导出模板。支持 Apple 芯片 macOS 和 Windows x64，不能把 Mac 本机构建当成 Windows 验证。

```bash
uv sync --locked --group dev --group build
uv run --group build python tools/build_native.py
```

脚本会重建同名 `dist/` 输出目录，运行两种任务的包内环境检查，并生成 ZIP 与 SHA-256。`--reuse-core` 仅适合核心和依赖完全未变的本地 GUI 调试；交付时完整重建。发布前核对版本、锁文件、平台、许可证、解压后的启动与原生文件窗口；未商业签名/公证的应用可能遇到系统安全提示。

[Core CI](../.github/workflows/ci.yml) 检查三个操作系统；[独立包工作流](../.github/workflows/native-test-build.yml) 可手动触发，也会在推送 `desktop-test` 分支时自动构建 Windows 测试包。推送到该分支会消耗构建资源，提交前应确认需要生成测试包。工作流仅保存构建产物，不创建 release。

`tools/package_release.py` 用于源码发行包；独立应用使用 `tools/build_native.py`。`tools/build_release_pdfs.py` 可生成中文使用说明和术语指南 PDF，输出位于 `output/pdf/`；分发前须逐页核对版式与内容。构建产物经测试验收后，由维护者手动发布。
