# PsyML Toolkit 科学正确性专项审查

> 后续更新：本文件保留第一轮审查的历史证据。用户随后授权并选择了完整嵌套家族/参数选择，已改变本文件所述家族选择限制与主结果语义；当前实现请以 [方法实施记录](NESTED_SELECTION.md) 和 [Computer Use 验收记录](CUA_ACCEPTANCE.md) 为准。第一轮改动已于提交 d4b139c 推送。

日期：2026-09-05。依据：本次开始时的实际工作树与本轮修复后的代码。起始 `git status --short` 为空；仓库及上级目录未找到适用的 AGENTS.md；未覆盖既有用户改动，未提交或推送。阅读了 README、配置/协议、数据读取、预处理、切分、模型工厂、runner、报告导出、Godot 场景/脚本及现有测试。没有把旧报告作为当前实现的事实来源。

**结论：现在可进行人工验收。发现并修复了具体实现错误；这不表示整个模型选择流程已获得无偏泛化性能估计。最重要的剩余限制是：模型家族用主要验证的外层成绩选出，获胜分数有选择乐观偏差。** 软件保持原有研究目标与指标规则，增加真实描述，不自动引入额外验证层、不替研究者改主要指标或排除规则。

## 确认缺陷与修复

严重程度：P1 = 可能影响样本、选择或性能结论；P2 = 影响复现、状态可信度或可用性。以下位置指修复后的文件/函数；历史行为由 diff 与直接复现记录核实。

| 编号/级别 | 位置与触发条件 | 直接证据及影响 | 修复与回归验证 |
|---|---|---|---|
| F1 · P1 | `src/psyml/runner.py:230` `_prepare_data`；选择部分预测变量，`missing_strategy='drop'`，未选列有缺失 | 原代码先对全表 dropna，再选预测列。48行数据加全缺失 admin 列会变成0行；本应不入分析的管理字段改变样本。缺失目标原先已删除，但不计入删除提示。 | 先按目标、组、实际预测列取子表，再执行既有缺失策略；单独报告缺失目标数。`test_unselected_missing_admin_does_not_exclude_rows`、`test_missing_target_is_counted_and_prediction_indices_survive` 验证保留48行、删后原索引及 observed 对应。没有改变“缺失目标删除”的既有规则。缺失组身份在填补模式下明确报错，不擅自填补/排除。 |
| F2 · P1 | `src/psyml/runner.py:146` `_build_stacking_pipeline`；使用 Stacking，尤其分组数据 | 原 `Pipeline(preprocess, StackingClassifier)` 在堆叠内部交叉拟合之前已对整份外层训练数据拟合预处理；其默认内部 CV 没有组信息。内部验证行参与编码/缩放统计，且同组可跨堆叠内部训练/测试。外层测试仍隔离，不能把该缺陷夸大成外层直接训练了测试标签。 | 基模型各自带完整预处理流水线；堆叠 CV 使用当前局部数据的组隔离；passthrough 的原始特征在元模型拟合内处理。`test_stacking_crossfits_preprocessing_and_groups[False/True]` 用混合类型48行、12组，实测基预处理有32行的内部训练拟合，检查每一内部切分的组交集为空并完成预测。所有分类模型原有运行测试通过。预拟合 cv='prefit' 不接受，组/类别不足时报错。 |
| F3 · P1 | `src/psyml/evaluation/metrics.py:19` `classification_metrics`；外层训练三类、测试折只含其中两类，或训练缺类别 | 原实现仅按 observed 的类别数选择二分类 AUC，并固定取概率第2列；例如训练0/1/2、测试0/2，会把类别1的概率解释成类别2的分数。其他类别缺失情况还会使概率矩阵维度错误，进而将本可评价的组合判失败。 | 类别集合不匹配时保留可定义的标签指标、略去 AUC，并在运行警告标记缺类别折。二分类按 estimator.classes_[1] 二值化观测；多分类给出对应 classes 标签。`test_multiclass_training_binary_test_does_not_invent_binary_auc` 直接复现原错误。另有反向类序的防御测试；当前受支持 sklearn 模型正常排序类别，未把反向类序本身列为实际触发缺陷。 |
| F4 · P2 | `src/psyml/runner.py:509` 最终拟合分支；主要验证为 holdout 且无多候选搜索 | 原代码返回留出训练集拟合的模型，却发出“fitted on all analyzed rows”事件并在说明中声明全数据拟合。 | 始终另做全数据最终拟合，保持已有外层预测和指标。`test_holdout_final_model_uses_all_rows_without_changing_oos` 验证最终 scaler 见48行而预测仅10条；更新原 scaler 回归测试，分别检查外层训练拟合和全数据拟合，避免把最终模型的统计量误当成验证折统计量。 |
| F5 · P2 | `runner.py` 输出配置；`reporting/research.py:119`；有搜索或模型比较 | 原三个配置文件同时保留搜索网格、又写入最终获胜参数；README 称 best_parameters 是“最常胜出参数”，实际是全数据再搜索。Methods 可能声称提供的组总被外层隔离，实际上普通 K 折不隔离。 | config/analysis_config/study_config 保存原始设计；best_parameters 与结果摘要保存最终参数覆盖；Methods 说明最终/外层参数、主要/敏感性验证、组规则及种子来源。`test_replay_config_retains_original_search_base` 验证配置字段；CLI 测试从导出的配置换新目录复跑，预测字节一致。**未证实原配置混写单独导致不同预测**，不将其标成已确认的数值复现失败。 |
| F6 · P2 | `src/psyml/models/factory.py:35`；Dummy 的 stratified/uniform 策略，或显式覆盖 MLP 等默认关键字 | Dummy 原先未接收配置种子；同种子两次构建的随机预测不同。工厂对 max_iter/random_state 等同时传默认值和 **params，合法覆盖报重复参数 TypeError。 | 用默认字典与显式覆盖合并，Dummy 接收 seed。`test_dummy_respects_seed` 比较100条随机预测完全一致；`test_default_parameter_can_be_overridden` 验证 max_iter=12。显式 estimator random_state 仍优先于全局种子，并在报告说明。 |
| F7 · P1 | `runner.py:437` `_choose_parameters`、组合排名；可用内部组/类不足，或 R² 等选择指标不可定义 | 没有可行内部切分时原代码静默用第一个候选；NaN 内部成绩可跳过部分折平均，外层全 NaN 还触发 KeyError。可能把未经声明的降级选择或不完整折评价用于排名。 | 多候选必须有可行内部切分；每个候选所有内部选择分数须有限；外层选择分数非有限时排除整个组合。次要未定义指标仍按原语义略去，但显式告知 n_folds。`test_no_inner_splits_cannot_silently_choose_first_candidate`（2组2外折）、`test_tiny_r2_primary_has_clear_failure`（3行3折）、失败折与主要验证失败测试覆盖。无搜索时不无故构造内层切分。 |
| F8 · P1/P2 | `gui/scripts/main.gd:851,980,993`；新运行、失败、终止、切语种；`core_bridge.gd:111` 进程终态 | 原新运行未清空 last_result_dir、旧表格/图形；失败或终止后仍能打开旧输出。结果页切语种不重绘已加载内容。bridge 在无终态事件且退出0时可不发失败，或收到完成后进程非0仍接受完成。 | 新运行/新预览清除旧结果；只接受有效完成摘要；切语种重绘同次结果；缺终态或完成后非0退出按失败处理。实际 Godot 流程测试验证分类→回归→终止→组数不足失败→修正成功→英法结果刷新，并保存状态截图。非0完成/无终态分支为代码审查修复，未单独做原生进程故障注入，见下方验证边界。 |
| F9 · P1/P2 | `src/psyml/runner.py:509`、`reporting/output.py:46`、`cli.py:25`；复用输出目录、导出中断、CLI SIGTERM | 已有 result.json 可与新一轮部分文件混在一起；原 CancellationRequested 是 Exception，可能被候选/折级宽泛捕获当成普通失败后继续。 | 非空目录拒绝写入并保留旧文件，成功摘要最后通过临时文件原子替换；取消使用单独的 BaseException 路径穿透拟合循环。`test_existing_output_is_preserved_on_retry`、`test_export_failure_never_leaves_success_marker`、`test_cancellation_inside_estimator_is_not_treated_as_failed_fold` 与 CLI 信号测试覆盖。GUI 强制停止明确提示部分输出不可用于研究。 |

补充来源一致性修复（P2，`runner.py` 入口）：直接 Python 调用同时传 `frame=` 和 input_path 时，原先可能分析内存表却对磁盘文件做 hash。现明确拒绝双来源，让调用者选择输入；GUI 本来只用文件输入，不受影响。`test_ambiguous_input_sources_are_rejected` 验证不会输出误导性来源记录。

补充 GUI 修复：预测变量的多选事件改用 `multi_selected`，避免取消选择后配置/按钮状态不及时刷新；长任务期间切语种重建的参数编辑器仍保持锁定；刷新预览时旧变量表被清除，异步旧响应不能配上新路径。

复现证据：[修复前12个失败用例输出](baseline-failures.txt)。该文件记录真正的修复前执行，并非事后推测。新增回归位于 [tests/test_scientific_audit.py](../../tests/test_scientific_audit.py)。其中 F2、F8、F9 的部分场景另由代码证据、GUI 流程或新增故障注入补足，不声称都包含在最初12个用例中。

## 全流程核对结论

| 环节 | 已核实行为 | 解释边界 |
|---|---|---|
| 数据导入与角色 | 9种格式通过现有加载测试；目标、显式组不可列为 feature_columns；选中列决定缺失行处理；原索引保留，切分/组/目标用 iloc 的局部位置同步取数。 | 管理标识不会被语义自动识别；默认候选预测列需人工检查。重复的输入索引可被保留，row_index 不保证唯一；做外部 join 前应核对原始索引。 |
| 学习型预处理 | 普通模型在每个内/外训练折拟合填补、编码、缩放；堆叠基模型内部也如此。类别类型由列 dtype 确定，不使用全数据取值拟合编码器。 | 没有时间序列、特征筛选等尚未实现功能的有效性保证；全空预测列、非法数值等仍可能使估计器失败，失败不能当性能差值。 |
| 验证切分 | GroupKFold、StratifiedGroupKFold、LOGO、带组 holdout 隔离组；普通 KFold/StratifiedKFold 不隔离，并有提示。内层在有组时保持组隔离。 | “提供组列”不等于所有外层策略自动变成分组策略；不要用普通随机折回答跨参与者外推问题。 |
| 超参数搜索 | 每个外部训练分区独立搜索；每次预处理也在内部训练折拟合。候选超上限用固定种子抽样，RMSE/MAE最小化，其余当前选择指标最大化。 | 候选范围不是科学最优证明；同分时按既定列表顺序选先者。失败候选不参与选择；所有失败时不给获胜参数。 |
| 模型与验证比较 | 每种验证独立排名，主要验证是配置数组第一项。GUI 按固定列表索引输出已选项，非点击时间顺序。主要验证全失败不会退回敏感性验证。 | GUI 没有重排控件；若需要另一主要验证顺序，应预先确定设计并通过配置/API明确表达，不能看完结果再选。 |
| 最终拟合 | 选定家族后，全数据多候选内层搜索确定最终覆盖参数，然后在全部可用数据拟合；不修改外层预测。 | 最终拟合模型没有独立新测试成绩，GUI也不序列化模型。 |
| 指标与预测 | 预测是当前获胜家族/主要验证的外部折预测；一般 K 折每行一次，holdout仅评价子集。折均值不加权，std(ddof=0)，summary标明有效折数。 | 不是全候选的逐样本预测仓库；不导出概率列；不同折规模不同时，均值不等于全体 OOF 池化指标。 |
| 配置与报告 | 原设计、最终参数、外层搜索证据分开保存；GUI固定seed=42/test_size=.2，Python配置可变。Methods说明组隔离、选择偏差、最终拟合和参数覆盖。 | 默认参数依赖记录的 sklearn 版本；显式覆盖不等于完整 estimator.get_params() 展开。报告是研究者核对材料，不是可直接无审阅发表的结论。 |
| 状态与导出 | 部分失败组合不会冒充成功排名；若仍有主要验证成功组合，可完成并在排行榜/警告暴露失败组合。失败导出无新成功标志；旧目录受保护。 | completed 表示本次结果与文件流程完成，不代表所有候选都成功，更不代表方法适合研究问题。 |

## 方法限制：保留为人工决策

1. **模型家族选择偏差（优先级最高）**。软件用外层分数选家族；获胜外层成绩虽然来自样本外预测，却已用于家族选择。现有参数嵌套只保护超参数选择。已在 GUI/Methods/warnings 明确提示；未改统计流程。选项：①预先指定单一家族，保留现有外层评价，计算少但不再用这些成绩选家族；②独立外部/最终测试集，固定全部选择后只评一次，需要额外数据且开发样本减少；③再加外层、把家族选择也包进内层，评价完整选择程序，成本更高且小样本不稳定。研究者需明确目标后决定。[scikit-learn 嵌套验证说明](https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html)。
2. **缺类别折与组权重**。当前保留可定义的标签指标并提示缺类别；宏平均/平衡指标依赖该折出现的标签。每折等权，既不是每样本统一权重，也未必是每组统一权重。可选预先定义全局标签集的指标、要求每折类别充分、组等权或样本等权；这些会改变评价目标，未自动选择。
3. **正类与概率解释**。二分类 AUC 按 estimator.classes_[1]；当前 GUI 无领域正类选择，AUC也不是概率校准证据。若领域关心某正类的灵敏度/特异度、校准或阈值决策，需另行预先设计。[scikit-learn ROC AUC 定义](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.roc_auc_score.html)。
4. **缺失与外推**。缺失目标沿用删除，drop沿用完整案例逻辑，但限定在本次所选列。是否接受完整案例分析、缺失机制假设、重复测量的组定义、跨中心与时间外推目标，均需研究者确定。
5. **小样本与推断**。只有两组时不能在每个外部训练分区再分组调参；不可为跑通而泄漏组。折间相关，折标准差不是置信区间；本轮未增加显著性检验、区间或时间序列策略。

## 待验证风险（不是本轮确认的新数值缺陷）

- 非默认 SVC `probability=True` 的概率校准由 libsvm 内部完成，应用没有传组路由；本轮未验证此非GUI预设路径的校准性能/组隔离。组数据的概率研究需专项设计；默认 GUI SVM 没有打开此选项。
- 多进程同时写同一个原本为空的目录、源文件在预览与执行之间被外部修改、磁盘满/强制关机在成功事件前后的全部时序，未做系统级压力测试。已有单次导出失败注入与目录保护不等于覆盖这些竞争条件。
- macOS实际启动已验证；其他系统的终止行为、原生文件选择器、屏幕阅读器和高缩放可访问性未实际观察。

## 验证记录与停止范围

- Python 全套：**93 passed**，3条预期的“单样本 R² 未定义”警告来自极小样本失败测试；[完整输出](core-tests.txt)。覆盖既有全部模型、格式、协议、报告以及本轮21个新增参数化回归场景。
- 代码检查：`ruff check src tests tools/generate_gui_test_data.py`、`git diff --check` 通过；已安装包 smoke test 通过。
- Godot 4.7.2：桥接测试通过；实际窗口流程完成分类、回归、取消/终止、错误恢复和三语结果刷新。见 [GUI流程](gui-flow.txt)、[最终截图与指南配置执行日志](gui-captures.txt)、[桥接日志](gui-bridge.txt)。早期沙箱启动无法访问窗口服务/日志目录，改用获准的本机窗口运行后成功，不把环境报错当成产品缺陷。
- 四页前后图与三语/边界/状态观察单列于 [视觉说明](VISUAL_REVIEW.md)，不以测试总数替代视觉或方法评价。
- 人工验收入口：[中文 GUI 人工测试指南](../GUI_MANUAL_TEST_ZH.md)。本轮停止在范围明确的修复、验证和文档交付；无提交、推送、新验证策略或新产品功能。
