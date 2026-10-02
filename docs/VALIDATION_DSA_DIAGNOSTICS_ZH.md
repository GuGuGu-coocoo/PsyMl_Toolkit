# DSA 数值差异诊断附录：Linux 内核对照与 macOS（aarch64）核查

[English](VALIDATION_DSA_DIAGNOSTICS_EN.md) · [Français](VALIDATION_DSA_DIAGNOSTICS_FR.md)

案例 `psyml_dsa_group_nested_v1`，固定提交 `de33abfe52ccfee67f461a850edd00a14d2fbfaa`，记录日期 2026-10-02。

## 1. 目的与结论

本附录记录对已公开保留的跨平台差异（`roc_auc_ovr_weighted` 约 2.03e-7、折外概率最大约 2e-5）的有界数值诊断：一份在 Linux parity 环境完成的受控内核对照实验（共 25 次拟合：5 次单折探针 + 20 次四折内核对照），以及 macOS（aarch64）上的最小只读核查。

**结论。** Linux 对照中，仅切换 OpenBLAS CPU 内核分派，或对标准化输入做 1 ulp 级扰动，就足以产生与记录差异同量级、折 2 同方向、同样为单对排序翻转的 AUC 变化，且硬预测不变——这支持"拟合数值路径对极微小数值差异敏感"的机制。macOS 复跑的两折差异也可精确分解为每折恰好一对严格排序翻转（折 1 类别 6、折 2 类别 13）；其数值后端为 Apple Accelerate，而非 OpenBLAS。**但原始 Mac 差异的具体根因（哪一个库、指令路径或预处理步骤）仍未确认**，折 1 的变化未被 Linux 内核对照复现。

本附录不改变训练核心、冻结容差、基线或科学协议；不把诊断用的 tol/ftol/内核设置变成产品默认；不宣称 Mac 已被完整模拟，也不宣称跨平台数值等价。

## 2. 材料与来源

- **Linux 诊断记录**（2026-10-01）：包含折 1 探针与四折 OpenBLAS 内核对照，共 25 次拟合；接收时按清单校验，26/26 个文件哈希匹配。本附录提供实验设置与结果摘要。
- **macOS 核查环境（aarch64，案例 parity，与官方 `uv.lock` 复跑分开）**：Python 3.12.14、NumPy 2.3.5、SciPy 1.17.0、scikit-learn 1.8.0、pandas 2.2.3、joblib 1.5.3、matplotlib 3.10.8；`OPENBLAS_NUM_THREADS`、`OMP_NUM_THREADS`、`MKL_NUM_THREADS` 均为 1。
- **数据与产物**：冻结派生 CSV（SHA-256 `75a5fe87a58f4cfde777d914d674362b5148854a3c7064d8c686c0e25c3a047e`）、冻结 Linux 参考产物、macOS 复跑产物（另见 `expected/reverification_macos.json`）。
- **工具**：`tools/cases/diagnose_auc_pairs.py`（本仓库新增，纯分析、不拟合模型、不参与训练）；单元测试 `tests/test_auc_rank_contribution.py`。

## 3. Linux 实验结果摘要

### 3.1 折 1 固定 C=1 探针（5 次拟合）

| 运行 | 迭代 | 停止条件 | 梯度 ∞-范数 | AUC 与基线差 | 概率最大差 | 硬预测变化 |
| --- | --- | --- | --- | --- | --- | --- |
| baseline | 443 | 投影梯度 ≤ gtol | 9.72e-9 | 0 | 1.11e-16 | 0 |
| repeat | 443 | 投影梯度 ≤ gtol | 9.72e-9 | 0 | 1.11e-16 | 0 |
| 输入 +1 ulp | 422 | 投影梯度 ≤ gtol | 8.43e-9 | −2.0305393111375025e-7 | 7.116e-5 | 0 |
| tol=1e-11 | 454 | 目标函数相对变化 | 6.20e-9 | 0 | 6.913e-6 | 0 |
| tol=1e-11 且 ftol=1e-16 | 531 | 目标函数相对变化 | 1.18e-9 | 0 | 1.457e-5 | 0 |

- 扰动把 82,080 个标准化值各朝正无穷移动 1 ulp，最大改动 3.55e-15；仅类别 5 出现一对严格排序翻转。加权 OVR 的单对单位为 `1/(19×120×2160) = 2.0305393112410655e-7`，与该 AUC 变化一致。
- 两次收紧容差的运行都按目标函数相对变化停止，未达到更严的梯度条件；AUC 与基线相同，但概率并非逐位一致。这是诊断观察，**不是修复建议**。
- 冻结记录的四折 `n_iter` 为 443/449/451/439，均远未用满 2000 次。

### 3.2 四折 OpenBLAS 内核对照（20 次拟合）

- 输入：由原 pipeline 物化的四折标准化训练/测试矩阵；逐折 imputer 统计量、scaler 均值/方差/scale 与冻结 `fit_audit` 完全相等。实际内核经 threadpoolctl 核实（默认 SkylakeX、Haswell、Sandybridge），线程数均为 1。
- 默认内核两次运行的系数、截距与概率数组完全相同。
- 仅切换内核即改变拟合参数与概率，硬预测均不变：
  - Haswell 四折概率最大差：1.01e-5、7.49e-6、2.28e-6、4.87e-6；Sandybridge：4.52e-5、7.64e-6、2.57e-6、2.15e-6。
  - 折 2 AUC 在 Haswell 与 Sandybridge 下均增加 2.030539311e-7，其余折 AUC 不变。
  - 折 2 的精确逐对计数均为类别 13、1 对严格翻转、无平局；排序重建的 AUC 差与报告值在浮点舍入内一致。
- 把全部模型参数放回默认内核、用共同预测内核重算输出，AUC 保持不变（概率重算差 ≤3.44e-15）→ 该对照中的 AUC 变化来自**拟合参数**，而非仅预测阶段的矩阵乘法。
- 以独立公式复算带 L2 惩罚的多项 logistic 平均负对数似然与梯度，与捕获的求解器输出吻合。
- 该内核对照未复现折 1 的 AUC 变化（折 1 概率有变化，但排序未变）。

## 4. macOS（aarch64）最小核查（2026-10-02）

### 4.1 输入与身份

派生 CSV 哈希与冻结值一致；四折成员与冻结 `fold_membership.json` 完全相同；选择轨迹相同且全部为 `logistic_regression, C=1.0`；两侧 `predictions_with_probabilities.csv` 各 9,120 行，按 `row_index`/`fold`/`observed` 对齐，概率列顺序一致。

### 4.2 折 1、折 2 的逐对排序分析

用 `tools/cases/diagnose_auc_pairs.py` 比较冻结 Linux 概率与 macOS 复跑概率：

| 折 | 类别 | 变化对 | 严格翻转 | 新平局 | 解除平局 | 净一致对 | 贡献 | 实测 AUC 差 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 6 | 1 | 1 | 0 | 0 | +1 | 2.0305393112410655e-7 | 2.0305393111375025e-7 |
| 2 | 13 | 1 | 1 | 0 | 0 | +1 | 2.0305393112410655e-7 | 2.0305393111375025e-7 |

两折的净贡献等于贡献绝对值（无类别间抵消）；重建贡献与实测 AUC 差相差约 1.04e-17（浮点舍入）。仓库既有记录中折 2 的差为 2.030539310e-7（末位不同来自指标累加顺序），同样在舍入范围内。

具体样本对（概率为该类别 OVR 概率，segment 编号可回联）：

- **折 1，类别 6**：正例 `a06_p4_s34`（行 2613）对负例 `a18_p8_s25`（行 8604）。冻结 margin −3.709e-7（负例更高）→ Mac margin +2.490e-7；两样本该类别概率变化分别为 +2.77e-7 与 −3.43e-7。
- **折 2，类别 13**：正例 `a13_p7_s36`（行 6155）对负例 `a17_p3_s25`（行 7824）。冻结 margin −2.122e-9 → Mac +4.936e-9；概率变化 +8.33e-9 与 +1.27e-9（概率水平约 0.00207）。

### 4.3 预处理、后端与优化器退出信息

- 逐折重建的 imputer/scaler 状态与冻结 `fit_audit` 相比：折 1、2 完全相等；折 3 方差差 8.88e-16、折 4 均值差 3.33e-16（求和顺序量级）。
- 逐折系数/截距与冻结参考的最大绝对差：折 1 3.14e-5/6.73e-5、折 2 2.23e-5/5.97e-5、折 3 2.31e-5/8.78e-5、折 4 1.99e-5/6.00e-5。
- 该 macOS 环境 NumPy 的 BLAS/LAPACK 为 **Apple Accelerate**（非 OpenBLAS）；threadpoolctl 仅报告 OpenMP 1 线程（该后端不经 threadpoolctl 暴露 BLAS 池）。
- 固定 C=1 的独立诊断重拟合（未改生产代码）：四折均以 "NORM OF PROJECTED GRADIENT <= PGTOL" 停止，`n_iter` 为 436/436/435/442（Linux 为 443/449/451/439），梯度 ∞-范数 9.08–9.84e-9；概率与 Mac 折外表最大差 1.11e-16，硬预测 0 变化。

## 5. 确认与未确认

**确认（限于本案例记录范围）**

- 极微小的输入数值变化（1 ulp 量级）或仅切换 OpenBLAS CPU 内核分派，就足以改变优化路径与停止位置，产生与记录差异同量级的概率与排序指标变化，同时保持硬预测与主要标签指标不变。
- macOS 复跑的两折差异同样可精确分解为每折一对严格排序翻转（折 1 类别 6、折 2 类别 13），无平局、无抵消；折 2 与 Linux 内核对照同为类别 13。
- Mac 与 Linux 的数值后端不同（Accelerate 对 OpenBLAS），而优化器停止条件相同（均为投影梯度准则），因此差异不是"停止条件不同"造成的。

**未确认**

- 原始 Mac 差异由哪一个具体库、指令路径或预处理步骤造成；本节只给出候选机制，不指定唯一原因。
- 折 1 的变化未被 Linux 内核对照复现，不能声称已被解释。
- 本附录不证明 Mac 已被完整模拟或跨平台全面数值等价；统一种子或调小 tol 也不保证逐位一致，本文的 tol/ftol 诊断即为反例。

## 6. 公开工具与复现入口

- 工具与测试：`tools/cases/diagnose_auc_pairs.py`、`tests/test_auc_rank_contribution.py`（覆盖无变化、单次严格翻转、生成/解除平局、相互抵消、不同类别权重、行/列未对齐拒绝；均为小型测试，不运行完整拟合）。
- 复现命令（仓库根目录）：

```bash
uv run python -m tools.cases.diagnose_auc_pairs \
  --baseline <冻结 predictions_with_probabilities.csv> \
  --alternative <复跑 predictions_with_probabilities.csv> \
  --fold 2 --segments <含 row_index、segment_id 的 CSV> \
  --output pair_diagnostics_fold2.json
```

## 7. 参考

1. scikit-learn 1.8.0 `sklearn/linear_model/_logistic.py`（L-BFGS 停止条件与参数）：<https://github.com/scikit-learn/scikit-learn/blob/1.8.0/sklearn/linear_model/_logistic.py>
2. SciPy `minimize(method='L-BFGS-B')` 文档（gtol/ftol 语义）：<https://docs.scipy.org/doc/scipy/reference/optimize.minimize-lbfgsb.html>
3. 本仓库跨平台记录：`examples/public/dsa_group_nested_v1/expected/reverification_macos.json`；官方锁定环境记录：`examples/public/dsa_group_nested_v1/expected/reverification_uv_lock.json`
