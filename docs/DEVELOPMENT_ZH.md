# 开发者指南

[README](../README.md#chinese) · [English](DEVELOPMENT_EN.md) · [Français](DEVELOPMENT_FR.md)

本文面向修改代码、参与维护或构建应用的开发者。研究者直接使用 GUI，无需安装开发工具或执行本文命令。当前代码版本只有一个维护来源：`src/psyml/__init__.py` 的 `__version__` 常量（`pyproject.toml` 通过 hatch 的 dynamic 读取同一值；当前源码为正式版本 `0.3.0`，界面原样显示；开发版 `0.3.0.dev0` 显示为 `0.3.0-dev`）。独立包与分发 PDF 的可下载附件以 [Releases](https://github.com/GuGuGu-coocoo/PsyMl_Toolkit/releases) 页面为准；v0.2.0 及更早的下载包不含源码检出的新功能与第二轮修复。

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

### 数据检查与结果解读接口

`psyml.data.profiling` 是数据检查的纯 helper：`profile_columns` / `column_profile` / `category_summary` / `identifier_signals` 从 DataFrame 生成逐列元数据（非缺失数、唯一数、近似唯一比例、可选取值计数与截断、以及有依据的疑似编号信号）。`protocol.dataframe_preview` 只在 `include_sample=True` 时附带取值，默认不返回值；GUI 第 1 页的 `gui/scripts/data_check_ui.gd` 消费该元数据，不从前 5 行估算，也不自动删除列或改变角色。

`psyml.reporting.interpretation` 的 `build_interpretation` 只聚合 runner 已算出的证据（procedure_results、逐组合折、tuning_rows、leaderboard、validation_summary），不增加任何模型拟合；`write_interpretation_outputs` 写 `result_interpretation.json`、`interpretation_baseline_differences.csv`、`result_interpretation.md`，并由 `result.json.artifacts` 索引。独立验证根目录由 `build_independent_interpretation` 只写概览索引。GUI 摘要在 `gui/scripts/result_interpretation_ui.gd`。核心回归在 `tests/test_profiling.py`、`tests/test_interpretation.py`；GUI 回归在 `gui/tests/test_data_check.gd`、`gui/tests/test_interpretation_results.gd`。基线只比较同验证、同折集合、同指标且已成功运行的 dummy，差值正负方向固定（正=更好），描述性统计不回流选择或调参。分组划分说明仅完善三语研究者术语指南，不涉及 GUI 或划分算法。

### 置换重要性接口

`ExperimentConfig.permutation_importance`（默认 `false`）与 `permutation_repeats`（1–100，默认 `10`）控制本功能，旧配置缺省即关闭。置换引擎在 `psyml.evaluation.permutation`，产物写入在 `psyml.reporting.permutation`。runner 只把内层选出的外层折 Pipeline 与其测试行交给引擎，并在选择冻结后写 `interpretations/<验证>/`；结果按 `dict[validation, list[record]]` 分开保存，失败记录保留 `status=failed` 与 `error_type/error`，不伪造变量。`result.json.permutation`、`analysis_manifest.json.interpretations` 和 Methods/复现报告只索引实际存在的文件。核心回归在 `tests/test_permutation*.py`；GUI 设置与结果区在 `gui/scripts/permutation_ui.gd`，回归在 `gui/tests/test_permutation.gd`；`examples/quickstart/*_permutation_config.json` 提供可导入的分类/回归冒烟。默认保持 OFF，不改变选择、划分或评价含义。

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

## 可选单样本解释依赖（explain extra）

单样本解释依赖 `shap`、`numba`、`llvmlite`，默认不安装，以免普通分析与预测增加冷启动和包体。需要时再装：

```bash
uv sync --extra explain
uv pip install -e ".[explain]"   # pip/venv 等价写法
```

`pyproject.toml` 按 Python 版本固定 SHAP（3.10 → 0.49.x，3.11 → 0.51.x，3.12 → 0.52.x），`uv.lock` 记录且不升级 scikit-learn 等无关依赖。`tools/build_native.py` 会把 shap/numba/llvmlite 打包进核心、把许可证复制到 `tools/licenses/`，`--explain-smoke` 检查包内分类/回归解释与重建。本机为 Mac，Windows 未执行。

## 拟合系数（无额外依赖）

[coefficients.py](../src/psyml/models/coefficients.py) 只从已拟合的 PsyML `preprocess`+`model` 流水线读取 `coef_`/`intercept_`，按 `ColumnTransformer.output_indices_` 与各子步骤（imputer `statistics_`、scaler `mean_/scale_` 或 `min_/scale_/data_min_/data_max_`、OneHotEncoder `categories_`）生成精确的变换特征/来源列/类别映射，并对样本以同一 pipeline `transform` 重建 `predict`（回归）或 `decision_function`（分类）进行核验（atol 1e-7 / rtol 1e-6）。它从不 fit、不改变模型、不回流调参，也不换算回原始单位。报告还完整记录 `input_features`/`dropped_features`（全缺失列及原因、原始序号、缺失策略）、`encoding.per_source`（逐列类别与 `drop_idx_`）与训练 dtype 来源（保存元数据或明确 unknown）。使用提供的样本且核验失败（误差超限/形状不符/非有限）时返回 `status=error` 并拒绝写出成功产物；无样本则保持未核验状态，二者在 CLI/GUI 中分开显示。常规 runner 在 `coefficients/` 写出 CSV/JSON/notes；CLI 为 `psyml coefficients`（沿用 trust/hash/version 与 `model_input`，只写新/空目录，JSON 最后）。加载模型路径会校验 PsyML 来源（`psyml_version`/`fit_scope`）与估计器类型，未知模型给出明确原因且普通预测不受影响。测试见 `tests/test_coefficients.py`、`tests/test_coefficients_cli.py` 与 `gui/tests/test_coefficients.gd`；`--coefficients-smoke` 检查本机包内分类/回归提取。

## 构建与发布维护

[build_native.py](../tools/build_native.py) 在目标操作系统构建独立应用，使用 PyInstaller 打包核心、Godot 导出 GUI；需要匹配的 Godot 导出模板。支持 Apple 芯片 macOS 和 Windows x64，不能把 Mac 本机构建当成 Windows 验证。

```bash
uv sync --locked --group dev --group build
uv run --group build python tools/build_native.py
```

脚本会重建同名 `dist/` 输出目录，运行两种任务的包内环境检查，并生成 ZIP 与 SHA-256。`--reuse-core` 仅适合核心和依赖完全未变的本地 GUI 调试；交付时完整重建。发布前核对版本、锁文件、平台、许可证、解压后的启动与原生文件窗口；未商业签名/公证的应用可能遇到系统安全提示。

**原生导出只走 `tools/build_native.py`。** `gui/export_presets.cfg` 中的 macOS/Windows 版本字段（`application/short_version`、`application/version`、`application/file_version`、`application/product_version`）保存的是占位符 `@PSYML_MACOS_VERSION@` / `@PSYML_WINDOWS_VERSION@`，不是可发布的版本号；直接用 Godot 编辑器的导出功能会失败或写出错误版本。`build_native.py` 在一次导出期间用 `src/psyml/__init__.py` 的单一常量派生数值版本（正式版 `0.3.0` 与开发版 `0.3.0.dev0` 都导出为 macOS `0.3.0`、Windows `0.3.0.0`），导出结束后在 `finally` 中恢复模板，成功或失败都不留下被改写的预设文件。因此原生导出统一通过该脚本触发，不要绕过它直接使用 Godot 预设。

[Core CI](../.github/workflows/ci.yml) 检查三个操作系统；[独立包工作流](../.github/workflows/native-test-build.yml) 可手动触发，也会在推送 `desktop-test` 分支时自动构建 Windows 测试包。推送到该分支会消耗构建资源，提交前应确认需要生成测试包。工作流仅保存构建产物，不创建 release。

### 发布附件与本地研究者分享包

0.3.0 的 GitHub Release 只上传 Windows-x64 与 macOS-arm64 两个独立应用 ZIP，发布说明保持中英法三语（见 [RELEASE_NOTES_0.3.0.md](RELEASE_NOTES_0.3.0.md)）。构建脚本仍生成 SHA-256 供本地验证，不上传校验附件或额外源码 ZIP；发布候选的校验清单由 `tools/verify_release_artifacts.py` 在本地复核。GitHub 自动提供的 Source code 留给开发者。`tools/package_release.py` 是可选的本地源码归档工具，需要干净工作区和最新 PDF；不要把它的输出混入应用附件。历史参考：v0.2.0 的 Release 采用同一规则。

先核对 README 与研究者指南对应 0.3.0，再生成 PDF；下方字体路径须替换为支持中文且允许嵌入的 TrueType 字体。`output/pdf/sources.json` 记录内容来源哈希；来源改变后应重新生成并逐页渲染检查。PDF 的默认标签来自核心版本（`v0.3.0`）；重新生成历史版本时显式传 `--label v0.2.0 --base-ref v0.2.0`，该文档会被标为历史版本而不是当前正式版。

```bash
uv run --with reportlab python tools/build_release_pdfs.py --font /path/to/chinese-font.ttf \
    --output-dir dist/v0.3.0/docs
uv run python tools/verify_release_artifacts.py --directory dist/v0.3.0 --platform all
uv run python tools/package_researcher_share.py --windows-zip dist/PsyML-Toolkit-0.2.0-Windows-x64.zip
```

`tools/verify_release_artifacts.py` 读取 ZIP 实际内容（BUILD.json 版本/提交/干净源、core 与 app 资源、必要许可证、安全路径）、对应 SHA-256 与（`all` 模式）两份非空中文 PDF 和发布清单 `SHA256SUMS`，不依赖日志中的成功字符串。`all` 模式要求 `dist/v0.3.0/` 同时存在两个平台 ZIP、`docs/README_ZH.pdf`、`docs/RESEARCHER_GUIDE_ZH.pdf`、`docs/sources.json` 与列全四件产物的 `SHA256SUMS`；单平台模式只要求该平台的 ZIP 与 `.sha256`，可在 Windows 包下载前先核验 Mac 包。

分享脚本不调用发布接口，输出根目录的 `PsyML-Toolkit-Researcher-Share-v0.2.0.zip`，只用于直接分享，**不得上传 Release**；分享包不是发布附件，需要时另行确认生成。v0.2.0 分享包（最近一次生成）中 Windows/ 为程序，TestData/ 为训练、配置及预测资料，Documents/ 为中文使用指南和术语 PDF，“从这里开始.txt”解释运行顺序与文件夹，并引导 Mac 用户到 GitHub 下载。输出目录若已存在，先移走或备份旧包再重建；不要混用旧 PDF。

版本升级时只在 `src/psyml/__init__.py` 修改 `__version__`（`pyproject.toml` 为 dynamic，自动读取；`gui/export_presets.cfg` 保持占位符，数值由 `tools/build_native.py` 在导出时派生），并核对 uv.lock、`tools/build_native.py`、`tools/NATIVE_START_HERE.txt`、PDF 构建器中的版本与链接，以及三语发布说明（`docs/RELEASE_NOTES_<版本>.md`）。检查 BUILD.json 的提交、初始工作区状态和构建生成的差异，用 `tools/verify_release_artifacts.py` 复核 ZIP 内容与本地校验值。界面包内检查覆盖分类/回归训练、模型保存与加载、各 10 行新数据预测（写入本次运行目录的 `predictions.csv`）以及“打开预测结果文件夹”恰指向该运行目录；不替代实际窗口检查。核心 CLI `export-table` 与多格式读写仍保留，不属于该包内检查范围。每项独立功能完成后单独 commit 并立即 push，不累积后一起推送。
