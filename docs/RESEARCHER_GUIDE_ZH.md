# 研究者参考：模型、指标、结果与术语

本指南描述源码检出 **0.3.0**（单一版本源）的行为，其中包含 v0.2.0 之后新增的功能与改进（置换重要性、数据检查与结果解读、单样本 SHAP、拟合系数，以及界面与输出流程改进）。独立包与分发 PDF 的版本与可下载附件以 [Releases](https://github.com/GuGuGu-coocoo/PsyMl_Toolkit/releases) 页面为准；v0.2.0 及更早的独立包与分发 PDF 不包含这些功能与修复，界面与输出布局可能与源码检出不同。版本只有一个维护来源：`src/psyml/__init__.py` 的 `__version__` 常量；`pyproject.toml` 通过 dynamic 读取它，独立包的 `BUILD.json` 由 `tools/build_native.py` 用同一常量生成，界面小字显示同一值（正式版本 `0.3.0` 原样显示，开发版 `0.3.0.dev0` 显示为 `0.3.0-dev`）。运行环境与依赖版本以结果中的 `analysis_manifest.json` 为准，不要用本指南标题推断下载包内容。

[返回 README 中文部分](../README.md#chinese) · **中文** · [English](RESEARCHER_GUIDE_EN.md) · [Français](RESEARCHER_GUIDE_FR.md)

本指南解释 PsyML Toolkit 当前实现中的概念，适合在设置分析或阅读结果时查阅。中文术语附有英文名称，代码名与配置及 CSV 保持一致。内容可离线阅读；外部参考链接需联网。简短公式用于理解，不要求研究者手算。Markdown 阅读器不支持公式时，可直接阅读公式前后的文字说明。

模型是否适用取决于研究问题、数据结构和验证设计，没有对所有研究都最好的模型，也没有通用的“合格分数”。本项目开展预测分析，不自动给出因果结论、显著性检验或临床决策依据。自动生成的摘要（summary）和报告需由研究者复核。

## 查阅导航

- [1. 数据与预处理](#data)
- [2. 本项目支持的模型](#models)
- [3. 分类与回归评价指标](#metrics)
- [4. 验证、调参与最终模型](#validation)
- [5. 结果文件与图形怎么读](#results)
- [6. 常见参数与术语速查](#glossary)
- [7. 常见误解与核查顺序](#checklist)
- [8. 实现依据与延伸阅读](#references)

<a id="data"></a>

## 1. 数据与预处理

| 术语 | 在本项目中的含义 |
| --- | --- |
| 分类（classification） | 预测离散类别，如条件 A/B；目标至少有两类。标签用数字表示，并不使它自动变成回归任务 |
| 回归（regression） | 预测连续数值，如量表总分；MAE/RMSE 的单位与目标变量一致；R² 无单位 |
| 目标变量（target / outcome，`target_column`） | 要预测的列，训练时作为答案，不作为预测变量 |
| 预测变量 / 特征（predictor / feature，`feature_columns`） | 用于预测目标的输入列；标识符、事后才知道的信息可能造成泄漏 |
| 分组变量（group identifier，`group_column`） | 标识同一参与者、家庭或中心的多行记录；从预测变量中排除，不等于分类目标中的类别 |
| 行与独立样本（row / independent sample） | 同一参与者的 10 行记录不等于 10 个独立参与者；验证设计必须反映这种依赖 |
| 流水线（pipeline） | 将填补、缩放、编码和模型串联，在每个训练分区内重新拟合 |

**缺失值处理（missing-value handling）**：目标缺失行首先删除。`drop` 再删除所选预测列、目标和分组列中仍有缺失的行；未选入的管理列不会触发删除。其他策略下，数值预测列按均值（mean）、中位数（median）或众数（mode）填补，类别预测列始终按众数填补。剩余分组标识缺失会报错，不会自动猜测组别。填补并不能证明缺失机制无偏。

**缩放（scaling）**：标准化（standardization，`standard`）按训练数据计算 `z = (x − mean_train) / std_train`；Min–Max 缩放（`minmax`）按训练数据的最小值和最大值缩放。新数据超出训练范围时，Min–Max 结果也可能超出 [0, 1]。`none` 表示不缩放。距离、正则化和梯度优化模型通常对量纲敏感；树模型通常不依赖这种缩放。

**独热编码（one-hot encoding）**：类别预测列转为类别指示列。当前代码按数据类型区分数值和类别；若把 1/2/3 编码的无序类别存成数值列，它会被当作数值处理，需在数据准备时核查。训练时未见过的类别在编码时被忽略，不代表模型已经学会该类别的含义。

**数据检查预览。** 选择分类目标后，界面显示实测类别数、每类数量及其占**非缺失目标**的比例，并写明总行数、非缺失分母与缺失数；目标全缺失时不做除零，未观测到的类别以及 NaN/None 不计为真实类别。界面另给出“疑似编号/参与者列”的启发式提醒（依据列名标记，或非缺失值接近唯一的整数/文本），并记录原因与比例；它只是“疑似、请判断”的提示，不自动删除列、不改变变量角色、也不阻止分析，分组列本身也可能是编号。类别与取值统计来自本地预览模式，默认预览不返回取值。

代码依据为[预处理流水线](../src/psyml/preprocessing/pipeline.py)与[数据准备及运行逻辑](../src/psyml/runner.py)。

<a id="models"></a>

## 2. 本项目支持的模型

项目提供 12 个分类选项、11 个回归选项，共 17 个不同代码名。相同名称在两种任务下可对应不同估计器。GUI 按任务过滤模型；下面的限制用于理解行为，不构成自动选型规则。实现见[模型工厂](../src/psyml/models/factory.py)和[模型目录](../src/psyml/models/catalog.py)。

### 两种任务都支持

| 模型与代码名 | 核心想法 | 如何理解其限制 |
| --- | --- | --- |
| 基线模型（Dummy，`dummy`） | 不利用预测变量的关系；分类按训练类别分布或多数类规则预测，回归按均值或中位数预测，取决于 `strategy` | 提供参照，不是“无用模型”。复杂模型是否超过它，应在相同验证设计下判断 |
| K 近邻（K-nearest neighbors，`knn`） | 查找最相似的 K 个训练样本；分类投票，回归平均，可按距离加权 | 依赖距离与缩放；维度多时近邻可能不再相似；K 不能超过相应训练折的样本数 |
| 决策树（decision tree，`decision_tree`） | 逐步用条件把样本分到不同叶节点，再给出类别或数值 | 可表达阈值和交互；深树容易过拟合，小幅数据变化可能改变树结构 |
| 随机森林（random forest，`random_forest`） | 结合多棵带有随机性的树，分类汇总类别概率，回归平均预测 | 往往比单树稳定，但更多树不等于更有效的研究设计；回归通常不擅长训练范围外推 |
| 梯度提升（gradient boosting，`gradient_boosting`） | 顺序增加树，逐步改善当前损失 | 学习率、树数与树深共同影响拟合；搜索范围过大可能增加过拟合和运算成本 |
| 多层感知机（multilayer perceptron，MLP，`mlp`） | 用多层加权变换和非线性激活学习映射 | 需要关注缩放、样本量与收敛警告；不是样本少时也必然更好的“深度学习方案” |

### 仅分类支持

| 模型与代码名 | 核心想法 | 如何理解其限制 |
| --- | --- | --- |
| 逻辑回归（logistic regression，`logistic_regression`） | 对类别概率建模，通常配合正则化；名称含 regression，但这里是分类器 | 基础决策边界是变换后特征的线性组合；系数不自动具有因果或显著性含义 |
| 支持向量机分类（support vector classification，`svm`） | 寻找具有较大间隔的分类边界，核函数可表达非线性 | 对缩放和 `C` 敏感；决策分数不是校准后的概率 |
| 高斯朴素贝叶斯（Gaussian naïve Bayes，`gaussian_nb`） | 给定类别时假设特征条件独立，并用高斯分布描述各特征 | 强相关特征或明显非高斯输入可能削弱假设；能输出概率不等于概率已校准 |
| 线性判别分析（linear discriminant analysis，LDA，`lda`） | 假设各类为高斯分布且共享协方差矩阵，形成线性边界 | 对类别分布与协方差结构有假设；高维、小样本或共线性需关注 |
| 二次判别分析（quadratic discriminant analysis，QDA，`qda`） | 允许各类有不同协方差矩阵，形成二次边界 | 相比 LDA 要估计更多量；每类样本少或特征冗余时协方差估计可能不稳定 |
| 堆叠集成（stacking，`stacking`） | 用基础模型的交叉拟合预测训练元模型（meta-model） | 当前基础模型是 KNN、随机森林和 SVM，元模型是逻辑回归。完整预处理随基础模型交叉拟合；有分组时使用分组切分。所需训练次数较多 |

二分类逻辑回归的直观形式是：

$$
p(y=1\mid x)=\frac{1}{1+\exp[-(b+\beta^\top x)]}.
$$

这里的 1 是数学上约定的正类，`b` 是截距（intercept），`β` 是系数，`x` 是预处理后的特征；本公式不表示 GUI 可以任意指定临床正类。模型训练目标与最终选择用的 F1 等指标也可以不同。

### 仅回归支持

| 模型与代码名 | 核心想法 | 如何理解其限制 |
| --- | --- | --- |
| 线性回归（linear regression，`linear_regression`） | 用特征的加权和预测数值，最小化残差平方和 | 基础形式不能自动表示任意非线性；共线性可使系数不稳定 |
| 岭回归（ridge regression，`ridge`） | 在线性回归中加入 L2 惩罚，收缩系数 | 通常保留多个非零系数；较大的 `alpha` 表示更强惩罚 |
| Lasso 回归（Lasso regression，`lasso`） | 加入 L1 惩罚，部分系数可收缩到零 | 零系数是该拟合与惩罚条件下的结果，不是“该变量没有科学作用” |
| 弹性网（Elastic Net，`elastic_net`） | 混合 L1 与 L2 惩罚，通过 `l1_ratio` 调整比例 | 特征强相关时仍需谨慎解释选择结果；惩罚强度与混合比例需共同考虑 |
| 支持向量回归（support vector regression，`svr`） | 用一个允许小误差的 ε 容忍区间拟合，可采用核函数 | `epsilon` 是目标尺度上的容忍宽度，不是置信区间；对缩放、`C` 与核函数敏感 |

线性预测写作 `ŷ = b + Σ βⱼxⱼ`。用一句概念式理解正则化（regularization）：

$$
\text{目标}=\text{拟合损失}+\lambda\times\text{惩罚},\qquad
L_1=\sum_j |\beta_j|,\quad L_2=\sum_j\beta_j^2.
$$

这是概念式，不是所有估计器共用的精确目标函数；损失归一化和参数含义可能不同。不能跨模型把相同数值的 `alpha` 当作相同惩罚强度；SVM/逻辑回归的 `C` 越小，一般表示正则化越强。原理可参阅 scikit-learn 的[线性模型](https://scikit-learn.org/stable/modules/linear_model.html)与[集成模型](https://scikit-learn.org/stable/modules/ensemble.html)文档。

<a id="metrics"></a>

## 3. 分类与回归评价指标

以下公式先描述一个测试分区中的指标；跨折汇总方式见本节末尾。实际输出代码见[评价指标](../src/psyml/evaluation/metrics.py)。

### 分类指标（classification metrics）

对某个类别采用一对其余（one-vs-rest，OvR）的理解：TP 是正确预测为该类，FP 是错把其他类预测为该类，FN 是该类被预测成其他类，TN 是其余类被正确预测为“非该类”。

$$
\mathrm{Precision}=\frac{TP}{TP+FP},\qquad
\mathrm{Recall}=\frac{TP}{TP+FN},\qquad
F_1=\frac{2TP}{2TP+FP+FN}.
$$

精确率（precision）问“预测为该类的样本中有多少是对的”；召回率（recall / sensitivity）问“真实属于该类的样本找回多少”。精确率不要与准确率（accuracy）混淆。

| 输出键与名称 | 含义与方向 | 阅读要点 |
| --- | --- | --- |
| `accuracy`：准确率（accuracy） | 正确预测数 / 总预测数；越高越好 | 多数类占绝对优势时可能掩盖少数类错误 |
| `balanced_accuracy`：平衡准确率（balanced accuracy） | 各真实类别召回率的等权平均；越高越好 | 分类默认选择指标；二分类且两类存在时等于敏感度与特异度的平均 |
| `precision_macro` / `recall_macro` / `f1_macro`：宏平均（macro average） | 分别计算各类 precision、recall、F1，再对类别等权平均；越高越好 | 小类别与大类别权重相同。宏 F1 不是宏 precision 与宏 recall 的调和平均 |
| `precision_weighted` / `recall_weighted` / `f1_weighted`：加权平均（weighted average） | 按测试分区中各类真实样本数加权；越高越好 | 大类别影响更大；当前单标签分类中，加权 recall 等于 accuracy |
| `roc_auc`：ROC 曲线下面积（area under the ROC curve） | 二分类分数对两类的排序能力；越高越好 | 不等于准确率或概率校准程度；0.5 是无区分排序的参照，并非适用于所有指标的“随机线” |
| `roc_auc_ovr_weighted`：加权一对其余多分类 AUC | 各类对其余类计算 AUC，再按类别样本数加权 | 当前仅在有概率输出且测试类别集与训练类别集一致时生成 |

宏平均与加权平均可以写作 `macro = Σ m_c / C` 和 `weighted = Σ (n_c / n) m_c`，其中 `m_c` 是该类指标，`n_c` 是测试分区中该类样本数，`C` 是参与平均的类别数。它们是类别权重，不是不同交叉验证折的权重。

**项目中的约定**：precision、recall、F1 的零分母按 `zero_division=0` 处理。二分类 AUC 以估计器 `classes_[1]` 为正类，优先用概率，否则用可用的决策分数；GUI 目前没有独立的正类或阈值选择控件。训练与测试类别集不一致时不输出 AUC。AUC 缺失表示本次条件不满足，不能填成 0 或当作“性能为零”。具体定义可查[scikit-learn 指标文档](https://scikit-learn.org/stable/modules/model_evaluation.html)。

**小例子**：100 个测试样本中，90 个为阴性、10 个为阳性，模型全部预测为阴性。accuracy 为 0.90，阳性 recall 为 0，balanced accuracy 为 0.50。它说明准确率高仍可能漏掉全部阳性；不是建议真实研究使用这些数值作为阈值。

### 回归指标（regression metrics）

令 `yᵢ` 为观测值（observed），`ŷᵢ` 为预测值（predicted），`n` 为当前测试分区的样本数，`ȳ` 为该测试分区的观测均值。

$$
\mathrm{MAE}=\frac{1}{n}\sum_{i=1}^{n}|y_i-\hat y_i|,\qquad
\mathrm{RMSE}=\sqrt{\frac{1}{n}\sum_{i=1}^{n}(y_i-\hat y_i)^2}.
$$

$$
R^2=1-\frac{\sum_i(y_i-\hat y_i)^2}{\sum_i(y_i-\bar y)^2}.
$$

| 输出键与名称 | 方向与单位 | 阅读要点 |
| --- | --- | --- |
| `mae`：平均绝对误差（mean absolute error） | 越小越好，最小为 0；目标变量的单位 | 可理解为平均偏离多少目标单位 |
| `rmse`：均方根误差（root mean squared error） | 越小越好，最小为 0；目标变量的单位 | 更强调大误差，是回归默认选择指标；不是折间标准差 |
| `r2`：决定系数（coefficient of determination） | 越高越好，最好为 1；无单位，可以为负 | 0 表示与直接使用该测试分区观测均值的平方误差相同；负数不是程序错误，也不等于负相关 |

R² 分母为零时，上面的普通公式不适用。当前调用遵循 scikit-learn `r2_score` 默认的有限值处理：常数目标且完全预测正确时为 1，否则为 0；测试样本少于 2 时不可定义。不可定义的次要指标会被排除并反映在有效折数中；选择指标不可定义可使分析失败。R² 也不是 Pearson 相关系数的平方的通用替代。

**小例子**：观测 `[1, 2, 3]`，预测 `[1, 2, 2]`，MAE = 1/3，RMSE = √(1/3)，R² = 0.5。这只是公式演示，不代表足够的研究样本量。

### 选择指标与汇总指标

- 内层选择（inner selection）可使用：分类 `balanced_accuracy`（默认）、`f1_macro`、`accuracy`；回归 `rmse`（默认）、`mae`、`r2`。不是每个输出指标都能选作调参目标。
- `metrics.csv` 保存**主要验证（独立模式为当前子目录验证）中各外层折指标的未加权均值**，不是把所有预测合并后重新计算的指标。各折大小不同时，二者可能不同；即使折大小相同，平均 RMSE 等非线性指标也不一定等于合并计算的结果。
- `metrics_summary.csv` 的 `std` 使用 `ddof=0`。若有效折数为 K，则 `std = √[Σ(m_k − mean)² / K]`；`n_folds` 是该指标的有效折数。各折共享训练信息，不能把这个 std 当作标准误（standard error）或置信区间（confidence interval，CI）。
- 留出法只有一个外层测试分区，std 可能为 0；这不意味着结果没有不确定性。

<a id="validation"></a>

## 4. 验证、调参与最终模型

### 六种验证策略

| 配置值 | 名称与用途 | 当前实现的边界 |
| --- | --- | --- |
| `holdout` | 留出法（holdout）：一次训练/测试切分 | 设置分组时按组切分，`test_size` 是组比例，不保证同样的行比例；无分组分类在条件允许时分层，样本过少仍可失败 |
| `k_fold` | K 折交叉验证（K-fold CV）：每折依次作为测试集 | 随机打乱；即使填写分组列，也不会按组隔离外层 |
| `stratified_k_fold` | 分层 K 折（stratified K-fold）：尽量维持类别比例 | 仅分类；仍不隔离外层分组 |
| `group_k_fold` | 分组 K 折（group K-fold）：同组行不跨训练/测试 | 需要足够多独立组；类别比例不一定平衡 |
| `stratified_group_k_fold` | 分层分组 K 折（stratified group K-fold） | 仅分类；在组不交叉约束下尽量平衡类别，不能保证每折都有每类 |
| `leave_one_group_out` | 留一组法（leave-one-group-out，LOGO）：每次留一整组测试 | 至少两组；折数由组数决定，不由 `n_splits` 决定；内层搜索还需足够训练组 |

**填写分组列并不自动让所有外层验证按组切分**。重复测量应选择与研究目标匹配的分组策略。当前没有专用的时间序列验证。一般原理见[交叉验证文档](https://scikit-learn.org/stable/modules/cross_validation.html)。

**随机分开与分组隔离的实际含义。** 未设置分组列时的随机划分（`holdout`、`k_fold`、`stratified_k_fold`）按行随机分开，同一参与者的多条记录可能一侧在训练、另一侧在测试，所以不能声称“同一个人只出现在一侧”。分组划分（`holdout` 设置分组列、`group_k_fold`、`stratified_group_k_fold`、`leave_one_group_out`）在**同一次划分内**保证整个组只进入训练或测试一侧；**不同折之间**同一组可以轮换到另一侧，这是分组交叉验证的正常行为，不破坏隔离。只有当分组列确实是参与者编号时，才可以把它读作“同一个人的记录不跨训练和测试”；若分组列是家庭、中心或批次，则对应的是这些单位的隔离，而不是个人。**仅选择分组列并不会让普通留出法或 K 折隔离组**：是否隔离取决于所选验证策略（见上表）。GUI 始终使用专业方法名，不把策略改写为场景化选项，也不改变划分算法。

### 嵌套选择（nested selection）按什么顺序发生

1. 留出当前外层测试折（outer test fold）。
2. 只在外层训练数据中进行内层验证（inner CV），选择模型家族及参数；设置分组时，内层隔离组。
3. 用选中的设置在该外层训练数据上拟合，再预测外层测试折。外层结果不用于替换内层选中的模型。
4. 汇总外层结果，评价完整选择流程。不同折可能选择不同家族。
5. 最后在全部分析数据上重新进行内层选择，再拟合最终模型（final fit）。这是给最终拟合选择设置，不产生新的独立测试分数。

单一家族已固定且只有一个参数候选时不需要内层搜索；选择多个家族时，即使 `tuning_mode="none"`，家族之间仍需在内层比较。候选任一内层折失败即不合格；并列按配置中的家族/候选顺序决定。项目使用 `selection_protocol="nested_family_v1"`，流程细节见[运行代码](../src/psyml/runner.py)；方法动机可参阅[嵌套与非嵌套验证示例](https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html)。

**主要验证（primary validation）**由 GUI 下拉框指定，序列化后排在 `validation_strategies` 首位，决定主指标、预测与图形。其他策略是敏感性分析（sensitivity analysis），用于观察结论是否依赖验证设计，不能查看最高分后再决定报告哪一个。也可选择**不指定主要验证**，配置为 `primary_validation: null`。此时每种验证分别执行相同的嵌套选择流程，完整结果保存在 `validations/<策略名>/`，结果页先提示选择验证，不自动突出任何一种。总目录不生成跨验证主指标或最佳模型。若部分失败，状态为 `completed_with_errors`，成功结果保留，失败项可查看错误；全部失败时不生成成功标记。旧配置省略该字段仍按首项为主要验证；策略名可显式指定主要项。

<a id="results"></a>

## 5. 结果文件与图形怎么读

以下文件说明适用于指定主要验证的运行，或“不指定”模式下每个成功验证的子目录。仅在独立模式下，总目录的 `validation_summary.csv` 使用 `role=independent`，不区分主次。Python API 可从 `validation_results[策略名]` 取完整结果；顶层模型为空、指标字典为空。

### 按问题查文件

| 想知道什么 | 查看文件 | 如何解读 |
| --- | --- | --- |
| 这次分析是否存在风险或失败？ | `warnings.json`、`result.json` | 先看警告；只有 completed 的结果才是完整成功输出，警告不一定阻止完成 |
| 样本外性能及波动如何？ | `metrics.csv`、`metrics_summary.csv`、`fold_metrics.csv` | 依次看主指标、有效折数及波动、每折明细 |
| 相对同折 Dummy 基线差多少、失败在哪一层？ | `result_interpretation.json`、`interpretation_baseline_differences.csv`、`result_interpretation.md` | 同验证、同折集合、同指标的配对差值与折间波动；描述性汇总，不回流选择或调参 |
| 换一种预定验证后是否一致？ | `validation_summary.csv` | 区分 primary / sensitivity；不要跨验证挑最高分 |
| 最终选择哪个模型？ | `result.json` 中 `best_model`、`best_parameters` | 最终全数据选择结果；不是每个外层折都用了这个模型 |
| 哪些家族值得进一步研究？ | `model_comparison.csv` | rank 在各验证内分别排序，属探索性比较；第一名可与最终模型不同 |
| 每一折选了什么？ | `selection_trace.csv` | 记录 `outer_training_fold` 或 `final_full_data`；`outer_fold=0` 是全数据选择，不是第 0 个测试折 |
| 某个参数为何被选中或失败？ | `parameter_search.csv` | 看内层 score、候选参数、status 与 error；score 是选择指标原始尺度，RMSE/MAE 仍是越小越好 |
| 最终参数能否重用？ | `best_parameters.json`、`best_parameters_configure.json` | 前者保存实际有效超参数（含默认值）；后者是固定最终模型与参数、关闭搜索的可运行配置 |
| 怎样复现原始分析设计？ | `config.json`、`analysis_config.json`、`study_config.json` | 保留原始搜索设计；三者用于兼容不同接口。重跑前核对 input_path 并改用新空 output_dir |
| 配置字段是什么？ | `configuration_guide.md` | 中英文简短解释；JSON 本身不加注释 |
| 哪些观测预测错了？ | `predictions.csv`、分类的 `confusion_matrix.csv` | `observed` 为真值、`predicted` 为预测；文件数据输入时 `row_index` 是从 0 开始的数据行索引，不是含表头的电子表格行号 |
| 环境与样本量能否对上？ | `analysis_manifest.json` | 比较输入/分析行数、特征数、数据指纹和依赖版本；输入特征数不等于独热编码后的列数 |
| 如何准备研究报告？ | `methods_summary_zh.md` / `methods_summary.md`、`reproducibility_report_zh.md` / `reproducibility_report.md` | 中英文离线摘要与报告是待核查草稿，不是已审核论文文本 |
| 保存模型在哪里？ | `model/best_<模型名>.joblib`、`model/model_metadata.json` | 仅开启保存的主要验证运行生成；供第 4 页加载，不是再次训练用的 JSON |

**“最佳参数”（best parameters）只表示在本次候选范围、指标、数据与切分下选出的设置**，不是全局最优或跨研究通用值。`best_parameters_configure.json` 重跑使用曾参与选择的数据，其新分数不能当作独立验证，也不等同于复现原始嵌套搜索。v0.2.0 起可在主要验证模式下保存已拟合的完整 Pipeline，供第 4 页加载预测；该 JSON 配置仍是重新训练的配方，与保存模型文件用途不同。

### 结果解读（基线差值、折间波动与失败）

结果页的**结果解读**只汇总已经产生的选择折外层证据（逐组合折、`parameter_search.csv`、`model_comparison.csv`、`validation_summary.csv`），输出 `result_interpretation.json`、`interpretation_baseline_differences.csv` 与 `result_interpretation.md`；不重新拟合模型、不重新选择家族或参数，也不把描述性结果回流到选择或调参。

- **基线差值**只与用户已选且成功运行的 Dummy 比较，要求同验证、同折集合、同指标且所有配对折分数有限；否则给出明确不可比较原因，不捏造差值。分类“越高越好”指标为 procedure−dummy，MAE/RMSE 为 dummy−procedure，正值一律表示所选流程相对基线更好；某折选中的就是 Dummy 时差值为 0 并标注该折模型，属正常情况。
- **折间波动**沿用既有汇总定义并注明 ddof=0，只作描述；单折时标准差与稳定性不可评估，也不设置“显著、可靠、不稳定”阈值，分数差异不等于统计显著，折间标准差也不是置信区间。
- **失败分层**：内层搜索候选失败、外层模型+验证失败、整种验证/流程失败分别计数并可追溯；代表原因可看，完整记录仍在 `parameter_search.csv`、`warnings.json` 与失败子目录。
- **独立验证**各自摘要，顶层只提供概览与索引，不跨验证比较。

### 保存模型与预测结果

主要验证模式默认开启 `save_best_model`；最终 Pipeline 保存为 `model/best_<模型名>.joblib`，同目录的 `model_metadata.json` 记录原始变量、类型、类别、有效参数、拟合范围和版本。关闭保存仍会完成分析；`primary_validation: null` 时根目录和各验证子目录均不自动保存模型。

三个参数记录要分开读：`best_parameters.json` 与 `result.json.effective_parameters` 是实际有效超参数（含默认值）；`result.json.best_parameters` 保留选择得到的参数覆盖，可能为空；`best_parameters_configure.json` 是可重新训练的配置，不能当成已拟合模型加载。模型文件由全数据最终拟合产生，并非外层得分最高折的模型。

第 4 页加载可信模型和新表格后会自动检查。只需模型要求的预测变量，不需要目标列或分组列；有变量名时按训练顺序自动选列。只有特征数而无名称时，需要确认手动映射的变量及顺序。缺列、不可用数值、无穷值或无法填补的缺失值会阻止预测；兼容性通过不代表人群分布一致，也不保证模型执行一定成功。训练时选择 `drop` 不会让预测页静默删除新样本。

预测结果保留原始行顺序和全部输入列，新增 `predicted_class`（分类）或 `predicted_value`（回归）；只有原生支持概率的分类模型新增 `probability_*`。类别名称会转换为可用列名，重名时新增列带数字后缀。目标列即使存在也只保留，不自动计算外部验证指标、校准概率或优化阈值。

支持 9 种输入格式；导出为 CSV、TSV、XLSX、SAV、DTA、XPT 或 Parquet。XLS、SAS7BDAT 仅支持读取，GUI 默认改存 XLSX。统计格式限制可能使导出失败，可改用 XLSX 或 Parquet。模型与元数据应成对保留；损坏、校验不匹配或 scikit-learn 版本不一致会报错，缺少元数据时尝试恢复信息但不保证完整。

**第 4 页产物与训练结果的输出位置。** 第 4 页与第 2 页共享同一个结果根目录：新的训练结果写入 `<结果根目录>/training/run_<时间>_<usec>/`，预测写入 `<结果根目录>/prediction/run_<时间>_<usec>/predictions.csv`，单样本 SHAP 与系数分别写入 `explanation/run_*/`、`coefficients/run_*/`。每次操作开始时冻结一个新运行目录，不覆盖已有文件；“打开预测结果文件夹”“打开结果文件夹”指向该次实际运行目录，“打开瀑布图”指向本次的 `shap_waterfall.png`。旧版本直接写在结果根目录下的 `run_*` 训练目录保持原位、仍可正常打开，不搬家、不改写；只有新训练才进入 `training/`。未选择根目录、路径为相对路径或根目录不可写时直接显示错误，不会回退到隐藏的应用数据目录。更改根目录只影响后续操作，已完成的产物保留在磁盘。

**预测产物怎么读（`prediction/run_*/predictions.csv`）。** 文件保留原始数据与行序，只追加预测列：回归追加 `predicted_value`，分类追加 `predicted_class`，分类器原生支持概率时按类别顺序追加 `probability_<类别>`。原始列（含目标列）不改动，列名冲突时只给新增列加数字后缀；目标列存在也只保留，不自动计算外部验证指标、校准概率或优化阈值。**分类与回归的区别**：分类输出类别与非负、不保证已校准的概率，回归只输出连续数值、不生成概率；“打开预测结果文件夹”打开的是本次运行目录，不是直接打开 CSV。预测可以没有真实目标，这**不是外部验证**：外部验证需要独立样本、真实目标和适当的评价设计。更换模型、数据或映射后会清除旧预测并重新检查，旧运行目录中的文件留在磁盘。

### 单样本 SHAP 解释（可选）

第 4 页在模型与数据检查通过后可解释单个样本：选择背景参考文件（background reference）、1 起始的样本行号、背景行数（background rows，默认 50，1–100）与排列轮数（permutation cycles，默认 5，1–20）；分类再选择要解释的类别并显示原始标签。计算在可取消子进程中运行，首次可能较慢，可随时取消。结果区显示从**基准值（base value）**逐项累加到模型输出的**累计瀑布图**（正负方向、原始变量名与值、TopN 与“其余 N 项之和”，CSV 保留全部贡献），只提供“打开瀑布图”与“打开结果文件夹”两个入口，不提供复制或另存导出入口。产物（默认位于 `explanation/run_*/`）为 `shap_explanation.json`、`shap_contributions.csv`、`shap_waterfall.png` 与 `shap_explanation_notes.md`，满足 `base + Σφ = 所选输出`（容差 1e-7/1e-6），且切换行/类别/设置或关闭页面时已完成产物保留在磁盘。命令行 `psyml explain --output-dir` 仍要求新建或空目录并拒绝 `--overwrite`，但界面不再提供导出操作。

怎么读这些结果：

- **基准值（base value）**：所选输出轴在背景参考行集合上的平均模型输出，是所有贡献累加的起点。
- **背景参考（background reference）**：用于近似“变量取参考值时输出会怎样”的参考数据；行数越多通常越稳定，但计算更慢，它不代表人群常模。
- **所选样本与类别**：决定被解释的是哪一行、哪个输出轴；分类必须选定类别，回归只有一个输出轴。
- **正负贡献**：每个变量把输出从基准值推高（正）或压低（负）的近似量；`base + Σφ = 所选输出`（CSV 逐项列出全部贡献，界面只折叠 TopN 之外的项）。
- **重建**：这条加法恒等式在容差内成立是核验条件，不表示因果机制；数值依赖背景集合与排列轮数。
- **近似限制**：有限排列的**近似** SHAP，不是精确 SHAP；背景替换不保持变量相关结构；不是因果效应，也不是外层测试性能。

这是有限排列的**近似** SHAP：不是精确 SHAP、不是因果效应，也不是外层测试性能；背景替换不保持变量相关结构。首版仅支持分类 `logistic_regression`、`decision_tree`、`random_forest` 与回归 `linear_regression`、`ridge`、`lasso`、`elastic_net`、`decision_tree`、`random_forest`，且仅接受带 PsyML 导出元数据（`psyml_version`/`fit_scope`）与标准 `preprocess`+`model` 结构的保存模型；缺少元数据或自定义预处理的外来模型明确提示不支持，普通预测不受影响。未安装 `explain` 可选依赖时该区不可用。

实现见[模型保存](../src/psyml/models/persistence.py)、[有效参数](../src/psyml/models/parameters.py)与[预测核心](../src/psyml/prediction.py)；解释核心见[explanation.py](../src/psyml/explanation.py)。

### 拟合系数与截距

第 4 页“拟合系数与截距”区只读取**已拟合模型**在**预处理后坐标空间**（缺失填补、缩放、独热编码之后）的参数，不重新拟合、不回流调参、也不换算回原始单位。首版支持回归 `linear_regression`、`ridge`、`lasso`、`elastic_net`、`svr`（`kernel='linear'`）与分类 `logistic_regression`、`lda`、`svm`（`kernel='linear'`，仅二分类）；多类 SVC 的成对系数、非线性核、树、KNN、MLP 与 stacking 给出具体不支持原因。若已加载兼容预测数据，会在同一流水线与容差（1e-7/1e-6）下重建回归预测或分类决策分数并显示核验状态；无数据时明确标注未核验。界面逐输出轴显示截距、输出单位与拟合范围，并区分“未提供核验数据”与“核验失败”；核验失败会拒绝发布任何系数产物（显示具体原因，不显示提取完成、不可导出）。`coefficients.json` 记录被删除的全缺失列及原因、逐原始列映射、`drop_idx_` 与逐列类别映射，训练 dtype 来源为保存元数据或明确 unknown。分类输出轴：二分类 logistic 为 `classes_[1]` 相对 `classes_[0]` 的 log-odds，多类 logistic 为各类 softmax logit，线性 SVC 仅为 margin（不是概率或 log-odds）；类别保存真实标签、类型与索引。第 4 页只保留“打开结果文件夹”（指向本次 `coefficients/run_*/`），不再提供复制或另存导出入口；提取成功时该运行目录一次写齐 `coefficients.csv`、`coefficients.json` 与 `coefficients_notes.md`（JSON 最后写入）。常规分析也会在本次分析目录的 `coefficients/` 写入同名三件，并标注 `fit_scope=all_analyzed_rows`。这些是最终全数据模型的拟合参数（不是超参数），不提供 p 值、置信区间、显著性、因果或定义明确的标准化效应；普通预测、超参数区与 SHAP 区不受影响。CLI 等价命令为 `psyml coefficients --model … --trust-model [--input …] [--output-dir …]`，另有 `--check-only`，且不需要 `explain` 可选依赖。

怎么读这些结果：

- **截距（intercept）**：每个输出轴上所有变换后特征取零时的输出基准值，单位与输出轴一致；不是原始数据中“没有人”或“没有测量”的含义。
- **变换后特征单位**：每个系数对应填补、缩放或独热编码之后的列（如 `numeric_score`、`categorical_category_A`），不是原始变量的原始单位；不要直接按原始单位换算，也不要跨模型直接比较大小。
- **输出单位**：分类必须结合类别轴阅读——二分类 logistic 是相对参照类的 log-odds，多类 logistic 是各类 softmax logit，线性 SVC 是 margin（原始决策分数，既不是概率也不是 log-odds）；回归的 `predict` 输出保持目标变量单位。
- **拟合范围（fit_scope）**：这些是最终全数据模型（`all_analyzed_rows`）的拟合参数，不是某个外层折的模型，也不是超参数。
- **未验证与失败**：没有加载兼容预测数据时显示“未提供核验数据（未核验）”；重建误差超限、形状不符或非有限时显示“核验失败”并拒绝写出任何系数产物。
- **非因果**：系数反映的是该拟合与惩罚条件下的关联，不提供 p 值、置信区间、显著性、因果或定义明确的标准化效应。

实现见[coefficients.py](../src/psyml/models/coefficients.py)。

### 图形（figures）

| 图形文件 | 轴或内容 | 核查问题 |
| --- | --- | --- |
| `confusion_matrix.png` | 行为真实类，列为预测类，单元格为计数 | 哪些类相互混淆？类别多或不平衡时不能只看对角线是否“深色” |
| `class_distribution.png` | 样本外真实与预测的各类数量 | 是否几乎只预测多数类？数量相似也可能逐个预测都错 |
| `observed_vs_predicted.png` | 横轴观测、纵轴预测；虚线是两者相等 | 是否存在系统性高估/低估？直线附近的散点仍需结合目标量纲与误差指标 |
| `residuals.png` | 横轴预测，纵轴残差（residual）= 观测 − 预测 | 正残差表示低估，负残差表示高估；曲线形状或漏斗形可提示结构未拟合或误差波动不均 |
| `residual_distribution.png` | 残差直方图 | 是否偏向一侧、重尾或有极端误差？单靠直方图不能证明正态性或独立性 |

这些图使用主要验证（独立模式为当前子目录验证）的样本外预测；留出法只包括测试部分，交叉验证通常包括每个保留样本的一次外层预测。分类图以 Class 1、Class 2 等显示，顺序对应 `confusion_matrix.csv`，不表示 GUI 指定了临床正类。图形可多选或全部取消，保存在本次 `figures/`；它们不是 SHAP、ROC 或置信区间图。特征重要性只在显式启用 `permutation_importance` 时以单独的 `interpretations/<验证>/permutation_importance.png` 输出（见下一节）。

### 置换重要性（可选，`permutation_importance`）

在 GUI 第 1 页启用后，系统对每种验证的每个外层折，用内层选择出的折模型仅在该折的外层测试行上逐变量边际置换，使用当前 `selection_metric` 衡量性能变化，并写入 `interpretations/<验证>/`：

- `permutation_raw.csv`：每次置换一行（validation、fold、model_family、variable、repeat、metric、importance、direction、baseline_score、n_rows）；
- `permutation_folds.csv`：逐折 baseline、`repeats`、`mean`、`repeat_std`（ddof=0）、`n_rows` 与状态/错误；
- `permutation_summary.csv`：同一验证内各折均值的等权平均 `fold_mean_equal_weight` 与 `between_fold_std`（ddof=1），并记录成功/计划折数；
- `permutation.json`：指标与高低方向、seed/repeats、held-out 行数、`model_scope=outer_fold_model`、编码映射、限制与失败原因；
- `permutation_importance.png`：带零线的有符号排序图。

读法与限制：`importance` 有符号，MAE/RMSE 正值为误差升高，其他指标正值为性能下降；保留负值，不归一化为百分比，也不称置信区间或 R² 百分比。`repeat_std` 是折内重复波动，`between_fold_std` 是折间波动，二者不能混用；只有一折时跨折标准差为空，折间标准差是描述性波动，不是标准误或置信区间。变量相关时贡献会被共享或掩盖；逐行置换不保留重复测量/分组结构，因此分组数据的解释更弱，需结合设计判断。缺折或失败标记 partial/failed，不补造完整排名；全部失败不生成成功表格或空白图。这是模型在特定折、特定指标下对变量扰动的敏感度，不是因果效应，也不等于所保存全数据模型的解释。未明确启用时不生成任何 `interpretations/`。

<a id="glossary"></a>

## 6. 常见参数与术语速查

| 术语 / 配置键 | 简明解释 |
| --- | --- |
| 模型家族（model family） | 如随机森林、Ridge，表示一类建模方法；不同参数候选仍可属于同一家族 |
| 参数（parameter）与超参数（hyperparameter） | 系数等通常由训练学得；树深、惩罚强度等通常由用户或搜索指定。项目中的 `model_params` 实际主要是估计器初始化超参数 |
| 候选 / 网格（candidate / parameter grid） | 候选是一组具体设置，网格定义各参数的候选值；组合数可快速增长 |
| `tuning_mode` | `none` 固定参数；`quick` 内置有限网格；`custom` 用户网格。quick 不是保证最优的推荐结论 |
| `max_candidates` | 每个模型候选组合上限；网格超过上限时抽样候选，不保证遍历全部组合 |
| `n_splits` / `inner_splits` | 外层 / 内层折数；可用样本、类别和组数必须支持切分，内层实际折数可能减少 |
| `random_seed` | 控制随机切分和设定了种子的估计器；显式模型 `random_state` 可覆盖估计器种子。种子相同不保证跨依赖版本逐位一致 |
| `n_neighbors` | KNN 邻居数；计数取整数 |
| `n_estimators` / `max_depth` / `min_samples_leaf` | 树数、最大树深、叶节点最小样本要求。`null` 可表示不限制树深；GUI 整数值候选按计数处理，合法小数比例须与参数规则一致 |
| `C` / `alpha` / `l1_ratio` | 惩罚控制参数；C 较小通常惩罚更强，alpha 较大通常惩罚更强，l1_ratio 调节 L1/L2 比例；具体含义依模型而定 |
| `learning_rate` / `learning_rate_init` | 提升模型学习率 / MLP 初始学习率，不能互换配置键 |
| `epsilon` | SVR 的容忍区间宽度参数，不是估计误差的置信范围 |
| `class_weight` / 类别不平衡（class imbalance） | 前者改变训练中各类的权重；它与评价阶段的 weighted average 不同 |
| 过拟合 / 欠拟合（overfitting / underfitting） | 前者把训练噪声也学入，后者未捕捉足够结构；不能仅凭一个测试分数确定具体原因 |
| 数据泄漏（data leakage） | 本不应参与训练或选择的测试信息进入了流程，导致评价过于乐观 |
| 样本外预测（held-out prediction） | 该样本未用于相应模型拟合；嵌套流程还使其不参与相应的模型/参数选择 |
| 泛化 / 外部验证（generalization / external validation） | 前者是对未见数据的表现，后者用独立外部数据检验；内部交叉验证不等于新中心、新时间或新人群验证 |
| 校准（calibration） | 预测概率是否与实际发生频率一致；排序良好的 AUC 不能保证校准良好 |
| 数据指纹（SHA-256 fingerprint） | 用于识别输入内容是否变化；不是加密、匿名化，也不证明数据质量 |
| 收敛警告（convergence warning） | 优化在设定条件下未达到停止标准；程序有输出也仍需核查，不应自动把结果视为稳定 |
| 最终模型 | 根据全数据内层选择确定模型家族和参数，再在全部分析样本上拟合；不是直接保存某个外层折的模型 |
| Pipeline（流水线） | 将已拟合的预处理与估计器一起保存，预测时自动沿用训练时的填补、编码和缩放 |
| 有效参数 | 最终估计器实际使用的初始化参数，包含未手动修改的默认值；不等于训练学得的系数 |
| model_metadata.json | 与模型并排保存的变量名、类型、类别、参数和版本等说明；分享模型时一起保留 |
| 特征兼容性 | 必需变量存在且类型可用；列顺序不同可自动选列，额外列保留。检查通过不代表新样本与训练人群相同 |
| predicted_class / predicted_value | 分类模型输出的类别 / 回归模型输出的数值；不是已知真实结果 |
| probability_* | 估计器原生提供的类别概率；不保证已经校准，也不直接等于临床风险，回归不生成此列 |
| 新数据预测 / 外部验证 | 预测可以没有真实目标；外部验证需要独立样本、真实目标和适当的评价设计。本版预测页不自动执行外部验证 |
| 预测产物（`prediction/run_*/predictions.csv`） | 保留原始数据与行序，只追加 `predicted_class` 或 `predicted_value`，分类可能有原生 `probability_*`；“打开预测结果文件夹”指向本次运行目录，不是直接打开 CSV |
| 基准值（base value）与背景参考（background reference） | 单样本解释中，对背景参考行取平均得到的所选输出轴基准与参考集合；背景不代表人群常模 |
| 贡献（contribution, φ）与重建（reconstruction） | 每个变量把输出从基准值推高或压低的近似量；`base + Σφ = 所选输出` 的加法关系可核对，但不表示因果 |
| 截距（intercept） | 变换后特征全为零时的输出基准值，位于预处理后坐标空间，不是原始变量单位 |
| 变换后特征（transformed feature） | 填补、缩放、独热编码之后的列；系数对应这些列，不能直接按原始单位换算 |
| log-odds / margin（决策分数） | 分类系数的输出单位：二分类 logistic 为 log-odds，多类 logistic 为 softmax logit，线性 SVC 为 margin；margin 不是概率也不是 log-odds |
| 拟合范围（`fit_scope`） | 系数来自哪个拟合范围；`all_analyzed_rows` 表示全部已分析行的最终模型，不是外层折模型 |
| 模型来源可信 | joblib/pickle 加载可能执行代码，只加载自己训练或确认可信来源的模型 |

<a id="checklist"></a>

## 7. 常见误解与核查顺序

先核对目标、预测变量、分组和缺失处理，再看警告与有效样本量，接着看主指标、每折波动和系统性预测错误，最后比较预先指定的基线与敏感性分析。记录设计修改，避免看结果后不断更换验证或指标。

- **“排行榜第一就是最终模型。”** 不一定，前者按探索性外层分数排序，后者由全数据内层选择得到。
- **“R² = 0.6 表示每个个体都预测准确 60%。”** 不成立；R² 是相对平方误差指标，不是个体正确率。
- **“F1、AUC 越高，临床应用一定越好。”** 不成立；还需结合误判代价、目标人群、阈值、校准和外部证据。
- **“标准差为 0 就没有不确定性。”** 不成立，尤其留出法只有一个分区时。
- **“Lasso 留下的变量就是因果因素。”** 不成立，预测选择不等于因果识别。
- **“跑出了 completed 就可以直接写论文。”** 不成立，它表示程序完成，不能代替数据和科学判断的验收。

<a id="references"></a>

## 8. 实现依据与延伸阅读

本项目行为以[模型目录](../src/psyml/models/catalog.py)、[模型工厂](../src/psyml/models/factory.py)、[指标实现](../src/psyml/evaluation/metrics.py)、[验证切分](../src/psyml/validation/split.py)、[运行逻辑](../src/psyml/runner.py)、[结果报告](../src/psyml/reporting/research.py)为准。默认值与行为可能随版本改变；复现时核对 `analysis_manifest.json` 中记录的版本。

通用原理可继续阅读 scikit-learn 的[指标说明](https://scikit-learn.org/stable/modules/model_evaluation.html)、[线性模型](https://scikit-learn.org/stable/modules/linear_model.html)、[集成模型](https://scikit-learn.org/stable/modules/ensemble.html)、[交叉验证](https://scikit-learn.org/stable/modules/cross_validation.html)及[嵌套验证示例](https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html)。这些参考不意味着项目实现了文档中所有功能。

## 从配置快速复现

用户测试从 [examples/quickstart/](../examples/quickstart/README.md) 开始：分类和回归分别提供配置、48 行训练数据与 10 行新预测数据，全部为合成数据。操作顺序见 [README 数据分析操作](../README.md#chinese)，保存模型与预测已并入第 9 步。

应用第 1 页的“导入配置…”可读取附带示例、结果目录的 `config.json`，或固定参数文件 `best_parameters_configure.json`；无需命令行。数据路径失效时，重新选择对应数据；程序会核对所需列。检查变量、验证与参数后，在第 2 页选择本机输出目录并运行。每次建立新的 `training/run_*` 结果子目录，导入的输出路径不会被沿用。“保存配置…”可保存当前设置。固定最佳参数的再运行不重现原搜索，也不是独立验证。

## 源码版复测步骤

独立应用包与源码检出可能包含不同的修复；以下 5 点用于源码版自测。

1. 在源码检出根目录启动界面（macOS 可双击 `Launch PsyML.command`），依赖安装见[开发者指南](DEVELOPMENT_ZH.md)；独立应用包不包含开发测试环境。导入 `examples/quickstart/` 的分类或回归配置并运行一次。
2. **版本小字**：软件名下方应以小字显示当前版本号 `0.3.0`。源码版唯一来源是 `src/psyml/__init__.py` 的 `__version__`（`pyproject.toml` 为 dynamic），独立包读取包内由同一常量生成的 `BUILD.json`；开发版 `0.3.0.dev0` 界面显示为 `0.3.0-dev`，正式版本 `0.3.0` 原样显示。
3. **输出目录与旧结果**：第 2 页新训练结果显示在所选结果根目录的 `training/run_*` 下；第 4 页预测、SHAP 与系数分别落在与第 2 页共享根目录下 `prediction/`、`explanation/`、`coefficients/` 的 `run_*` 新目录，不覆盖已有文件，也不写入隐藏的应用数据目录。旧版本直接放在结果根目录的 `run_*` 目录仍能原位打开、内容不被改写。
4. **第 4 页只打开、不导出**：三块都只有“打开结果文件夹”（预测为“打开预测结果文件夹”，直接打开本次运行目录而不是 CSV）与“打开瀑布图”，没有复制或另存导出入口；预测产物是可直接打开的 `predictions.csv`，不再有 `predictions.parquet`。
5. **滚动控制与收尾状态**：在长页面与嵌套小表格之间滚动时，从整页起手经过小表格仍继续滚动整页，从小表格起手才滚动该表格，停顿约 250 毫秒后再滚动才重新选择控制层（锁定只作用于滚轮/滑动）；运行收尾阶段应显示“正在整理并写出结果…”且进度条未满，完成后才进入结果页。记录问题时使用“复制完整报错”。
