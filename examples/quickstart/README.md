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

建议先测分类：

1. 第 1 页点击“导入配置…”，选择 `classification_config.json`。对话框默认定位到此资料夹。训练数据和设置一起恢复，预测变量为 score/category；不要导入 `_predict.csv` 来训练。
2. 保持“保存最佳模型”勾选（第 1 页右侧向下滚动，随机种子下方）。到第 2 页选择结果保存位置并运行。
3. 第 3 页点击“打开完整结果文件夹”，在本次运行的 `model/` 中找到 `best_decision_tree.joblib`。保留旁边的 `model_metadata.json`。
4. 第 4 页确认模型来源可信，点击“加载模型…”选择上述模型；点击“加载预测数据…”选择 `classification_predict.csv`。首次打开该数据对话框也默认定位到此资料夹。
5. 自动检查通过后点击“运行预测”，应得到 10 行结果，保留 sample_id/category/score，并追加 predicted_class、probability_0、probability_1。点击“预测结果另存为…”即可保存。
6. 再导入 `regression_config.json`，重复训练；加载其 `best_ridge.joblib` 和 `regression_predict.csv`。应得到 10 行结果，追加 predicted_value，不生成概率列。

预测文件的变量顺序与训练不同，并额外保留 sample_id，用于检查自动选列和原始列保留。两组新样本都只需要 score/category，不需要目标或分组列。预测数值随配置和依赖版本可能不同；这里只检查流程和输出结构，不验证真实模型效果。

若测试错误提示，请另存预测 CSV 的副本，删除 score 列或把其值改成文字后加载；预期会阻止预测。不要改动原始测试文件。旧的 `examples/synthetic/` 保留给现有开发测试；用户试用从本资料夹开始。

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

Import the classification JSON on page 1. Keep **Save best model** enabled, below Random seed in the lower settings area. Choose an output folder and run on page 2. On page 3, open the result folder; keep `model/best_decision_tree.joblib` with `model_metadata.json`. On page 4, trust and load that model, then load `classification_predict.csv`. The configuration and first prediction-data dialogs start in this folder. When automatic checks pass, run and save predictions: expect 10 rows with original sample_id/category/score plus predicted_class and probability_0/probability_1.

Repeat with the regression JSON, its saved `best_ridge.joblib`, and `regression_predict.csv`: 10 rows, with predicted_value and no probability columns. Do not train on the `_predict.csv` files. Their feature order differs from training, and extra sample_id values test column preservation. Predictors require only score/category; no target/group column is needed. Exact predictions may vary with settings and dependency versions; this is not a validation of real-world model quality.

For error testing, save a separate copy of prediction data and remove score or replace numbers with text; prediction should be blocked. Preserve the original files. `examples/synthetic/` remains for existing developer tests; start user testing here.

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

Importez le JSON de classification à la page 1. Gardez l’enregistrement du meilleur modèle activé, sous la graine aléatoire en bas des réglages. Choisissez le dossier de sortie et lancez à la page 2. À la page 3, ouvrez les résultats ; gardez `model/best_decision_tree.joblib` avec `model_metadata.json`. À la page 4, confirmez la confiance, chargez ce modèle puis `classification_predict.csv`. Les dialogues de configuration et de première sélection des données à prédire commencent ici. Après vérification automatique, lancez et enregistrez : 10 lignes, colonnes sample_id/category/score conservées, plus predicted_class et probability_0/probability_1.

Recommencez avec le JSON de régression, son `best_ridge.joblib` et `regression_predict.csv` : 10 lignes, predicted_value ajouté, sans probabilités. Ne pas entraîner sur les fichiers `_predict.csv`. Leur ordre de variables diffère et sample_id teste la conservation des colonnes supplémentaires. Seuls score/category sont requis, sans cible ni groupe. Les valeurs prédites peuvent varier selon les réglages et versions ; ceci ne valide pas les performances réelles.

Pour tester les erreurs, créez une copie des données à prédire, supprimez score ou remplacez les nombres par du texte : la prédiction doit être bloquée. Conservez les originaux. `examples/synthetic/` reste destiné aux tests de développement ; commencez les essais utilisateur ici.
