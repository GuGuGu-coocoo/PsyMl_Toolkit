# PsyML 公开行为数据验证：DSA 按参与者分组嵌套案例

[English](VALIDATION_DSA_EN.md) · [Français](VALIDATION_DSA_FR.md)

本文件记录一个可复算的软件验证案例：在公开的 UCI *Daily and Sports Activities*（DSA, UCI 256）数据上，用预先冻结的按参与者分组嵌套交叉验证协议运行 PsyML，并与一个不导入 PsyML 的独立 scikit-learn 实现逐项核对。案例的可运行示例见 [`examples/public/dsa_group_nested_v1/`](../examples/public/dsa_group_nested_v1/README.md)，固定期望值见该目录的 [`expected/`](../examples/public/dsa_group_nested_v1/expected/README.md)。

## 1. 目的与验证范围

本案例用于项目维护与流程验收：检查数据转换、切分成员、训练折内预处理、嵌套选择、折外预测、指标计算、混淆矩阵导出以及模型保存/加载回放是否按冻结协议执行，并且两套实现是否给出相同的数值结果。它**不是**新算法、不是原论文基准复现、不是同类工具比较，也不支持心理构念测量、临床、因果或用户错误减少方面的结论。

验证范围限于案例实际覆盖的部分：

> 我们在一份公开日常活动数据上预先固定按参与者分组的嵌套验证协议，使用独立 scikit-learn 工作流核对软件的切分、训练折预处理、内层选择、折外预测、评估和模型持久化。冻结环境中两者逐行预测及预处理统计一致，并通过定向扰动测试。此案例提供所测流程的数值符合性与可复算证据；未对算法新颖性、其他人群外部效度或用户错误减少作经验断言。

作为研究软件维护工作，本案可表述的贡献范围是"研究设计、训练折内预处理、嵌套选择、评估语义与复现产物的统一执行与记录"；这不构成新模型、性能领先或人因效果声明。

## 2. 版本、时间与环境

- 固定源码提交：`de33abfe52ccfee67f461a850edd00a14d2fbfaa`（PsyML `0.3.0`）。
- 协议冻结时间：2026-10-01 11:48:43 UTC；首次真实数据执行开始于 11:49:02.979300 UTC。建模前冻结，未按分数修改方案。
- 冻结配置原模板 SHA-256：`a156dee0bde4e65f4e89ceef28320faa6931ded8dc9eccab62b514b2dba69941`（含当时的工作路径，仅作法证核验；仓库示例配置保留科学字段并改用相对路径）。
- 案例 parity 环境（Linux x86_64）：Python 3.12.14、NumPy 2.3.5、pandas 2.2.3、scikit-learn 1.8.0、SciPy 1.17.0、joblib 1.5.3、matplotlib 3.10.8、pyreadstat 1.3.6；`OPENBLAS_NUM_THREADS`、`OMP_NUM_THREADS`、`MKL_NUM_THREADS` 均为 1。未安装 pyarrow 与 SHAP。
- 该环境是**案例 parity 环境**：在一个隔离 venv 中安装上述依赖并以 `--no-deps` 构建固定源码，**没有**重建仓库官方 `uv.lock`。仓库官方锁定环境（当前 `uv.lock` 在 Python ≥ 3.11 上为 scikit-learn 1.9.0）属于另一个环境，未用于本案的逐值基线。
- 仓库内运行 `uv run psyml ...` 使用仓库当前环境。换版本或换平台运行得到的是**新的验证结果**，不能覆盖 `expected/`，也不能放宽容差。

## 3. 数据、归属与转换

- 数据：Barshan, B. & Altun, K. (2010). *Daily and Sports Activities* [Dataset]. UCI Machine Learning Repository. DOI <https://doi.org/10.24432/C5C59F>；官方页 <https://archive.ics.uci.edu/dataset/256/daily+and+sports+activities>；许可 CC BY 4.0（依据官方数据页；ZIP 内未发现附加限制成员）。作者未对 PsyML 或本案例作背书。
- 结构：8 名 20–30 岁成人参与者、19 类活动、每人每类 60 个五秒片段，共 9,120 段；每段原始形状 125×45。文件夹 `p1..p8` 即正式参与者编号。**8 名参与者才是独立单位，9,120 段不能当作 9,120 个独立个体**；相邻片段可能相关，官方档案没有训练/测试划分。
- 原始 ZIP：170,800,010 字节，SHA-256 `f42ad7744ecf14151c9fa3a86dfb5b24de9d7cb7ffe956ef5de242983459c77e`；只从上述官方地址下载并先核对完整哈希。
- 转换：只读取 `data/a01..a19/p1..p8/s01..s60.txt` 这 9,120 个成员（严格枚举；缺失、重复、额外非目录成员、形状不是 125×45 或出现 NaN/无穷都终止），每段只取前 6 列（躯干加速度 x/y/z 与躯干角速度 x/y/z），逐段逐通道计算 mean 与总体标准差 `std(ddof=0)`，按“每通道 mean 后 std”的顺序得到 12 个特征。不做滤波、PCA、特征筛选或跨段归一化。
- 派生 CSV：2,343,871 字节，SHA-256 `75a5fe87a58f4cfde777d914d674362b5148854a3c7064d8c686c0e25c3a047e`；列固定为 `segment_id,subject_id,activity` + 12 特征；UTF-8、LF、无 index、`float_format %.17g`；每 participant×activity 恰 60 行、每类 480 行、每人 1,140 行。另有一份独立检查用 `csv.reader` + `math.fsum` 复算全部 12 个统计量，最大绝对差 1.2434497875801753e-14（atol=rtol=1e-12）。
- 角色列 `segment_id`、`subject_id`、`activity` 只作回联与分组/目标，**绝不进入 `feature_columns`**。
- 仓库不分发数据：`examples/public/data/` 被 Git 忽略，派生 CSV 只在本地生成；`tools/cases/prepare_dsa.py` 只提交下载/转换方式、归属与哈希，不下载、不整树解压、不执行压缩包内代码。

## 4. 冻结协议与选择规则

- 外层：`GroupKFold(n_splits=4, shuffle=False)`，按原始行序；4 折测试参与者依次为 `[4,8]`、`[3,7]`、`[2,6]`、`[1,5]`（每折测试 2,280 段、训练 6,840 段）。
- 内层：`StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=20261001 + 外层折号)`（折号从 1 开始，即 20261002…20261005），每折验证 2 人、训练 4 人，且每个分区都含 19 类。
- 最终全数据选择：同样的 `StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=20261001)`；它**不提供新的无偏测试分数**。
- 每次拟合都从头新建 `ColumnTransformer(numeric) → SimpleImputer(strategy='median') → StandardScaler → estimator`，只在对应训练行上 fit。
- 候选：家族顺序 `['dummy','logistic_regression']`；`DummyClassifier(strategy='prior', random_state=20261001)`；`LogisticRegression(C∈[0.1, 1.0], solver='lbfgs', max_iter=2000, tol=1e-8, class_weight=None, fit_intercept=True, random_state=20261001)`；`max_candidates=2` 按家族生效，不触发随机抽样。
- 选择：内层 balanced accuracy 的未加权均值；**严格大于**才替换，完全平手保留先出现的家族/候选；不使用外层分数打破平手。任一内折失败即该候选失败（不平均成功内折）；内层赢家在外层失败则整个流程失败，不用其他家族补位。
- 规模：一个完整流程 45 次内层 fit + 8 次家族外层 fit + 1 次全数据 fit = 54 次；CPU、单数值库线程、不使用 SHAP。

## 5. 三种执行的角色与代码边界

| 执行 | 位置 | 角色 | 边界 |
| --- | --- | --- | --- |
| 原生 CLI 主结果 | `uv run psyml run --config ...` | 唯一主结果 | 生产入口，不修改源码 |
| 独立参考 | [`tools/cases/reference_dsa.py`](../tools/cases/reference_dsa.py) | 用公开 scikit-learn API 独立重建同一协议 | **不导入 psyml**，不复制其 runner 调用链；测试用 AST 静态检查导入，并人工审查数据流 |
| 观察性补充 | [`tools/cases/observe_psyml_dsa.py`](../tools/cases/observe_psyml_dsa.py) | 补全生产调用中的折成员与 54 次拟合记录 | 只包装并记录生产函数，不改变输入/切分/模型/阈值；**不冒充独立实现** |
| 比较验收 | [`tools/cases/compare_dsa.py`](../tools/cases/compare_dsa.py) | 26 项数值 + 4 项结构 + 2 项导出核验 | 允许导入 PsyML 来观察模型保存/加载；失败保留差异并非零退出 |
| 工程负控 | [`tools/cases/check_dsa_controls.py`](../tools/cases/check_dsa_controls.py) | row-split 审计、固定外折 1 扰动、shuffled-label canary | 诊断用途；扰动分数从不用于修订协议或选模型 |

独立参考与 PsyML 共用 scikit-learn 的估计器、切分器与指标实现，因此核对的是工作流而不是 sklearn 求解器本身；比较脚本另用类别 TP/FN/FP 计数按定义复算 balanced accuracy 与 macro-F1，作为指标层面的交叉核验（不是第二次独立拟合）。

比较器不采用"只比较部分列"：生产表的每一列都必须在参考表中存在并逐项核对；行数不一致、任一生产列缺失、或出现未登记的参考独有列都会判失败。数值字段另有显式规则：任何 ±Inf、单侧 NaN、或**必须有限的统计量**中的 NaN（即使两侧一致）都判失败；只有两类空值被允许——登记为可空的诊断列（如空 `error` 列）与 `status=failed` 候选行的 NaN 分数；两侧 dtype 不一致（数值 vs 文本）同样判失败。参考实现有意多出的 `inner_scores` 诊断列不会被跳过，而是必须为每个已完成候选提供与内层折数一致的有限分数列表，且其未加权均值等于该候选分数，否则该项检查失败。该策略的由来：首版辅助函数要求两表列集合完全一致，把参考的诊断列误判为不一致并把 `inf` 序列化进 JSON 导致运行中断；修正为上述"所有生产列必须核对、已登记诊断列单独核验、未登记列判失败、非有限值显式拒绝"的行为，并在 `tests/test_public_dsa_case_contract.py` 保留三组回归测试：不可掩盖失败（缺列/未登记列/数值漂移/行数不一致必须失败）、非有限数值拒绝（单侧 NaN、统计量双侧 NaN、Inf、dtype 不一致）、参考诊断列必须被核验。

## 6. 指标口径

- 主指标：4 个外层折上"内层选中的流程"balanced accuracy 的**未加权折均**。折间 SD 使用 `ddof=0`，是描述性变异，不是标准误或置信区间。
- 次要：同口径 accuracy、macro-F1（`zero_division=0`）；pooled 折外混淆矩阵（明确标为 pooled）；procedure−Dummy 的同折配对差；8 名参与者各自的 balanced accuracy（描述性）。
- **fold mean 与 pooled 不能混用**：本案例均衡且等大的外折使 pooled accuracy/BA 恰与折均一致，但 macro-F1 不同（pooled 0.5702035749465654 vs 折均 0.5513874769696934）。
- final 全数据模型只在所有分析行上 fit，其回放检验持久化与 schema 行为，**不是**独立外部验证，也不能当泛化成绩。

## 7. 实测数值与选择轨迹（冻结案例记录）

本节数值来自原案例包在 Linux 云环境的冻结运行（包内记录），不是本仓库测试重新产生的数字；本轮本机复跑见第 9 节，未执行项见第 12 节。

| 指标 | 值 |
| --- | --- |
| 外折 1（测试参与者 4、8）balanced accuracy | 0.5394736842105263 |
| 外折 2（测试参与者 3、7）balanced accuracy | 0.4986842105263158 |
| 外折 3（测试参与者 2、6）balanced accuracy | 0.6644736842105264 |
| 外折 4（测试参与者 1、5）balanced accuracy | 0.5934210526315788 |
| **主 balanced accuracy（折均）** | **0.5740131578947368** |
| 折均 macro-F1 | 0.5513874769696934 |
| 折间 SD（ddof=0，BA / macro-F1） | ≈ 0.062103 / ≈ 0.068311 |
| 同折 Dummy balanced accuracy | 1/19 = 0.05263157894736842 |
| procedure − Dummy 平均差 | 0.5213815789473684 |
| pooled 折外 macro-F1 | 0.5702035749465654 |
| 参与者 OOF balanced accuracy 范围 | 约 0.4553–0.6658（8 人，描述性） |

四次外层与最终全数据的内层选择均为 `logistic_regression, C=1.0`，内层均值依次为 0.5381578947368421、0.577485380116959、0.5399122807017545、0.508187134502924，最终选择 0.5450779727095517。外层家族排行榜仅供探索，不能当新的"最佳模型"无偏成绩，也不能据此断言多家族比较无用。

## 8. 验收与负控结果

| 类别 | 数量 | 结果 | 证据 |
| --- | --- | --- | --- |
| 数值验收 | 26 | 通过 | 比较脚本输出 `checks.json` |
| 结构核验 | 4 | 通过 | 分区无交叉且覆盖源行、每分区 19 类、内层范围严格属于对应外层训练行、角色列被排除 |
| 导出核验 | 2 | 通过 | 概率列顺序按 `classes_`；保存模型元数据与独立最终模型一致 |
| 真实数据负控 | 7 | 通过 | 普通 row-split 被补充 group 审计器识别；固定外折 1 标签旋转不改变内层分数/选择/训练统计/测试预测与概率；外折 1 测试特征 +1000 不改变训练统计与内层选择 |
| shuffled-label canary | 6 + 1 | 通过 | 人内打乱标签的完整嵌套流程与独立参考一致；BA = 0.0532894736842105，未触发预设 >0.10 告警；打乱只改目标列（1 项字节级检查） |

其他关键事实：9,120 条折外预测逐行一致；54 次拟合的训练行、家族、参数、预处理统计全部对齐（统计最大绝对差 ≤1e-12，系数/截距差 0）；PsyML 与独立参考的概率最大绝对差 0；原生 CLI 与观察性重跑的文件逐项一致；可信加载后的保存模型回放类别与概率与独立最终模型一致，列重排无影响、缺特征被拒绝；输入 CSV 哈希与冻结值一致。源码中已有的外层排名扰动/失败补位测试（`tests/test_nested_family_selection.py`）在本轮维护中**实际运行**，不是只引用名字。

关于组泄漏：PsyML 对"提供了分组列却选择普通 K 折"会给出警告，但**不是**产品本体硬阻断；本案例中由补充审计器识别该故障注入，不能把审计器行为写成 PsyML 自带保障。

维护期运行记录（2026-10-01，三个环境分开记录）：

- **仓库本地 `.venv`**（Python 3.12.13；numpy 2.5.2、pandas 3.0.5、scikit-learn 1.9.0、scipy 1.18.1、joblib 1.6.0、matplotlib 3.11.1、pyarrow 23.0.1，并装有 explain extra `shap 0.52.0`）：`ruff check src tests tools` 通过；默认套件 `pytest -q` **1212 passed**（当前测试集；本轮较早、尚未加入 3 项比较器回归测试时为 1209 passed）；`tools/audit_repository.py` 隐私审计通过。因装有 explain extra，SHAP 解释测试在此环境实际执行。
- **官方 `uv.lock` 环境**（独立路径，`UV_PROJECT_ENVIRONMENT=… uv sync --locked --group dev`，未改动 `uv.lock`）：Python 3.12.13 与同一锁定版本（scikit-learn 1.9.0、joblib 1.6.0、matplotlib 3.11.1、pyarrow 23.0.1 等）；`pytest -q` **1152 passed, 2 skipped**，exit 0。2 项 skip 是 `tests/test_explanation.py` 与 `tests/test_explanation_cli.py` 的模块级 `pytest.importorskip("shap")`，因为该命令按仓库规范不安装 explain extra——这 2 项**不记为通过**；该环境也**没有**复跑 DSA 案例本身。
- **案例 parity 环境**（Python 3.12.14、scikit-learn 1.8.0、scipy 1.17.0 等）只用于 DSA 案例复算，与上述两个测试环境不同：不能把这套数字写成官方锁定环境或仓库本地环境的结果。

## 9. 本轮 macOS 复跑记录（新增证据）

在本仓库整合工作中，使用固定源码与同一 parity 版本（macOS aarch64、Python 3.12.14、scikit-learn 1.8.0 等，见 [`expected/reverification_macos.json`](../examples/public/dsa_group_nested_v1/expected/reverification_macos.json)）重新执行了全部阶段：

- 原生 CLI、独立参考、观察审计、比较与负控的退出码分别为 0、0、0、1、0；比较阶段的 1 仅来自跨平台的 golden 指标差异（见下）。
- 26 项数值 + 4 项结构 + 2 项导出核验全部通过；9,120 条折外预测与冻结结果**逐字节一致**（`predictions.csv` SHA-256 `36c39a34c9317d568c79f37de17c2b566d10f24db9de0625886f3bda83022b53`）；四次折 BA、选择轨迹、macro-F1、Dummy 差均与冻结基线相同。
- 与冻结基线相比，唯一差异是由概率导出的 `roc_auc_ovr_weighted`（涉及 `fold_metrics.csv`、`metrics.csv`、`metrics_summary.csv` 的 mean/std/min）：外折 1、2 各约 2.03e-7，外折 3、4 为 0。9,120 条 OOF 概率最大绝对差 1.9762588500393807e-05（逐折最大差：折 1 1.98e-5、折 2 8.70e-6、折 3 6.56e-6、折 4 5.23e-6；173,280 个概率单元中 97,415 个超过 1e-10）。硬预测、折成员、选择与所有基于标签的指标完全一致；**本轮不宣称跨平台数值等价**。
- 差异明细已核对并对齐：类别顺序（两侧 `probability_1..19`、两端最终模型 `classes_` 均为 1..19）、样本对齐（`row_index` 序列与 `fold/observed/predicted/model` 完全一致、9,120 条硬预测逐字节一致）、依赖与数值库配置（macOS 侧 numpy/scipy 配置、两侧环境记录）都已保存到本机 Git 忽略的证据归档；逐行/逐折差异与顶层差异行在 `probability_difference_details.json` 与 `probability_differences_by_row.csv` 中。
- 差异定位实验（同一 parity 版本）：把**冻结的概率矩阵**在 macOS 上重新计算 ROC-AUC，与冻结报告值只差 ≤1.11e-16，说明指标计算本身跨平台一致；差异跟随概率值——两个最终模型的系数最大差约 3.07e-5、截距最大差约 7.08e-5、全数据概率最大差约 3.03e-6。结论：差异来自拟合所得的模型参数/概率层面；**原因尚未确认，可能与平台数值实现有关**——未做实现级根因实验，不写成"已由线性代数路径造成"。该差异被原样保留并记录，未用来放宽容差或替换基线；因此本案例不写成"全面通过"。
- shuffled-label canary 的 BA 与打乱 CSV 哈希均与冻结值一致（`e02699c680cfaa6ec91477c79fff68d7229013d7cc9f7c2acb2ddc4b0d961d86`）；特征 +1000 后预测改变数 2,122，与 Linux 结果相同。
- 运行后按冻结的 423 个仓库文件清单复核：无任何 Python/GUI/测试/锁文件差异；仅有本整合工作有意编辑的 3 个公开文档（`README.md`、`docs/TESTING.md`、`examples/public/README.md`）不同。
- 所有阶段 stderr 为空；原生 CLI `warnings.json` 保留一条科研解释提示（主指标评估嵌套选择流程、外层排行榜只供探索），独立参考、观察与负控的 warnings 列表均为空，没有 ConvergenceWarning。

这次复跑是跨平台的补充证据，不取代 Linux 冻结基线；Windows 与官方锁定环境仍未运行。

## 10. 警告、差异与保留的失败

- 案例包的首轮便携复跑曾因新字体扫描无可用缓存目录而在严格 stderr 门槛处退出 1；数值比较已通过，日志完整保留，随后只把子进程缓存路径指向新输出目录下的可写目录并完整重跑通过。这属于 launcher 的环境可移植性配置，不是训练逻辑错误。
- 独立比较脚本首轮曾对空 `error` 列产生 All-NaN 诊断警告；仅修正报告诊断，不影响模型、数据、选择、容差与结果。本仓库的 `tools/cases/*` 已在实现中跳过非有限/空诊断，不把空 error 列当作科学失败。
- 本案例没有发现需要修改 PsyML 核心数值流程的缺陷。

## 11. 原生混淆图的可读性限制

原生导出的 19 类混淆矩阵图在默认紧凑尺寸下，相邻三位数标注与横轴标签拥挤，部分数字视觉上粘连；底层 CSV、总计与指标均正确。这是真实观察到的导出图可读性限制，**不是数值失败，也不代表 GUI 已被测试**。原图原样保留；另有一张明确标注为"独立重绘"的放大图（使用完全相同的 CSV，全部 361 格已程序化核对），该附图不属于生产输出。本仓库不包含生产图形修复；如需按类别数自适应 figsize/字号或减少零值标注，应先给出最小变更方案、覆盖三语与多类别图的验证计划，再单独决定。

## 12. 未运行范围

- 完整 Python 测试集的本案复算由维护期记录覆盖：本次整合实际运行了 `ruff check src tests tools`（通过）、仓库本地 `.venv` 的默认套件 `pytest -q`（1212 passed，含 19 项新增契约测试与现有外层排名扰动/失败补位测试）和 `tools/audit_repository.py`（通过）；官方 `uv.lock` 环境在独立路径按仓库规范复跑测试套件（1152 passed + 2 项 explain-extra 跳过，见第 8 节），但**未**在该环境复跑 DSA 案例。
- Godot/GUI、真实窗口、Windows 与 macOS 独立应用包（本轮 macOS 复跑是源码环境，不是打包应用）。
- SHAP/解释、除 CSV 外的全部输入格式、跨平台容差专项、用户研究与外部数据验证、完整安全审计。
- 原始大 ZIP 的重新下载与转换（本轮用交付的派生 CSV 复算；`prepare_dsa.py` 已由合成小 ZIP 的契约测试覆盖严格枚举、哈希、形状、有限性与计数拒绝行为）。

## 13. 复算命令与失败条件

```bash
# 1) 可选：从官方 ZIP 生成派生 CSV（严格校验，不执行包内代码）
uv run python tools/cases/prepare_dsa.py --archive <official.zip> --output-dir examples/public/data
# 2–5) CLI 主结果、独立参考、观察审计、比较、负控：见
#      examples/public/dsa_group_nested_v1/README.md 的完整命令序列
```

失败条件与底线：任一哈希不符、成员集合异常、非有限值、形状/计数错误、分区组交叉、平手被近似打破、指标/概率超容差、保存模型回放不一致、canary BA > 0.10 或 stderr 出现未审阅警告，都应停止并保留证据。不得用改容差、删折、增迭代、换 C、换数据或挑选另一种验证方式"修绿"。CLI 与各工具都要求**新的空输出目录**，已有结果不被覆盖；`input_path`/`output_dir` 按进程当前目录解析。

## 14. 陈述边界

- 8 名参与者的公开活动记录不足以支持临床、普遍人群或自然生活场景的结论；本案例不是外部验证。
- 独立参考共用 scikit-learn 求解器；canary 是单次工程扰动，不是置换检验，不估计假阳性率，也不证明不存在泄漏。
- 结果只说明所测流程在所记录环境中的数值符合性与可复算性；不宣称新算法、领先性能或用户错误减少。
