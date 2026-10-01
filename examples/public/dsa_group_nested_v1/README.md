# DSA 公开案例：按参与者分组的嵌套验证

本目录记录 PsyML 在公开 *Daily and Sports Activities*（UCI 256）数据上的一个软件符合性与可复算案例。它用真实行为数据检查软件的切分、训练折内预处理、嵌套选择、折外预测、评估和模型保存/加载行为，并用一个不导入 PsyML 的独立 scikit-learn 流程逐项复算。**它不是新算法、不是论文基准复现，也不支持临床、因果或其他人群的结论。**

- English version: [below](#english)
- 详细验证范围与结果：[`docs/VALIDATION_DSA_ZH.md`](../../../docs/VALIDATION_DSA_ZH.md)
- 固定期望值与容差：[`expected/`](expected/README.md)

## 数据与方法

- 数据：Barshan, B. & Altun, K. (2010). *Daily and Sports Activities* [Dataset]. UCI Machine Learning Repository. DOI <https://doi.org/10.24432/C5C59F>，许可 CC BY 4.0。
- 结构：8 名参与者、19 类活动、每人每类 60 个五秒片段，共 9,120 段；每段原始形状 125×45。8 名参与者是独立单位，9,120 段不是 9,120 个独立个体。
- 特征：每段只取躯干三轴加速度与三轴角速度（前 6 列），逐段、逐通道计算 mean 与总体标准差 `std(ddof=0)`，得到 12 个固定预测变量。其余传感器、磁力计、滤波、PCA 与特征筛选均未使用。
- 协议：外层 `GroupKFold(n_splits=4, shuffle=False)`；内层 `StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=20261001+外层折号)`；每次拟合都新建 `SimpleImputer(median) → StandardScaler → estimator`，只在训练折上拟合；选择指标为内层 balanced accuracy 的未加权均值，严格大于才替换、完全平手保留先出现者；全数据最终模型用同样的内层规则选择后再拟合。完整字段见 [`configs/dsa_group_nested_v1.json`](../configs/dsa_group_nested_v1.json)。
- 基线记录：主指标为 4 个外折 balanced accuracy 的未加权均值 **0.5740131578947368**（8 人、19 类），四次外折与最终选择均为 `logistic_regression, C=1.0`；同折 Dummy 为 1/19 ≈ 0.0526；人内打乱标签 canary 为 0.0533（预设告警阈值 0.10，未触发）。这些是冻结案例记录值，不是本仓库测试重新产生的数字。

## 运行（仓库根目录）

```bash
# 1) 可选：从官方 ZIP 重新生成派生 CSV（默认输出 examples/public/data/，该目录被 Git 忽略）
uv run python tools/cases/prepare_dsa.py \
  --archive /path/to/daily_and_sports_activities.zip \
  --output-dir examples/public/data

# 2) 原生 CLI 主结果（输出目录必须不存在；见下方“重跑”说明）
uv run psyml run --config examples/public/configs/dsa_group_nested_v1.json --events

# 3) 独立 scikit-learn 复算 + 观察性补充记录
uv run python tools/cases/reference_dsa.py \
  --config examples/public/configs/dsa_group_nested_v1.json \
  --output examples/public/results/dsa_group_nested_v1/reference
uv run python tools/cases/observe_psyml_dsa.py \
  --config examples/public/configs/dsa_group_nested_v1.json \
  --output examples/public/results/dsa_group_nested_v1/observed

# 4) 冻结容差下的数值与结构验收（约定 26 项数值 + 4 项结构 + 2 项导出核验）
uv run python tools/cases/compare_dsa.py \
  --config examples/public/configs/dsa_group_nested_v1.json \
  --primary examples/public/results/dsa_group_nested_v1 \
  --reference examples/public/results/dsa_group_nested_v1/reference \
  --observed examples/public/results/dsa_group_nested_v1/observed \
  --output examples/public/results/dsa_group_nested_v1/comparison

# 5) 工程负控：row-split 审计、固定外折 1 标签/特征扰动、人内打乱标签 canary
uv run python tools/cases/check_dsa_controls.py \
  --config examples/public/configs/dsa_group_nested_v1.json \
  --output examples/public/results/dsa_group_nested_v1/controls
```

说明：

- 数据下载只允许使用上面的 UCI 官方地址。`prepare_dsa.py` 不会下载、不会解压整棵数据树、也不会执行压缩包内任何代码；只有完整 ZIP 哈希与冻结值一致时才会读取成员。
- `input_path`/`output_dir` 按**进程当前目录**解析，不做配置目录相对解析，因此请在仓库根目录运行，或显式传入绝对路径。
- 输出写入 `examples/public/results/`，该目录被 Git 忽略。CLI 拒绝已存在且非空的输出目录；重跑请先复制配置并把 `output_dir` 改为新目录，或在本地脚本中重定位，不能覆盖旧结果。
- `uv run` 使用仓库当前环境（官方 `uv.lock` 在 Python ≥ 3.11 上使用 scikit-learn 1.9.0）。冻结案例的逐值基线是在案例 parity 环境（Python 3.12.14、scikit-learn 1.8.0）下记录的；换版本或换平台得到的数字属于**新的验证结果**，必须单独记录，不能用来覆盖 `expected/` 或放宽容差。
- `compare_dsa.py` 可加 `--golden <目录>` 与本地保存的冻结主结果做逐行精确比较；`expected/golden_hashes.json` 记录这些文件的 SHA-256。

## 目录内容

| 路径 | 说明 |
| --- | --- |
| `../../configs/dsa_group_nested_v1.json` | 冻结科学字段的示例配置（仓库相对路径） |
| `expected/` | 固定期望值：哈希、结构、指标、折成员、容差与来源说明 |
| `../../../tools/cases/prepare_dsa.py` | 数据下载后转换（严格枚举、shape/finite/计数校验、逐成员哈希与 manifest） |
| `../../../tools/cases/reference_dsa.py` | 独立 sklearn 复算（不导入 PsyML） |
| `../../../tools/cases/observe_psyml_dsa.py` | 观察性补充运行（只记录生产调用，不修改源码） |
| `../../../tools/cases/compare_dsa.py` | 数值、结构与导出验收，失败返回非零 |
| `../../../tools/cases/check_dsa_controls.py` | 真实数据工程负控与 shuffled-label canary |
| `../../../tests/test_public_dsa_case_contract.py` | 合成小数据的契约测试（默认不联网、不拟合 9,120 行） |

## 限制

- 只有 8 名参与者，且来自同一采集协议；不能外推到其他人群、设备或自然生活场景，也不构成外部验证。
- 独立参考与 PsyML 共用 scikit-learn 的估计器、切分器和指标实现，因此核对的是**工作流**而不是 sklearn 求解器本身。
- canary 是单次工程扰动，不是置换检验，不估计假阳性率，也不证明不存在泄漏。
- 原生 19 类混淆矩阵图在默认尺寸下标注拥挤（三位数相邻、横轴标签密集）；数值 CSV 与指标不受影响。该展示问题被原样保留、未在核心或 GUI 中修改。
- 本案例只维护文档与示例层：不改变核心训练逻辑、不修改 GUI、不升级版本号。

## English

This directory records a software-conformance and reproducibility case for
PsyML on the public UCI *Daily and Sports Activities* dataset. It checks
splitting, training-fold preprocessing, nested selection, out-of-fold
prediction, evaluation and model persistence on real behavioural data, and
recomputes the same protocol with an independent scikit-learn workflow that
never imports PsyML. It is not a new algorithm, not a reproduction of the
original paper's benchmark and not evidence for clinical, causal or
population-level claims.

Data and features: 8 participants × 19 activities × 60 five-second segments =
9,120 rows (each 125×45). Only the torso three-axis acceleration and angular
rate (first six columns) are used; each segment contributes per-channel mean
and population standard deviation (`ddof=0`), giving 12 fixed predictors.
Frozen protocol: outer `GroupKFold(n_splits=4, shuffle=False)`; inner
`StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=20261001+fold)`;
fresh `SimpleImputer(median) → StandardScaler → estimator` fitted inside every
training partition; selection by the unweighted mean of inner balanced
accuracies with strict-greater replacement and first-in-order ties; final
full-data model chosen by the same inner rule. The recorded baseline is mean
outer-fold balanced accuracy **0.5740131578947368**, every fold and the final
choice selecting `logistic_regression, C=1.0`; the same-fold Dummy baseline is
1/19 ≈ 0.0526 and the within-subject shuffled-label canary is 0.0533 (below the
predeclared 0.10 alarm). These are frozen case-recorded values, not numbers
regenerated by the repository tests.

Run the commands above from the repository root. Paths in the configuration
resolve against the process working directory, not the configuration directory.
The CLI rejects an existing non-empty output directory; reruns must choose a
new directory and never overwrite frozen results. `uv run` uses the repository
environment (the official `uv.lock` pins scikit-learn 1.9.0 on Python ≥ 3.11),
whereas the frozen per-value baseline was recorded in the case-parity
environment (Python 3.12.14, scikit-learn 1.8.0). Results from another version
or platform are new verification results and must be recorded separately.

Limits: only 8 participants on one acquisition protocol; no external validity.
The independent reference shares scikit-learn estimators, splitters and metrics,
so it validates the workflow rather than the solvers. The canary is one
engineering perturbation, not a permutation test or a false-positive-rate
estimate. The native 19-class confusion-matrix figure is crowded at its default
size; numeric CSVs and metrics are unaffected and the display issue is
preserved unchanged. This example changes documentation and examples only.
