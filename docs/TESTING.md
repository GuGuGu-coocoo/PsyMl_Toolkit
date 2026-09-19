# 开发者测试 / Developer testing / Tests de développement

[中文开发者指南](DEVELOPMENT_ZH.md) · [Developer guide](DEVELOPMENT_EN.md) · [Guide de développement](DEVELOPMENT_FR.md)

本文是维护代码时使用的回归检查清单，不是研究者使用 GUI 的前置步骤。
Developer regression checklist; not a prerequisite for using the GUI.
Liste de contrôles de régression pour le développement ; non requise pour utiliser l’interface.

## 中文

先按开发者指南安装依赖，在项目根目录运行。测试全部使用合成数据；不要替换为参与者数据。

- `tests/`：Python 核心自动测试，位于根目录下一层。
- `gui/tests/`：GUI 与核心桥接、完整流程、滚动、多语言及独立验证测试。
- `examples/quickstart/`：用户试用的分类、回归配置，48 行训练数据与各 10 行预测数据。
- `examples/synthetic/`：旧开发夹具与格式矩阵；`two_groups.csv` 用于边界检查。
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
godot --headless --path gui --script res://tests/test_prediction.gd
godot --headless --path gui --script res://tests/test_permutation.gd
godot --headless --path gui --script res://tests/test_data_check.gd
godot --headless --path gui --script res://tests/test_interpretation_results.gd
godot --headless --path gui --script res://tests/test_explanation.gd
```

单样本 SHAP 解释的可选依赖单独安装：`uv sync --extra explain`（或 `uv pip install -e ".[explain]"`）。未安装时 `tests/test_explanation.py`、`tests/test_explanation_cli.py` 与 `gui/tests/test_explanation.gd` 会跳过或明确报缺依赖；普通预测始终可用。首次运行会触发 numba JIT 与 matplotlib 字体缓存，可能较慢；把 `NUMBA_CACHE_DIR`、`MPLCONFIGDIR`、`PSYML_TEST_TMP` 指向项目 `tmp/phase-C-worker/` 下。自动检查覆盖累计瀑布分段（base→output、TopN+余项）、绘图端点使用与核心一致的 atol/rtol、GUI 产物查看/导出与跨切换保留、计算中上下文阻止、取消后立即重启、分片 JSON 与大 stderr；导出仅写新建/空目录，目标非空时新建唯一子目录且不改动已有同名 CSV/模型/背景，同源目录、缺产物与复制失败都报错且不留成功标记；CLI `explain` 拒绝非空输出目录与 `--overwrite`。真实窗口外观与多变量 CJK 图仍需人工看图，自动通过不替代。

人工快速检查：打开分类样例，目标选 `target`、分组选 `participant`，预测变量仅 `score`、`category`，模型选 Decision Tree 和 Dummy，分组 K 折、外层 3、内层 2；选择不指定主要验证，并加选留出法。运行后应先显示验证选择提示，切换后分别显示完整结果。切换三种语言、检查结果与配置是否保持；在研究设计和结果摘要文字处测试滚轮/触控板，在小表格中检查独立滚动；再运行回归配置并检查回归指标与图形。报错、终止与重试也应分别复测。

自动测试通过不等于真实研究设计已验证。少于两个测试样本的 R² 边界测试会有预期警告。CI 在 Windows、macOS、Linux 上运行；查看对应提交的 CI 状态，不把本地测试等同于其他平台已通过。

## English

Install as described in the developer guide and run the commands above from the project root. `tests/` contains core tests, `gui/tests/` GUI tests, and `examples/synthetic/` adjacent CSV/JSON pairs. Public datasets are optional. Tests use synthetic data only. Run these commands in a source checkout, not a standalone app archive. The privacy audit additionally requires `legacy/`; skip it only when that directory is absent from the source copy.

Set `PSYML_PYTHON` to the installed environment: `.venv/bin/python` on macOS/Linux, `.venv/Scripts/python.exe` on Windows. The platform-specific commands above configure it. Godot 4.7.2 is required for GUI checks.

Install the optional single-sample explanation dependency separately with `uv sync --extra explain` (or `uv pip install -e ".[explain]"`). Without it, `tests/test_explanation.py`, `tests/test_explanation_cli.py` and `gui/tests/test_explanation.gd` skip or report the missing dependency, and ordinary prediction keeps working. The first explanation triggers numba JIT and the matplotlib font cache and can be slow; point `NUMBA_CACHE_DIR`, `MPLCONFIGDIR` and `PSYML_TEST_TMP` into `tmp/phase-C-worker/`. Automated checks cover the cumulative waterfall segments (base→output, top N + remainder), waterfall endpoints using the same atol/rtol as the core, GUI artifact view/export and persistence across changes, blocked context changes during computation, immediate cancel+restart, and chunked JSON plus large stderr. Export writes only to a new/empty folder, falls back to a unique new subdirectory without changing an existing same-named CSV/model/background, and reports an error with no success marker for the same-source folder, missing artifacts or copy failure; the CLI `explain` rejects a non-empty output directory and `--overwrite`. Real-window appearance and many-predictor CJK figures still need human inspection, and passing headless tests does not replace it.

For manual review, load classification data; use target `target`, group `participant`, predictors `score` and `category`, Decision Tree and Dummy, group K-fold with 3 outer/2 inner folds. Add holdout and select no primary validation. Results should begin with a neutral selector; inspect each validation, switch all UI languages without losing choices, check page versus table scrolling, then run regression. Also check error copying, cancellation and retry. Tiny-sample R² warnings are expected in boundary tests. Automated success is not scientific acceptance. Check the commit's CI results separately for each OS.

## Français

Installer selon le guide de développement et exécuter les commandes ci-dessus à la racine. `tests/` contient les tests du noyau, `gui/tests/` ceux de l’interface, et `examples/synthetic/` les paires CSV/JSON voisines. Les données publiques sont facultatives. N’utiliser que des données synthétiques pour les tests. Exécuter ces commandes dans les sources, pas dans une archive d’application autonome. L’audit exige aussi `legacy/` ; ne l’ignorer que si ce dossier est absent de la copie des sources.

Définir `PSYML_PYTHON` avec l’environnement installé : `.venv/bin/python` sous macOS/Linux, `.venv/Scripts/python.exe` sous Windows. Les commandes propres à chaque système sont données plus haut. Les tests GUI nécessitent Godot 4.7.2.

Installer séparément la dépendance facultative d’explication : `uv sync --extra explain` (ou `uv pip install -e ".[explain]"`). Sans elle, `tests/test_explanation.py`, `tests/test_explanation_cli.py` et `gui/tests/test_explanation.gd` sont ignorés ou signalent la dépendance manquante, et la prédiction ordinaire reste disponible. Le premier calcul déclenche la compilation JIT de numba et le cache de polices matplotlib ; diriger `NUMBA_CACHE_DIR`, `MPLCONFIGDIR` et `PSYML_TEST_TMP` vers `tmp/phase-C-worker/`. Les contrôles automatiques couvrent les segments de la cascade cumulative (base→sortie, top N + reste), les extrémités de la cascade avec le même atol/rtol que le noyau, la visualisation/export et la persistance des artefacts, le blocage des changements de contexte pendant le calcul, l'annulation suivie d'un redémarrage immédiat, ainsi que le JSON fragmenté et un stderr volumineux. L'export n'écrit que dans un dossier nouveau/vide, crée un sous-dossier unique sans modifier un CSV/modèle/référence de même nom déjà présent, et signale une erreur sans marque de succès pour le dossier source, un artefact manquant ou un échec de copie ; la CLI `explain` refuse un dossier de sortie non vide et `--overwrite`. L'aspect en fenêtre réelle et les figures CJK à nombreuses variables demandent encore une inspection humaine, qu'un succès headless ne remplace pas.

Vérification manuelle : classification, cible `target`, groupe `participant`, prédicteurs `score` et `category`, Decision Tree et Dummy, K plis par groupes avec 3 plis externes/2 internes. Ajouter holdout sans validation principale. Les résultats doivent commencer par un sélecteur neutre ; vérifier chaque validation, les trois langues sans perte des choix et le défilement des pages/tableaux, puis lancer la régression. Vérifier aussi copie des erreurs, arrêt et reprise. Les avertissements R² sur de minuscules tests sont attendus. La réussite automatique ne valide pas le plan scientifique ; consulter séparément le CI du commit pour chaque système.

## Configuration import / 配置导入 / Importation de configuration

中文：仅测试配置导入时，打开应用，在第 1 页点击“导入配置…”，选择附带的 `examples/quickstart/classification_config.json`。确认目标为 `target`、分组为 `participant`、预测变量为 `score` 和 `category`，模型为 Decision Tree，验证为 Group K Fold。切换中英法语言，确认设置保留。点击“保存配置…”，重新导入所存文件，然后运行一次。再导入回归配置，确认任务和模型切换为回归与 Ridge。将配置复制到另一目录、临时改名原数据，再导入，确认出现重新选择数据的窗口；取消应保留当前设置。测试后恢复数据文件名。GUI 始终使用本机所选输出文件夹的新子目录。

English: Open the app and click **Import configuration…** on page 1. Choose the bundled `examples/quickstart/classification_config.json`. Verify target `target`, group `participant`, predictors `score` and `category`, Decision Tree and Group K Fold. Switch among all three languages and verify settings persist. Save the configuration, reimport it and run once. Import the regression example and check Regression and Ridge. Copy a configuration elsewhere, temporarily rename its data, and import: a data-relink dialog should appear. Cancelling must preserve the current settings. Restore the data filename afterward. GUI output always goes to a fresh subfolder of the selected local directory.

Français : ouvrez l’application et cliquez sur **Importer une configuration…** à la page 1. Choisissez `examples/quickstart/classification_config.json`. Vérifiez cible `target`, groupe `participant`, prédicteurs `score` et `category`, Decision Tree et Group K Fold. Changez de langue et vérifiez la conservation des réglages. Enregistrez, réimportez et lancez une analyse. Importez l’exemple de régression et vérifiez Régression et Ridge. Copiez le JSON ailleurs, renommez temporairement ses données puis importez : une boîte de dialogue doit permettre de les réassocier. Annuler conserve les réglages actuels. Rétablissez ensuite le nom du fichier. Chaque exécution utilise un nouveau sous-dossier local.

Developer checks: `tests/test_gui_config.py` and `gui/tests/test_config_import.gd`. During native builds, `tools/build_native.py` invokes `gui/scripts/native_smoke.gd` through the exported app’s `--psyml-smoke-test` argument, with development Python variables removed. It trains classification and regression, saves and reloads both models, predicts 10 new quickstart rows per task and exports XLSX through the bundled core. `.github/workflows/native-test-build.yml` retains Windows test artifacts and never publishes a release. Build only when packaging is intended; see the developer guide for triggers.

## 原生窗口与可读性 / Native dialogs and readability / Dialogues natifs et lisibilité

中文：实际打开数据、配置导入、配置保存和目录选择，确认使用系统原生窗口；配置导入需保留 JSON 筛选，取消不改变当前设置。悬停、聚焦、选中数值与下拉选项，检查深色文字、浅色背景及禁用状态。分别切换中英法检查，系统窗口自身语言由操作系统决定。无窗口自动测试不能代替这项检查。

English: Open data, configuration import/save and folder selection and verify OS-native dialogs, the JSON import filter and cancellation without state changes. Inspect hover, focus, selected numbers/options and disabled contrast in all three UI languages. OS dialogs follow the system’s language. Headless tests cannot replace this visual check.

Français : vérifiez les dialogues natifs pour les données, l’importation/sauvegarde JSON et les dossiers, le filtre JSON et l’annulation sans changement des réglages. Inspectez survol, focus, nombres/options sélectionnés et contraste des contrôles désactivés dans les trois langues. Les dialogues système suivent la langue du système. Les tests sans fenêtre ne remplacent pas cette vérification.

## 小数据参数组合矩阵

[合成数据与覆盖说明](../examples/synthetic/matrix/README.md)提供 27 份、每份 48 行的九格式测试数据及可直接导入 GUI 的配置。快速运行所有模型、内置快速参数网格、预处理、验证方法、嵌套调参和失败路径：

```bash
uv run pytest tests/test_parameter_matrix.py -q --durations=10
```

它随默认核心测试自动运行，无需额外服务或网络。可添加 `--junitxml=output/parameter-matrix.xml` 保存逐项结果。不要把这组兼容性检查当作模型效能验证，也不要为避免失败而静默改变研究者的参数；对数据与模型不兼容的组合，验证明确报错或保留失败候选记录。

## 0.2.0 模型保存与预测 / Model saving and prediction / Enregistrement et prédiction

中文：从 `examples/quickstart/` 导入分类配置，保留“保存最佳模型”，确认主要验证为分组 K 折。训练后加载 `model/best_decision_tree.joblib` 与 `classification_predict.csv`，应保留 sample_id/category/score 并生成 10 行分类结果和两列概率。回归配置使用 `best_ridge.joblib` 与 `regression_predict.csv`，应生成 10 行 predicted_value 且没有概率列。检查另存为、切换模型/数据时旧输出清空、缺列与数值错误阻止预测、取消信任后无法运行。独立验证模式不应产生模型文件。新测试入口无“测试数据”按钮；配置和首次预测数据对话框默认定位 quickstart。

English: Import the quickstart classification configuration, keep saving enabled and verify group K-fold as primary. Load best_decision_tree.joblib and classification_predict.csv; expect 10 rows retaining sample_id/category/score, predicted_class and two probability columns. Repeat regression with best_ridge.joblib and regression_predict.csv: 10 predicted_value rows, no probabilities. Check export, cleared old output after model/data changes, missing-column/numeric failures and disabled prediction after trust is revoked. Independent mode must not save models. There is no Sample data button; configuration and first prediction-data dialogs open quickstart.

Français : importez la configuration quickstart de classification, gardez l’enregistrement et la validation principale par groupes. Chargez best_decision_tree.joblib puis classification_predict.csv : 10 lignes, sample_id/category/score conservés, predicted_class et deux probabilités. Répétez avec best_ridge.joblib et regression_predict.csv : 10 predicted_value, sans probabilités. Vérifiez export, effacement des anciennes sorties, blocage pour colonnes absentes/valeurs invalides et retrait de confiance. Aucun modèle enregistré en mode indépendant. Le bouton Données de test est supprimé ; dialogues de configuration et de première prédiction ouverts sur quickstart.

Focused checks / 专项检查 : `tests/test_quickstart.py`, `tests/test_model_persistence.py`, `tests/test_prediction.py`, `gui/tests/test_prediction.gd`. These supplement visual inspection; they do not validate real-world model performance.

## 置换重要性 / Permutation importance / Importance par permutation

中文：默认关闭。在 GUI 第 1 页启用“置换重要性（解释）”并把重复次数设为 2，选择一个验证运行，确认结果区出现“置换重要性”摘要且 `interpretations/<验证>/` 含 raw/folds/summary CSV、`permutation.json` 与 PNG；图可选中并显示零线。切换三种语言后设置与结果保持。关闭后运行不得生成 `interpretations/`，且结果区清空。切换到另一个验证再切回，不得混用摘要；独立验证模式每个子目录各自解释，根目录无全局排名。取消运行后不得显示成功解释。人工检查时用 `examples/quickstart/classification_permutation_config.json` 或 `regression_permutation_config.json`；用中文长变量名截图核对可读性。自动检查：`tests/test_permutation.py`、`tests/test_permutation_runner.py`、`tests/test_permutation_export.py`、`tests/test_quickstart.py`、`gui/tests/test_permutation.gd`。headless 通过不代替看图。

English: Off by default. On page 1 enable **Export permutation importance** with 2 repeats, pick one validation and run. The results block must show a permutation summary and `interpretations/<validation>/` must contain the raw/folds/summary CSV, `permutation.json` and the PNG; the figure must be selectable and show a zero line. Switch all three languages and confirm settings/results persist. An OFF run must create no `interpretations/` and clear the block. Switch to another validation and back without mixing summaries; independent validations keep separate interpretations and no global ranking. A cancelled run must not show a successful interpretation. For manual review use `examples/quickstart/*_permutation_config.json` and check long/Unicode variable names in a real window. Automated: `tests/test_permutation*.py`, `tests/test_quickstart.py`, `gui/tests/test_permutation.gd`. Headless success does not replace looking at the figures.

Français : désactivé par défaut. À la page 1, activez **Exporter l’importance par permutation** avec 2 répétitions, choisissez une validation et lancez. Le bloc de résultats doit afficher un résumé et `interpretations/<validation>/` doit contenir les CSV brut/par pli/récapitulatif, `permutation.json` et le PNG ; la figure doit être sélectionnable et montrer la ligne zéro. Changez de langue et vérifiez la persistance. Une exécution désactivée ne doit créer aucun `interpretations/` et vider le bloc. Alternez entre validations sans mélanger les résumés ; en mode indépendant, chaque sous-dossier garde son interprétation sans classement global. Une annulation ne doit pas afficher d’interprétation réussie. Pour la revue manuelle, utilisez `examples/quickstart/*_permutation_config.json` et vérifiez les noms longs/Unicode dans une vraie fenêtre. Automatique : `tests/test_permutation*.py`, `tests/test_quickstart.py`, `gui/tests/test_permutation.gd`. Le succès headless ne remplace pas l’examen des figures.

## 数据检查与结果解读 / Data check and result interpretation

中文：读取预览后，分类目标应显示实际类别数、每类数量与占非缺失目标比例，并写明总行数、非缺失分母和缺失数；全缺失目标不除零，未观测类别与 NaN/None 不计为真实类别。疑似编号提示需有依据（列名或接近唯一的整数/文本）且可忽略，切换目标/任务/分组、导入配置、失效路径、语言切换后不残留旧统计；默认预览不得返回取值。结果解读需与同验证同折同指标的已成功 Dummy 比较，正负方向正确，无基线/失败/折集合不同/非有限分数时明确不可比较，单折不谈稳定性，内层候选/外层模型+验证/整种验证失败分层计数，独立验证各自摘要，`result_interpretation.json` 真实存在且被 `result.json` 索引。自动检查：`tests/test_profiling.py`、`tests/test_interpretation.py`、`gui/tests/test_data_check.gd`、`gui/tests/test_interpretation_results.gd`。headless 通过不替代真实窗口视觉检查。

English: After loading a preview, a classification target must show the observed category count, each category count and its share of the non-missing target, with total rows, non-missing denominator and missing count explicit; an all-missing target never divides by zero, and unobserved categories plus NaN/None are not real classes. Identifier hints must be evidence-based (name token or near-unique integer/text) and dismissable, and switching target/task/group, importing a configuration, an invalid path or a language switch must not leave stale statistics; the default preview must return no values. Result interpretation must compare only against a successfully completed dummy on the same validation, folds and metric, get the sign right, state an explicit not-comparable reason for no baseline/failure/fold-set mismatch/non-finite scores, avoid stability claims on a single fold, count inner-candidate/outer-model+validation/whole-validation failures in layers, summarise independent validations separately, and write a real, indexed `result_interpretation.json`. Automated: `tests/test_profiling.py`, `tests/test_interpretation.py`, `gui/tests/test_data_check.gd`, `gui/tests/test_interpretation_results.gd`. Headless success does not replace real-window visual review.

Français : après l’aperçu, une cible de classification doit afficher le nombre de catégories observées, l’effectif de chacune et sa part parmi les valeurs non manquantes, avec total de lignes, dénominateur non manquant et manquants explicites ; une cible entièrement manquante ne divise pas par zéro et les catégories non observées ou NaN/None ne sont pas des classes réelles. Les indices d’identifiant doivent être justifiés (mot-clé du nom ou valeurs entières/texte quasi uniques) et ignorables ; changer cible/tâche/groupe, importer une configuration, un chemin invalide ou changer de langue ne doit pas laisser de statistiques obsolètes ; l’aperçu par défaut ne renvoie aucune valeur. L’interprétation ne doit comparer qu’à un dummy réussi sur la même validation, les mêmes plis et la même métrique, avec le bon sens, une raison explicite de non-comparabilité (absence/échec/ensembles de plis différents/scores non finis), aucune affirmation de stabilité sur un pli unique, des échecs comptés par couches (candidats internes / modèle+validation externe / validation entière), des validations indépendantes résumées séparément, et un `result_interpretation.json` réel et indexé. Automatique : `tests/test_profiling.py`, `tests/test_interpretation.py`, `gui/tests/test_data_check.gd`, `gui/tests/test_interpretation_results.gd`. Le succès headless ne remplace pas la revue visuelle en fenêtre réelle.
