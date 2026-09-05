# 开发者测试 / Developer testing / Tests de développement

[中文开发者指南](DEVELOPMENT_ZH.md) · [Developer guide](DEVELOPMENT_EN.md) · [Guide de développement](DEVELOPMENT_FR.md)

本文是维护代码时使用的回归检查清单，不是研究者使用 GUI 的前置步骤。
Developer regression checklist; not a prerequisite for using the GUI.
Liste de contrôles de régression pour le développement ; non requise pour utiliser l’interface.

## 中文

先按开发者指南安装依赖，在项目根目录运行。测试全部使用合成数据；不要替换为参与者数据。

- `tests/`：Python 核心自动测试，位于根目录下一层。
- `gui/tests/`：GUI 与核心桥接、完整流程、滚动、多语言及独立验证测试。
- `examples/synthetic/`：分类、回归 CSV 与相邻 JSON 配置；`two_groups.csv` 用于边界检查。
- `examples/public/`：可选公开数据示例，需要额外下载；默认快速测试不需要。

这些命令在完整源码检出中执行，独立应用包不包含开发测试环境。隐私审计还需要 `legacy/` 中的历史夹具；只有源码副本明确不含该目录时，才跳过 `tools/audit_repository.py`。

```bash
uv sync --locked --group dev
uv run ruff check src tests tools
uv run pytest -q
uv run python tools/audit_repository.py
uv build
```

GUI 自动检查需要 Godot 4.7.2。macOS/Linux 先运行 `export PSYML_PYTHON="$PWD/.venv/bin/python"`；Windows PowerShell 先运行 `$env:PSYML_PYTHON = (Resolve-Path .venv/Scripts/python.exe).Path`，再运行：

```bash
godot --headless --editor --path gui --quit
godot --headless --path gui --script res://tests/test_bridge.gd
godot --headless --path gui --script res://tests/test_ui_flow.gd
godot --headless --path gui --script res://tests/test_feedback.gd
godot --headless --path gui --script res://tests/test_parameter_context.gd
godot --headless --path gui --script res://tests/test_independent_results.gd
godot --headless --path gui --script res://tests/test_config_import.gd
```

人工快速检查：打开分类样例，目标选 `target`、分组选 `participant`，预测变量仅 `score`、`category`，模型选 Decision Tree 和 Dummy，分组 K 折、外层 3、内层 2；选择不指定主要验证，并加选留出法。运行后应先显示验证选择提示，切换后分别显示完整结果。切换三种语言、检查结果与配置是否保持；在研究设计和结果摘要文字处测试滚轮/触控板，在小表格中检查独立滚动；再运行回归配置并检查回归指标与图形。报错、终止与重试也应分别复测。

自动测试通过不等于真实研究设计已验证。少于两个测试样本的 R² 边界测试会有预期警告。CI 在 Windows、macOS、Linux 上运行；查看对应提交的 CI 状态，不把本地测试等同于其他平台已通过。

## English

Install as described in the developer guide and run the commands above from the project root. `tests/` contains core tests, `gui/tests/` GUI tests, and `examples/synthetic/` adjacent CSV/JSON pairs. Public datasets are optional. Tests use synthetic data only. Run these commands in a source checkout, not a standalone app archive. The privacy audit additionally requires `legacy/`; skip it only when that directory is absent from the source copy.

Set `PSYML_PYTHON` to the installed environment: `.venv/bin/python` on macOS/Linux, `.venv/Scripts/python.exe` on Windows. The platform-specific commands above configure it. Godot 4.7.2 is required for GUI checks.

For manual review, load classification data; use target `target`, group `participant`, predictors `score` and `category`, Decision Tree and Dummy, group K-fold with 3 outer/2 inner folds. Add holdout and select no primary validation. Results should begin with a neutral selector; inspect each validation, switch all UI languages without losing choices, check page versus table scrolling, then run regression. Also check error copying, cancellation and retry. Tiny-sample R² warnings are expected in boundary tests. Automated success is not scientific acceptance. Check the commit's CI results separately for each OS.

## Français

Installer selon le guide de développement et exécuter les commandes ci-dessus à la racine. `tests/` contient les tests du noyau, `gui/tests/` ceux de l’interface, et `examples/synthetic/` les paires CSV/JSON voisines. Les données publiques sont facultatives. N’utiliser que des données synthétiques pour les tests. Exécuter ces commandes dans les sources, pas dans une archive d’application autonome. L’audit exige aussi `legacy/` ; ne l’ignorer que si ce dossier est absent de la copie des sources.

Définir `PSYML_PYTHON` avec l’environnement installé : `.venv/bin/python` sous macOS/Linux, `.venv/Scripts/python.exe` sous Windows. Les commandes propres à chaque système sont données plus haut. Les tests GUI nécessitent Godot 4.7.2.

Vérification manuelle : classification, cible `target`, groupe `participant`, prédicteurs `score` et `category`, Decision Tree et Dummy, K plis par groupes avec 3 plis externes/2 internes. Ajouter holdout sans validation principale. Les résultats doivent commencer par un sélecteur neutre ; vérifier chaque validation, les trois langues sans perte des choix et le défilement des pages/tableaux, puis lancer la régression. Vérifier aussi copie des erreurs, arrêt et reprise. Les avertissements R² sur de minuscules tests sont attendus. La réussite automatique ne valide pas le plan scientifique ; consulter séparément le CI du commit pour chaque système.

## Configuration import / 配置导入 / Importation de configuration

中文：仅测试配置导入时，打开应用，在第 1 页点击“导入配置…”，选择附带的 `examples/synthetic/classification_config.json`。确认目标为 `target`、分组为 `participant`、预测变量为 `score` 和 `category`，模型为 Decision Tree，验证为 Group K Fold。切换中英法语言，确认设置保留。点击“保存配置…”，重新导入所存文件，然后运行一次。再导入回归配置，确认任务和模型切换为回归与 Ridge。将配置复制到另一目录、临时改名原数据，再导入，确认出现重新选择数据的窗口；取消应保留当前设置。测试后恢复数据文件名。GUI 始终使用本机所选输出文件夹的新子目录。

English: Open the app and click **Import configuration…** on page 1. Choose the bundled `examples/synthetic/classification_config.json`. Verify target `target`, group `participant`, predictors `score` and `category`, Decision Tree and Group K Fold. Switch among all three languages and verify settings persist. Save the configuration, reimport it and run once. Import the regression example and check Regression and Ridge. Copy a configuration elsewhere, temporarily rename its data, and import: a data-relink dialog should appear. Cancelling must preserve the current settings. Restore the data filename afterward. GUI output always goes to a fresh subfolder of the selected local directory.

Français : ouvrez l’application et cliquez sur **Importer une configuration…** à la page 1. Choisissez `examples/synthetic/classification_config.json`. Vérifiez cible `target`, groupe `participant`, prédicteurs `score` et `category`, Decision Tree et Group K Fold. Changez de langue et vérifiez la conservation des réglages. Enregistrez, réimportez et lancez une analyse. Importez l’exemple de régression et vérifiez Régression et Ridge. Copiez le JSON ailleurs, renommez temporairement ses données puis importez : une boîte de dialogue doit permettre de les réassocier. Annuler conserve les réglages actuels. Rétablissez ensuite le nom du fichier. Chaque exécution utilise un nouveau sous-dossier local.

Developer checks: `tests/test_gui_config.py` and `gui/tests/test_config_import.gd`. During native builds, `tools/build_native.py` invokes `gui/scripts/native_smoke.gd` through the exported app’s `--psyml-smoke-test` argument, with development Python variables removed. It runs classification and regression through the bundled core. `.github/workflows/native-test-build.yml` retains Windows test artifacts and never publishes a release. Build only when packaging is intended; see the developer guide for triggers.

## 原生窗口与可读性 / Native dialogs and readability / Dialogues natifs et lisibilité

中文：实际打开数据、配置导入、配置保存和目录选择，确认使用系统原生窗口；配置导入需保留 JSON 筛选，取消不改变当前设置。悬停、聚焦、选中数值与下拉选项，检查深色文字、浅色背景及禁用状态。分别切换中英法检查，系统窗口自身语言由操作系统决定。无窗口自动测试不能代替这项检查。

English: Open data, configuration import/save and folder selection and verify OS-native dialogs, the JSON import filter and cancellation without state changes. Inspect hover, focus, selected numbers/options and disabled contrast in all three UI languages. OS dialogs follow the system’s language. Headless tests cannot replace this visual check.

Français : vérifiez les dialogues natifs pour les données, l’importation/sauvegarde JSON et les dossiers, le filtre JSON et l’annulation sans changement des réglages. Inspectez survol, focus, nombres/options sélectionnés et contraste des contrôles désactivés dans les trois langues. Les dialogues système suivent la langue du système. Les tests sans fenêtre ne remplacent pas cette vérification.

## 小数据参数组合矩阵

[合成数据与覆盖说明](../examples/synthetic/matrix/README.md)提供 27 份、每份 48 行的九格式测试数据及可直接导入 GUI 的配置。快速运行所有模型、推荐参数网格、预处理、验证方法、嵌套调参和失败路径：

```bash
uv run pytest tests/test_parameter_matrix.py -q --durations=10
```

它随默认核心测试自动运行，无需额外服务或网络。可添加 `--junitxml=output/parameter-matrix.xml` 保存逐项结果。不要把这组兼容性检查当作模型效能验证，也不要为避免失败而静默改变研究者的参数；对数据与模型不兼容的组合，验证明确报错或保留失败候选记录。
