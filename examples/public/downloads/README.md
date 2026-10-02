# Data downloads and conversion scripts

[中文](#中文) · [English](#english) · [Français](#français)

## 中文

下载下面的 CSV 和案例页提供的 JSON 配置，即可在 PsyML 界面中导入。CSV 已完成参考分析所用的数据转换，普通复现不需要运行脚本。可下载软件与已验证源码的版本区别见 [README](../../../README.md)。

| 案例 | 可直接导入的 CSV | 原始数据 | 转换脚本与说明 |
| --- | --- | --- | --- |
| DSA | [dsa_torso_mean_std.csv（2.34 MB）](https://raw.githubusercontent.com/GuGuGu-coocoo/PsyMl_Toolkit/main/examples/public/downloads/dsa_torso_mean_std.csv) | [UCI 官方 ZIP](https://archive.ics.uci.edu/static/public/256/daily%2Band%2Bsports%2Bactivities.zip) · [数据页](https://doi.org/10.24432/C5C59F) | [prepare_dsa.py](../../../tools/cases/prepare_dsa.py) · [可选重建步骤](../dsa_group_nested_v1/README.md) |
| California Housing | [california_housing.csv（2.54 MB）](https://raw.githubusercontent.com/GuGuGu-coocoo/PsyMl_Toolkit/main/examples/public/downloads/california_housing.csv) | [Figshare 官方 TGZ](https://ndownloader.figshare.com/files/5976036) · [数据页](https://doi.org/10.6084/m9.figshare.3829992.v2) | [prepare_california.py](../../../tools/cases/prepare_california.py) · [可选重建步骤](../california_random_nested_v1/README.md) |

如果浏览器显示文件内容，使用“另存为”，保留 `.csv` 扩展名。不要用表格软件重新保存后再核对字节校验值：重新保存可能改变小数格式或换行。

DSA 来源为 Barshan, B. 与 Altun, K. (2010)，*Daily and Sports Activities*，UCI，DOI [10.24432/C5C59F](https://doi.org/10.24432/C5C59F)。按原始活动、参与者、片段顺序读取全部 9,120 段；每段取躯干三轴加速度及三轴角速度，每个通道计算均值和总体标准差（`ddof=0`），共 12 个预测变量。`segment_id` 用于识别记录，`subject_id` 用于分组，`activity` 是目标；这些列不进入预测变量。没有删行、跨片段归一化或依据结果选择特征。数据保留原始公开参与者编号，没有添加身份信息。

California 来源为 Liu, Nelson (2016)，*scikit-learn california housing dataset cal_housing.tgz*，Figshare，version 2，DOI [10.6084/m9.figshare.3829992.v2](https://doi.org/10.6084/m9.figshare.3829992.v2)。原研究为 [Pace 与 Barry (1997)](https://doi.org/10.1016/S0167-7152(96)00140-X)。保留全部 20,640 行和顺序，将房间数、卧室数、人口数分别除以家庭数，得到相应均值；房价中位数除以 100,000，得到 `MedHouseVal`。其余字段按 scikit-learn 的变量定义排列，封顶值原样保留。[完整来源与公式](../california_random_nested_v1/expected/provenance.json) · [归属说明](../california_random_nested_v1/ATTRIBUTION.md)。

两份数据均按原始来源标注的 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 再分发；引用或转发时请保留作者、来源、许可及上述转换说明。数据作者和提供方不为 PsyML 背书。项目的 Apache 2.0 代码许可不替代数据许可。

脚本仅供核查或重新转换数据。两份脚本及其辅助模块已包含在仓库中；需要运行时使用完整仓库，不能只下载单个 Python 文件。脚本先核对官方压缩包 SHA-256，不执行压缩包内容。下载的 CSV 与历史参考分析使用的 CSV 逐字节相同，具体校验值见下表。

## English

Download a CSV below and the JSON configuration linked on its case page, then import them through PsyML. The CSV already has the reference transformation; running a script is optional. See the [README](../../../README.md) for the distinction between downloadable applications and tested source revisions.

- DSA: [prepared CSV](https://raw.githubusercontent.com/GuGuGu-coocoo/PsyMl_Toolkit/main/examples/public/downloads/dsa_torso_mean_std.csv) · [official ZIP](https://archive.ics.uci.edu/static/public/256/daily%2Band%2Bsports%2Bactivities.zip) · [conversion script](../../../tools/cases/prepare_dsa.py) · [optional rebuilding](../dsa_group_nested_v1/README.md)
- California: [prepared CSV](https://raw.githubusercontent.com/GuGuGu-coocoo/PsyMl_Toolkit/main/examples/public/downloads/california_housing.csv) · [official TGZ](https://ndownloader.figshare.com/files/5976036) · [conversion script](../../../tools/cases/prepare_california.py) · [optional rebuilding](../california_random_nested_v1/README.md)

If the browser displays the contents, use Save as and retain `.csv`. Resaving in spreadsheet software may change decimal formatting or line endings and therefore change the byte checksum.

DSA: Barshan, B. & Altun, K. (2010), *Daily and Sports Activities*, UCI, DOI [10.24432/C5C59F](https://doi.org/10.24432/C5C59F). All 9,120 segments are kept in activity/participant/segment order. For each segment, the converter computes mean and population standard deviation (`ddof=0`) for torso acceleration x/y/z and angular rate x/y/z: 12 predictors. `segment_id` identifies the record, `subject_id` groups participants and `activity` is the target; none is a predictor. There is no row removal, cross-segment normalization or result-driven feature selection. Original public participant IDs are retained, with no additional identity information.

California: Liu, Nelson (2016), *scikit-learn california housing dataset cal_housing.tgz*, Figshare version 2, DOI [10.6084/m9.figshare.3829992.v2](https://doi.org/10.6084/m9.figshare.3829992.v2). Original research: [Pace & Barry (1997)](https://doi.org/10.1016/S0167-7152(96)00140-X). All 20,640 rows remain in source order. Room, bedroom and population totals are divided by households to obtain averages; median house value is divided by 100,000 to obtain `MedHouseVal`. Other fields follow scikit-learn's feature definitions; capped values are retained. [Provenance and formulas](../california_random_nested_v1/expected/provenance.json) · [attribution](../california_random_nested_v1/ATTRIBUTION.md).

Both datasets are redistributed under the sources' [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) licence. Retain authors, source, licence and transformation details when citing or sharing them. Data authors and providers do not endorse PsyML. The project's Apache 2.0 code licence does not replace the data licences.

The scripts and their helper modules are in the repository. Use the whole repository if you choose to run them; a single downloaded Python file is insufficient. They verify the official archive SHA-256 before reading it and never execute archive contents. The prepared CSVs are byte-identical to the historical reference inputs; checksums are below.

## Français

Téléchargez un CSV ci-dessus et la configuration JSON de sa page de cas, puis importez-les dans PsyML. Le CSV contient déjà la transformation de référence ; exécuter un script reste facultatif. Le [README](../../../README.md) distingue les applications téléchargeables des révisions source testées.

- DSA : [CSV préparé](https://raw.githubusercontent.com/GuGuGu-coocoo/PsyMl_Toolkit/main/examples/public/downloads/dsa_torso_mean_std.csv) · [ZIP officiel](https://archive.ics.uci.edu/static/public/256/daily%2Band%2Bsports%2Bactivities.zip) · [script de conversion](../../../tools/cases/prepare_dsa.py) · [reconstruction facultative](../dsa_group_nested_v1/README.md)
- California : [CSV préparé](https://raw.githubusercontent.com/GuGuGu-coocoo/PsyMl_Toolkit/main/examples/public/downloads/california_housing.csv) · [TGZ officiel](https://ndownloader.figshare.com/files/5976036) · [script de conversion](../../../tools/cases/prepare_california.py) · [reconstruction facultative](../california_random_nested_v1/README.md)

Si le navigateur affiche le contenu, utilisez « Enregistrer sous » en conservant `.csv`. Un nouvel enregistrement dans un tableur peut modifier les décimales ou les fins de ligne et donc l’empreinte du fichier.

DSA : Barshan, B. et Altun, K. (2010), *Daily and Sports Activities*, UCI, DOI [10.24432/C5C59F](https://doi.org/10.24432/C5C59F). Les 9 120 segments sont conservés dans l’ordre activité/participant/segment. Pour chacun, le convertisseur calcule moyenne et écart-type de population (`ddof=0`) de l’accélération et de la vitesse angulaire du torse sur trois axes : 12 prédicteurs. `segment_id` identifie le segment, `subject_id` le groupe et `activity` la cible ; aucune de ces colonnes n’est un prédicteur. Aucune ligne n’est supprimée ; aucune normalisation entre segments ou sélection de variables selon les résultats n’est appliquée. Les identifiants publics d’origine sont conservés, sans ajout d’informations d’identité.

California : Liu, Nelson (2016), *scikit-learn california housing dataset cal_housing.tgz*, Figshare version 2, DOI [10.6084/m9.figshare.3829992.v2](https://doi.org/10.6084/m9.figshare.3829992.v2). Étude originale : [Pace et Barry (1997)](https://doi.org/10.1016/S0167-7152(96)00140-X). Les 20 640 lignes gardent leur ordre d’origine. Les totaux de pièces, chambres et habitants sont divisés par le nombre de ménages ; la valeur médiane des logements est divisée par 100 000 pour obtenir `MedHouseVal`. Les autres champs suivent les définitions de scikit-learn, avec conservation des valeurs plafonnées. [Provenance et formules](../california_random_nested_v1/expected/provenance.json) · [attribution](../california_random_nested_v1/ATTRIBUTION.md).

Les deux jeux sont redistribués sous la licence [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) indiquée par leurs sources. Conservez auteurs, source, licence et transformations lors d’une citation ou redistribution. Les auteurs et fournisseurs des données ne cautionnent pas PsyML. La licence Apache 2.0 du code ne remplace pas celles des données.

Les scripts et leurs modules auxiliaires figurent dans le dépôt. Pour les exécuter, utilisez le dépôt complet ; un fichier Python isolé ne suffit pas. Ils vérifient le SHA-256 de l’archive officielle avant lecture et n’exécutent jamais son contenu. Les CSV préparés sont identiques octet pour octet aux entrées de référence historiques.

## File identity / 文件校验 / Empreintes

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `dsa_torso_mean_std.csv` | 2343871 | `75a5fe87a58f4cfde777d914d674362b5148854a3c7064d8c686c0e25c3a047e` |
| `california_housing.csv` | 2539419 | `157b6c0d3acd6d93a50c411d0cd4130d8c719ce5eb17b61f1c45300f2af6fc85` |
| UCI DSA source ZIP | 170800010 | `f42ad7744ecf14151c9fa3a86dfb5b24de9d7cb7ffe956ef5de242983459c77e` |
| Figshare `cal_housing.tgz` | 441963 | `aaa5c9a6afe2225cc2aed2723682ae403280c4a3695a2ddda4ffb5d8215ea681` |
