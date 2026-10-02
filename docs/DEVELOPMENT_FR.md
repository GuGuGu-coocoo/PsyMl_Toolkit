# Guide de développement

[README](../README_FR.md) · [中文](DEVELOPMENT_ZH.md) · [English](DEVELOPMENT_EN.md)

Ce guide concerne la modification, la maintenance et la construction de PsyML. Les chercheurs utilisent l’interface sans outils de développement ni ces commandes. La version du code n’a qu’une seule source maintenue : la constante `__version__` de `src/psyml/__init__.py` (`pyproject.toml` la lit via les métadonnées dynamiques de hatch ; la source actuelle est la version officielle `0.3.0`, affichée telle quelle, tandis qu’une version de développement `0.3.0.dev0` s’affiche `0.3.0-dev`). Les paquets autonomes et PDF de distribution disponibles par version sont ceux listés sur la page Releases ; les paquets v0.2.0 et antérieurs ne contiennent ni les nouvelles fonctions ni les correctifs de la seconde série présents dans ces sources.

## Environnement et lancement

Utilisez Git, Python 3.10–3.12, [uv](https://docs.astral.sh/uv/) et [Godot 4.7.2](https://godotengine.org/download/archive/4.7.2-stable/). Les applications autonomes utilisent Python 3.12.13. À la racine d’un clone complet :

```bash
uv sync --locked --group dev
uv run python tools/launch_gui.py
```

Le lanceur définit `PSYML_PYTHON` avec l’environnement courant. Si Godot est absent du PATH, définissez son chemin complet dans `PSYML_GODOT`. Sous macOS, après installation, `Launch PsyML.command` est également disponible. Ne résolvez pas le lien `.venv/bin/python` vers un interpréteur extérieur : les dépendances du projet pourraient devenir introuvables.

## Structure du dépôt

| Emplacement | Rôle |
| --- | --- |
| `src/psyml/config.py`, `protocol.py`, `schemas/` | Validation des configurations et contrats JSON versionnés |
| `src/psyml/runner.py` | Orchestration, sélection imbriquée, validations indépendantes |
| `src/psyml/data/`, `preprocessing/`, `validation/` | Lecture, prétraitement limité à l’entraînement, partitions |
| `src/psyml/models/catalog.py`, `factory.py`, `evaluation/metrics.py` | Catalogue des modèles/paramètres, estimateurs, métriques |
| `src/psyml/reporting/` | Prédictions, métriques, figures, rapports et versions |
| `src/psyml/gui_config.py` | Résolution des chemins importés et contrôle des colonnes |
| `gui/main.tscn`, `gui/scripts/main.gd` | Structure et interactions de l’interface |
| `gui/scripts/core_bridge.gd`, `configuration_io.gd` | Sous-processus, importation et sauvegarde des configurations |
| `gui/scripts/i18n.gd`, `light_theme.gd` | Trois langues et couleurs des états interactifs |
| `tests/`, `gui/tests/`, `examples/synthetic/` | Tests et paires de données/configurations synthétiques |
| `tools/`, `.github/workflows/` | Lancement, construction, contrôles et CI |
| `src/psyml/models/persistence.py`, `parameters.py`, `src/psyml/prediction.py` | Pipeline final, paramètres effectifs, contrôle et prédiction |
| `gui/scripts/prediction_page.gd`, `data_preview.gd` | Page 4 et aperçus communs |
| `examples/quickstart/`, `tests/test_quickstart.py` | Dossier utilisateur portable et vérification entraînement-prédiction |

`legacy/` archive du code ancien et des jeux synthétiques ; ce n’est pas le point d’entrée actuel. Ne versionnez pas les sorties locales `dist/`, `tmp/`, `output/`, `.venv/` ni de vraies données de recherche.

## Interfaces du noyau

L’interface appelle le noyau Python local, via l’environnement virtuel en développement et `psyml-core` intégré dans les applications autonomes. Conservez la logique d’analyse dans le noyau.

```bash
uv run psyml --help
uv run psyml capabilities
uv run psyml preview --input examples/synthetic/classification.csv
uv run psyml import-config --config examples/synthetic/classification_config.json
uv run psyml schema analysis_config
uv run psyml run --config examples/synthetic/classification_config.json --events
uv run psyml run --config examples/synthetic/regression_config.json --events
```

`capabilities` décrit modèles, formats, métriques et validations. `preview` renvoie les métadonnées ; `--include-sample` ajoute des lignes. `schema` accepte `analysis_config`, `event`, `result`. La sortie `run --events` doit rester du JSONL valide, avec progression et événements terminaux, sans journaux mélangés. L’API Python expose `ExperimentConfig` et `run_experiment` depuis `psyml` ; `psyml.protocol.load_config` lit le JSON.

En CLI, les chemins relatifs dépendent du dossier courant ; `output_dir` est utilisé tel quel et les résultats existants ne sont pas écrasés. Choisissez un nouveau dossier vide pour relancer. L’importation GUI recherche les données près du JSON puis reconnaît les chemins des exemples du dépôt. Un chemin manquant demande une réassociation ; une colonne manquante provoque une erreur. L’interface crée toujours un nouveau sous-dossier local. Le chemin sauvegardé des données n’est relatif que si données et configuration partagent le même dossier.

Dans le JSON, `primary_validation: null` active les sorties séparées par validation ; un nom désigne une validation principale et l’omission conserve le comportement historique. En Python, utiliser `validation_results[stratégie]` ; `model=None` et `metrics={}` à la racine sont intentionnels.

### Interfaces 0.2.0 : entraînement, enregistrement et prédiction

`examples/quickstart/` est l’entrée des essais utilisateur ; `examples/synthetic/` et `matrix/` restent des jeux de développement, avec les commandes précédentes toujours valables. Les JSON quickstart utilisent les noms des CSV voisins : entrez d’abord dans ce dossier pour la CLI. `load_config()` ne recalcule pas les chemins relativement au JSON. Vérifiez l’absence d’anciens résultats dans `results/quickstart_classification` et `results/quickstart_regression` ; choisissez de nouveaux dossiers de sortie dans les JSON avant de relancer.

```bash
cd examples/quickstart
uv run psyml run --config classification_config.json --events
uv run psyml model-info --model results/quickstart_classification/model/best_decision_tree.joblib --trust-model
uv run psyml predict --model results/quickstart_classification/model/best_decision_tree.joblib --input classification_predict.csv --check-only --trust-model
uv run psyml predict --model results/quickstart_classification/model/best_decision_tree.joblib --input classification_predict.csv --output results/quickstart_classification/new_predictions.xlsx --trust-model
uv run psyml export-table --input results/quickstart_classification/new_predictions.xlsx --output results/quickstart_classification/new_predictions.csv
uv run psyml run --config regression_config.json --events
uv run psyml predict --model results/quickstart_regression/model/best_ridge.joblib --input regression_predict.csv --output results/quickstart_regression/new_predictions.csv --trust-model
cd ../..
```

Chaque prédiction contient 10 lignes et conserve sample_id/category/score. La classification ajoute predicted_class et deux colonnes probability_* ; la régression ajoute predicted_value. `model-info` renvoie les métadonnées. Inspectez `compatibility.compatible` et les erreurs de `predict --check-only`, pas seulement le code de sortie. Prédire exige `--output`, dont le suffixe détermine le format ; aucun écrasement sans `--overwrite` explicite. Répétez `--feature` dans l’ordre d’entraînement pour une correspondance manuelle. `export-table` convertit une table sans relancer le modèle. XLS/SAS7BDAT sont en lecture seule ; utilisez XLSX en sortie.

Interfaces Python de `psyml.prediction` : `load_model(path, trusted=True)`, `compatibility_check(loaded, frame, mapping=None)`, `predict_dataframe(loaded, frame, mapping=None)`. La dernière renvoie `(DataFrame, liste_des_colonnes_ajoutées)`. La confiance explicite est requise même pour examiner les métadonnées.

`save_best_model` vaut true par défaut. Une analyse principale consigne état et chemins relatifs dans `model_export`, avec les index `result.json.artifacts.saved_model` / `model_metadata` ; le mode indépendant n’enregistre pas automatiquement de modèles. `best_parameters.json`, `result.json.effective_parameters` et best_parameters des métadonnées incluent les défauts effectifs ; `result.json.best_parameters` et la recette fixe conservent les valeurs remplaçant les défauts. Préservez cette distinction.

### Interfaces de contrôle des données et d’interprétation des résultats

`psyml.data.profiling` est le helper pur du contrôle des données : `profile_columns` / `column_profile` / `category_summary` / `identifier_signals` construisent des métadonnées par colonne (valeurs non manquantes, valeurs uniques, ratio quasi unique, effectifs optionnels avec troncature et signaux d’identifiant justifiés). `protocol.dataframe_preview` n’attache des valeurs que si `include_sample=True` et n’en renvoie aucune par défaut ; l’interface `gui/scripts/data_check_ui.gd` consomme ces métadonnées sans estimer depuis les cinq premières lignes et ne supprime ni colonne ni rôle.

`build_interpretation` dans `psyml.reporting.interpretation` n’agrège que les preuves déjà calculées par le runner (procedure_results, plis par combinaison, tuning_rows, leaderboard, validation_summary) et n’ajoute aucun ajustement ; `write_interpretation_outputs` écrit `result_interpretation.json`, `interpretation_baseline_differences.csv` et `result_interpretation.md`, indexés par `result.json.artifacts`. En validation indépendante, `build_independent_interpretation` n’écrit qu’un aperçu/index racine. Le résumé GUI est dans `gui/scripts/result_interpretation_ui.gd`. Régression noyau : `tests/test_profiling.py`, `tests/test_interpretation.py` ; GUI : `gui/tests/test_data_check.gd`, `gui/tests/test_interpretation_results.gd`. La baseline ne compare qu’un dummy réussi sur la même validation, les mêmes plis et la même métrique, avec un signe fixe (positif = meilleur) ; les statistiques descriptives ne reviennent jamais dans la sélection ou le réglage. L'explication du découpage par groupes ne modifie que les guides trilingues, sans GUI ni algorithme de découpage.

### Interfaces d’importance par permutation

`ExperimentConfig.permutation_importance` (par défaut `false`) et `permutation_repeats` (1–100, par défaut `10`) contrôlent cette fonction ; les anciennes configurations sans ces clés restent désactivées. Le moteur est dans `psyml.evaluation.permutation`, l’écriture des artefacts dans `psyml.reporting.permutation`. Le runner ne confie au moteur que le Pipeline de pli externe choisi à l’intérieur et ses lignes de test, puis écrit `interpretations/<validation>/` une fois la sélection figée. Les résultats sont séparés par validation (`dict[validation, list[record]]`) ; un enregistrement en échec garde `status=failed` et `error_type/error` sans inventer de variables. `result.json.permutation`, `analysis_manifest.json.interpretations` et les rapports Methods/reproductibilité n’indexent que des fichiers existants. La régression du noyau est dans `tests/test_permutation*.py` ; l’interface et l’affichage sont dans `gui/scripts/permutation_ui.gd` avec la régression `gui/tests/test_permutation.gd` ; `examples/quickstart/*_permutation_config.json` fournit un test de fumée importable. Laisser désactivé par défaut et ne pas modifier la sélection, le découpage ni les métriques.

## Comportements à préserver

- Ajuster encodage, imputation et mise à l’échelle sur la partition d’entraînement pertinente. Choisir familles/paramètres dans les partitions internes, jamais via le classement externe. Justifier les changements scientifiques au-delà de la réussite des tests.
- `primary_validation: null` produit des résultats complets séparés ou des erreurs enregistrées. Aucun gagnant global ni score principal à la racine, aucune sélection automatique du meilleur score.
- Coordonner les modifications de configuration entre classes, schémas, protocole, importation/sauvegarde GUI et tests. Préserver compatibilité, paramètres, candidats, ordre des variables et choix des figures.
- Utiliser les boîtes de dialogue natives du système. Vérifier le contraste au survol, au focus, à la sélection et dans les états désactivés des contrôles personnalisés.
- Actualiser les trois langues, le README, les guides et les captures correspondantes. Changer de langue ne doit pas changer l’analyse. Le README précise les limites linguistiques des figures et erreurs brutes.
- Enregistrer les versions dans `analysis_manifest.json`. Une modification de dépendances implique de vérifier `uv.lock`, rapports, métadonnées intégrées et licences.

## Vérification et contributions

[TESTING.md](TESTING.md) décrit les contrôles de régression et vérifications manuelles des développeurs ; ils ne sont pas exigés des utilisateurs du GUI. Adaptez les contrôles aux changements, inspectez l’interface réellement et vérifiez les méthodes avec de petits jeux contrôlables. Utilisez uniquement des exemples synthétiques ou partageables publiquement.

Une PR doit expliquer problème, comportement obtenu, vérifications et limites. Évitez les refactorisations sans rapport ; explicitez les conséquences scientifiques, de compatibilité ou de dépendances. Les contributions suivent [Apache-2.0](../LICENSE). N’envoyez jamais de données de participants, documents non publiés ou identifiants. Les commandes de développement ne sont pas des étapes obligatoires pour les chercheurs.

## Extension facultative d'explication

La fonctionnalité d'explication d'un échantillon dépend de `shap`, `numba` et `llvmlite`, exclus de l'installation par défaut afin de préserver le démarrage à froid et la taille du paquet pour l'analyse et la prédiction ordinaires. Installer uniquement si nécessaire :

```bash
uv sync --extra explain
uv pip install -e ".[explain]"   # équivalent pip/venv
```

`pyproject.toml` fixe les versions SHAP adaptées à Python (3.10 → 0.49.x, 3.11 → 0.51.x, 3.12 → 0.52.x) ; `uv.lock` les enregistre sans mettre à jour scikit-learn ni d'autres dépendances. `tools/build_native.py` intègre shap/numba/llvmlite au noyau, copie les notices maintenues dans `tools/licenses/` vers le répertoire `licenses/` du paquet et `--explain-smoke` vérifie l'explication et la reconstruction en classification/régression.

## Coefficients ajustés (sans dépendance supplémentaire)

[coefficients.py](../src/psyml/models/coefficients.py) lit `coef_`/`intercept_` uniquement depuis un pipeline PsyML `preprocess`+`model` déjà ajusté. Il construit une correspondance exacte variable transformée/colonne source/catégorie à partir de `ColumnTransformer.output_indices_` et de chaque sous-étape (imputer `statistics_`, scaler `mean_/scale_` ou `min_/scale_/data_min_/data_max_`, OneHotEncoder `categories_`), puis vérifie la reconstruction de `predict` (régression) ou `decision_function` (classification) via le même transform sur les lignes fournies (atol 1e-7 / rtol 1e-6). Il n'ajuste jamais, ne modifie pas le modèle, ne revient pas dans la sélection et ne convertit pas vers les unités brutes. Le rapport consigne aussi `input_features`/`dropped_features` (colonnes entièrement manquantes avec raison, index d'origine, stratégie), `encoding.per_source` (catégories par colonne et `drop_idx_`) et la source des dtypes d'entraînement (métadonnées ou explicitement inconnue). Avec des lignes fournies, un échec (tolérance/forme/non fini) renvoie `status=error` et refuse de publier un artefact de succès ; sans lignes, le rapport reste explicitement non vérifié, et CLI/GUI distinguent les deux états. Le runner écrit CSV/JSON/notes sous `coefficients/` ; la commande CLI est `psyml coefficients` (trust/hash/version et `model_input` réutilisés, écriture seulement dans un dossier nouveau/vide, JSON en dernier). Le chemin modèle chargé vérifie la provenance PsyML (`psyml_version`/`fit_scope`) et le type d'estimateur ; un modèle inconnu donne une raison précise et la prédiction ordinaire n'est pas affectée. Tests : `tests/test_coefficients.py`, `tests/test_coefficients_cli.py` et `gui/tests/test_coefficients.gd` ; `--coefficients-smoke` vérifie l'extraction en classification/régression dans le paquet.

## Construction et publication

[build_native.py](../tools/build_native.py) utilise PyInstaller pour le noyau et Godot pour l’interface, sur le système cible avec les modèles d’export correspondants. Cibles : macOS avec puce Apple et Windows x64. Une construction effectuée sous macOS ne valide pas Windows.

```bash
uv sync --locked --group dev --group build --extra explain
uv run --locked --group build --extra explain python tools/build_native.py --output-dir dist/v0.3.0 \
    --permutation-smoke --explain-smoke --coefficients-smoke
```

Le script reconstruit le dossier de sortie de même nom dans `dist/`, vérifie classification et régression avec l’environnement intégré, puis crée un ZIP et son SHA-256. `--reuse-core` sert uniquement au débogage local du GUI quand noyau et dépendances sont inchangés ; reconstruisez intégralement avant livraison. Vérifiez versions, verrouillage, architecture, licences, démarrage après extraction et dialogues natifs. Sans signature commerciale/notarisation, le système peut afficher une alerte.

Avant la construction, le script vérifie le système, Python natif 64 bits et les en-têtes des exécutables Python/Godot ; après export, il vérifie que le GUI et le noyau gelé correspondent à la cible annoncée (Mach-O arm64 ou PE x64). Les commandes ci-dessus conservent l’extra explain à l’installation et à l’exécution, et lancent les trois tests intégrés optionnels requis pour la livraison. BUILD.json consigne l’état initial des sources, le commit, le SHA-256 de uv.lock et l’état final après les tests. Toute nouvelle modification des sources, du commit ou du verrouillage interrompt l’empaquetage. La liste des changements de sources autorisés après construction est vide : dist/, tmp/ et gui/.godot/ sont déjà ignorés. Examinez et commitez toute modification de source/import Godot avant de reconstruire ; ne dispensez pas globalement le GUI du contrôle. Un arbre initialement modifié ou un noyau réutilisé sert seulement au débogage local et échoue à la vérification de publication.

**L’export natif passe uniquement par `tools/build_native.py`.** Les champs de version macOS/Windows de `gui/export_presets.cfg` (`application/short_version`, `application/version`, `application/file_version`, `application/product_version`) contiennent les jetons `@PSYML_MACOS_VERSION@` / `@PSYML_WINDOWS_VERSION@`, pas des numéros publiables ; un export direct depuis l’éditeur Godot échoue ou écrit de mauvaises versions. `build_native.py` dérive les versions numériques de la constante unique de `src/psyml/__init__.py` le temps d’un export (la version officielle `0.3.0` comme la version de développement `0.3.0.dev0` donnent macOS `0.3.0`, Windows `0.3.0.0`) puis restaure le modèle dans un bloc `finally` : ni un succès ni un échec ne laisse de preset modifié. Déclenchez donc toujours l’export natif via ce script plutôt que d’utiliser directement le preset Godot.

[Core CI](../.github/workflows/ci.yml) couvre trois systèmes. Le [workflow autonome](../.github/workflows/native-test-build.yml) construit Windows sur déclenchement manuel ou push vers `desktop-test`. Un push consomme des ressources de construction ; utilisez cette branche lorsqu’un paquet de test est nécessaire. Il conserve les artefacts sans créer de release.

### Pièces jointes de publication et dossier de partage local

La Release 0.3.0 ne reçoit que les ZIP Windows-x64 et macOS-arm64, avec des notes chinoises, anglaises et françaises (voir [RELEASE_NOTES_0.3.0.md](RELEASE_NOTES_0.3.0.md)). Les scripts produisent toujours des SHA-256 pour vérification locale ; ne publiez ni ces fichiers ni un ZIP de sources supplémentaire, et vérifiez le candidat localement avec `tools/verify_release_artifacts.py`. GitHub fournit ses téléchargements Source code. `tools/package_release.py` est un outil facultatif d’archivage local exigeant des sources propres et des PDF actuels ; sa sortie ne fait pas partie des applications publiées. Référence historique : la Release v0.2.0 suivait les mêmes règles.

Vérifiez d’abord README et guide de référence pour 0.3.0, puis produisez les PDF. Remplacez le chemin ci-dessous par une police TrueType chinoise autorisant l’intégration. `dist/v0.3.0/docs/sources.json` conserve les empreintes des sources de ce candidat ; régénérez et inspectez visuellement toutes les pages après modification. L’étiquette PDF par défaut vient de la version du noyau (`v0.3.0`) ; pour régénérer un document historique, passez explicitement `--label v0.2.0 --base-ref v0.2.0`, et le fichier est alors marqué comme historique plutôt que comme version courante.

```bash
uv run --with reportlab python tools/build_release_pdfs.py --font /path/to/chinese-font.ttf \
    --output-dir dist/v0.3.0/docs
```

Placez les deux ZIP et leurs fichiers .sha256, issus du même commit propre, dans `dist/v0.3.0/`. Après génération et inspection des PDF, créez `SHA256SUMS` avec l’empreinte SHA-256 et le chemin relatif des deux ZIP et des deux PDF, puis lancez le vérificateur complet. Cette commande Python multiplateforme écrit les quatre entrées requises :

```bash
uv run python -c "import hashlib; from pathlib import Path; d=Path('dist/v0.3.0'); names=['PsyML-Toolkit-0.3.0-macOS-arm64.zip','PsyML-Toolkit-0.3.0-Windows-x64.zip','docs/README_ZH.pdf','docs/RESEARCHER_GUIDE_ZH.pdf']; (d/'SHA256SUMS').write_text(''.join(hashlib.sha256((d/n).read_bytes()).hexdigest()+'  '+n+'\n' for n in names), encoding='utf-8')"
uv run python tools/verify_release_artifacts.py --directory dist/v0.3.0 --platform all
```

`tools/verify_release_artifacts.py` lit le contenu réel des ZIP (version/commit/sources propres avant et après construction dans BUILD.json, ressources/licences/environnement requis non vides, architecture réelle des exécutables noyau et GUI, chemins sûrs), les SHA-256 correspondants et, en mode `all`, les deux PDF chinois non vides et le manifeste `SHA256SUMS` ; il ne se fie jamais à une chaîne de succès dans un journal. Le mode `all` exige les deux ZIP de plateforme, `docs/README_ZH.pdf`, `docs/RESEARCHER_GUIDE_ZH.pdf`, `docs/sources.json` et un `SHA256SUMS` listant les quatre artefacts dans `dist/v0.3.0/` ; le mode mono-plateforme ne demande que le ZIP et le `.sha256` de cette plateforme, ce qui permet de valider le paquet Mac avant l’arrivée du téléchargement Windows.

Pour un dossier de partage local demandé séparément, générez les PDF actuels dans `output/pdf/`, répertoire lu par `package_researcher_share.py`. Cette destination est distincte des PDF du candidat dans `dist/v0.3.0/docs/` :

```bash
uv run --with reportlab python tools/build_release_pdfs.py --font /path/to/chinese-font.ttf \
    --output-dir output/pdf
uv run python tools/package_researcher_share.py --windows-zip dist/v0.3.0/PsyML-Toolkit-0.3.0-Windows-x64.zip
```

Le script de partage lit la version actuelle du noyau et crée `PsyML-Toolkit-Researcher-Share-v0.3.0.zip` à la racine. Il n’appelle aucune API de publication ; générez-le après confirmation séparée et conservez-le hors des pièces jointes de Release. Windows/ contient l’application, TestData/ les données et configurations, Documents/ les deux PDF chinois, et 从这里开始.txt explique les dossiers et renvoie les utilisateurs Mac vers GitHub. Déplacez ou sauvegardez tout dossier existant avant reconstruction. Régénérez les deux destinations PDF après modification des documents.

Pour changer la version, ne modifiez que `__version__` dans `src/psyml/__init__.py` (`pyproject.toml` est dynamique et suit automatiquement ; `gui/export_presets.cfg` garde ses jetons et `tools/build_native.py` dérive les valeurs numériques à l’export). Vérifiez aussi uv.lock, `tools/build_native.py`, `tools/NATIVE_START_HERE.txt`, versions/liens du générateur PDF et notes trilingues (`docs/RELEASE_NOTES_<version>.md`). Inspectez commit et états des sources dans BUILD.json, puis archives et empreintes locales avec `tools/verify_release_artifacts.py`. Les tests intégrés couvrent l’entraînement classification/régression, l’enregistrement/chargement, dix nouvelles prédictions par tâche (écrites dans `predictions.csv` du dossier de cette exécution) et le fait que l’action d’ouverture cible exactement ce dossier ; ils ne remplacent pas l’examen d’une vraie fenêtre. Le CLI `export-table` et la lecture/écriture multi-format restent pris en charge et ne font pas partie de ce contrôle intégré. Faites un commit par fonctionnalité indépendante terminée et poussez immédiatement, sans accumulation.


## Ouvrir l’application

Consultez [Releases](https://github.com/GuGuGu-coocoo/PsyMl_Toolkit/releases) pour les versions et plateformes disponibles. Les ZIP autonomes v0.3.0 (`macOS-arm64`, `Windows-x64`) sont construits depuis le même commit ; les fichiers et plateformes réellement disponibles sont ceux listés sur la page [Release v0.3.0](https://github.com/GuGuGu-coocoo/PsyMl_Toolkit/releases/tag/v0.3.0), et les versions officielles antérieures restent sur la même page Releases. Ces applications incluent leur environnement. Les archives Source code générées par GitHub ne contiennent que les sources ; leur installation est décrite dans le [guide de développement](../docs/DEVELOPMENT_FR.md).

**Sources et paquet téléchargé.** Cette copie des sources correspond à la version officielle **0.3.0** (source unique) et contient les fonctions et améliorations ajoutées après le paquet v0.2.0 (importance par permutation, contrôle des données et interprétation, SHAP d’un échantillon, coefficients ajustés, ainsi que des améliorations d’interface et de flux de sortie). Les paquets téléchargés et PDF de distribution suivent leur propre version : fiez-vous aux fichiers listés sur la page Releases et aux documents et à l’interface du paquet utilisé ; les paquets v0.2.0 et antérieurs ne contiennent ni ces fonctions ni ces correctifs : interface, disposition des sorties et captures restent l’ancienne version. La version n’a qu’une source maintenue : `__version__` dans `src/psyml/__init__.py` (`pyproject.toml` est dynamique) ; le `BUILD.json` autonome est généré à partir de la même constante par `tools/build_native.py`. Sous macOS, les sources se lancent en double-cliquant sur `Launch PsyML.command` à la racine (dépendances : [guide de développement](../docs/DEVELOPMENT_FR.md)).

- **macOS (puce Apple)** : décompressez entièrement l’archive correspondante puis double-cliquez sur `PsyML Toolkit.app`.
- **Windows (Intel/AMD x64)** : décompressez entièrement l’archive puis double-cliquez sur `PsyML Toolkit.exe`. Conservez le dossier `core` adjacent ; ne déplacez pas seulement l’EXE.
- Python, dépendances scientifiques et moteur de l’interface sont intégrés. Aucun terminal, installation supplémentaire ou téléchargement Internet n’est requis. Les fichiers de test sont réunis dans `examples/quickstart/` ; commencez par **Importer une configuration…**.
- Une petite étiquette sous le nom de l’application affiche la version courante : un paquet autonome lit son `BUILD.json`, une exécution depuis les sources lit `__version__` dans `src/psyml/__init__.py` (`pyproject.toml` est dynamique et lit la même constante) ; la version officielle `0.3.0` s’affiche telle quelle, une version de développement `0.3.0.dev0` s’affiche `0.3.0-dev`, et la valeur n’est pas codée en dur.
- Les applications n’ont pas encore de signature commerciale ni de notarisation. Le système peut demander une confirmation au premier lancement : **Réglages Système → Confidentialité et sécurité** sous macOS, ou une alerte de sécurité sous Windows. Vérifiez la provenance et respectez la politique informatique de votre établissement.

## Vérifications depuis les sources

Un paquet autonome et une copie des sources peuvent contenir des correctifs différents. Les cinq points ci-dessous vous aident à vérifier le comportement depuis les sources.

1. Lancez l'interface depuis la racine des sources (sous macOS, double-cliquez sur `Launch PsyML.command`) ; l'installation des dépendances est décrite dans le [guide de développement](DEVELOPMENT_FR.md). Les paquets autonomes n'incluent pas l'environnement de test. Importez une configuration de classification ou de régression de `examples/quickstart/` et exécutez-la une fois.
2. **Étiquette de version :** une petite étiquette sous le nom de l'application doit afficher le numéro de version courant `0.3.0`. La source unique des sources est `__version__` dans `src/psyml/__init__.py` (`pyproject.toml` est dynamique) ; un paquet autonome lit son `BUILD.json`, généré à partir de la même constante, et une version de développement `0.3.0.dev0` s'affiche `0.3.0-dev` tandis que la version officielle `0.3.0` s'affiche telle quelle.
3. **Dossiers de sortie et anciens résultats :** une nouvelle exécution d'entraînement de la page 2 apparaît sous `training/run_*` dans la racine choisie ; prédiction, SHAP et coefficients de la page 4 arrivent dans de nouveaux dossiers `run_*` sous `prediction/`, `explanation/` et `coefficients/` dans la racine partagée, sans écraser de fichier existant ni écrire dans le dossier de données masqué de l'application. Les anciens dossiers d'entraînement `run_*` directement sous la racine s'ouvrent toujours en place, sans réécriture de leur contenu.
4. **Actions de la page 4 :** les trois blocs proposent **Ouvrir le dossier de résultats** (prédiction : **Ouvrir le dossier des prédictions**, qui ouvre le dossier d'exécution, pas le CSV) et **Ouvrir l'image en cascade**. La sortie de prédiction est un `predictions.csv` directement ouvrable.
5. **Appartenance du défilement et état de finalisation :** un geste commencé sur la page continue de la faire défiler au passage sur un tableau imbriqué, seul un geste commencé sur le tableau fait défiler celui-ci, et une pause d'environ 250 ms démarre un nouveau geste pouvant choisir une autre couche (le verrouillage ne concerne que la molette et le balayage). Pendant l'écriture finale des résultats, l'état doit afficher « Finalisation et écriture des résultats… » avec une barre de progression non pleine ; la page des résultats ne s'ouvre qu'après `completed`. Utilisez **Copier l'erreur complète** pour signaler un problème.

Ce guide décrit le comportement des sources **0.3.0** (source unique), avec les fonctions et améliorations ajoutées après v0.2.0 (importance par permutation, contrôle des données et interprétation, SHAP d’un échantillon, coefficients ajustés, ainsi que des améliorations d’interface et de flux de sortie). Les paquets autonomes et PDF de distribution suivent leur propre version : voir les fichiers listés sur la page Releases ; les paquets v0.2.0 et antérieurs et leurs PDF ne contiennent ni ces fonctions ni ces correctifs : l’interface et la disposition des sorties peuvent donc différer des sources. La version n’a qu’une seule source maintenue : la constante `__version__` de `src/psyml/__init__.py`. `pyproject.toml` la lit via les métadonnées dynamiques, le `BUILD.json` autonome est généré par `tools/build_native.py` à partir de la même constante, et l’interface affiche la même valeur (version officielle `0.3.0` telle quelle, version de développement `0.3.0.dev0` affichée `0.3.0-dev`). Consultez `analysis_manifest.json` dans chaque sortie d’analyse pour les versions d’exécution et de dépendances, et ne déduisez pas le contenu du paquet téléchargé du titre de ce guide.

## Prédiction en ligne de commande

```bash
psyml predict --model output/model/best_ridge.joblib --input new_data.xlsx --output predictions.xlsx --trust-model
```

charger uniquement des modèles PsyML de confiance : joblib/pickle peut exécuter du code ; `--trust-model` confirme la source. Utiliser `--check-only` sans `--output` pour vérifier la compatibilité. Les prédicteurs sont remis dans l’ordre d’entraînement ; colonnes absentes, nombres invalides et valeurs manquantes sans imputation bloquent la prédiction. Toutes les colonnes originales (cible comprise) et l’ordre des lignes sont conservés. La régression ajoute `predicted_value`, la classification `predicted_class` et les probabilités natives disponibles. Un suffixe numérique évite les collisions. Répéter `--feature` dans l’ordre attendu si les noms manquent. Les 9 formats d’entrée restent disponibles ; export CSV, TSV, XLSX, SAV, DTA, XPT et Parquet. XLS/SAS7BDAT sont en lecture seule : choisir XLSX. Les restrictions de noms/types des formats statistiques produisent une erreur explicite ; choisir XLSX/Parquet. L’extension de sortie fixe le format CLI ; pas d’écrasement par défaut.

Le noyau d’apprentissage automatique a été écrit par l’auteur du projet ; l’interface Godot a été développée avec une assistance IA. Celle-ci ne remplace ni la revue humaine du code ni le jugement scientifique.
