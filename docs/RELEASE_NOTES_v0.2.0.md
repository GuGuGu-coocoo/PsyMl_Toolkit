# PsyML Toolkit v0.2.0

## 中文

本版打通训练、保存最终模型和新数据预测流程，并统一用户测试资料。界面及本说明提供中文、英文和法文。

- **Windows x64（Intel/AMD）**：下载 `PsyML-Toolkit-0.2.0-Windows-x64.zip`，完整解压后双击 `PsyML Toolkit.exe`，保留旁边的 `core` 文件夹。
- **Apple 芯片 Mac**：下载 `PsyML-Toolkit-0.2.0-macOS-arm64.zip`，双击 `PsyML Toolkit.app`。两种应用均包含运行环境，无需安装 Python 或使用命令行。
- **保存最佳模型**：指定主要验证时可保存经全数据重新拟合的完整预处理与模型 Pipeline，以及模型元数据；有效参数包含实际采用的默认值。各验证独立运行模式不生成单一最佳模型。
- **第 4 页“模型与预测”**：加载可信模型，自动核对所需变量和类型，对新数据批量预测并导出。分类提供类别和模型原生支持的概率；回归提供预测值。保留输入列，支持不同列顺序与额外编号列。
- **统一测试入口**：`examples/quickstart/README.md` 解释分类、回归的训练 CSV、配置 JSON 和各 10 行新预测 CSV。第 1 页导入配置即可恢复设置；首次预测数据选择也定位到该资料夹。删除原“测试数据”按钮。
- 更新中英法操作说明和界面截图。普通用户只需下载对应平台的应用 ZIP；GitHub 自动生成的 Source code 不是独立应用。

应用未商业签名/公证，首次启动可能需要按系统提示确认。仅加载来源可信的 joblib/pickle 模型。合成测试数据用于熟悉软件；内部验证分数不保证保存模型在新数据上的表现，新数据预测不等于独立外部验证。

## English

This version connects training, final-model saving and prediction on new data, with one organized quick-start folder. The interface and these notes are available in Chinese, English and French.

- **Windows x64 (Intel/AMD):** download `PsyML-Toolkit-0.2.0-Windows-x64.zip`, extract everything and open `PsyML Toolkit.exe`; keep the adjacent `core` folder.
- **Apple Silicon Mac:** download `PsyML-Toolkit-0.2.0-macOS-arm64.zip` and open `PsyML Toolkit.app`. Both include the runtime; no Python installation or terminal is needed.
- **Save best model:** with a primary validation selected, save the full preprocessing/model Pipeline refitted on all analyzed data and its metadata. Effective parameters include applied defaults. Independent validation mode does not export a single best model.
- **Page 4, Model & Prediction:** load a trusted model, check required variables and types automatically, predict new rows and export results. Classification includes labels and native probabilities where supported; regression includes predicted values. Original columns are retained, including extra IDs, regardless of feature order.
- **One test entry point:** `examples/quickstart/README.md` explains the classification/regression training CSVs, JSON configurations and separate 10-row prediction CSVs. Import configuration on page 1 restores settings; the first prediction-data dialog also opens this folder. The old Sample data button is removed.
- Updated Chinese, English and French instructions and screenshots. Users only need the application ZIP for their platform. GitHub's automatic Source code downloads are not standalone apps.

Applications are not commercially signed/notarized; follow the OS first-launch prompts. Load only trusted joblib/pickle models. Synthetic examples exercise software workflows. Internal validation scores do not guarantee future saved-model performance, and prediction alone is not independent external validation.

## Français

Cette version relie entraînement, enregistrement du modèle final et prédiction sur de nouvelles données, avec un dossier de prise en main unique. Interface et notes sont disponibles en chinois, anglais et français.

- **Windows x64 (Intel/AMD) :** téléchargez `PsyML-Toolkit-0.2.0-Windows-x64.zip`, décompressez tout et ouvrez `PsyML Toolkit.exe` ; conservez le dossier `core` voisin.
- **Mac avec puce Apple :** téléchargez `PsyML-Toolkit-0.2.0-macOS-arm64.zip` et ouvrez `PsyML Toolkit.app`. L’environnement est inclus ; aucune installation Python ni commande nécessaire.
- **Enregistrer le meilleur modèle :** avec une validation principale, enregistrez le Pipeline complet de prétraitement et modèle réajusté sur toutes les données analysées, avec ses métadonnées. Les paramètres effectifs comprennent les valeurs par défaut appliquées. Le mode de validations indépendantes ne produit pas un meilleur modèle unique.
- **Page 4, Modèle et prédiction :** chargez un modèle de confiance, vérifiez automatiquement variables et types, prédisez les nouvelles lignes et exportez. La classification fournit classes et probabilités natives si disponibles ; la régression fournit les valeurs prédites. Les colonnes initiales et identifiants supplémentaires sont conservés, même si l’ordre des variables change.
- **Point d’entrée unique :** `examples/quickstart/README.md` décrit les CSV d’entraînement, configurations JSON et CSV de 10 nouveaux exemples pour classification et régression. Importez le JSON à la page 1 ; le premier dialogue de données à prédire ouvre également ce dossier. L’ancien bouton Données de test est supprimé.
- Instructions et captures actualisées dans les trois langues. Il suffit de télécharger le ZIP de l’application pour votre plateforme. Les archives Source code automatiques de GitHub ne sont pas des applications autonomes.

Applications sans signature commerciale ni notarisation ; suivez les indications du système au premier lancement. Ne chargez que des modèles joblib/pickle de confiance. Les exemples synthétiques testent le logiciel. Les scores de validation interne ne garantissent pas les performances futures du modèle enregistré ; prédire ne constitue pas une validation externe indépendante.
