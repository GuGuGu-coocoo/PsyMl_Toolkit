# PsyML Toolkit Development Plan

## 1. Project Overview

PsyML Toolkit 来源于本科阶段在真实科研与横向项目中逐步积累的一组 Python Machine Learning（机器学习）脚本。

早期开发时尚未使用：

- Git
- GitHub
- uv
- 现代 Python project structure（项目结构）
- automated testing（自动化测试）
- GUI（图形界面）

历史版本主要通过：

- 整个项目复制到不同文件夹
- 在文件夹名称中加入版本号
- 不同分析任务分别维护脚本

的方式进行版本管理。

目前已确认存在的代码包括：

### Regression（回归）
- KNN Regression
- Lasso Regression
- MLP Regression
- Random Forest Regression
- Support Vector Regression

### Classification（分类）
- KNN Classification
- Random Forest Classification
- Stacking Classification
- Support Vector Machine Classification
- MLP Classification
- Decision Tree Classification

### Other Legacy Experiments（其他旧实验）
- 一个基于 RNN（循环神经网络）的 NLP（自然语言处理）语义分类项目
- 其他可能尚未完成盘点的旧脚本、绘图、预处理和结果输出代码

当前阶段目标不是开发一个大型 AutoML（自动机器学习）系统，而是把已有代码整理为一个：

- 可运行
- 可复现
- 可维护
- 统计方法更规范
- 能避免常见 Data Leakage（数据泄漏）
- 对非程序研究者友好
- 具有基础 GUI

的 Research ML Toolkit（科研机器学习工具包）。

---

# 2. Current Development Scope

当前开发只规划到：

1. 旧代码完整盘点
2. 隐私与知识产权检查
3. 保存 Legacy Version（旧版本）
4. Git / GitHub 管理
5. 旧版本命名与版本关系整理
6. uv 环境管理
7. Codex 全面 Review
8. 修复统计和工程问题
9. 建立新的 PsyML Core（核心代码）
10. 补齐基础模型
11. 建立统一 preprocessing（预处理）
12. 建立 Cross-Validation（交叉验证）
13. 建立 Data Leakage Protection（数据泄漏保护）
14. 统一评价指标和结果输出
15. 建立基础 GUI

当前阶段不继续规划：

- AutoML
- Transformer
- LLM
- Cloud Service
- 数据库
- SHAP 高级解释系统
- 复杂模型搜索
- 大规模深度学习
- Web SaaS
- 商业化

---

# 3. Phase 0 — Legacy Asset Inventory

## Goal

完整搞清楚本科阶段到底留下了哪些 ML / Data Analysis（数据分析）代码。

在正式重构之前，不假设当前文件夹中的代码已经完整。

建立：

`docs/legacy_inventory.md`

---

## 3.1 Scan Existing Directories

重点检查：

- `program/`
- `psyml/`
- 带版本号的历史文件夹
- 单独的 NLP 项目
- 决策树项目
- 其他旧项目

例如：

- `Classiffication_Models-v1.1.2`
- `Regression_Models-v1.1.0`

以及其他：

- `v1.0`
- `v1.1`
- `final`
- `new`
- `test`
- `backup`

之类历史目录。

---

## 3.2 Record Model Assets

记录所有已经存在的模型。

### Regression

已确认：

- KNN
- Lasso
- MLP
- Random Forest
- SVR

继续检查是否还有：

- Linear Regression
- Ridge
- Elastic Net
- Decision Tree Regression
- Gradient Boosting
- 其他模型

### Classification

已确认：

- KNN
- Random Forest
- Stacking
- SVM
- MLP
- Decision Tree

继续检查是否还有：

- Logistic Regression
- Naive Bayes
- Gradient Boosting
- 其他模型

### Specialized

记录：

- RNN NLP
- tokenizer
- embedding
- sequence preprocessing
- 文本分类相关逻辑

---

## 3.3 Record Supporting Functions

检查是否已有：

- Train/Test Split
- K-Fold Cross-Validation
- Stratified Cross-Validation
- Grid Search
- Random Search
- StandardScaler
- MinMaxScaler
- Missing Value Handling
- Feature Selection
- Feature Importance
- ROC Curve
- Confusion Matrix
- R²
- MAE
- RMSE
- Accuracy
- Precision
- Recall
- F1
- AUC
- plotting
- result export
- CSV output
- Excel output
- model saving
- random seed
- config

不要重复开发已经存在且正确的功能。

---

# 4. Phase 1 — Legacy Version Archaeology

## Goal

还原本科时期通过文件夹管理版本的历史。

建立：

`docs/legacy_versions.md`

---

## 4.1 Preserve Original Names

第一次保存旧代码时：

**不要修改原文件夹名称。**

例如：

`Classiffication_Models-v1.1.2`

即使 `Classiffication` 拼写错误，也先保留。

因为：

> 原文件夹名称本身属于历史信息。

---

## 4.2 Compare Historical Versions

让 Codex 比较不同版本：

- 文件差异
- 函数差异
- 模型差异
- 参数差异
- preprocessing 差异
- output 差异
- 新增功能
- 删除功能

分类为：

### Latest Candidate
可能是最新版本。

### Superseded
已经被后续版本替代。

### Experimental Branch
独立实验，不属于版本升级关系。

### Unique Component
旧版本中存在但新版本丢失的独特功能。

### Unknown
无法确定。

不能只根据：

`v1.1.2 > v1.1.1`

就自动认为前者完全包含后者。

---

# 5. Phase 2 — Backup and Privacy / IP Audit

## Goal

在 GitHub 前保证项目安全。

先保存：

`psyml_legacy_backup/`

作为完全不修改的历史备份。

---

## 5.1 Remove Sensitive Information

检查并删除或替换：

- 真实被试数据
- 姓名
- 学号
- 手机号
- 学校名称
- 企业名称
- 客户名称
- 内部项目编号
- API Key
- Token
- Password
- 服务器地址
- 数据库信息
- 本地绝对路径
- 商业项目专用逻辑
- 无权公开的数据
- 无权公开的第三方代码

---

## 5.2 IP Check

检查原横向项目是否涉及：

- Source Code Ownership（源码归属）
- Intellectual Property（知识产权）
- Confidentiality（保密）
- Client Ownership（客户所有权）

如果暂时不能确认：

> GitHub Repository 保持 Private（私有）。

---

# 6. Phase 3 — Git Repository Initialization

创建：

`psyml-toolkit`

Git repository。

第一次导入尽量保留原始历史结构。

建议：

```text
legacy/
└── original/
    └── program/
        ├── Classiffication_Models-v1.1.2/
        ├── Regression_Models-v1.1.0/
        ├── nlp_rnn/
        ├── decision_tree/
        └── other/

第一次 commit：

chore: import legacy PsyML research code

建立 tag：

legacy-v0.1

6.1 Git Replaces Folder Versioning

从这一刻开始停止：

xxx-v1.1.3
xxx-final
xxx-final2
xxx-new

这种目录复制式版本管理。

以后使用：

Git commit
Git branch
Git tag

管理版本。

7. Phase 4 — Initial README

README 第一版不需要包装得很漂亮。

至少写：

Project

PsyML Toolkit

Background

该项目起源于本科阶段真实科研与应用项目中开发的 Python ML scripts。

Current Capabilities
Regression
KNN
Lasso
MLP
Random Forest
SVM
Classification
KNN
Random Forest
Stacking
SVM
MLP
Decision Tree
Experimental
RNN-based NLP classification
Status

Legacy preservation and modernization in progress.

8. Phase 5 — uv Migration

采用：

uv

建立：

pyproject.toml
uv.lock

明确：

Python version
dependencies
development dependencies

目标：

uv sync

可以建立环境。

8.1 Dependency Discovery

从旧代码扫描真实依赖：

可能包括：

numpy
pandas
scipy
scikit-learn
matplotlib
tensorflow
keras
torch
openpyxl
其他实际存在的库

原则：

先让旧代码能够运行，再考虑依赖升级。

不要为了“现代化”一次性把所有依赖升到最新版。

9. Phase 6 — Current State Baseline

建立：

docs/current_state.md

记录：

Working

当前可以运行的脚本。

Broken

已经无法运行的脚本。

Unknown

尚未测试。

Manual Configuration

目前需要人工修改：

data path
target variable
feature list
model
parameters
output path
Inputs

支持：

CSV
XLSX
其他实际格式
Outputs

当前已有：

predictions
metrics
plots
model files
CSV
Excel
其他
10. Phase 7 — Codex Read-Only Review

完成 Legacy 保存和环境恢复后，让 Codex 进行一次完整 Review。

此阶段：

只分析，不修改代码。

生成：

docs/legacy_code_review.md

11. Statistical / ML Review

检查：

Data Split
Train/Test Split 是否规范
是否提前使用 test data
Data Leakage
scaling 是否在完整数据 fit
imputation 是否在完整数据 fit
feature selection 是否泄漏
hyperparameter tuning 是否泄漏
stacking 是否存在 leakage
participant-level leakage 是否可能存在
Model-Specific Issues

检查：

KNN 是否正确 scaling
SVM 是否正确 scaling
Lasso 是否正确标准化
MLP preprocessing 是否正确
RF 是否有合理参数
Stacking 是否正确使用 out-of-fold predictions
Decision Tree 是否合理
RNN 是否确实用于序列/NLP数据
Evaluation

检查已有：

Accuracy
Precision
Recall
F1
AUC
R²
MAE
RMSE

计算是否正确。

12. Software Engineering Review

检查：

duplicated code
hard-coded paths
hard-coded parameters
global variables
long scripts
repeated preprocessing
repeated evaluation
config
output management
exception handling
logging
deprecated APIs
dependency problems
maintainability
testability
13. Legacy Classification

Codex 把旧代码划分为：

Core Candidate

适合进入 PsyML Core。

预计包括：

KNN
Lasso
MLP
RF
SVM
Stacking
Decision Tree

但必须以 Review 为准。

Specialized / Experimental

例如：

RNN NLP

暂时保留但不进入 GUI 主流程。

Archive Only

强绑定旧项目、已经淘汰或无通用价值的代码。

14. Phase 8 — First Round Fixes

优先解决：

P0
Data Leakage
明显统计错误
程序无法运行
deprecated API
privacy / security
P1
hard-coded paths
duplicated preprocessing
duplicated evaluation
random seed
config
input/output consistency

当前不要追求完美 architecture。

先保证：

正确 + 可运行 + 可复现。

15. Phase 9 — Create Modern PsyML Core

Legacy 代码保持不动。

建立新的：

src/
└── psyml/
    ├── data/
    ├── models/
    │   ├── regression/
    │   └── classification/
    ├── preprocessing/
    ├── validation/
    ├── evaluation/
    ├── reporting/
    └── utils/
15.1 Naming Convention

统一：

snake_case

例如：

classification
regression
preprocessing
evaluation

不再使用：

Classiffication_Models-v1.1.2
Regression_Models-v1.1.0
program
final
new

但这些名字继续保留在 legacy/ 中。

# Phase 16 — Research Methods & Reproducibility Output

## Goal

PsyML Toolkit 不仅输出模型结果，还应自动记录一次分析所需的关键 Methods（方法）和 Reproducibility（可复现性）信息。

目标是帮助研究者：

- 撰写论文 Methods（方法）部分
- 保存完整分析设置
- 复现过去的分析
- 向审稿人报告模型与软件环境
- 检查可能的数据泄漏和分析风险

---

## 16.1 Analysis Manifest

每次分析自动生成：

`analysis_manifest.json`

至少记录：

### Software

- PsyML Toolkit version
- Python version
- operating system
- scikit-learn version
- numpy version
- pandas version
- scipy version

如果本次分析实际使用：

- PyTorch version
- TensorFlow version
- CUDA version
- GPU model

则同时记录。

不使用的框架无需强制记录。

---

## 16.2 Analysis Configuration

记录：

- analysis type
- target variable
- feature variables
- participant / group variable
- sample size
- model
- model hyperparameters
- preprocessing
- missing-data strategy
- scaling
- encoding
- validation strategy
- number of folds
- train/test ratio
- class weighting
- random seed
- evaluation metrics

---

## 16.3 Data Provenance

可记录：

- dataset filename
- dataset dimensions
- timestamp
- optional dataset hash

Dataset Hash（数据集哈希）用于帮助确认后续复现时是否使用了完全相同的数据文件。

不得在报告中自动写入：

- 被试姓名
- 学号
- 手机号
- 其他直接身份信息

---

## 16.4 Methods Summary

每次分析自动生成：

`methods_summary.md`

内容使用适合论文 Methods（方法）部分参考的自然语言描述。

例如：

> A random forest classifier was implemented using scikit-learn under Python. Missing values were imputed using median imputation, and continuous predictors were standardized within each training fold. Model performance was evaluated using five-fold group cross-validation, with participant ID used as the grouping variable to prevent participant-level data leakage. Performance was summarized using balanced accuracy, F1 score, and ROC-AUC. A fixed random seed was used for reproducibility.

Methods Summary 必须根据本次真实分析配置自动生成。

不得生成用户未实际执行的分析步骤。

---

## 16.5 Reproducibility Report

自动生成：

`reproducibility_report.md`

至少包括：

### Environment
- PsyML version
- Python version
- relevant library versions
- OS
- GPU / CUDA information if applicable

### Data
- sample size
- number of features
- target
- grouping variable
- dataset hash if enabled

### Preprocessing
- missing-data handling
- scaling
- encoding
- feature selection

### Validation
- split strategy
- Cross-Validation strategy
- number of folds
- group-aware validation
- random seed

### Model
- model name
- hyperparameters

### Evaluation
- metrics
- warnings
- possible leakage risks detected by PsyML

---

## 16.6 Result Directory

统一 Result Output 扩展为：

results/
└── run_xxx/
    ├── metrics.csv
    ├── predictions.csv
    ├── config.json
    ├── analysis_manifest.json
    ├── methods_summary.md
    ├── reproducibility_report.md
    └── figures/

---

## 16.7 GUI Integration

Godot GUI 后续只负责：

- 查看 Methods Summary
- 查看 Reproducibility Report
- 导出上述文件
- 提示用户保存完整分析记录

所有 Methods 和 Reproducibility 内容都由 Python PsyML Core 生成。

Godot 不自行推断或生成统计方法描述。

以下编号自动顺延一位:

16. Phase 10 — Basic Model Completion

不要一次性增加很多模型。

目标只是补齐科研中最基础的 baseline（基线）。

Regression

保留已有：

KNN
Lasso
MLP
Random Forest
SVR

检查是否已有，如果没有则补：

Linear Regression
Ridge Regression
Dummy Regressor

可选：

Decision Tree Regression
Classification

保留已有：

KNN
RF
SVM
MLP
Stacking
Decision Tree

检查是否已有，如果没有则补：

Logistic Regression
Dummy Classifier

暂时不要求：

XGBoost
LightGBM
Transformer

# 17. PsyML GUI Architecture

PsyML 采用：

```text
Godot GUI
    ↓
Analysis Configuration
    ↓
PsyML Interface Layer
    ↓
Python PsyML Core
    ↓
Preprocessing
    ↓
Validation
    ↓
Model Training
    ↓
Evaluation
    ↓
Result Export
    ↓
Godot Results Viewer
Godot 与 Python Core 必须保持明确边界。
Godot 不直接：
- 训练模型
- 进行 Cross-Validation
- 进行数据标准化
- 计算统计指标
- 管理 sklearn Pipeline
Godot 只负责：
- 选择文件
- 选择变量
- 设置分析参数
- 启动分析
- 显示运行状态
- 显示 Warning
- 展示结果
- 导出结果
18. Godot ↔ Python Interface
第一阶段应优先选择简单、稳定、可调试的通信方式。
推荐顺序：
First Choice
Local Process / Local API（本地进程 / 本地接口）
例如：
Godot
↓
analysis_config.json
↓
Python PsyML Core
↓
results.json / CSV / figures
↓
Godot
或者：
Godot
↓
Local HTTP API
↓
Python PsyML Core
↓
JSON Response
↓
Godot
具体方案在实现阶段根据：
- 打包难度
- Windows compatibility
- macOS compatibility
- 调试便利性
- 性能
选择。
第一阶段不要为了追求“纯单进程应用”而使用复杂 Python embedding。
19. GUI v0.1 Workflow
Godot GUI 第一阶段只实现基础科研流程。
Step 1 — Import Data
支持：
- CSV
- XLSX
用户通过 File Picker（文件选择器）选择数据。
Godot 将文件路径传给 Python Core。
显示：
- rows
- columns
- variable names
- missing values
- inferred variable types
Step 2 — Select Task
选择：
- Regression（回归）
- Classification（分类）
RNN / NLP 暂时不进入 GUI 主流程。
Step 3 — Select Variables
GUI 提供：
Target Variable
单选。
Feature Variables
多选。
Participant / Group Variable
可选。
如果用户数据包含重复测量，应提醒考虑使用：
- Group K-Fold
- Leave-One-Group-Out
Step 4 — Preprocessing
允许选择：
Missing Data
- Drop
- Mean Imputation
- Median Imputation
- Mode Imputation
Scaling
- None
- StandardScaler
- MinMaxScaler
Encoding
- One-Hot Encoding
Godot 仅生成配置。
真正 preprocessing 由 Python Core 执行。
Step 5 — Validation
支持：
- Train/Test Split
- K-Fold
- Stratified K-Fold
- Group K-Fold
- Leave-One-Group-Out
如果用户选择了 Group Variable：
GUI 应优先提示 Group-Aware Validation（分组验证）。
Step 6 — Select Model
Regression
- Linear Regression
- Ridge Regression
- Lasso
- KNN
- Random Forest
- SVR
- MLP
Classification
- Logistic Regression
- Decision Tree
- KNN
- Random Forest
- SVM
- MLP
- Stacking
Step 7 — Review Configuration
运行前展示 Analysis Summary（分析摘要）：
Task
Target
Features
Group Variable
Preprocessing
Validation
Model
Random Seed
用户确认后再运行。
Step 8 — Run Analysis
点击：
Run Analysis
Godot：
1. 生成 analysis config；
2. 调用 Python PsyML Core；
3. 显示运行状态；
4. 接收分析结果。
GUI 应显示：
- Waiting
- Loading Data
- Preprocessing
- Training
- Cross-Validation
- Evaluating
- Complete
如果 Python Core 返回 Warning 或 Error：
Godot 应直接显示可理解的信息。
Step 9 — Results
Regression
显示：
- R²
- MAE
- RMSE
- Predicted vs Actual
Classification
显示：
- Accuracy
- Balanced Accuracy
- Precision
- Recall
- F1
- ROC-AUC
- Confusion Matrix
Godot 可以负责结果展示。
但所有数值计算必须来自 Python Core。
Step 10 — Export
允许用户选择：
Export Results
输出：
- metrics.csv
- predictions.csv
- analysis_config.json
- figures
- analysis summary
20. Cross-Platform Strategy
PsyML GUI 的目标平台优先级：
Tier 1
- Windows
- macOS
作为第一阶段正式支持平台。
Tier 2
- Linux
在核心 GUI 稳定后测试。
Tier 3
- Web
Godot 可以导出 Web，但 Web 版本不能假设浏览器可以直接运行本地 Python / scikit-learn。
因此未来 Web 版本需要：
Godot Web Frontend
↓
HTTPS API
↓
Python PsyML Backend
Web 不属于当前开发阶段。
当前阶段不得为了 Web 支持而增加服务器架构。
21. GUI Development Principles
Godot GUI 必须遵循：
Separation of Concerns
Godot：
Interface

Python：
Scientific Computation

No Duplicate Scientific Logic
不得同时存在：
Python calculates metric A
Godot also calculates metric A
唯一真值来源：
Python PsyML Core

Config-Driven
GUI 应生成统一 Analysis Config。
例如：
{
  "task": "classification",
  "target": "outcome",
  "features": ["x1", "x2", "x3"],
  "group_variable": "participant_id",
  "model": "random_forest",
  "validation": "group_k_fold",
  "scaling": "standard",
  "random_seed": 2026
}
Python Core 根据 config 执行分析。
这样未来：
- GUI
- CLI
- Python API
都可以调用同一 Core。
22. GUI v0.1 Explicit Non-Goals
Godot GUI 第一阶段不做：
- RNN / NLP
- Web deployment
- Cloud backend
- User account
- Database
- AutoML
- SHAP
- Optuna
- LLM
- Plugin system
- Fancy animations
- Online collaboration
GUI 的目标只有：
让不会修改 Python 代码的研究者，
可以通过 Godot GUI 完成一次规范的 Regression 或 Classification 分析。

23. Testing Required Before GUI Stage Completion
至少完成：
Core
- Regression pipeline 可独立运行
- Classification pipeline 可独立运行
- Cross-Validation 正确
- Group-Aware Validation 正确
- preprocessing 无 Data Leakage
- metrics 正确
- result export 正确
Godot ↔ Python
- Godot 可以启动分析
- config 可以正确传递
- Python Error 可以返回 Godot
- Python Warning 可以返回 Godot
- analysis results 可以正确读取
- 中文路径可以正常工作
- 路径包含空格时可以正常工作
Platform
至少测试：
Windows
完整 Regression Demo。
Windows
完整 Classification Demo。
macOS
完整 Regression Demo。
macOS
完整 Classification Demo。
GUI
测试：
- CSV import
- XLSX import
- variable selection
- preprocessing selection
- model selection
- validation selection
- result display
- result export
24. Current Development Finish Line
当前阶段完成标准：
- Legacy Code 完成盘点
- 历史版本关系基本明确
- Legacy 原始版本保存
- Privacy / IP Audit 完成
- Git / GitHub 管理完成
- uv 环境完成
- Codex Legacy Review 完成
- P0 问题修复
- PsyML Core 建立
- 基础 Regression 模型补齐
- 基础 Classification 模型补齐
- preprocessing 统一
- Cross-Validation 统一
- Group-Aware Validation 支持
- Data Leakage Warning 支持
- Evaluation Metrics 统一
- Result Export 统一
- Analysis Config 统一
- Godot ↔ Python interface 跑通
- Godot GUI 可以完成 Regression 分析
- Godot GUI 可以完成 Classification 分析
- Windows GUI 基础流程可用
- macOS GUI 基础流程可用
- nalysis_manifest.json 可以自动生成
- methods_summary.md 可以根据实际分析自动生成
- reproducibility_report.md 可以记录环境、模型、验证和预处理信息
达到这里后：
暂停扩展功能，邀请真实研究者试用。

再根据 User Feedback（用户反馈）决定下一阶段。