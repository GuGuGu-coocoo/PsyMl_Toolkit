# PsyML Toolkit v0.1.0

## 中文

历史发行记录，仅描述 [v0.1.0](https://github.com/GuGuGu-coocoo/PsyMl_Toolkit/releases/tag/v0.1.0) 附件。该版本的安装步骤见[对应版本 README](https://github.com/GuGuGu-coocoo/PsyMl_Toolkit/blob/v0.1.0/README.md#chinese)；当前使用说明见[主 README](../README.md#chinese)。

首个正式发布版本。PsyML Toolkit 提供本地分类与回归分析，包含 12 个分类、11 个回归模型选项、9 种表格格式和 6 种验证策略。

- 三语 GUI：数据与分析设置、检查与运行、结果。预测变量位于研究设计内，设置与结果摘要随页面滚动，小表格独立滚动。
- 模型家族与参数在内层共同选择，外层评价完整选择流程；支持固定参数、有限网格与自定义搜索。
- 可指定主要验证，也可让多种验证分别输出完整指标、预测、图形和报告；结果页不自动挑最高分，失败验证有明确记录。
- 图形多选、运行进度与预计时间、终止任务、复制报错、每次运行独立文件夹。
- 中文指标附英文名称或缩写；README、截图和研究者指南提供中、英、法三种语言。报告为中英文，科学图形轴和底层错误原文保持英文。
- 分类/回归合成数据及可运行配置位于 `examples/synthetic/`；核心测试在 `tests/`，GUI 测试在 `gui/tests/`。

**下载与运行**：优先下载 `PsyML-Toolkit-v0.1.0.zip`，完整解压后按 README 安装 Python 3.10–3.12、uv 和 Godot 4.7.2。执行 `uv sync --locked --group dev`，再执行 `uv run python tools/launch_gui.py`；macOS 安装后可双击 `Launch PsyML.command`。这是源码包，不是免安装应用。首次安装需联网，分析可离线运行。

ZIP 含源码、GUI、测试、合成数据/配置，以及 `docs/pdf/README_ZH.pdf` 和 `docs/pdf/RESEARCHER_GUIDE_ZH.pdf`。Python wheel 和 tar.gz 仅提供核心/CLI，不含完整 GUI；GitHub 自动生成的 Source code 压缩包不含额外 PDF。`SHA256SUMS.txt` 用于核对附件完整性，ZIP 中的 `RELEASE_MANIFEST.json` 记录提交与文件校验值。

复现示例：`uv run psyml run --config examples/synthetic/classification_config.json`。再次运行前改用新空 `output_dir`；配置路径相对于执行命令的目录。`best_parameters_configure.json` 是固定参数重新训练配方，不等同于重现嵌套搜索的分数。自动摘要必须由研究者复核，内部验证不能替代外部验证。本版不提供已拟合模型文件导出、阈值选择或时间序列专用验证。

## English

Historical notes for the [v0.1.0 assets](https://github.com/GuGuGu-coocoo/PsyMl_Toolkit/releases/tag/v0.1.0) only. Use the [versioned README](https://github.com/GuGuGu-coocoo/PsyMl_Toolkit/blob/v0.1.0/README.md#english) for that release’s setup, or the [main README](../README.md#english) for current usage.

First release of PsyML Toolkit: local classification and regression with 12 classification and 11 regression model options, 9 tabular formats and 6 validation strategies.

- Three-language, three-page GUI: data/analysis setup, review/run and results. Predictors are inside Research design; settings and result summaries scroll with the page while small tables scroll independently.
- Joint inner selection of model family and parameters, evaluated by outer validation; fixed, bounded-grid and custom parameter modes.
- Choose a primary validation or generate complete independent outputs for each validation. No automatic highest-score validation; failures remain explicit.
- Selectable figures, progress/ETA, cancellation, error copying and a separate directory per run.
- Chinese metrics include English names/abbreviations. README, screenshots and researcher guides are available in Chinese, English and French. Reports are Chinese/English; plot axes and raw backend errors remain English.
- Runnable synthetic CSV/JSON pairs in `examples/synthetic/`, core tests in `tests/`, GUI tests in `gui/tests/`.

**Download and run:** use `PsyML-Toolkit-v0.1.0.zip`, extract it, then follow README to install Python 3.10–3.12, uv and Godot 4.7.2. Run `uv sync --locked --group dev`, then `uv run python tools/launch_gui.py`. On macOS, `Launch PsyML.command` opens the installed environment. This is source code, not a standalone application. Initial installation needs internet; analysis works offline.

The ZIP includes source, GUI, tests, synthetic data/configurations and Chinese PDFs at `docs/pdf/README_ZH.pdf` and `docs/pdf/RESEARCHER_GUIDE_ZH.pdf`. The Python wheel and tar.gz contain only core/CLI, not the complete GUI. GitHub's automatic Source code archives omit the extra PDFs. Verify assets with `SHA256SUMS.txt`; `RELEASE_MANIFEST.json` inside the ZIP records the commit and individual file hashes.

Quick reproduction: `uv run psyml run --config examples/synthetic/classification_config.json`. Use a new empty `output_dir` before repeating; relative paths resolve from the command's working directory. `best_parameters_configure.json` retrains fixed parameters and does not reproduce nested-search scores. Researchers must review automatic summaries; internal validation cannot replace external validation. Saved fitted-model export, threshold selection and dedicated time-series validation are not provided.

## Français

Notes historiques concernant uniquement les [fichiers de v0.1.0](https://github.com/GuGuGu-coocoo/PsyMl_Toolkit/releases/tag/v0.1.0). Consultez le [README de cette version](https://github.com/GuGuGu-coocoo/PsyMl_Toolkit/blob/v0.1.0/README.md#french) pour son installation, ou le [README principal](../README.md#french) pour l’utilisation actuelle.

Première version de PsyML Toolkit : classification et régression locales, avec 12 choix de modèles de classification, 11 de régression, 9 formats tabulaires et 6 stratégies de validation.

- Interface trilingue à trois pages : données/analyse, vérification/exécution, résultats. Prédicteurs intégrés au plan de recherche ; réglages et résumés défilent avec la page, petits tableaux indépendamment.
- Sélection conjointe famille/paramètres dans les plis internes, évaluée dans les plis externes ; paramètres fixes, grille limitée ou personnalisée.
- Validation principale facultative ou sorties complètes indépendantes par validation ; aucun choix automatique du meilleur score et échecs explicités.
- Figures sélectionnables, progression/temps estimé, arrêt, copie d’erreurs et dossier distinct par exécution.
- Métriques chinoises accompagnées de noms/abréviations anglais. README, captures et guides en chinois, anglais et français. Rapports chinois/anglais ; axes et erreurs brutes en anglais.
- Paires CSV/JSON synthétiques exécutables dans `examples/synthetic/`, tests du noyau dans `tests/`, tests GUI dans `gui/tests/`.

**Téléchargement et lancement :** utiliser `PsyML-Toolkit-v0.1.0.zip`, le décompresser puis installer Python 3.10–3.12, uv et Godot 4.7.2 selon le README. Lancer `uv sync --locked --group dev`, puis `uv run python tools/launch_gui.py`. Sous macOS, `Launch PsyML.command` ouvre l’environnement installé. C’est une distribution source, pas une application autonome. L’installation initiale nécessite Internet ; l’analyse fonctionne hors ligne.

Le ZIP contient sources, interface, tests, données/configurations synthétiques et PDF chinois dans `docs/pdf/README_ZH.pdf` et `docs/pdf/RESEARCHER_GUIDE_ZH.pdf`. Le wheel Python et le tar.gz ne contiennent que noyau/CLI, pas l’interface complète. Les archives Source code automatiques de GitHub omettent les PDF supplémentaires. `SHA256SUMS.txt` vérifie les pièces jointes ; `RELEASE_MANIFEST.json` dans le ZIP conserve commit et empreintes des fichiers.

Reproduction rapide : `uv run psyml run --config examples/synthetic/classification_config.json`. Choisir un nouveau `output_dir` vide avant de répéter ; les chemins relatifs dépendent du dossier de travail. `best_parameters_configure.json` réentraîne des paramètres fixes et ne reproduit pas les scores de recherche imbriquée. Les résumés automatiques nécessitent une vérification humaine ; la validation interne ne remplace pas l’externe. Cette version ne propose pas d’export de modèle ajusté, de choix de seuil ou de validation temporelle dédiée.
