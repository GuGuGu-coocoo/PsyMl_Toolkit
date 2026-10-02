# California Housing 回归：下载数据、运行配置、核对结果

[English](CALIFORNIA_VALIDATION_EN.md) · [Français](CALIFORNIA_VALIDATION_FR.md) · [返回 README](../README.md)

这个案例用收入、房龄等 8 个地区特征，预测 1990 年加州人口普查中 20,640 个街区组的房价中位数。这里检查的是 PsyML 与独立 scikit-learn 程序的计算是否一致；这些旧数据不能用来判断今天的房价。

## 下载并在软件里运行

- [下载分析用 CSV：california_housing.csv，2.54 MB](https://raw.githubusercontent.com/GuGuGu-coocoo/PsyMl_Toolkit/main/examples/public/downloads/california_housing.csv)。数据已按参考分析完成转换，可直接导入。
- [下载配置：california_config.json](https://raw.githubusercontent.com/GuGuGu-coocoo/PsyMl_Toolkit/a1450dfc374b8a39109c41f2548fdc0dbcad23c1/examples/public/california_random_nested_v1/california_config.json)。这是含 `verbose=0` 的原始 v1 配置，也是修复后源码验证使用的配置。
- [查看官方原始数据、转换脚本、许可和文件校验值](../examples/public/downloads/README.md)。转换脚本已经公开，核对数据处理时可以使用；运行本例不需要执行脚本。

把 CSV 和 JSON 放在同一个本地文件夹。若浏览器直接显示文件内容，使用“另存为”，保留原来的扩展名。

目前可下载的应用仍为 v0.3.0，尚无包含后续源码修复的新安装包。历史参考对应本页注明的源码环境，不能作为现有下载包的验收结果；若要验证修复后的应用，需要相应安装包。软件可下载平台见 [Releases](https://github.com/GuGuGu-coocoo/PsyMl_Toolkit/releases)。

1. 打开 PsyML，在第 1 页点击“导入配置…”，选择 `california_config.json`。若弹出数据选择窗口，选择刚下载的 `california_housing.csv`；随后核对数据路径，必要时用“浏览…”重选。
2. 核对：20,640 行；回归；目标 `MedHouseVal`；8 个预测变量；不分组；外层 K 折 5 折、内层 3 折；随机种子 `20261002`；以 RMSE 选择；候选模型为 Dummy、Ridge、Random Forest。完整变量名列在下文的数据说明中。
3. 在“2 检查与运行”选择本地结果文件夹，点击“运行分析”。不要改候选参数或为了接近参考值更换随机种子。
4. 完成后到“3 结果”查看 RMSE，点击“打开完整结果文件夹”。保留 `config.json`、`metrics.csv`、`metrics_summary.csv`、`fold_metrics.csv`、预测和环境记录。

五个外层测试每次留出 4,128 行；剩余数据内部再分三次比较模型和参数，选择误差较低的设置。这叫嵌套验证。每行的测试预测都来自没有用该行训练的模型，合起来称为折外预测（OOF）。

## 数字、配置和结果文件

下面是原始 v1 独立参考程序的数值；2026-10-02 修复后源码的真实 GUI 导出已与其逐项核对。每一行都使用同一个 [california_config.json](https://raw.githubusercontent.com/GuGuGu-coocoo/PsyMl_Toolkit/a1450dfc374b8a39109c41f2548fdc0dbcad23c1/examples/public/california_random_nested_v1/california_config.json) 和 `california_housing.csv`，不需要分别运行不同配置。

| 参考值 | 含义 | 在哪里核对 |
| --- | --- | --- |
| 0.5339815958325378 | 主要结果：五个外层测试 RMSE 的平均值。RMSE 是均方根误差，越低越好，单位为 10 万美元 | 本次 `metrics.csv` 的 `rmse`；[参考均值表](../examples/public/california_random_nested_v1/expected/historical_metrics_summary.csv)，`rmse/mean` |
| 0.01850680156369903 | 五个 RMSE 的标准差，描述测试之间的波动；不是置信区间 | 本次 `metrics_summary.csv`；[同一参考表](../examples/public/california_random_nested_v1/expected/historical_metrics_summary.csv)，`rmse/std` |
| 0.3610547401259507 | 五个测试的平均绝对误差（MAE）均值，单位同上 | 本次 `metrics.csv` 的 `mae`；[同一参考表](../examples/public/california_random_nested_v1/expected/historical_metrics_summary.csv)，`mae/mean` |
| 0.7856663784093894 | 五个测试的 R² 均值；衡量预测相对目标波动的拟合程度，不是“准确率 78.6%” | 本次 `metrics.csv` 的 `r2`；[同一参考表](../examples/public/california_random_nested_v1/expected/historical_metrics_summary.csv)，`r2/mean` |
| 0.5343022051161513 | 独立参考合并 20,640 条测试预测后重算的 RMSE；`metrics.csv` 不直接提供这一项，与五折平均值不同 | [合并预测参考表](../examples/public/california_random_nested_v1/expected/historical_pooled_metrics.csv)，`procedure/rmse` |
| 1.153954483920011 / 0.7273658464149191 | 同一配置中的 Dummy / Ridge 各自的外层 RMSE 均值；Dummy 只预测训练数据目标均值，Ridge 是带正则化的线性回归 | 本次 `model_comparison.csv`；[逐模型、逐折参考表](../examples/public/california_random_nested_v1/expected/historical_family_fold_metrics.csv) |

五个外层测试和最终全数据训练均选中 Random Forest。逐折 RMSE 和其他指标见下文“实际结果”，也都属于这份配置。最终模型在全部数据上训练；用它预测原数据不能再算一次独立测试成绩。

## 已记录的原始 v1 验证

[查看本次验证记录：配置与数据校验值、运行环境、270 项检查的汇总及范围](CALIFORNIA_REPAIRED_V1_RECORD.json)。

2026-10-02，修复后的 Linux 源码 GUI 使用原始 v1 配置（保留整数 `verbose=0`），完成导入、保存、重导入、训练及模型加载后的 10 行预测。270 项可观察检查全部通过，未使用 v1.1 兼容修订；外层 RMSE 均值为 0.5339815958325378。GUI 的进度计划为 106 次拟合，未另行记录生产程序每次拟合的调用轨迹。

该次验证的应用代码与公开提交 [948c451](https://github.com/GuGuGu-coocoo/PsyMl_Toolkit/commit/948c451bb0e401c7ffe1c9ab65439ebc3521031b) 相同；后续 `a1450df` 仅增加历史文件的换行保护。环境为 Linux x86_64、Python 3.12.14、scikit-learn 1.8.0、NumPy 2.3.5、pandas 2.2.3、SciPy 1.17.0、Godot 4.6.3，数值库单线程。当前官方锁定环境的 scikit-learn 为 1.9.0，不能把两种环境混写为同一次运行。[a1450df 三平台 CI](https://github.com/GuGuGu-coocoo/PsyMl_Toolkit/actions/runs/36978714686)是自动测试记录，不能代替 macOS、Windows 或安装包的真实窗口验证。

上表链接的历史 CSV 保留了同一原始 v1 独立参考的数值。修复前，原始 v1 的 GUI 运行曾失败；当时省略 `verbose` 的 v1.1 兼容配置另有一次成功记录。下文保留这两段历史，均不改写成这次原始 v1 修复验证。

正式比较使用绝对和相对容差 `atol=rtol=1e-10`，同时核对行、折分、候选模型和有效参数。它不是跨平台结果逐位相同的承诺。界面的舍入数字适合初看，[比较程序与独立参考](../examples/public/california_random_nested_v1/README.md)检查完整导出文件。270/270 只说明这次可观察检查通过；常规导出没有暴露全部内层成员、每次内层拟合的预处理状态或非选中家族的逐行预测。

随机划分会让相邻地区同时进入训练和测试。这个结果不能说明模型能预测新地区、未来市场或因果关系，也不支持住房或信贷决策。原始目标的封顶值保留在数据中。每次新运行都应保留配置、软件与库版本和独立输出目录。

## 历史记录：修复前原始 v1 失败与 v1.1 兼容验证

以下内容记录较早的源码 `a145e07`，与上面的修复后原始 v1 验证分开阅读。历史数值表对应 [california_config_v1_1.json](../examples/public/california_random_nested_v1/california_config_v1_1.json)，配置修订号不代表软件版本。

## 1 结论与范围

PsyML 0.3.0 的 Linux 源码 GUI 已完成本例的数据与配置导入、设置检查、运行、结果查看、完整预测导出、保存模型加载及10行预测。兼容性修订版 v1.1 的实际导出与独立参考在预先冻结容差下通过270项检查。原始配置没有通过：真实窗口发现了 Random Forest 的 verbose 参数整数类型丢失，失败结果已保留，原始重新核查为195/227项通过、32项失败。

测试固定于提交 a145e07c4b6a4135781725c1390f68192ab8e92c。原始测试没有修改 PsyML 源码或公共仓库。公开复算工具可用于检查其他运行；后续源码修复需要对应版本的验证记录。这里验证的是一个有界回归流程，不代表整个工具包、全部参数或其他平台已经通过验证。

## 2 数据和方法

### 数据来源与转换

使用 scikit-learn 指向的 Figshare 文件5976036。官方记录标示 CC BY4.0；作者、版本、许可链接和源文件信息保存在[归属说明](../examples/public/california_random_nested_v1/ATTRIBUTION.md)与[原始公开元数据](../examples/public/california_random_nested_v1/expected/figshare_metadata.json)。来源记录：[Liu, Nelson (2016), version2](https://doi.org/10.6084/m9.figshare.3829992.v2)。原始研究为 [Pace 与 Barry (1997)](https://doi.org/10.1016/S0167-7152(96)00140-X)。

归档大小441,963字节，SHA-256为 aaa5c9a6afe2225cc2aed2723682ae403280c4a3695a2ddda4ffb5d8215ea681，与 scikit-learn 的源文件校验值一致。转换后的 CSV SHA-256为157b6c0d3acd6d93a50c411d0cd4130d8c719ce5eb17b61f1c45300f2af6fc85。

数据含20,640个人口普查街区组、8个数值预测变量及目标 MedHouseVal，没有缺失或非有限值。变量顺序为 MedInc、HouseAge、AveRooms、AveBedrms、Population、AveOccup、Latitude、Longitude。房间、卧室及人口总量按家庭数计算相应均值，目标以10万美元为单位；转换公式见[原始 provenance](../examples/public/california_random_nested_v1/expected/provenance.json)。保留原始行序，没有删行、缩尾、目标变换或特征选择。目标上限5.00001有965行，占4.6754%，原样保留。

### 评分前冻结的设计

- 外层：KFold(5, shuffle=True, random_state=20261002)，每折测试4,128行
- 内层：KFold(3, shuffle=True)，外折1至5分别使用种子20261003至20261007；最终全数据选择使用20261002
- 每次拟合都新建数值列预处理管线，训练折内中位数填补及 StandardScaler，再拟合估计器
- 家族顺序：Dummy(strategy=mean)、Ridge(alpha为0.1/1/10，solver=svd)、RandomForest(100棵树、max_depth=10、min_samples_leaf=3、n_jobs=1)
- 每个候选以内层3折RMSE的等权均值选择；严格更低才替换，精确并列保留配置顺序；外层成绩不参与选择
- 完整计划为90次内层拟合、15次家族外层拟合和1次最终拟合。独立参考实际记录106次；GUI进度显示总任务106，但未额外记录生产端每次fit调用
- 主指标为内层所选流程的外层5折RMSE均值；同时报告MAE、R²、描述性折间标准差(ddof=0)和单列的合并OOF指标
- 固定CPU单线程，不运行SHAP或置换重要性

配置、协议和数据在第一次评分前留存；源哈希及版本记录见[固定证据目录](../examples/public/california_random_nested_v1/expected/README.md)。其中原始协议与配置字节保持不变；仓库相对路径模板仅改变 input_path/output_dir，并以保留 JSON 数字类型的科学字段指纹单独核对。

### 原始失败与 v1.1 修订

原配置显式指定 RF verbose=0。Godot 将 JSON 数值保存为double，变为verbose=0.0；PsyML整数参数正规化列表未包含verbose，scikit-learn拒绝该候选。五个外折及最终全数据选择的RF候选均失败。该运行只剩其他家族，不能作为原冻结流程的有效验证。

v1.1只省略这一设置，令scikit-learn使用相同的默认整数0。修订发生在发现兼容性故障之后，明确单独版本化。再次拟合前已核对有效估计器参数完全相同；科学设计与容差没有改变。原始配置、失败输出、类型审计、单键差异和修订理由均保留。没有把原始失败改写为通过。

### 独立参考与验收

参考脚本不导入PsyML或其帮助函数，用公开scikit-learn API重建切分、每次预处理、模型选择、OOF预测和全数据拟合。静态导入检查及执行源码哈希均留存。两者共享scikit-learn估计器与切分器，因此验证的是工作流组织，不是独立验证底层求解器。

所有有限浮点比较采用评分前冻结的atol=rtol=1e-10；行标识、切分、候选/选择及有效参数按结构要求核对。容差允许CSV和浮点舍入，仍远小于有意义的预测差异；没有根据结果放宽。比较器另有15项故障注入测试。

## 3 实际结果

| 指标 | v1.1结果 |
|---|---:|
| 主指标，外折RMSE均值 | 0.5339815958325378 |
| RMSE折间SD，ddof=0 | 0.01850680156369903 |
| 外折MAE均值 | 0.3610547401259507 |
| 外折R²均值 | 0.7856663784093894 |
| 合并OOF RMSE | 0.5343022051161513 |
| 合并OOF R² | 0.7856041590209227 |
| Dummy外折RMSE均值 | 1.153954483920011 |
| Ridge外折RMSE均值 | 0.7273658464149191 |

| 外折 | 所选家族 | RMSE |
|---|---|---:|
| 1 | Random Forest | 0.5622963920650870 |
| 2 | Random Forest | 0.5191199276807156 |
| 3 | Random Forest | 0.5316590028567558 |
| 4 | Random Forest | 0.5460596387779938 |
| 5 | Random Forest | 0.5107730177821366 |

五个外折及最终全数据选择均选中Random Forest。家族分数只作描述性对照，不应事后据此选择验证方法。折间SD不是标准误或置信区间；RMSE单位是10万美元，不应解释为当前房价误差。

### 数值与持久化证据

- 最终比较270/270项通过，退出码0。实际GUI导出含全部20,640个OOF行，行覆盖与外折归属匹配
- 默认pandas读取CSV时，OOF预测最大差8.88e-16；10行GUI模型预测最大差4.44e-16，均在冻结容差内
- 使用round_trip解析进行诊断时，OOF数值、全部30个候选均值分数和分折指标完全相等；这一诊断不替换冻结的验收解析方式
- 最终保存模型在全数据及重新排列的10行特征上的直接回放，与参考模型完全相等；最终中位数、缩放均值/方差/尺度也完全相等
- 实际GUI预测保持10行sample_id次序及原始列，新增predicted_value。这是列匹配与持久化检查，不是另一个测试集成绩
- 成功运行的warnings仅保留嵌套选择与外部效度说明，30个候选搜索记录均完成，没有失败候选

## 4 真实窗口证据和运行条件

原始完整证据包保存数据导入、预处理和折数、候选网格、随机种子、106任务进度、完成结果、指标、OOF预览、加载模型、列兼容性和预测导出的截图。分析用 CSV 已在[数据下载页](../examples/public/downloads/README.md)提供；大体积截图、模型与结果树不进入 Git；公开目录保留精简结果、失败标识及原始文件哈希。哈希只在对应原文件可用时证明身份，不表示大体积原始包已公开托管。截图证明界面动作与状态；完整CSV/JSON和比较记录支持数值结论。

环境为Linux x86_64、Python3.12.14、scikit-learn1.8.0、NumPy2.3.5、SciPy1.17.0、pandas2.2.3、joblib1.5.3、Matplotlib3.10.8、Godot4.6.3。该历史案例未复跑官方uv.lock环境。这里没有宣称打包版本或macOS/Windows真实窗口已测试。

首次源码启动需要Godot标准资源/类缓存导入；Python包元数据也必须正确安装。另一个界面问题是此云桌面缺少有效默认Documents路径，保存配置时的无效输出目录错误只显示在第2页。设定明确输出目录后可继续。这些准备障碍是原始测试观察，不是所有安装或当前源码的普遍结论。另一个独立的 Python 包元数据安装故障使首次失败运行未完成最终模型导出；该缺失同样保留为失败。

## 5 证据边界

生产端常规导出没有全部内层切分成员、90次内层拟合的预处理状态、每个内层单折分数及所有非所选家族的逐行OOF。参考实现的完整审计不能冒充生产端的逐fit观察。当前270项通过覆盖实际可观察导出和最终模型；没有另跑带观测钩子的生产流程，也没有执行DSA案例的分组泄漏或扰动负控。

本案使用随机按行折分，街区组有空间依赖。相邻地理区域可同时进入训练与测试；不能据此推断地区外推、时间外推、未来市场预测、因果关系或高影响应用适用性。原数据来自1990年人口普查，存在目标封顶；这些限制不因软件数值符合而消失。


## 6 公开复现与集成验证

完整命令见[案例说明](../examples/public/california_random_nested_v1/README.md)。

- prepare_california.py：离线读取用户从官方来源取得的归档，先验证完整 SHA-256，再严格验证两个常规文件成员、形状、有限值和正数分母；不解压、不执行归档内容。转换输出复现原始 CSV 字节，目标封顶与行序不变。
- reference_california.py：独立复算完整106次拟合，导出30个候选均值、90个内层单折分数、完整成员与106次拟合状态；这不是生产端逐次拟合观察。
- compare_california.py：只比较与加载本地可信结果模型，不拟合；遇缺列、非有限值、标识或容差不符返回非零。joblib可能执行代码，禁止传入不可信模型或结果目录。比较器运行环境必须与参考的sklearn版本一致，生产模型元数据也必须一致。
- check_california_controls.py 与契约测试：无下载、无20640行拟合，使用微型合成归档、比较器故障注入和独立参考预处理检查；不构成真实数据泄漏负控、置换检验或新GUI验收。

原始v1仍严格要求GUI保存的原始科学JSON数字类型恒等。只有历史v1.1保留已有的指定计数字段正规化，且会明确报告原始JSON数字类型差异；实际执行配置与有效估计器类型仍须精确一致，不能把无效 verbose=0.0 或比例型 min_samples_* 偷换成整数。

当前仓库锁定环境在Python≥3.11上使用scikit-learn1.9.0，与历史1.8.0不同。参考默认拒绝sklearn版本不一致；显式 --allow-environment-change 可生成单独标识的新验证，但不改变科学设计、容差或历史身份。所有新输出必须进入新目录。

仓库集成新增路径重定位科学身份、运行环境及预测原始列保留等检查，因此新比较器的检查项数可以不同；历史270项记录不变。对保留的旧导出重验会单列于[integration_verification.json](../examples/public/california_random_nested_v1/expected/integration_verification.json)，不宣称重新拟合或重新操作GUI。
