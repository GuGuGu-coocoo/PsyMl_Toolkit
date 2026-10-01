# PsyML 在公开人体活动数据上的分组嵌套交叉验证：数值复现与跨平台核验

[English](VALIDATION_DSA_EN.md) · [Français](VALIDATION_DSA_FR.md)

案例 `psyml_dsa_group_nested_v1` · PsyML `0.3.0`（提交 `de33abfe52ccfee67f461a850edd00a14d2fbfaa`） · 2026-10-01

## 摘要

**目的。** 用一份公开的人体活动数据，检验 PsyML 的参与者分组嵌套验证流程在真实数据上的数值行为：切分成员、训练折内预处理、内层选择、折外预测、指标计算与模型持久化是否按事先冻结的协议执行，并能被一份独立实现复算。

**方法。** 数据为 UCI *Daily and Sports Activities*（DSA）：8 位参与者、19 类活动、每人每类 60 条五秒记录，共 9,120 条。每段只取躯干三轴加速度与三轴角速度，逐段计算均值与总体标准差，得到 12 个特征。外层为 4 折参与者分组交叉验证；内层为 3 折分层分组交叉验证；候选为 Dummy 与逻辑回归；选择指标为内层 balanced accuracy 的未加权均值。独立参考实现不导入 PsyML，只用公开 scikit-learn API 重建同一协议；另有分组隔离审计、固定外折扰动与打乱标签 canary 等工程负控。

**主要结果。** 主指标为 4 个外层折的折均 balanced accuracy：0.5740131578947368。9,120 条折外预测在两套实现间逐行一致；54 次拟合的训练行、家族、参数与预处理统计对齐；保存模型回放与独立最终模型一致。该数值来自原案例包的 Linux 冻结运行；在本机 macOS 复跑中，硬预测逐字节一致，仅概率导出的 ROC-AUC 相差约 2.03e-7、折外概率最大差约 1.98e-5，该差异被原样保留。

**结论边界。** 结果只支持所测流程在该案例中的数值符合性与可复现性；不构成新算法、性能领先、临床或人群结论，也不代表工具包全部功能已在所有平台验证。

## 1. 引言

机器学习工具的正确性并不只体现在最终分数上。对研究者而言，同样关键的是：划分是否真的按参与者隔离、预处理是否只在训练折内拟合、模型与参数是否只依据训练侧证据选择、折外预测与指标是否能被独立复算、保存的模型是否能忠实回放。在真实行为数据上用一个固定协议检验这些环节，比只用合成数据更能暴露数据转换与分组语义上的问题；而按参与者（而非按行）划分，避免把同一人的相邻片段分到训练和测试两侧，是这类数据最基本的防泄漏要求。

本报告记录一个此类案例：在公开的 UCI *Daily and Sports Activities*（DSA）数据上，以事先冻结的协议运行 PsyML，并与不导入 PsyML 的独立 scikit-learn 实现逐项核对。它属于软件维护与流程验收，**不是**新方法论文、不是原论文基准复现，也不是同类工具比较；不涉及心理构念测量、临床、因果或人因效果结论。

## 2. 数据与方法

### 2.1 数据来源、许可与归属

- 数据：Barshan, B. & Altun, K. (2010). *Daily and Sports Activities* [Dataset]. UCI Machine Learning Repository. DOI [10.24432/C5C59F](https://doi.org/10.24432/C5C59F)，官方页 <https://archive.ics.uci.edu/dataset/256/daily+and+sports+activities>。
- 许可：官方数据页标示 CC BY 4.0；下载的 ZIP 内未发现附带额外限制的成员。作者未对 PsyML 或本案例作背书。
- 原始论文：Altun, K., Barshan, B., & Tunçel, O. (2010). Comparative study on classifying human activities with miniature inertial and magnetic sensors. *Pattern Recognition*, 43(10), 3605–3620. <https://doi.org/10.1016/j.patcog.2010.04.019>。
- 原始 ZIP 170,800,010 字节，SHA-256 `f42ad7744ecf14151c9fa3a86dfb5b24de9d7cb7ffe956ef5de242983459c77e`；只从官方地址下载，并在读取前核对完整哈希。

### 2.2 参与者、类别与记录

数据包含 8 位 20–30 岁成人的 19 类日常与运动活动记录，每人每类 60 个五秒片段，共 9,120 段，每段原始形状为 125 行 × 45 列。文件夹 `p1..p8` 即正式参与者编号。**8 位参与者才是独立单位；9,120 段不能被当作 9,120 个独立个体**，相邻片段之间也可能相关。官方档案没有训练/测试划分。

### 2.3 特征构建

按固定顺序只读取 `data/a01..a19/p1..p8/s01..s60.txt` 这 9,120 个成员：缺失、重复、额外非目录成员、形状不是 125×45 或出现 NaN/无穷都终止转换，不做静默删除。每段只取前 6 列（躯干加速度 x/y/z 与躯干角速度 x/y/z），逐段、逐通道计算均值与总体标准差 `std(ddof=0)`，按"每通道均值后标准差"的顺序得到 12 个特征；不使用其余传感器与磁力计，不做滤波、PCA、特征筛选或跨段归一化。派生 CSV 为 UTF-8、LF、无索引，`float_format %.17g`；`segment_id`、`subject_id`、`activity` 只作回联、分组与目标，绝不进入特征列。

### 2.4 训练折内预处理

每次拟合都从头构建 `ColumnTransformer(numeric) → SimpleImputer(strategy='median') → StandardScaler → estimator`，只在对应的训练行上拟合。案例没有缺失值，但保留可见的预处理管道，以便核验其拟合范围。

### 2.5 外层与内层划分

- 外层：`GroupKFold(n_splits=4, shuffle=False)`，按原始行序；4 折的测试参与者依次为 `[4,8]`、`[3,7]`、`[2,6]`、`[1,5]`，每折测试 2,280 段、训练 6,840 段。
- 内层：`StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=20261001 + 外层折号)`（折号从 1 开始），用于在外层训练集内部选择；每折验证 2 人、训练 4 人，且每个分区都包含 19 类。
- 最终全数据选择：同样的 3 折分层分组交叉验证，`random_state=20261001`；它只用于确定全数据最终模型，**不提供新的无偏测试分数**。

### 2.6 候选模型与选择规则

候选家族顺序为 `['dummy', 'logistic_regression']`：`DummyClassifier(strategy='prior')` 与 `LogisticRegression(C∈[0.1, 1.0], solver='lbfgs', max_iter=2000, tol=1e-8, class_weight=None, fit_intercept=True)`，两者的 `random_state` 均为 20261001。每个固定参数都显式写在配置中，`max_candidates=2` 按家族生效，不触发随机抽样。

选择规则：对每个候选，取 3 个内层折 balanced accuracy 的未加权均值；只有**严格大于**才替换当前最优，完全平手保留先出现的家族/候选；不使用外层分数打破平手。任一内折失败即该候选失败，不对成功的内折求均值；若内层选中的模型在外层失败，则整个流程失败，不用其他家族补位。一次完整流程共 54 次拟合：45 次内层拟合 + 8 次家族外层拟合 + 1 次全数据拟合；只使用 CPU、单数值库线程，不启用 SHAP。

### 2.7 指标定义与报告口径

- 主指标：4 个外层折上"内层选中的流程"balanced accuracy 的**未加权折均**。折间标准差（`ddof=0`）只作描述性变异报告，**不能当作标准误或人群推断的置信区间**。
- 次要：同口径 accuracy 与 macro-F1（`zero_division=0`）；折外预测汇总（pooled）的混淆矩阵与 macro-F1；procedure−Dummy 的同折配对差；8 位参与者各自的 balanced accuracy（描述性）。
- **折均与 pooled 分开报告**：本案例各折大小相等且类别均衡，pooled accuracy/BA 恰好等于折均，但 macro-F1 不同，见 3.1。
- 全数据最终模型只在所有分析行上拟合，其回放检验的是持久化与 schema 行为，**不是**外部验证，也不能当作泛化成绩。

### 2.8 独立参考实现与观察性补充

- 独立参考实现（[`tools/cases/reference_dsa.py`](../tools/cases/reference_dsa.py)）**不导入 PsyML**，只用公开 scikit-learn API 重建划分、预处理、内层选择、折外预测与最终拟合；测试中以 AST 静态检查其导入，并人工审查数据流。它与 PsyML **共用 scikit-learn 的估计器、切分器与指标实现**，核对的是工作流而不是 sklearn 求解器本身。
- 观察性补充运行（[`tools/cases/observe_psyml_dsa.py`](../tools/cases/observe_psyml_dsa.py)）只包装并记录 PsyML 的生产调用，用于补全折成员与 54 次拟合记录；它不冒充独立实现。
- 比较器（[`tools/cases/compare_dsa.py`](../tools/cases/compare_dsa.py)）按事先声明的容差核对成员、类别集合、组隔离、拟合范围、预处理统计、候选参数与分数、选择轨迹、折外预测与概率、指标与保存模型回放；它允许导入 PsyML 来检查保存/加载行为，**不冒充独立实现**；此外用类别 TP/FN/FP 计数按定义复算 balanced accuracy 与 macro-F1。任何失败保留差异并以非零码退出，见附录 D。

### 2.9 工程负控与验收

在真实数据上执行四类负控：普通行划分的组泄漏审计（应被补充审计器识别；PsyML 本体对该情形只警告、不硬阻断，不能写成产品自带保障）；固定外折 1 的标签循环旋转（内层分数、选择、训练统计与测试预测/概率必须不变）；固定外折 1 的测试特征整体加 1000（训练统计与内层选择必须不变，预测可变）；以及一次人内打乱标签的 canary（按 `subject_id` 升序、单一 `default_rng(20261002)`，保持特征与行序；预设告警阈值为折均 BA > 0.10）。canary 是工程扰动，**不是置换检验**，也不估计假阳性率。

## 3. 结果

### 3.1 主要数值

以下数值来自原案例包在 Linux 云环境的冻结运行（包内记录），并由本机 macOS 复跑核对（3.5）。

| 指标 | 值 |
| --- | --- |
| 外层 1（测试参与者 4、8）balanced accuracy | 0.5394736842105263 |
| 外层 2（测试参与者 3、7）balanced accuracy | 0.4986842105263158 |
| 外层 3（测试参与者 2、6）balanced accuracy | 0.6644736842105264 |
| 外层 4（测试参与者 1、5）balanced accuracy | 0.5934210526315788 |
| **主指标：折均 balanced accuracy** | **0.5740131578947368** |
| 折均 macro-F1 | 0.5513874769696934 |
| 折间标准差（ddof=0，BA / macro-F1） | ≈ 0.062103 / ≈ 0.068311 |
| 同折 Dummy balanced accuracy | 1/19 = 0.05263157894736842 |
| procedure − Dummy 折均差 | 0.5213815789473684 |
| pooled 折外 macro-F1 | 0.5702035749465654 |
| 参与者折外 balanced accuracy 范围 | 约 0.4553–0.6658（8 人，描述性） |

0.574 左右的主指标是本案例在既定协议下的结果，用于检验流程是否被正确执行；它不是新算法成果，也不应与使用不同传感部位、不同特征或不同划分的论文数值直接比较高低。

### 3.2 逐折结果与选择轨迹

四次外层与最终全数据的内层选择均为 `logistic_regression, C=1.0`，内层均值依次为 0.5381578947368421、0.577485380116959、0.5399122807017545、0.508187134502924，最终选择为 0.5450779727095517。外层家族排行仅供探索，不能当作新的"最佳模型"无偏成绩。

### 3.3 软件与参考实现符合性

- 9,120 条折外预测在两套实现间逐行一致（案例包记录为完全一致；本机复跑的硬预测文件与冻结结果逐字节一致，见 3.5）。
- 54 次拟合的训练行、家族、参数与预处理统计全部对齐；比较器还按训练行直接复算 median/mean/var 以及类别 TP/FN/FP 定义的 BA 与 macro-F1。
- PsyML 与独立参考的概率最大绝对差为 0；原生 CLI 与观察性重跑导出的预测、折指标、搜索与选择文件逐项一致。
- 可信加载保存模型后，其类别与概率与独立最终模型一致；输入列重排不影响结果，缺少特征被拒绝。回放使用的是原分析行，**不构成外部验证**。

### 3.4 负控结果

| 类别 | 数量 | 结果 | 内容摘要 |
| --- | --- | --- | --- |
| 数值验收 | 26 | 通过 | 成员、拟合、预处理、选择、折外预测/概率、保存模型回放等逐项核对 |
| 结构核验 | 4 | 通过 | 分区无交叉且覆盖源行；每分区含 19 类；内层范围严格属于对应外层训练行；角色列被排除 |
| 导出核验 | 2 | 通过 | 概率列顺序按 `classes_`；保存模型元数据与独立最终模型一致 |
| 真实数据负控 | 7 | 通过 | 行划分组泄漏被补充审计器识别；固定外折 1 标签旋转不改变内层分数/选择/训练统计/测试预测与概率；外折 1 测试特征 +1000 不改变训练统计与内层选择 |
| 打乱标签 canary | 6 + 1 | 通过 | 完整嵌套流程与独立参考一致；折均 BA = 0.0532894736842105，未触发 >0.10 告警；打乱仅改目标列 |

对组泄漏需区分两层事实：PsyML 在"提供分组列却选择普通 K 折"时给出警告，但**不是**产品本体硬阻断；本案例的故障注入由补充审计器识别。此外，仓库现有的外层排名扰动/失败补位测试（`tests/test_nested_family_selection.py`）在本轮维护中实际运行并通过。

### 3.5 跨平台核验

本仓库整合期间，在 macOS（aarch64）上使用与冻结案例相同的 parity 版本（Python 3.12.14、scikit-learn 1.8.0、SciPy 1.17.0 等）重新执行了全部阶段，记录见 [`expected/reverification_macos.json`](../examples/public/dsa_group_nested_v1/expected/reverification_macos.json)。

- 原生 CLI、独立参考、观察审计、比较与负控的退出码为 0、0、0、1、0；比较阶段的 1 只来自下述跨平台指标差异，属有意保留。
- 9,120 条折外硬预测与冻结结果**逐字节一致**（`predictions.csv` SHA-256 `36c39a34c9317d568c79f37de17c2b566d10f24db9de0625886f3bda83022b53`）；四次折 BA、选择轨迹、macro-F1 与 Dummy 差都与冻结基线相同。
- 唯一差异出现在由概率导出的 `roc_auc_ovr_weighted`（涉及 `fold_metrics.csv`、`metrics.csv` 与 `metrics_summary.csv` 的 mean/std/min）：外层 1、2 各约 2.03e-7，外层 3、4 为 0。折外概率最大绝对差为 1.9762588500393807e-05（逐折最大值：1.98e-5、8.70e-6、6.56e-6、5.23e-6；173,280 个概率单元中 97,415 个超过 1e-10）。
- 对齐与定位核查：两侧概率列顺序均为 `probability_1..19`，最终模型 `classes_` 均为 1..19；`row_index` 序列与 `fold/observed/predicted/model` 完全一致。把**冻结的概率矩阵**在 macOS 上重新计算 ROC-AUC，与冻结报告值只差 ≤1.11e-16，说明指标计算本身跨平台一致；差异跟随拟合概率——两个最终模型的系数最大差约 3.07e-5、截距最大差约 7.08e-5、全数据概率最大差约 3.03e-6。
- **该差异的原因尚未确认，可能与平台数值实现有关**；未做实现级根因实验，也不写成"已由某个线性代数库造成"。本案例不宣称跨平台数值等价，容差与基线均未因此修改。
- canary 的 BA 与打乱 CSV 哈希均与冻结值一致；外折特征 +1000 后预测改变 2,122 条，与 Linux 结果相同。运行后按冻结的 423 个仓库文件清单复核，无 Python/GUI/测试/锁文件差异；仅本整合有意编辑的 3 个公开文档不同。

### 3.6 测试环境、警告与 CI

三个环境分开记录，避免混同：

- **案例 parity 环境**：Linux x86_64 与 macOS aarch64 上的 Python 3.12.14、scikit-learn 1.8.0 等，用于 3.1–3.5 的数值；不是官方锁定环境。
- **仓库本地 `.venv`**（Python 3.12.13，scikit-learn 1.9.0，另装 explain extra `shap 0.52.0`）：`ruff` 通过，默认套件 `pytest -q` **1217 passed**（含本案例 24 项契约/集成测试），隐私审计通过；SHAP 解释测试在此环境实际执行。
- **官方 `uv.lock` 环境**（独立路径，`UV_PROJECT_ENVIRONMENT=… uv sync --locked --group dev`，未修改 `uv.lock`）：`pytest -q` **1152 passed, 2 skipped**，退出码 0。2 项跳过是 `tests/test_explanation*.py` 的模块级 `pytest.importorskip("shap")`，因为该命令按仓库规范不安装 explain extra——这两项不记为通过；该环境未复跑 DSA 案例本身。

案例运行中的 Python 警告：原生 CLI 的 `warnings.json` 保留一条科研解释提示（主指标评估的是嵌套选择流程，家族排行仅供探索）；独立参考、观察与负控的警告列表为空；没有 ConvergenceWarning；所有阶段 stderr 为空。

推送后，仓库的 Core CI（运行 [36880091260](https://github.com/GuGuGu-coocoo/PsyMl_Toolkit/actions/runs/36880091260)）在 Windows、macOS 与 Linux 三个平台全部通过（lint、测试、Godot GUI 套件、wheel 构建与 smoke）。CI 通过说明的是仓库现有自动化检查在该提交上通过，**不代表 Windows 已复跑本 DSA 案例**，也不替代真实窗口与打包应用的人工验证。

## 4. 讨论

### 4.1 证据支持什么

本案例支持的结论是：在记录的代码版本、协议与环境中，PsyML 的参与者分组嵌套流程与一份独立重建的 scikit-learn 实现给出相同的切分、选择与预测结果，训练折内预处理与持久化行为可被逐项核对；工程负控没有发现该流程中的组泄漏或选择污染迹象。它也确认了仓库只在本地生成派生数据、不重新分发数据。

### 4.2 与既有研究的区别

原论文比较多种分类算法，使用胸部、双臂、双腿共 5 个传感单元（含磁力计）、经 PCA 处理的特征，并考察随机子采样、随机 10 折与按参与者留一法等多种评估方式；数据输入、特征、模型范围与划分协议均与本案例不同。本案例只取单个躯干单元的 12 个固定统计量，固定 4 折分组外层与 3 折分层分组内层，候选只有 Dummy 与逻辑回归，且不追求与原论文或任何其他研究比较分数。原论文已经评估过新参与者泛化；本案例不是"首次引入"分组验证，也不对本案例数值作领域性能解读。

### 4.3 局限与未验证范围

- 8 位参与者的公开记录不足以支持临床、普遍人群或自然生活场景的结论；本案例不是外部验证，也不覆盖其他采集协议、设备或人群。
- 独立参考与 PsyML 共用 scikit-learn 求解器；打乱标签 canary 是单次工程扰动，不是置换检验，不估计假阳性率，也不证明不存在泄漏。
- 跨平台差异的原因尚未确认；报告保留原始差异，不将其解释为软件缺陷或改进。
- 未执行：Godot/GUI 自动化检查以外的真实窗口检查、Windows 与 macOS 打包应用、官方 `uv.lock` 环境中的 DSA 案例复跑、SHAP 解释在官方锁定环境的执行、非 CSV 输入格式、用户研究与外部数据验证、完整安全审计，以及原始大 ZIP 的重新下载与转换（`prepare_dsa.py` 的严格枚举、哈希、形状、有限性与计数拒绝行为由合成小 ZIP 的契约测试覆盖）。

### 4.4 图形可读性

原生导出的 19 类混淆矩阵图在默认紧凑尺寸下，相邻三位数标注与横轴标签拥挤，部分数字视觉上粘连；底层 CSV、总计与指标均正确。这是导出图的可读性限制，**不是数值失败，也不代表 GUI 已被测试**。原图原样保留；另有一张明确标注为独立重绘的放大图（使用完全相同的 CSV，全部 361 格已程序化核对），不属于生产输出。如需按类别数自适应 figsize/字号或减少零值标注，应先给出最小变更方案与覆盖三语、多类别图的验证计划，再单独决定。

## 5. 数据与代码可用性及复现步骤

- 数据按 CC BY 4.0 从 UCI 官方地址获取；仓库**不重新分发**数据，派生 CSV 只在本地的 Git 忽略目录 `examples/public/data/` 生成。归属与修改说明见 `examples/public/dsa_group_nested_v1/expected/` 与 `tools/cases/prepare_dsa.py`。
- 代码以 Apache License 2.0 发布。案例工具位于 `tools/cases/`，配置在 `examples/public/configs/dsa_group_nested_v1.json`，固定期望值在 `examples/public/dsa_group_nested_v1/expected/`，契约与集成测试在 `tests/test_public_dsa_case_contract.py`。
- 复现步骤（仓库根目录）：

```bash
# 1) 可选：从官方 ZIP 生成派生 CSV（严格校验，不执行压缩包内代码）
uv run python tools/cases/prepare_dsa.py --archive <official.zip> --output-dir examples/public/data
# 2–5) 原生 CLI、独立参考、观察审计、比较、负控：完整命令序列见
#      examples/public/dsa_group_nested_v1/README.md
```

CLI 与各工具都要求新的空输出目录，已有结果不被覆盖；`input_path`/`output_dir` 按进程当前目录解析。失败条件包括：任一哈希不符、成员集合异常、非有限值或形状/计数错误、分区组交叉、平手被近似打破、指标或概率超容差、保存模型回放不一致、canary BA > 0.10，或出现未审阅的 stderr 警告。不允许通过修改容差、删折、增加迭代、更换 C、替换数据或改选验证方式来让失败"变绿"。

## 6. 参考文献

1. Barshan, B., & Altun, K. (2010). *Daily and Sports Activities* [Dataset]. UCI Machine Learning Repository. <https://doi.org/10.24432/C5C59F>（官方数据页：<https://archive.ics.uci.edu/dataset/256/daily+and+sports+activities>；许可：<https://creativecommons.org/licenses/by/4.0/>）
2. Altun, K., Barshan, B., & Tunçel, O. (2010). Comparative study on classifying human activities with miniature inertial and magnetic sensors. *Pattern Recognition*, 43(10), 3605–3620. <https://doi.org/10.1016/j.patcog.2010.04.019>
3. scikit-learn developers. Common pitfalls and recommended practices（数据泄漏）.<https://scikit-learn.org/stable/common_pitfalls.html>
4. scikit-learn developers. Nested versus non-nested cross-validation.<https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html>
5. scikit-learn developers. Tuning the hyper-parameters of an estimator（参数搜索）.<https://scikit-learn.org/stable/modules/grid_search.html>
6. scikit-learn developers. Cross-validation: evaluating estimator performance（分组交叉验证）.<https://scikit-learn.org/stable/modules/cross_validation.html>
7. Collins, G. S., et al. TRIPOD+AI statement: updated guidance for reporting clinical prediction models that use regression or machine learning methods. *BMJ*, 385, e078378. <https://www.bmj.com/content/385/bmj-2023-078378>

## 附录

### A. 冻结协议要点

- 协议版本 `psyml_dsa_group_nested_v1`；冻结时间 2026-10-01 11:48:43 UTC；首次真实数据执行开始于 11:49:02.979300 UTC。配置在建模前冻结，未按分数修改。
- 外层 `GroupKFold(4, shuffle=False)`；内层与全数据选择 `StratifiedGroupKFold(3, shuffle=True)`，种子分别为 20261001+折号与 20261001；候选与选择规则见 2.6；预期 54 次拟合。
- 冻结配置原模板 SHA-256 `a156dee0bde4e65f4e89ceef28320faa6931ded8dc9eccab62b514b2dba69941`（含当时工作路径，仅作法证核验）；仓库示例配置保留全部科学字段并改用相对路径。

### B. 哈希与固定期望值

| 对象 | SHA-256 |
| --- | --- |
| 原始 ZIP | `f42ad7744ecf14151c9fa3a86dfb5b24de9d7cb7ffe956ef5de242983459c77e` |
| 派生 CSV | `75a5fe87a58f4cfde777d914d674362b5148854a3c7064d8c686c0e25c3a047e` |
| 打乱标签 CSV（canary） | `e02699c680cfaa6ec91477c79fff68d7229013d7cc9f7c2acb2ddc4b0d961d86` |
| 本机 macOS 复跑的主预测文件 | `36c39a34c9317d568c79f37de17c2b566d10f24db9de0625886f3bda83022b53`（与冻结结果逐字节一致） |

冻结配置、期望数值、折成员与容差的机器可读版本见 `examples/public/dsa_group_nested_v1/expected/`（其中 `case_summary.json` 给出主指标与验收计数，`fold_membership_expected.json` 给出折参与者与选择轨迹，`golden_hashes.json` 记录冻结产物哈希）。

### C. 环境

案例 parity 环境：Python 3.12.14；NumPy 2.3.5；pandas 2.2.3；scikit-learn 1.8.0；SciPy 1.17.0；joblib 1.5.3；matplotlib 3.10.8；pyreadstat 1.3.6；`OPENBLAS_NUM_THREADS`、`OMP_NUM_THREADS`、`MKL_NUM_THREADS` 均为 1；未安装 pyarrow 与 SHAP。该环境为隔离 venv 中以 `--no-deps` 安装固定源码，未重建官方 `uv.lock`。本机 macOS 复跑使用相同 parity 版本；其 numpy/scipy 数值库配置与两侧环境记录保存在本机 Git 忽略的证据归档中。仓库本地 `.venv` 与官方 `uv.lock` 环境的测试结果见 3.6。

### D. 验收工具的行为与失败入口

- 比较器为每类验收表定义**固定必需列契约**，在生产侧与参考侧分别检查：任一侧缺列、两侧同时缺同一关键列、行数不一致、出现未登记的参考独有列，均判失败并报告表名与缺失列；生产表每一列还必须在参考表中存在并逐项核对。
- 数值字段规则：任何 ±Inf、单侧 NaN、或必须有限的统计量中的 NaN 都判失败；仅允许空的可空诊断列（如空 `error` 列）与 `status=failed` 候选行的 NaN 分数；两侧 dtype 不一致同样失败。参考实现多出的 `inner_scores` 诊断列不被跳过，而是核验其折数、有限性与与候选分数一致的均值。
- 诊断核验与直接指标复算先检查各自实际依赖列（`status/score/inner_scores`、`fold/accuracy/balanced_accuracy/f1_macro`）；缺列时以失败条目报告表名、缺失列与原因，不中断报告写出，仍可执行的独立检查继续运行。
- 容差：同环境指标绝对差 ≤1e-12；预处理 atol=rtol=1e-12；概率 atol=1e-10、rtol=1e-8。这些容差未因跨平台差异而调整。
- 相关回归测试在 `tests/test_public_dsa_case_contract.py`；详细验收输出与失败记录入口在本机归档 `docs/internal/completed/reports/2026-10-01-dsa-case-macos-reverification/`（Git 忽略，含 `checks/`、`diff/`、`logs/`、`environment/` 与 `handoff/`）。

### E. 保留的差异、警告与失败记录

- 跨平台差异：`roc_auc_ovr_weighted` 约 2.03e-7 与外折概率最大约 1.98e-5 被保留并公开；原因尚未确认（见 3.5），未以此调整任何容差或基线。
- 比较器缺陷修复记录：首版辅助函数曾把参考诊断列误判为不一致并把 `inf` 序列化进 JSON 导致运行中断；随后发现"必需列依赖生产表列名"以及"诊断/复算缺列抛异常使报告写不出"两处问题，均已修复并补充回归测试与整流程集成测试。
- 案例包首轮便携复跑曾因字体缓存目录不可写而在严格 stderr 门槛处退出 1，随后只调整子进程缓存路径并完整重跑通过；该记录属于运行器环境配置，不是训练逻辑错误。
- 本案例没有发现需要修改 PsyML 核心数值流程的缺陷。
