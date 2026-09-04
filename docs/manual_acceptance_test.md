# PsyML Toolkit 明日人工验收流程

建议完整执行一次，约需 25–40 分钟。测试只使用仓库中的随机合成数据和有明确许可的 UCI 公开数据，不要导入真实研究数据。

## 1. 更新并确认环境

在仓库根目录运行：

```bash
git pull --ff-only
git status --short
python3 --version
uv --version
godot --version
uv sync --locked --group dev
```

通过标准：

- `git status --short` 没有输出；
- Python 为 3.10–3.12；
- Godot 为 4.7.2；
- 依赖安装没有报错。

## 2. 启动与三语界面

```bash
uv run python tools/launch_gui.py
```

检查：

- 首次打开默认显示中文；
- 四个页面分别是“数据与变量、分析设置、检查与运行、结果”；
- 依次切换 English 和 Français，标题、字段、按钮、状态与错误提示随语言切换；
- 切回中文继续测试。

## 3. 分类分析

1. 在“数据与变量”选择 `gui/tests/fixtures/sample.tsv`，点击“读取预览”。
2. 确认显示 30 行、4 列，并能看到 `score`、`category`、`participant`、`target`。
3. 在“分析设置”选择：
   - 任务：分类
   - 目标变量：`target`
   - 分组变量：`participant`
   - 缺失值：中位数填补
   - 数值缩放：标准化
   - 验证策略：分组 K 折
   - 折数：5
   - 模型：Decision Tree
4. 返回“数据与变量”，确认预测变量只选择 `score` 和 `category`；`target` 与 `participant` 必须被排除。
5. 在“检查与运行”把结果目录设为 `/tmp/PsyML 明日测试/分类`，核对 JSON 后运行。

通过标准：

- 状态变为“分析完成”，没有崩溃或 traceback；
- 结果页显示分类指标、预测表和真实混淆矩阵；
- 输出目录包含 `result.json`、`analysis_config.json`、`analysis_manifest.json`、`predictions.csv`、指标 CSV、`methods_summary.md`、`reproducibility_report.md` 和 `figures/confusion_matrix.png`；
- `participant` 没有进入预测变量。

## 4. 回归分析

继续使用同一份随机 TSV：

1. 任务改为“回归”，目标变量改为 `score`，分组变量保持 `participant`。
2. 预测变量选择 `category` 和 `target`。
3. 保持分组 K 折、5 折、标准化，模型选择 Ridge。
4. 结果目录改为 `/tmp/PsyML 明日测试/回归`，检查配置并运行。

通过标准：

- 结果页显示 R²、MAE、RMSE、预测表和 observed-versus-predicted 图；
- 输出目录包含与分类相同的可复现性文件，以及 `figures/observed_vs_predicted.png`；
- 中文及空格路径没有引起错误。

## 5. 配置重跑

记录第一次分类预测文件的哈希，使用保存的配置重跑，再次计算哈希：

```bash
shasum -a 256 "/tmp/PsyML 明日测试/分类/predictions.csv"
uv run psyml run --config "/tmp/PsyML 明日测试/分类/analysis_config.json"
shasum -a 256 "/tmp/PsyML 明日测试/分类/predictions.csv"
```

通过标准：两次 `predictions.csv` 的 SHA-256 完全相同，重跑后的 `result.json` 状态仍为 `completed`。

## 6. 错误与取消

- 在数据路径中输入一个不存在的文件并读取预览，应显示本地化的“找不到文件”错误，而不是 traceback。
- 恢复有效数据后启动分析并立即点击“取消”。若小数据完成得太快，可在公开 Concrete 数据上选择 MLP 和 5 折后重试。应显示“分析已取消”，之后仍可再次正常运行。

## 7. 公开标准数据

关闭 GUI 后运行：

```bash
uv run python tools/fetch_public_examples.py
uv run psyml run --config examples/public/configs/iris_classification.json
uv run psyml run --config examples/public/configs/concrete_regression.json
```

通过标准：

- 下载哈希验证通过；
- 两次运行均返回 `"status": "completed"`；
- Iris 产生分类混淆矩阵，Concrete 产生回归预测图；
- `examples/public/data/` 和 `examples/public/results/` 保持被 Git 忽略。

## 8. 最终自动检查

```bash
uv run ruff check src tests tools
uv run pytest -q
uv run python tools/audit_repository.py
git status --short
```

通过标准：

- Ruff 无错误；
- 66 项测试全部通过；
- 隐私检查输出 `PSYML_PRIVACY_AUDIT_OK workbooks=39 csv=2 sav=1`；
- `git status --short` 没有因测试产生的新文件。

同时确认 GitHub Actions 最新一次运行在 Windows、macOS、Linux 三个平台全部为绿色。

## 9. 公开前 Go / No-Go

以下项目全部通过才建议公开：

- [ ] 中文、英文、法文切换正常，无明显截断；
- [ ] 分类与回归 GUI 流程均完成；
- [ ] 目标变量和分组变量没有进入预测变量；
- [ ] warning、指标、预测、图形和完整结果目录可读；
- [ ] 中文/空格路径和保存配置重跑通过；
- [ ] 错误信息可理解，取消后可以重新运行；
- [ ] 两个 UCI 示例通过；
- [ ] 自动测试、隐私审计和三平台 CI 全绿；
- [ ] `git status` 干净，没有真实数据或测试结果待提交；
- [ ] 已决定公开方式：仅公开可见，或添加明确许可证以允许他人复用。

发现问题时请记录：操作系统、界面语言、所选配置、发生步骤、错误文字、结果目录和截图；不要附带任何真实研究数据。
