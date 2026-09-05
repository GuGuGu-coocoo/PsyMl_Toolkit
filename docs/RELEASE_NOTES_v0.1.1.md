# PsyML Toolkit v0.1.1

## 中文

提供可离线运行的独立桌面应用，内含 Python、Godot 和机器学习依赖。完整解压后双击应用即可使用，无需输入命令或另行下载运行环境。

- **Apple 芯片 Mac**：下载 `PsyML-Toolkit-0.1.1-macOS-arm64.zip`，双击 `PsyML Toolkit.app`。
- **Windows x64（Intel/AMD）**：下载 `PsyML-Toolkit-0.1.1-Windows-x64.zip`，双击 `PsyML Toolkit.exe`；保留旁边的 `core` 文件夹。
- 每个平台包都含分类和回归合成数据及 JSON 配置。在第 1 页点击“导入配置…”，选择 `examples/synthetic/classification_config.json`；在第 2 页选择结果文件夹并运行。回归示例使用 `regression_config.json`。
- 界面支持中文、英文和法文；报告为中文和英文。支持系统原生配置导入/保存窗口、多种验证分别查看完整结果，以及每次分析的主要库版本记录。
- 使用新的 PsyML 图标；附直接和间接依赖的第三方许可证及 SHA-256 校验文件。
- 新增 27 份、每份 48 行的小数据与配置（9 种格式，覆盖二分类、多分类和回归）；在 `examples/synthetic/matrix` 中选择对应配置即可试用。SAS7BDAT 为真实二进制格式的合成样例，已测试本软件读取，未经 SAS 软件认证。
- 修复多分类 Stacking 的 `predict` 与 `passthrough` 组合，以及可空类别和统计文件空字符串的缺失值处理。核心测试含 805 项小数据参数与格式检查；测试通过不能保证任意真实数据和参数均可运行。
- `PsyML-Toolkit-Researcher-Share-v0.1.1.zip` 同时包含两套应用、两份中文 PDF 和合成样例，适合直接分享给老师。`PsyML-Toolkit-v0.1.1.zip` 是含离线 PDF 的完整活动源码包，供开发者使用。

首次启动可能需要系统安全确认：应用未使用商业证书签名/公证。macOS 可在“系统设置 → 隐私与安全性”确认打开；Windows 可核对来源后按系统提示打开，并遵守机构电脑管理要求。合成数据仅用于练习；自动报告需研究者复核，内部验证不能替代独立外部验证。**GitHub 自动生成的 Source code 附件是源码，不是独立应用。**

## English

Self-contained desktop applications include Python, Godot and machine-learning dependencies. Extract the complete archive and double-click the application. No terminal, runtime installation or additional download is required for local analysis.

- **Apple Silicon Mac:** download `PsyML-Toolkit-0.1.1-macOS-arm64.zip` and open `PsyML Toolkit.app`.
- **Windows x64 (Intel/AMD):** download `PsyML-Toolkit-0.1.1-Windows-x64.zip` and open `PsyML Toolkit.exe`; keep the adjacent `core` folder.
- Each package includes synthetic classification/regression data and JSON configurations. On page 1 choose **Import configuration…** and `examples/synthetic/classification_config.json`; select a local output folder on page 2 and run. Use `regression_config.json` for regression.
- Chinese, English and French interface; Chinese/English reports. Native configuration import/save dialogs, complete results per validation and per-analysis library version records are included.
- New PsyML icon, direct and transitive dependency licenses, and SHA-256 checksums.
- 27 tiny datasets and configurations (48 rows each, nine formats, binary/multiclass classification and regression) in `examples/synthetic/matrix`. The synthetic SAS7BDAT files exercise actual binary-file reading in this application; they are not certified by SAS.
- Fixes multiclass Stacking with `predict` plus `passthrough`, nullable categorical values and blank strings in statistical files. The core suite includes 805 small-data parameter/format checks; this does not guarantee compatibility with arbitrary real data and parameters.
- `PsyML-Toolkit-Researcher-Share-v0.1.1.zip` bundles both applications, two Chinese PDF guides and synthetic examples. `PsyML-Toolkit-v0.1.1.zip` contains the complete active sources and offline PDFs for developers.

The applications are not commercially signed/notarized, so the OS may require first-launch confirmation. On macOS use System Settings → Privacy & Security; on Windows verify the source and follow the OS prompt, subject to institutional policies. Synthetic examples are for practice only. Researchers must review reports; internal validation does not replace independent external validation. **GitHub’s automatic Source code assets are not standalone applications.**

## Français

Les applications autonomes comprennent Python, Godot et les dépendances d’apprentissage automatique. Décompressez l’archive entière puis double-cliquez sur l’application. Aucun terminal, environnement à installer ou téléchargement supplémentaire n’est nécessaire pour l’analyse locale.

- **Mac avec puce Apple :** téléchargez `PsyML-Toolkit-0.1.1-macOS-arm64.zip` puis ouvrez `PsyML Toolkit.app`.
- **Windows x64 (Intel/AMD) :** téléchargez `PsyML-Toolkit-0.1.1-Windows-x64.zip` puis ouvrez `PsyML Toolkit.exe` ; conservez le dossier `core` voisin.
- Chaque paquet contient des données synthétiques de classification/régression et leurs configurations JSON. À la page 1, choisissez **Importer une configuration…** puis `examples/synthetic/classification_config.json` ; sélectionnez un dossier de résultats à la page 2 et lancez l’analyse. Utilisez `regression_config.json` pour la régression.
- Interface chinoise, anglaise et française ; rapports chinois/anglais. Dialogues natifs d’importation/sauvegarde, résultats complets par validation et versions des bibliothèques enregistrées pour chaque analyse.
- Nouvelle icône PsyML, licences des dépendances directes et transitives, et empreintes SHA-256.
- 27 petits jeux synthétiques et configurations (48 lignes chacun, neuf formats, classification binaire/multiclasse et régression) dans `examples/synthetic/matrix`. Les fichiers SAS7BDAT testent la lecture binaire réelle dans cette application ; ils ne sont pas certifiés par SAS.
- Correction de Stacking multiclasse avec `predict` et `passthrough`, des catégories nulles et des chaînes vides dans les fichiers statistiques. La suite comprend 805 vérifications de paramètres/formats sur petits jeux ; elle ne garantit pas toutes les combinaisons sur des données réelles.
- `PsyML-Toolkit-Researcher-Share-v0.1.1.zip` réunit les deux applications, deux guides PDF en chinois et les exemples synthétiques. `PsyML-Toolkit-v0.1.1.zip` contient les sources actives complètes et les PDF hors ligne pour les développeurs.

Sans signature commerciale ni notarisation, une confirmation du système peut être nécessaire au premier lancement. Sous macOS, utilisez Réglages Système → Confidentialité et sécurité ; sous Windows, vérifiez la provenance puis suivez les indications du système, selon les règles de votre établissement. Les exemples synthétiques servent à la prise en main. Les rapports nécessitent une vérification humaine ; la validation interne ne remplace pas une validation externe indépendante. **Les fichiers Source code générés par GitHub ne sont pas des applications autonomes.**
