# 研究者参考：模型、指标、结果与术语

版本 : **v0.1.0**.

[返回 README 中文部分](../README.md#chinese) · **中文** · [English](RESEARCHER_GUIDE_EN.md) · [Français](RESEARCHER_GUIDE_FR.md)

本指南解释 PsyML Toolkit 当前实现中的概念，适合在设置分析或阅读结果时查阅。中文术语附有英文名称，代码名与配置及 CSV 保持一致。内容可离线阅读；外部参考链接需联网。简短公式用于理解，不要求研究者手算。Markdown 阅读器不支持公式时，可直接阅读公式前后的文字说明。

模型是否适用取决于研究问题、数据结构和验证设计，没有对所有研究都最好的模型，也没有通用的“合格分数”。本项目开展预测分析，不自动给出因果结论、显著性检验或临床决策依据。自动生成的 summary 和报告不保证绝对正确，需由研究者复核。

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
| 换一种预定验证后是否一致？ | `validation_summary.csv` | 区分 primary / sensitivity；不要跨验证挑最高分 |
| 最终选择哪个模型？ | `result.json` 中 `best_model`、`best_parameters` | 最终全数据选择结果；不是每个外层折都用了这个模型 |
| 哪些家族值得进一步研究？ | `model_comparison.csv` | rank 在各验证内分别排序，属探索性比较；第一名可与最终模型不同 |
| 每一折选了什么？ | `selection_trace.csv` | 记录 `outer_training_fold` 或 `final_full_data`；`outer_fold=0` 是全数据选择，不是第 0 个测试折 |
| 某个参数为何被选中或失败？ | `parameter_search.csv` | 看内层 score、候选参数、status 与 error；score 是选择指标原始尺度，RMSE/MAE 仍是越小越好 |
| 最终参数能否重用？ | `best_parameters.json`、`best_parameters_configure.json` | 前者保存参数覆盖，`{}` 表示使用默认值；后者是固定最终模型与参数、关闭搜索的可运行配置 |
| 怎样复现原始分析设计？ | `config.json`、`analysis_config.json`、`study_config.json` | 保留原始搜索设计；三者用于兼容不同接口。重跑前核对 input_path 并改用新空 output_dir |
| 配置字段是什么？ | `configuration_guide.md` | 中英文简短解释；JSON 本身不加注释 |
| 哪些观测预测错了？ | `predictions.csv`、分类的 `confusion_matrix.csv` | `observed` 为真值、`predicted` 为预测；文件数据输入时 `row_index` 是从 0 开始的数据行索引，不是含表头的电子表格行号 |
| 环境与样本量能否对上？ | `analysis_manifest.json` | 比较输入/分析行数、特征数、数据指纹和依赖版本；输入特征数不等于独热编码后的列数 |
| 如何准备研究报告？ | `methods_summary_zh.md` / `methods_summary.md`、`reproducibility_report_zh.md` / `reproducibility_report.md` | 中英文离线摘要与报告是待核查草稿，不是已审核论文文本 |

**“最佳参数”（best parameters）只表示在本次候选范围、指标、数据与切分下选出的设置**，不是全局最优或跨研究通用值。`best_parameters_configure.json` 重跑使用曾参与选择的数据，其新分数不能当作独立验证，也不等同于复现原始嵌套搜索。当前 GUI 没有导出可直接加载的已拟合模型文件；该配置是重新训练的配方。

### 图形（figures）

| 图形文件 | 轴或内容 | 核查问题 |
| --- | --- | --- |
| `confusion_matrix.png` | 行为真实类，列为预测类，单元格为计数 | 哪些类相互混淆？类别多或不平衡时不能只看对角线是否“深色” |
| `class_distribution.png` | 样本外真实与预测的各类数量 | 是否几乎只预测多数类？数量相似也可能逐个预测都错 |
| `observed_vs_predicted.png` | 横轴观测、纵轴预测；虚线是两者相等 | 是否存在系统性高估/低估？直线附近的散点仍需结合目标量纲与误差指标 |
| `residuals.png` | 横轴预测，纵轴残差（residual）= 观测 − 预测 | 正残差表示低估，负残差表示高估；曲线形状或漏斗形可提示结构未拟合或误差波动不均 |
| `residual_distribution.png` | 残差直方图 | 是否偏向一侧、重尾或有极端误差？单靠直方图不能证明正态性或独立性 |

这些图使用主要验证（独立模式为当前子目录验证）的样本外预测；留出法只包括测试部分，交叉验证通常包括每个保留样本的一次外层预测。分类图以 Class 1、Class 2 等显示，顺序对应 `confusion_matrix.csv`，不表示 GUI 指定了临床正类。图形可多选或全部取消，保存在本次 `figures/`；它们不是 SHAP、特征重要性、ROC 或置信区间图，当前并未导出这些额外图形。

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

应用第 1 页的“导入配置…”可读取附带示例、结果目录的 `config.json`，或固定参数文件 `best_parameters_configure.json`；无需命令行。数据路径失效时，重新选择对应数据；程序会核对所需列。检查变量、验证与参数后，在第 2 页选择本机输出目录并运行。每次建立新的结果子目录，导入的输出路径不会被沿用。“保存配置…”可保存当前设置。固定最佳参数的再运行不重现原搜索，也不是独立验证。
