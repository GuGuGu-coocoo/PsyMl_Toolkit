# PsyML Toolkit v0.3.1

## 中文

本版集中改进配置往返、结果可追溯性、图形呈现与公开案例复现，并重新整理三语使用说明。

- **配置与界面**：保留估计器参数的 JSON 数值类型；拒绝含糊的多模型固定参数组合；配置保存错误显示在发起操作的页面。混淆矩阵适配多类别结果，图形正确呈现折间不确定性与类别标签。
- **结果记录**：保存成功运行中的优化器和估计器警告；预测清单记录类别映射与来源；分析文件哈希、行标识和数值运行环境绑定到实际输入快照。常量目标的 R² 约定明确写入结果说明，类别计数以已观测值为准。
- **公开复现**：提供 DSA 活动分类与 California Housing 回归的可导入 CSV、配置、三语步骤和有环境记录的比较结果；California 冻结数据在 Windows 检出时保持原始字节。各案例的验证范围与环境见对应记录。
- **使用说明**：英文、中文和法文 README 各自提供简短入口；完整图形界面流程、模型与指标说明集中到对应语言的研究者指南。
- **自动发布检查**：三平台核心与 GUI 测试、Python 分发包及 wheel 冒烟测试；Mac/Windows 原生独立打包，包含分类/回归训练与预测、置换重要性、单样本 SHAP、拟合系数冒烟测试；归档完整性、真实二进制架构、版本、锁文件、干净源码提交及 SHA-256 校验。

**下载**：Apple Silicon Mac 使用 `PsyML-Toolkit-0.3.1-macOS-arm64.zip`；Windows x64 使用 `PsyML-Toolkit-0.3.1-Windows-x64.zip`。完整解压后打开应用；Windows 保留旁边的 `core` 文件夹。两种应用均包含运行环境。Release 仅附这两个应用 ZIP，GitHub 自动提供源码下载。

macOS 应用采用临时代码签名，未经 Apple 公证；Windows 应用未作商业代码签名。首次打开时系统可能提示来源确认，请遵循所在机构的安全政策。自动结果仍需研究者复核，内部验证不能替代独立外部验证。

## English

This release improves configuration round-tripping, result provenance, figures and reproducible public examples, with reorganized documentation in three languages.

- **Configuration and interface:** preserve JSON numeric parameter types; reject ambiguous fixed-parameter combinations across multiple models; show configuration-save errors on the originating page. Confusion matrices support many classes, and figures preserve fold uncertainty and class labels.
- **Result records:** retain optimizer and estimator warnings from successful runs; record prediction class mappings and provenance; bind input hashes, row identities and numerical runtime information to actual data snapshots. Reports disclose constant-target R² conventions, and category counts use observed values.
- **Public examples:** importable CSVs, configurations, three-language instructions and environment-specific comparisons for DSA activity classification and California Housing regression. Frozen California data retain their original bytes on Windows checkout. Each case documents its own scope and recorded environment.
- **Documentation:** separate, concise English, Chinese and French entry pages lead to complete GUI walkthroughs and researcher references in the matching language.
- **Automated release checks:** core and GUI tests on three operating systems, Python distribution builds and wheel smoke tests; native Mac/Windows application builds with classification/regression training and prediction, permutation-importance, single-sample SHAP and fitted-coefficient smoke tests; archive integrity, executable architecture, version, dependency lock, clean source provenance and SHA-256 verification.

**Downloads:** `PsyML-Toolkit-0.3.1-macOS-arm64.zip` for Apple Silicon Mac; `PsyML-Toolkit-0.3.1-Windows-x64.zip` for Windows x64. Extract the complete archive and open the application; keep the Windows `core` folder next to the executable. Both include their runtime. The Release attaches only these two application ZIPs; GitHub supplies automatic source downloads.

The macOS app is ad-hoc signed and is not Apple-notarized; the Windows app has no commercial code signature. Your OS may require first-launch confirmation; follow your institution's security policy. Researchers must review generated results, and internal validation does not replace independent external validation.

## Français

Cette version améliore la conservation des configurations, la traçabilité des résultats, les figures et les exemples publics reproductibles, avec une documentation réorganisée en trois langues.

- **Configuration et interface :** conservation des types numériques JSON ; rejet des paramètres fixes ambigus pour plusieurs modèles ; erreurs de sauvegarde affichées sur la page d'origine. Les matrices de confusion prennent en charge de nombreuses classes ; les figures conservent l'incertitude entre plis et les étiquettes des classes.
- **Résultats :** conservation des avertissements des estimateurs et des optimiseurs ; correspondance des classes et provenance dans le manifeste de prédiction ; empreintes des données, identifiants de lignes et environnement numérique liés aux données effectivement lues. Les rapports explicitent le R² pour une cible constante ; le comptage des catégories utilise les valeurs observées.
- **Exemples publics :** CSV et configurations importables, instructions trilingues et comparaisons documentées par environnement pour DSA et California Housing. Les octets des données California figées sont préservés lors de l'extraction Git sous Windows. Chaque dossier précise la portée de sa validation.
- **Documentation :** trois README courts, en anglais, chinois et français, donnent accès au parcours GUI complet et aux références pour chercheurs dans la langue choisie.
- **Vérifications automatiques :** tests du noyau et de l'interface sur trois systèmes, distributions Python et test du wheel ; applications natives Mac/Windows avec tests de classification/régression, prédiction, importance par permutation, SHAP individuel et coefficients ajustés ; intégrité des archives, architecture des exécutables, version, dépendances verrouillées, provenance du code et SHA-256.

**Téléchargements :** `PsyML-Toolkit-0.3.1-macOS-arm64.zip` pour Mac Apple Silicon ; `PsyML-Toolkit-0.3.1-Windows-x64.zip` pour Windows x64. Décompressez l'archive entière et ouvrez l'application ; sous Windows, conservez le dossier `core` à côté de l'exécutable. L'environnement est inclus. Seules ces deux archives applicatives sont jointes à la Release ; GitHub fournit les archives du code source.

L'application macOS porte une signature ad hoc, sans notarisation Apple ; l'application Windows ne possède pas de signature commerciale. Le système peut demander une confirmation au premier lancement ; respectez les règles de sécurité de votre établissement. Les résultats nécessitent une vérification humaine ; la validation interne ne remplace pas une validation externe indépendante.
