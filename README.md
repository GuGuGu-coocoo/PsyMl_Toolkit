# PsyML Toolkit

<p align="center">
  <a href="#chinese">中文</a> · <a href="#english">English</a> · <a href="#french">Français</a>
</p>

<a id="chinese"></a>

## 中文

PsyML Toolkit 将本科科研与应用项目中积累的 Python 机器学习脚本，逐步整理为可复现、可维护、能避免常见数据泄漏的科研工具。新的分析仅使用现代化的 `src/psyml/` 核心；`legacy/original/program/` 只作为历史参考保留。

### 当前能力

- 表格回归：KNN、Lasso、MLP、随机森林与 SVR。
- 表格分类：KNN、随机森林、SVM、MLP、决策树与 Stacking。
- 支持 CSV、XLSX、XLS 读取，训练集内预处理，可选分组切分，留出集评价，以及 CSV/JSON 结果导出。
- 命令行入口：`psyml` 或 `python -m psyml`。

### 当前状态

Phase 0–9 已完成。下一阶段是补齐基础模型和常用科研数据格式，之后生成可复现性报告并开发 Godot GUI。Legacy 审查已确认旧脚本存在数据泄漏、可移植性与可复现性风险，不应用于新的分析。

### 文档

- [开发计划](docs/PSYML_TOOLKIT_DEVELOPMENT_PLAN.md)
- [已完成阶段](docs/completed_phases.md)
- [Legacy 资产清单](docs/legacy_inventory.md)
- [Legacy 版本关系](docs/legacy_versions.md)
- [当前状态基线](docs/current_state.md)
- [隐私与知识产权审计](docs/privacy_ip_audit.md)
- [合成数据验证](docs/data_sanitization_verification.md)
- [Phase 8/9 完成记录](docs/phase_8_9_completion.md)
- [Legacy 代码审查](docs/legacy_code_review.md)

Legacy 目录中的原始数据已经删除。仓库仅保留保持原文件格式与结构的随机合成数据，用于后续开发与测试。在数据归属和公开权限完成独立核验前，仓库应保持私有。

<a id="english"></a>

## English

PsyML Toolkit turns Python machine-learning scripts accumulated during undergraduate research and applied projects into a reproducible, maintainable research toolkit with protection against common data leakage. New analyses use only the modern `src/psyml/` core; `legacy/original/program/` is retained as historical reference.

### Current capabilities

- Tabular regression: KNN, Lasso, MLP, Random Forest and SVR.
- Tabular classification: KNN, Random Forest, SVM, MLP, Decision Tree and Stacking.
- CSV, XLSX and XLS loading, training-only preprocessing, optional group-aware splitting, held-out evaluation, and CSV/JSON result export.
- Command-line entry point: `psyml` or `python -m psyml`.

### Status

Phases 0–9 are complete. The next phase adds baseline models and common research data formats, followed by reproducibility reporting and the Godot GUI. The legacy review found leakage, portability and reproducibility risks, so old scripts must not be used for new analyses.

Original data has been removed from the legacy tree. The repository retains only random synthetic datasets with the original file formats and structures for future development and testing. It should remain private until data ownership and publication permissions are independently verified.

<a id="french"></a>

## Français

PsyML Toolkit transforme les scripts Python d'apprentissage automatique issus de projets de recherche et d'application de premier cycle en une boîte à outils reproductible et maintenable, protégée contre les fuites de données courantes. Les nouvelles analyses utilisent uniquement le noyau moderne `src/psyml`; `legacy/original/program/` est conservé comme référence historique.

### Fonctionnalités actuelles

- Régression tabulaire : KNN, Lasso, MLP, forêt aléatoire et SVR.
- Classification tabulaire : KNN, forêt aléatoire, SVM, MLP, arbre de décision et Stacking.
- Lecture CSV, XLSX et XLS, prétraitement ajusté uniquement sur l'ensemble d'entraînement, séparation optionnelle par groupes, évaluation sur jeu de test et export CSV/JSON.
- Point d'entrée en ligne de commande : `psyml` ou `python -m psyml`.

### État du projet

Les phases 0–9 sont terminées. La prochaine phase ajoute des modèles de référence et des formats de données courants en recherche, avant les rapports de reproductibilité et l'interface Godot. La revue du code historique a identifié des risques de fuite, de portabilité et de reproductibilité; les anciens scripts ne doivent donc pas servir aux nouvelles analyses.

Les données originales ont été supprimées de l'arborescence historique. Le dépôt ne conserve que des jeux de données synthétiques aléatoires ayant les mêmes formats et structures, destinés au développement et aux tests futurs. Il doit rester privé jusqu'à la vérification indépendante des droits sur les données et des autorisations de publication.
