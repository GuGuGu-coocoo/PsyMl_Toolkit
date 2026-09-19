# 用户测试入口 / GUI quick start / Test de l’interface

## 中文

这是用户试用所需的完整资料夹。请整体保留或复制这个资料夹，不要只复制 JSON。全部数据为合成数据，仅用于检查软件流程。

| 文件 | 用途 | 在哪里使用 |
| --- | --- | --- |
| [classification_config.json](classification_config.json) | 分类测试配置，自动关联训练数据；开启保存模型 | 第 1 页“导入配置…” |
| [classification_train.csv](classification_train.csv) | 48 行分类训练数据，含目标 target | 配置导入时自动读取，无需另外打开 |
| [classification_predict.csv](classification_predict.csv) | 10 行新样本，无目标列 | 第 4 页“加载预测数据…” |
| [regression_config.json](regression_config.json) | 回归测试配置，自动关联训练数据；开启保存模型 | 第 1 页“导入配置…” |
| [regression_train.csv](regression_train.csv) | 48 行回归训练数据，含目标 target | 配置导入时自动读取，无需另外打开 |
| [regression_predict.csv](regression_predict.csv) | 10 行新样本，无目标列 | 第 4 页“加载预测数据…” |

先打开含“4 模型与预测”的新版 GUI；macOS 源码版可在项目根目录双击 `Launch PsyML.command`。独立应用请使用 v0.2.0 或更新版本。

建议先测分类：

1. 第 1 页点击“导入配置…”，选择 `classification_config.json`。对话框默认定位到此资料夹。训练数据和设置一起恢复，预测变量为 score/category；不要导入 `_predict.csv` 来训练。
2. 保持“保存最佳模型”勾选（第 1 页右侧向下滚动，随机种子下方）。到第 2 页选择结果保存位置并运行。
3. 第 3 页点击“打开完整结果文件夹”，在本次运行的 `model/` 中找到 `best_decision_tree.joblib`。保留旁边的 `model_metadata.json`。
4. 第 4 页确认模型来源可信，点击“加载模型…”选择上述模型；点击“加载预测数据…”选择 `classification_predict.csv`。首次打开该数据对话框也默认定位到此资料夹。
5. 自动检查通过后点击“运行预测”，应得到 10 行结果，保留 sample_id/category/score，并追加 predicted_class、probability_0、probability_1。点击“预测结果另存为…”即可保存。
6. 再导入 `regression_config.json`，重复训练；加载其 `best_ridge.joblib` 和 `regression_predict.csv`。应得到 10 行结果，追加 predicted_value，不生成概率列。

预测文件的变量顺序与训练不同，并额外保留 sample_id，用于检查自动选列和原始列保留。两组新样本都只需要 score/category，不需要目标或分组列。预测数值随配置和依赖版本可能不同；这里只检查流程和输出结构，不验证真实模型效果。

若测试错误提示，请另存预测 CSV 的副本，删除 score 列或把其值改成文字后加载；预期会阻止预测。不要改动原始测试文件。旧的 `examples/synthetic/` 保留给现有开发测试；用户试用从本资料夹开始。

### 置换重要性测试（可选）

改导入 `classification_permutation_config.json` 或 `regression_permutation_config.json` 可检查新增的置换重要性（原有两个配置仍默认关闭，行为不变）。配置已开启“导出置换重要性”且重复次数为 10。在第 2 页运行后，第 3 页“置换重要性”区域应显示所选验证的汇总表与状态，并可点击“打开解释产物文件夹”查看 `interpretations/<验证>/`：其中含逐次 `permutation_raw.csv`、逐折 `permutation_folds.csv`、汇总 `permutation_summary.csv`、`permutation.json` 和有符号排序图 `permutation_importance.png`。数值有符号：MAE/RMSE 表示误差升高，其他指标表示性能下降；保留负值，不归一化为百分比，不是因果关系或置信区间，相关变量会共享或掩盖贡献。若选择多个验证，可用结果页的验证选择器切换查看各自的解释。

### 单样本 SHAP 解释测试（可选，需 explain 依赖）

按上文训练分类或回归并加载其保存模型与 `_predict.csv`。在第 4 页“解释单个样本（近似 SHAP）”区，把“加载背景参考数据…”也选择同一个 `_predict.csv`，样本行号填 1，背景行数 10、排列轮数 2；分类再选择要解释的类别。点击“解释这个样本”，首次可能较慢，可随时取消。完成后应看到基值、输出、重建误差、按绝对值排序的贡献表，以及从基值逐项累加到输出的**累计瀑布图**（正负方向、原始变量名与值、TopN 与“其余 N 项之和”），并有“打开瀑布图”“打开结果文件夹”“导出解释结果…”控件；“导出解释结果…”只写入新建或空文件夹，不覆盖已有文件（目标非空时新建唯一子目录，当前结果目录不可作为目标）。产物写入 `shap_explanation.json`、`shap_contributions.csv`、`shap_waterfall.png`、`shap_explanation_notes.md`。切换行/类别/设置或离开页面只清除界面，已完成的产物保留在磁盘。贡献是有限排列的近似 SHAP（`base + Σφ = 所选输出`，容差 1e-7/1e-6），不是精确 SHAP、不是因果，也不代表外层测试性能；首版仅支持 logistic/decision tree/random forest（分类）与 linear/ridge/lasso/elastic net/decision tree/random forest（回归），且仅接受带 PsyML 导出元数据的保存模型。未安装 `uv sync --extra explain` 时该区不可用，普通预测不受影响。

## English

Keep or copy this entire folder so each JSON stays beside its training CSV. All data is synthetic and intended only for software testing.

| File | Purpose | Use |
| --- | --- | --- |
| [classification_config.json](classification_config.json) | Classification settings with model saving enabled | Page 1: Import configuration… |
| [classification_train.csv](classification_train.csv) | 48 training rows including target | Loaded automatically by the configuration |
| [classification_predict.csv](classification_predict.csv) | 10 new samples without target | Page 4: Load prediction data… |
| [regression_config.json](regression_config.json) | Regression settings with model saving enabled | Page 1: Import configuration… |
| [regression_train.csv](regression_train.csv) | 48 training rows including target | Loaded automatically by the configuration |
| [regression_predict.csv](regression_predict.csv) | 10 new samples without target | Page 4: Load prediction data… |

Open the updated GUI with page 4, Model & Prediction (on macOS, source users can double-click `Launch PsyML.command` in the project root). Use standalone version v0.2.0 or later.

Import the classification JSON on page 1. Keep **Save best model** enabled, below Random seed in the lower settings area. Choose an output folder and run on page 2. On page 3, open the result folder; keep `model/best_decision_tree.joblib` with `model_metadata.json`. On page 4, trust and load that model, then load `classification_predict.csv`. The configuration and first prediction-data dialogs start in this folder. When automatic checks pass, run and save predictions: expect 10 rows with original sample_id/category/score plus predicted_class and probability_0/probability_1.

Repeat with the regression JSON, its saved `best_ridge.joblib`, and `regression_predict.csv`: 10 rows, with predicted_value and no probability columns. Do not train on the `_predict.csv` files. Their feature order differs from training, and extra sample_id values test column preservation. Predictors require only score/category; no target/group column is needed. Exact predictions may vary with settings and dependency versions; this is not a validation of real-world model quality.

For error testing, save a separate copy of prediction data and remove score or replace numbers with text; prediction should be blocked. Preserve the original files. `examples/synthetic/` remains for existing developer tests; start user testing here.

### Permutation-importance test (optional)

Import `classification_permutation_config.json` or `regression_permutation_config.json` to exercise the new permutation importance (the original two configs stay off by default and are unchanged). Both enable **Export permutation importance** with 10 repeats. After running on page 2, the page-3 **Permutation importance** block shows the selected validation's summary and status; **Open interpretation folder** reveals `interpretations/<validation>/` containing raw `permutation_raw.csv`, per-fold `permutation_folds.csv`, summary `permutation_summary.csv`, `permutation.json` and the signed figure `permutation_importance.png`. Values are signed (error increase for MAE/RMSE, otherwise performance drop), keep negatives, are not normalised percentages, not causal and not confidence intervals; correlated variables share or mask attribution. When several validations are selected, switch between them with the results-page validation selector.

### Single-sample SHAP test (optional, needs the explain extra)

Train classification or regression as above, then load its saved model and `_predict.csv`. In the page-4 **Explain one sample (approximate SHAP)** block, also choose the same `_predict.csv` as the background reference, set sample row 1, background rows 10 and cycles 2, and for classification choose the class. Click **Explain this sample**; the first run may be slow and can be cancelled. You should see base value, output, reconstruction error, contributions sorted by absolute value, and a **cumulative waterfall** stepping from base to output (signed direction, original names/values, top N plus "other N (sum)"), with **Open waterfall image**, **Open results folder** and **Export explanation…** controls. **Export explanation…** writes only to a new or empty folder and never overwrites existing files (a non-empty destination gets a unique new subdirectory, and the current results folder cannot be the destination). Artifacts are written to `shap_explanation.json`, `shap_contributions.csv`, `shap_waterfall.png` and `shap_explanation_notes.md`; changing row/class/settings or leaving the page only clears the display and keeps completed artifacts on disk. Contributions are approximate finite-permutation SHAP (`base + Σφ = selected output`, tolerance 1e-7/1e-6), not exact SHAP, not causal and not outer test performance; the first release covers logistic/decision tree/random forest (classification) and linear/ridge/lasso/elastic net/decision tree/random forest (regression), and only accepts saved models with PsyML export metadata. Without `uv sync --extra explain` the section is unavailable and ordinary prediction still works.

## Français

Conservez ou copiez ce dossier entier pour garder chaque JSON à côté de son CSV d’entraînement. Toutes les données sont synthétiques, destinées uniquement aux tests du logiciel.

| Fichier | Utilité | Utilisation |
| --- | --- | --- |
| [classification_config.json](classification_config.json) | Réglages de classification, modèle enregistré | Page 1 : Importer une configuration… |
| [classification_train.csv](classification_train.csv) | 48 lignes d’entraînement avec target | Chargé automatiquement par le JSON |
| [classification_predict.csv](classification_predict.csv) | 10 nouveaux exemples sans cible | Page 4 : Charger les données à prédire… |
| [regression_config.json](regression_config.json) | Réglages de régression, modèle enregistré | Page 1 : Importer une configuration… |
| [regression_train.csv](regression_train.csv) | 48 lignes d’entraînement avec target | Chargé automatiquement par le JSON |
| [regression_predict.csv](regression_predict.csv) | 10 nouveaux exemples sans cible | Page 4 : Charger les données à prédire… |

Ouvrez la version avec la page 4, Modèle et prédiction (sources macOS : double-cliquez sur `Launch PsyML.command` à la racine). Utilisez une application autonome v0.2.0 ou ultérieure.

Importez le JSON de classification à la page 1. Gardez l’enregistrement du meilleur modèle activé, sous la graine aléatoire en bas des réglages. Choisissez le dossier de sortie et lancez à la page 2. À la page 3, ouvrez les résultats ; gardez `model/best_decision_tree.joblib` avec `model_metadata.json`. À la page 4, confirmez la confiance, chargez ce modèle puis `classification_predict.csv`. Les dialogues de configuration et de première sélection des données à prédire commencent ici. Après vérification automatique, lancez et enregistrez : 10 lignes, colonnes sample_id/category/score conservées, plus predicted_class et probability_0/probability_1.

Recommencez avec le JSON de régression, son `best_ridge.joblib` et `regression_predict.csv` : 10 lignes, predicted_value ajouté, sans probabilités. Ne pas entraîner sur les fichiers `_predict.csv`. Leur ordre de variables diffère et sample_id teste la conservation des colonnes supplémentaires. Seuls score/category sont requis, sans cible ni groupe. Les valeurs prédites peuvent varier selon les réglages et versions ; ceci ne valide pas les performances réelles.

Pour tester les erreurs, créez une copie des données à prédire, supprimez score ou remplacez les nombres par du texte : la prédiction doit être bloquée. Conservez les originaux. `examples/synthetic/` reste destiné aux tests de développement ; commencez les essais utilisateur ici.

### Test de l’importance par permutation (facultatif)

Importez `classification_permutation_config.json` ou `regression_permutation_config.json` pour essayer la nouvelle importance par permutation (les deux configurations d’origine restent désactivées par défaut et inchangées). Elles activent **Exporter l’importance par permutation** avec 10 répétitions. Après l’exécution (page 2), le bloc **Importance par permutation** (page 3) affiche le résumé et l’état de la validation choisie ; **Ouvrir le dossier d’interprétation** montre `interpretations/<validation>/` avec `permutation_raw.csv` (brut), `permutation_folds.csv` (par pli), `permutation_summary.csv` (récapitulatif), `permutation.json` et la figure signée `permutation_importance.png`. Les valeurs sont signées (augmentation de l’erreur pour MAE/RMSE, sinon baisse de performance), conservent les négatifs, ne sont ni des pourcentages normalisés, ni causales, ni des intervalles de confiance ; les variables corrélées partagent ou masquent l’attribution. Avec plusieurs validations, utilisez le sélecteur de la page des résultats.

### Test d'explication SHAP d'un échantillon (facultatif, extension explain requise)

Entraînez la classification ou la régression ci-dessus, puis chargez son modèle enregistré et `_predict.csv`. Dans le bloc **Expliquer un échantillon (SHAP approximatif)** de la page 4, choisissez aussi le même `_predict.csv` comme référence, la ligne 1, 10 lignes de référence et 2 cycles ; en classification, choisissez la classe. Cliquez sur **Expliquer cet échantillon** ; le premier calcul peut être lent et annulable. Vous verrez la valeur de base, la sortie, l'erreur de reconstruction, les contributions triées par valeur absolue et une **cascade cumulative** de la base à la sortie (sens signé, noms/valeurs d'origine, top N plus « autres N (somme) »), avec **Ouvrir l'image en cascade**, **Ouvrir le dossier de résultats** et **Exporter l'explication…**. **Exporter l'explication…** n'écrit que dans un dossier nouveau ou vide et n'écrase jamais de fichier existant (une destination non vide reçoit un sous-dossier unique, et le dossier de résultats courant ne peut pas être la destination). Les artefacts sont enregistrés dans `shap_explanation.json`, `shap_contributions.csv`, `shap_waterfall.png` et `shap_explanation_notes.md` ; changer ligne/classe/réglages ou quitter la page ne vide que l'affichage et conserve les artefacts terminés. Ce sont des SHAP approximatifs par permutations finies (`base + Σφ = sortie choisie`, tolérance 1e-7/1e-6), non exacts, non causaux et non une performance de test externe ; la première version couvre logistic/decision tree/random forest (classification) et linear/ridge/lasso/elastic net/decision tree/random forest (régression), et n'accepte que les modèles avec métadonnées d'export PsyML. Sans `uv sync --extra explain`, cette section est indisponible et la prédiction ordinaire fonctionne.
