# PsyML Toolkit

<p align="center">
  <a href="#chinese">中文</a> · <a href="#english">English</a> · <a href="#french">Français</a>
</p>

<a id="chinese"></a>

## 中文

PsyML Toolkit 将本科科研与应用项目中积累的 Python 机器学习脚本，逐步整理为可复现、可维护、能避免常见数据泄漏的科研工具。新的分析仅使用现代化的 `src/psyml/` 核心；`legacy/original/program/` 只作为历史参考保留。

### 当前能力

- 表格回归：Dummy、Linear、Ridge、Lasso、Elastic Net、KNN、SVR、决策树、随机森林、Gradient Boosting 与 MLP。
- 表格分类：Dummy、Logistic Regression、Gaussian Naive Bayes、LDA、QDA、KNN、SVM、决策树、随机森林、Gradient Boosting、MLP 与 Stacking。
- 支持 CSV、TSV、XLSX、XLS、SAV、DTA、SAS7BDAT、XPT 与 Parquet；训练集内预处理、五种验证策略、完整评价指标，以及 CSV/JSON 结果导出。
- 自动生成分析清单、Methods 参考说明、可复现性报告，以及回归预测图或分类混淆矩阵图。
- 提供版本化 JSON 配置/结果/状态接口、数据预览与能力查询；Windows、macOS、Linux 持续集成通过。
- 命令行入口：`psyml` 或 `python -m psyml`。

### 当前状态

Phase 0–12 已完成，当前进入 Phase 13：开发默认中文、支持英文和法文的 Godot 图形界面。Legacy 审查已确认旧脚本存在数据泄漏、可移植性与可复现性风险，不应用于新的分析。

### 文档

- [开发计划](docs/PSYML_TOOLKIT_DEVELOPMENT_PLAN.md)
- [已完成阶段](docs/completed_phases.md)
- [Legacy 资产清单](docs/legacy_inventory.md)
- [Legacy 版本关系](docs/legacy_versions.md)
- [当前状态基线](docs/current_state.md)
- [隐私与知识产权审计](docs/privacy_ip_audit.md)
- [合成数据验证](docs/data_sanitization_verification.md)
- [Phase 8/9 完成记录](docs/phase_8_9_completion.md)
- [Phase 10 完成记录](docs/phase_10_completion.md)
- [Phase 11 完成记录](docs/phase_11_completion.md)
- [Phase 12 完成记录](docs/phase_12_completion.md)
- [Core JSON 接口](docs/core_interface.md)
- [Legacy 代码审查](docs/legacy_code_review.md)

Legacy 目录中的原始数据已经删除。仓库仅保留保持原文件格式与结构的随机合成数据，用于开发与测试；数据隐私复查未发现原始个人数据。正式发布前仍需在 Phase 14 完成许可证与发布审计。

<a id="english"></a>

## English

PsyML Toolkit turns Python machine-learning scripts accumulated during undergraduate research and applied projects into a reproducible, maintainable research toolkit with protection against common data leakage. New analyses use only the modern `src/psyml/` core; `legacy/original/program/` is retained as historical reference.

### Current capabilities

- Tabular regression: Dummy, Linear, Ridge, Lasso, Elastic Net, KNN, SVR, Decision Tree, Random Forest, Gradient Boosting and MLP.
- Tabular classification: Dummy, Logistic Regression, Gaussian Naive Bayes, LDA, QDA, KNN, SVM, Decision Tree, Random Forest, Gradient Boosting, MLP and Stacking.
- CSV, TSV, XLSX, XLS, SAV, DTA, SAS7BDAT, XPT and Parquet loading; training-only preprocessing, five validation strategies, comprehensive metrics, and CSV/JSON result export.
- Automatic analysis manifests, Methods summaries, reproducibility reports, and regression-prediction or classification-confusion figures.
- Versioned JSON configuration/result/event interfaces, private-by-default data preview and capability discovery; CI passes on Windows, macOS and Linux.
- Command-line entry point: `psyml` or `python -m psyml`.

### Status

Phases 0–12 are complete. Phase 13 is now building a Godot graphical interface that defaults to Chinese and also supports English and French. The legacy review found leakage, portability and reproducibility risks, so old scripts must not be used for new analyses.

Original data has been removed from the legacy tree. The repository retains only random synthetic datasets with the original file formats and structures for development and testing; the privacy recheck found no original personal data. License and release auditing remains scheduled for Phase 14.

<a id="french"></a>

## Français

PsyML Toolkit transforme les scripts Python d'apprentissage automatique issus de projets de recherche et d'application de premier cycle en une boîte à outils reproductible et maintenable, protégée contre les fuites de données courantes. Les nouvelles analyses utilisent uniquement le noyau moderne `src/psyml`; `legacy/original/program/` est conservé comme référence historique.

### Fonctionnalités actuelles

- Régression tabulaire : Dummy, régression linéaire, Ridge, Lasso, Elastic Net, KNN, SVR, arbre de décision, forêt aléatoire, Gradient Boosting et MLP.
- Classification tabulaire : Dummy, régression logistique, Gaussian Naive Bayes, LDA, QDA, KNN, SVM, arbre de décision, forêt aléatoire, Gradient Boosting, MLP et Stacking.
- Lecture CSV, TSV, XLSX, XLS, SAV, DTA, SAS7BDAT, XPT et Parquet ; prétraitement ajusté uniquement sur l'ensemble d'entraînement, cinq stratégies de validation, métriques complètes et export CSV/JSON.
- Génération automatique d'un manifeste d'analyse, d'un résumé Methods, d'un rapport de reproductibilité et d'une figure de prédiction ou de matrice de confusion.
- Interfaces JSON versionnées pour la configuration, les résultats et les événements, aperçu privé par défaut et découverte des capacités ; l’intégration continue passe sous Windows, macOS et Linux.
- Point d'entrée en ligne de commande : `psyml` ou `python -m psyml`.

### État du projet

Les phases 0–12 sont terminées. La phase 13 développe maintenant une interface graphique Godot en chinois par défaut, également disponible en anglais et en français. La revue du code historique a identifié des risques de fuite, de portabilité et de reproductibilité ; les anciens scripts ne doivent donc pas servir aux nouvelles analyses.

Les données originales ont été supprimées de l'arborescence historique. Le dépôt ne conserve que des jeux de données synthétiques aléatoires ayant les mêmes formats et structures pour le développement et les tests ; la nouvelle vérification de confidentialité n'a trouvé aucune donnée personnelle originale. L'audit des licences et de la publication reste prévu pour la phase 14.
