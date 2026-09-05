# Computer Use 验收与研究者使用评估

2026-09-05，macOS / Godot 4.7.2 / 本机虚拟环境。第一轮代码已推送为 `d4b139c`；随后按用户选择实施完整嵌套家族/参数选择。本记录依据**真实窗口操作及其实际输出**，不把旧脚本测试冒充人工操作。

所有导入、变量/模型/策略选择、参数编辑、运行、终止、语言切换、窗口拖动和文件选择器操作均由 Computer Use 完成。最后截图使用 [被动截图工具](../../gui/tests/capture_manual.gd)：它只加载原场景并在 F12 时保存当前视口，不填写配置、切页或启动分析。数值文件用只读检查核对。记录了覆盖范围，不声称穷举所有选项的笛卡尔积。

## 科学正确性结论

完整嵌套选择已执行并通过信息边界反例；主结果不再由获胜家族的外层最高分替代。最终模型也不依赖外层排行榜。方法依据、统计目标、失败规则与剩余独立验证要求见 [方法实施记录](NESTED_SELECTION.md)。这允许进入研究者人工验收，**不等于模型具有已证明的外部效度**。

实际运行的配置、摘要、候选记录、逐折选择、预测与文件哈希归档在 [cua-evidence](cua-evidence/summary.json)。重点证据：

- [最终指南分类配置](cua-evidence/final-guide-class/config.json)：48 行、score/category、participant、分组3折、Decision Tree + Dummy、推荐搜索、内层2折、每家族2候选、seed=42。
- [逐折与最终选择](cua-evidence/final-guide-class/selection_trace.csv)：3个外层选择＋1个全数据选择；[候选证据](cua-evidence/final-guide-class/parameter_search.csv) 共16行，最终搜索同时包含两个家族。预测48行且原始索引唯一。
- [分类全矩阵](cua-evidence/nested-class-all/model_comparison.csv)：12家族×6验证=72组合，66成功、QDA的6组合失败。原始错误明确为类内协方差不满秩，见[候选错误](cua-evidence/nested-class-all/parameter_search.csv)。失败项不入成功排名；[六种选择流程](cua-evidence/nested-class-all/validation_summary.csv) 均完成。
- [QDA恢复](cua-evidence/qda-custom/config.json)：保持同一测试变量，使用自定义 `reg_param=[0.1,0.5]`、宏平均F1，成功完成并选择0.1。这是验收用例，不是向真实研究推荐事后改参数以追求成功。
- [回归全矩阵](cua-evidence/nested-reg-all/model_comparison.csv)：11家族×4验证=44组合均完成，最终家族为 Linear Regression；主指标评价完整选择流程，敏感性单列。
- [缺失删除](cua-evidence/final-missing-warning/predictions.csv)：46行，恰好排除原索引0（目标缺失）和4（所选预测值缺失）；observed与源表逐行一致。全缺失但未选的admin_note没有造成额外删除。

## GUI 功能与状态覆盖

| 范围 | 实际操作与结果 | 解释边界 |
|---|---|---|
| 启动与四页 | 常规启动器启动项目窗口；未加载数据时禁止运行。浏览导入后自动跳到设置，再返回检查角色。 | 不是 Godot 项目管理器。机器存在两份 Godot，测试按完整应用路径选择并置前。 |
| 九种格式 | CSV48×5；TSV/XLSX/XLS/SAV/DTA/XPT/Parquet各6×3；真实SAS7BDAT5×7。逐个通过路径输入、读取预览、数据页核对列名/值/行数。 | 除SAS外使用本地合成数据；SAS为[pyreadstat公开测试样本](https://github.com/Roche/pyreadstat/blob/master/test_data/basic/sample.sas7bdat)，哈希见证据摘要。没有把原来只模拟SAS分派的单测算作真实读取。 |
| 变量定义与多选 | 目标、组排除于预测变量；仅选score/category；普通点击及方向键＋空格增选/取消；长变量名可在下拉菜单与配置核对。 | 管理字段不会被语义自动识别；换文件会重置目标/分组，必须重新检查。 |
| 预处理 | 中位数、均值、众数、删除，以及标准化、min-max、不缩放均从GUI选择并在相应运行的配置中核对。 | 填补数值及训练折隔离由核心回归另验；GUI矩阵不声称逐一穷举所有缺失机制。 |
| 模型与验证 | 全部23模型、分类六策略/回归四策略实际运行；组数不足失败；多策略按固定列表的第一项为主要验证。 | 失败组合如实保留；有组列但使用普通K折时明确提示外层未隔离组。 |
| 搜索与指标 | 无参数搜索、推荐范围和自定义范围均运行；非法JSON禁用运行并指出参数；恢复后成功。实际GUI运行了平衡准确率、宏平均F1和RMSE。 | Accuracy/MAE/R²的选择与数值方向另由核心测试覆盖，未各自重跑一套GUI矩阵。内层折数不足的保护有直接核心反例。 |
| 导出 | 实际点击“打开完整结果文件夹”，Finder打开正确目录并列出结果文件；配置、主预测和Methods核对。 | 自动导出，无另一个“导出”按钮。只读数值核对不计为GUI操作。 |
| 终止 | 真实运行中点击“终止运行”，显示“任务已终止”；结果页为空、打开按钮禁用、无result.json；换新目录可重试。 | 不删除文件，部分输出不供研究使用。未模拟强制关机。 |
| 失败恢复 | 12组请求20折得到清楚失败；旧图/旧结果清空；改3折、换新目录后恢复。 | 失败目录无成功标志。 |
| 路径与文件夹 | 不存在路径报错并失效旧预览；非空输出/相对输出禁用运行；原生结果目录选择器能选空文件夹；文件选择器Cancel保持当前预览。 | 原生按钮由macOS显示为Open/Cancel，不随应用语言翻译。 |
| 三语、缩放和键盘 | 中英法四页及结果说明刷新；实际拖到最小窗口并恢复；Tab到“刷新配置”后空格激活，焦点边框清楚。 | 持续按住按钮的那一帧未单独抓取；hover/pressed样式定义已检查，不能据截图推断所有持续状态。 |
| 长文字与宽表 | 含中文/法文/空格的长路径、长目标名实际导入并运行；结果表实际水平拖动，下方指标/预测通过页面滚动可达。 | 短预览仍有截断；全值查CSV。表格仅预览前30组合、20预测。 |

工具偶尔未正确输入下划线/JSON标点，或粘贴已成功却返回超时；均通过重新观察真实输入框修正，未将这些自动操作工具问题归为产品缺陷。没有以“已点击”代替读取真实终态。

## 此次额外确认并修复的 GUI 问题

| 级别 | 触发、影响和证据 | 修复 |
|---|---|---|
| P2 | 不搜索参数时，模型选择变化走提前返回，未立即刷新检查配置/运行条件。清空模型后可遗留旧检查状态。 | 提前返回前刷新；真实GUI显示“请至少选择一个模型”并禁用运行；GUI回归明确触发多选信号。 |
| P2 | 缺失目标删除1行与所选字段缺失删除1行，被翻译为两条相同的泛化提示，研究者无法在界面区分排除原因。 | 三语分别保留原因和行数；实际重跑并保存[中文](cua-final/16-zh_CN-page4.png)、[英文](cua-final/17-en-page4.png)、[法文](cua-final/18-fr-page4.png)证据。 |
| P2 | 自定义Dummy分类候选prior进入回归；修复前直接测试失败：“Classification parameters leaked into regression: [prior]”。搜索模式切换也可能用预设值覆盖自定义缓存。 | 缓存按任务隔离，且只保存自定义编辑器的值。往返分类→回归→分类及自定义→推荐→自定义均经GUI实际检查，见[原分类值](cua-cache/01-zh_CN-page2.png)、[回归默认值](cua-cache/02-zh_CN-page2.png)、[恢复分类值](cua-cache/03-zh_CN-page2.png)。 |

这些修复不改变研究目标、正类定义或评价权重。方法上的家族选择更改是用户明确选择后的单独实施。

## 最终截图

| 页面 | 中文 | English | Français |
|---|---|---|---|
| 数据与变量 | [图](cua-final/01-zh_CN-page1.png) | [图](cua-final/06-en-page1.png) | [图](cua-final/09-fr-page1.png) |
| 分析设置 | [图](cua-final/03-zh_CN-page2.png) | [图](cua-final/07-en-page2.png) | [图](cua-final/08-fr-page2.png) |
| 检查与运行 | [图](cua-final/04-zh_CN-page3.png) | [图](cua-final/05-en-page3.png) | [图](cua-final/10-fr-page3.png) |
| 结果 | [图](cua-final/11-zh_CN-page4.png) | [图](cua-final/12-en-page4.png) | [图](cua-final/13-fr-page4.png) |

另有[推荐参数](cua-final/02-zh_CN-page2.png)、[最小窗口法文](cua-final/14-fr-page4.png)、[长路径与变量](cua-final/15-zh_CN-page1.png)。第一轮同夹具的前后视觉对照仍见[视觉说明](VISUAL_REVIEW.md)；当前图使用48行指南数据，不能用图中分数变化推断视觉修改影响了性能。

## 研究者视角的交付范围

适合本地表格模型开发、预先设计的内部评价和探索性比较。第一版还需要用户按[人工指南](../GUI_MANUAL_TEST_ZH.md)独立验收。输入选项和排行榜不能替研究者确定研究问题：管理ID须排除，数值编码的名义变量须正确表达类型，重复测量须定义独立分组；换文件后不能沿用对旧目标/组的假设。

已有结果属于上次已完成的运行；仅修改配置不会生成新结果，状态栏的“分析完成”也可能仍指上一次运行。新运行/新导入、失败和终止会清空旧结果；核对结果时以其config.json和目录为准。未声称具备冻结模型独立评分、概率/校准/阈值决策、时间切分或置信区间功能。

本次不把跨平台、屏幕阅读器、原生对话框所有系统操作、并发写同目录或磁盘故障的未测试情况写成通过。它们不属于此次macOS功能验收的已证实范围。

验证记录：[GUI完整流程](cua-evidence/gui-final-test.txt)、[参数缓存回归](cua-evidence/gui-parameter-context.txt)、[真实截图保存日志](cua-evidence/manual-capture.txt)、[Python完整套件](cua-evidence/core-final.txt)。核心99项通过，3条警告来自极小样本R²失败保护用例；这些数字证明相应实现检查通过，不代替方法适用性判断。
