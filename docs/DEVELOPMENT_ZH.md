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
| `src/psyml/models/persistence.py`、`parameters.py`、`src/psyml/prediction.py` | 最终 Pipeline 保存、有效参数记录、模型检查与批量预测 |
| `gui/scripts/prediction_page.gd`、`data_preview.gd` | 第 4 页预测交互与共享数据预览 |
| `examples/quickstart/`、`tests/test_quickstart.py` | 可整体复制的用户测试资料与训练到预测验证 |

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

### 0.2.0 训练、保存与预测接口

`examples/quickstart/` 是统一的用户试用入口；`examples/synthetic/` 及 `matrix/` 保留给开发回归检查。上面的旧合成示例命令仍有效。下面的 quickstart 配置使用相邻训练文件名，CLI 需先进入该目录；`load_config()` 本身不会按 JSON 所在目录改写相对路径。首次运行前确认 `results/quickstart_classification` 和 `results/quickstart_regression` 不含旧结果；重跑请修改配置选择新输出目录。

```bash
cd examples/quickstart
uv run psyml run --config classification_config.json --events
uv run psyml model-info --model results/quickstart_classification/model/best_decision_tree.joblib --trust-model
uv run psyml predict --model results/quickstart_classification/model/best_decision_tree.joblib --input classification_predict.csv --check-only --trust-model
uv run psyml predict --model results/quickstart_classification/model/best_decision_tree.joblib --input classification_predict.csv --output results/quickstart_classification/new_predictions.xlsx --trust-model
uv run psyml export-table --input results/quickstart_classification/new_predictions.xlsx --output results/quickstart_classification/new_predictions.csv
uv run psyml run --config regression_config.json --events
uv run psyml predict --model results/quickstart_regression/model/best_ridge.joblib --input regression_predict.csv --output results/quickstart_regression/new_predictions.csv --trust-model
cd ../..
```

两份预测输出均应为 10 行，保留 sample_id/category/score；分类新增 predicted_class 和两列 probability_*，回归新增 predicted_value。`model-info` 返回模型信息；`predict --check-only` 返回 `compatibility.compatible` 和错误列表，不能仅凭退出码判断兼容。实际预测必须指定 `--output`，其扩展名决定格式；默认不覆盖，`--overwrite` 仅在有意替换时使用。`--feature` 可按训练顺序重复提供手动映射。`export-table` 转换已有表格，不重新运行模型。XLS/SAS7BDAT 只读，可输出 XLSX。

Python 预测接口位于 `psyml.prediction`：`load_model(path, trusted=True)`、`compatibility_check(loaded, frame, mapping=None)`、`predict_dataframe(loaded, frame, mapping=None)`；最后一个返回 `(DataFrame, 新增列名列表)`。模型加载需要显式可信来源，不因只是查看信息就跳过信任检查。

`save_best_model` 默认为 true。主要验证运行的 `model_export` 记录保存状态和相对路径，`result.json.artifacts.saved_model` / `model_metadata` 提供文件索引；独立验证模式不自动保存。`best_parameters.json`、`result.json.effective_parameters` 与模型 metadata 的 best_parameters 含实际默认值；`result.json.best_parameters` 和固定参数配置保留参数覆盖，不能混为同一字段语义。

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

### 发布附件与本地研究者分享包

0.2.0 的 GitHub Release 只上传 Windows-x64 与 macOS-arm64 两个独立应用 ZIP，发布说明保持中英法三语。构建脚本仍生成 SHA-256 供本地验证，不上传校验附件或额外源码 ZIP。GitHub 自动提供的 Source code 留给开发者。`tools/package_release.py` 是可选的本地源码归档工具，需要干净工作区和最新 PDF；不要把它的输出混入应用附件。

先核对 README 与研究者指南对应 0.2.0，再生成 PDF；下方字体路径须替换为支持中文且允许嵌入的 TrueType 字体。`output/pdf/sources.json` 记录内容来源哈希；来源改变后应重新生成并逐页渲染检查。

```bash
uv run --with reportlab python tools/build_release_pdfs.py --font /path/to/chinese-font.ttf
uv run python tools/package_researcher_share.py --windows-zip dist/PsyML-Toolkit-0.2.0-Windows-x64.zip
```

分享脚本不调用发布接口，输出根目录的 `PsyML-Toolkit-Researcher-Share-v0.2.0.zip`，只用于直接分享，**不得上传 Release**。其中 Windows/ 为程序，TestData/ 为训练、配置及预测资料，Documents/ 为中文使用指南和术语 PDF，“从这里开始.txt”解释运行顺序与文件夹，并引导 Mac 用户到 GitHub 下载。输出目录若已存在，先移走或备份旧包再重建；不要混用旧 PDF。

版本升级时核对 pyproject.toml、src/psyml/__init__.py、uv.lock、gui/export_presets.cfg、tools/build_native.py、tools/NATIVE_START_HERE.txt、PDF 构建器中的版本与链接，以及三语发布说明。检查 BUILD.json 的提交、初始工作区状态和构建生成的差异，核对 ZIP 与本地校验值。界面包内检查覆盖分类/回归训练、模型保存、加载、各 10 行新数据预测及 XLSX 导出；不替代实际窗口检查。每项独立功能完成后单独 commit 并立即 push，不累积后一起推送。
