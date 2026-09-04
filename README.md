# PsyML Toolkit

<p align="center">
  <a href="#chinese">中文</a> · <a href="#english">English</a> · <a href="#french">Français</a>
</p>

<a id="chinese"></a>

## 中文

PsyML Toolkit 是面向研究者的本地机器学习工具。新的分析只使用现代化的 `src/psyml/` 核心；Godot 图形界面负责配置和展示，训练、预处理、验证与指标始终由同一 Python 核心完成。数据不会上传。

支持回归与分类、23 种模型、9 种表格格式、训练集内预处理、5 种验证策略、完整评价指标，以及预测、图形、Methods 说明和可复现性报告导出。界面默认中文，也可切换英文和法文。

### 快速开始

需要 Python 3.10–3.12、[uv](https://docs.astral.sh/uv/) 和 [Godot 4.7.2](https://godotengine.org/download/archive/4.7.2-stable/)。在仓库根目录运行：

```bash
uv sync --locked --group dev
uv run python tools/launch_gui.py
```

也可以只使用命令行：`uv run psyml --help`。若 Godot 不在系统路径中，请把 `PSYML_GODOT` 设为 Godot 可执行文件的完整路径。

### 图文操作流程

1. 选择数据文件并点击“读取预览”。核对行列数、变量类型和缺失值；预览只在本机处理。再选择预测变量，目标和分组变量会自动从预测变量中排除。

![中文数据与变量界面](docs/images/zh/01-data.png)

2. 选择分类或回归、目标变量、可选分组变量、缺失值与缩放策略、验证方法和模型。重复测量或同一参与者多行数据应选择分组变量与分组验证。

![中文分析设置界面](docs/images/zh/02-configure.png)

3. 选择结果目录，检查完整 JSON 配置后运行。固定的随机种子和保存的 `analysis_config.json` 可用于重跑。

![中文检查与运行界面](docs/images/zh/03-review.png)

4. 查看风险提示、指标、预测和图形。“打开完整结果文件夹”可访问 CSV、JSON、PNG、Methods 与 reproducibility 文件。

![中文结果界面](docs/images/zh/04-results.png)

截图使用随机合成数据，不包含真实参与者信息。公开可复查示例采用 UCI 的 [Iris（分类）](https://doi.org/10.24432/C56C76)与[混凝土抗压强度（回归）](https://doi.org/10.24432/C5PK67)，两者均为 CC BY 4.0；运行方法见 [公开示例说明](examples/public/README.md)。

### 隐私与复现

PsyML 在本机运行，不会上传输入数据。仓库中的截图与测试夹具均为合成数据；公开示例数据会在本地下载、校验固定哈希，且不会提交到仓库。每次成功分析都会保存实际配置、Methods 说明和可复现性报告。当前分析只使用 `src/psyml/`；`legacy/` 仅作历史代码参考，不参与运行。

除另行标注的第三方内容外，本项目代码与文档采用 [Apache License 2.0](LICENSE)，允许使用、修改和分发，并包含明确的专利授权。第三方依赖与公开数据仍遵循各自的许可证。

<a id="english"></a>

## English

PsyML Toolkit is a local machine-learning tool for researchers. New analyses use only the modern `src/psyml/` core. The Godot interface handles configuration and presentation, while the same Python core performs training, preprocessing, validation and metric calculation. Data are never uploaded.

It supports regression and classification, 23 models, 9 tabular formats, training-only preprocessing, 5 validation strategies, comprehensive metrics, predictions, figures, a Methods summary and a reproducibility report. The interface is available in Chinese, English and French.

### Quick start

Install Python 3.10–3.12, [uv](https://docs.astral.sh/uv/) and [Godot 4.7.2](https://godotengine.org/download/archive/4.7.2-stable/), then run from the repository root:

```bash
uv sync --locked --group dev
uv run python tools/launch_gui.py
```

For command-line use, run `uv run psyml --help`. If Godot is not on `PATH`, set `PSYML_GODOT` to the complete path of the Godot executable.

### Illustrated workflow

1. Choose a data file and select “Load preview”. Check its dimensions, variable types and missing values, then select predictors. The outcome and group columns are automatically excluded from predictors.

![English data and variables screen](docs/images/en/01-data.png)

2. Select classification or regression, the outcome, an optional group column, preprocessing, validation and model. For repeated observations, use a group column and group-aware validation.

![English analysis setup screen](docs/images/en/02-configure.png)

3. Choose the result folder, review the complete JSON configuration and run. The fixed seed and saved `analysis_config.json` support exact reruns.

![English review and run screen](docs/images/en/03-review.png)

4. Inspect warnings, metrics, predictions and the figure. Open the complete result folder for CSV, JSON, PNG, Methods and reproducibility files.

![English results screen](docs/images/en/04-results.png)

The screenshots use random synthetic data and contain no participant information. Auditable public examples use UCI’s CC BY 4.0 [Iris classification dataset](https://doi.org/10.24432/C56C76) and [Concrete Compressive Strength regression dataset](https://doi.org/10.24432/C5PK67); see the [public example instructions](examples/public/README.md).

### Privacy and reproducibility

PsyML runs locally and does not upload input data. Repository screenshots and test fixtures use synthetic data. Public example datasets are downloaded locally, checked against pinned hashes and never committed. Every successful analysis saves the effective configuration, a Methods summary and a reproducibility report. Current analyses use only `src/psyml/`; `legacy/` is historical reference code and is not executed.

Except for separately identified third-party material, this project's code and documentation are licensed under the [Apache License 2.0](LICENSE), which permits use, modification and distribution and includes an express patent grant. Third-party dependencies and public datasets remain subject to their own licenses.

<a id="french"></a>

## Français

PsyML Toolkit est un outil local d’apprentissage automatique pour la recherche. Les nouvelles analyses utilisent uniquement le noyau moderne `src/psyml/`. L’interface Godot gère la configuration et l’affichage ; le même noyau Python réalise l’entraînement, le prétraitement, la validation et le calcul des métriques. Aucune donnée n’est téléversée.

L’outil prend en charge la régression et la classification, 23 modèles, 9 formats tabulaires, le prétraitement ajusté uniquement sur l’entraînement, 5 stratégies de validation, des métriques complètes, les prédictions, les figures, un résumé Methods et un rapport de reproductibilité. L’interface est disponible en chinois, anglais et français.

### Démarrage rapide

Installez Python 3.10–3.12, [uv](https://docs.astral.sh/uv/) et [Godot 4.7.2](https://godotengine.org/download/archive/4.7.2-stable/), puis exécutez depuis la racine du dépôt :

```bash
uv sync --locked --group dev
uv run python tools/launch_gui.py
```

Pour la ligne de commande : `uv run psyml --help`. Si Godot n’est pas dans le `PATH`, définissez `PSYML_GODOT` avec le chemin complet de l’exécutable Godot.

### Parcours illustré

1. Choisissez un fichier puis « Charger l’aperçu ». Vérifiez les dimensions, les types et les valeurs manquantes, puis sélectionnez les prédicteurs. La cible et le groupe sont automatiquement exclus.

![Écran français des données et variables](docs/images/fr/01-data.png)

2. Choisissez la classification ou la régression, la cible, un groupe éventuel, le prétraitement, la validation et le modèle. Pour des observations répétées, utilisez une variable de groupe et une validation par groupes.

![Écran français de configuration](docs/images/fr/02-configure.png)

3. Choisissez le dossier de résultats, vérifiez la configuration JSON complète, puis lancez l’analyse. La graine fixe et le fichier `analysis_config.json` permettent de la reproduire.

![Écran français de vérification](docs/images/fr/03-review.png)

4. Consultez les alertes, les métriques, les prédictions et la figure. Ouvrez le dossier complet pour accéder aux fichiers CSV, JSON, PNG, Methods et de reproductibilité.

![Écran français des résultats](docs/images/fr/04-results.png)

Les captures utilisent des données synthétiques aléatoires sans information de participant. Les exemples publics vérifiables emploient les jeux UCI sous CC BY 4.0 [Iris pour la classification](https://doi.org/10.24432/C56C76) et [Concrete Compressive Strength pour la régression](https://doi.org/10.24432/C5PK67) ; voir les [instructions des exemples publics](examples/public/README.md).

### Confidentialité et reproductibilité

PsyML fonctionne localement et ne téléverse pas les données d’entrée. Les captures et les données de test du dépôt sont synthétiques. Les jeux d’exemple publics sont téléchargés localement, vérifiés à l’aide d’empreintes figées et ne sont jamais commités. Chaque analyse réussie enregistre la configuration effective, un résumé Methods et un rapport de reproductibilité. Les analyses actuelles utilisent uniquement `src/psyml/` ; `legacy/` contient du code historique qui n’est pas exécuté.

Sauf mention contraire pour les éléments tiers, le code et la documentation de ce projet sont placés sous [licence Apache 2.0](LICENSE). Celle-ci autorise l’utilisation, la modification et la distribution et comprend une concession explicite de droits de brevet. Les dépendances tierces et les jeux de données publics restent soumis à leurs propres licences.
