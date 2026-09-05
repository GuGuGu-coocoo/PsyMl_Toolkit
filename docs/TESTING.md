# Testing / 测试 / Tests

[README](../README.md) · v0.1.0

## 中文

先按 README 安装依赖，在项目根目录运行。测试全部使用合成数据；不要替换为参与者数据。

- `tests/`：Python 核心自动测试，位于根目录下一层。
- `gui/tests/`：GUI 与核心桥接、完整流程、滚动、多语言及独立验证测试。
- `examples/synthetic/`：分类、回归 CSV 与相邻 JSON 配置；`two_groups.csv` 用于边界检查。
- `examples/public/`：可选公开数据示例，需要额外下载；默认快速测试不需要。

隐私审计命令针对完整 Git 仓库中的历史夹具；使用 release ZIP 时没有 `legacy/`，跳过 `tools/audit_repository.py` 这一行。

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
```

人工快速检查：打开分类样例，目标选 `target`、分组选 `participant`，预测变量仅 `score`、`category`，模型选 Decision Tree 和 Dummy，分组 K 折、外层 3、内层 2；选择不指定主要验证，并加选留出法。运行后应先显示验证选择提示，切换后分别显示完整结果。切换三种语言、检查结果与配置是否保持；在研究设计和结果摘要文字处测试滚轮/触控板，在小表格中检查独立滚动；再运行回归配置并检查回归指标与图形。报错、终止与重试也应分别复测。

自动测试通过不等于真实研究设计已验证。少于两个测试样本的 R² 边界测试会有预期警告。CI 在 Windows、macOS、Linux 上运行；查看对应提交的 CI 状态，不把本地测试等同于其他平台已通过。

## English

Install as described in README and run the commands above from the project root. `tests/` contains core tests, `gui/tests/` GUI tests, and `examples/synthetic/` adjacent CSV/JSON pairs. Public datasets are optional. Tests use synthetic data only. The repository privacy audit requires the full Git checkout with `legacy/`; skip that command in the release ZIP.

Set `PSYML_PYTHON` to the installed environment: `.venv/bin/python` on macOS/Linux, `.venv/Scripts/python.exe` on Windows. The platform-specific commands above configure it. Godot 4.7.2 is required for GUI checks.

For manual review, load classification data; use target `target`, group `participant`, predictors `score` and `category`, Decision Tree and Dummy, group K-fold with 3 outer/2 inner folds. Add holdout and select no primary validation. Results should begin with a neutral selector; inspect each validation, switch all UI languages without losing choices, check page versus table scrolling, then run regression. Also check error copying, cancellation and retry. Tiny-sample R² warnings are expected in boundary tests. Automated success is not scientific acceptance. Check the commit's CI results separately for each OS.

## Français

Installer selon le README et exécuter les commandes ci-dessus à la racine. `tests/` contient les tests du noyau, `gui/tests/` ceux de l’interface, et `examples/synthetic/` les paires CSV/JSON voisines. Les données publiques sont facultatives. N’utiliser que des données synthétiques pour les tests. L’audit de confidentialité exige le dépôt Git complet avec `legacy/` ; ignorer cette commande dans le ZIP de release.

Définir `PSYML_PYTHON` avec l’environnement installé : `.venv/bin/python` sous macOS/Linux, `.venv/Scripts/python.exe` sous Windows. Les commandes propres à chaque système sont données plus haut. Les tests GUI nécessitent Godot 4.7.2.

Vérification manuelle : classification, cible `target`, groupe `participant`, prédicteurs `score` et `category`, Decision Tree et Dummy, K plis par groupes avec 3 plis externes/2 internes. Ajouter holdout sans validation principale. Les résultats doivent commencer par un sélecteur neutre ; vérifier chaque validation, les trois langues sans perte des choix et le défilement des pages/tableaux, puis lancer la régression. Vérifier aussi copie des erreurs, arrêt et reprise. Les avertissements R² sur de minuscules tests sont attendus. La réussite automatique ne valide pas le plan scientifique ; consulter séparément le CI du commit pour chaque système.
