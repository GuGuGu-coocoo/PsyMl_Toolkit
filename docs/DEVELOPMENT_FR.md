# Guide de développement

[README](../README.md#french) · [中文](DEVELOPMENT_ZH.md) · [English](DEVELOPMENT_EN.md)

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

FR-007 : `psyml.data.profiling` est un helper pur ; `profile_columns` / `column_profile` / `category_summary` / `identifier_signals` construisent des métadonnées par colonne (valeurs non manquantes, valeurs uniques, ratio quasi unique, effectifs optionnels avec troncature et signaux d’identifiant justifiés). `protocol.dataframe_preview` n’attache des valeurs que si `include_sample=True` et n’en renvoie aucune par défaut ; l’interface `gui/scripts/data_check_ui.gd` consomme ces métadonnées sans estimer depuis les cinq premières lignes et ne supprime ni colonne ni rôle.

FR-009 : `build_interpretation` dans `psyml.reporting.interpretation` n’agrège que les preuves déjà calculées par le runner (procedure_results, plis par combinaison, tuning_rows, leaderboard, validation_summary) et n’ajoute aucun ajustement ; `write_interpretation_outputs` écrit `result_interpretation.json`, `interpretation_baseline_differences.csv` et `result_interpretation.md`, indexés par `result.json.artifacts`. En validation indépendante, `build_independent_interpretation` n’écrit qu’un aperçu/index racine. Le résumé GUI est dans `gui/scripts/result_interpretation_ui.gd`. Régression noyau : `tests/test_profiling.py`, `tests/test_interpretation.py` ; GUI : `gui/tests/test_data_check.gd`, `gui/tests/test_interpretation_results.gd`. La baseline ne compare qu’un dummy réussi sur la même validation, les mêmes plis et la même métrique, avec un signe fixe (positif = meilleur) ; les statistiques descriptives ne reviennent jamais dans la sélection ou le réglage. FR-008 ne modifie que les guides trilingues, sans GUI ni algorithme de découpage.

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

La fonctionnalité FR-004 dépend de `shap`, `numba` et `llvmlite`, exclus de l'installation par défaut afin de préserver le démarrage à froid et la taille du paquet pour l'analyse et la prédiction ordinaires. Installer uniquement si nécessaire :

```bash
uv sync --extra explain
uv pip install -e ".[explain]"   # équivalent pip/venv
```

`pyproject.toml` fixe les versions SHAP adaptées à Python (3.10 → 0.49.x, 3.11 → 0.51.x, 3.12 → 0.52.x) ; `uv.lock` les enregistre sans mettre à jour scikit-learn ni d'autres dépendances. `tools/build_native.py` intègre shap/numba/llvmlite au noyau, copie leurs licences dans `tools/licenses/` et `--explain-smoke` vérifie l'explication et la reconstruction en classification/régression. Windows n'est pas exécuté sur ce Mac.

## Coefficients ajustés (FR-005, sans dépendance supplémentaire)

[coefficients.py](../src/psyml/models/coefficients.py) lit `coef_`/`intercept_` uniquement depuis un pipeline PsyML `preprocess`+`model` déjà ajusté. Il construit une correspondance exacte variable transformée/colonne source/catégorie à partir de `ColumnTransformer.output_indices_` et de chaque sous-étape (imputer `statistics_`, scaler `mean_/scale_` ou `min_/scale_/data_min_/data_max_`, OneHotEncoder `categories_`), puis vérifie la reconstruction de `predict` (régression) ou `decision_function` (classification) via le même transform sur les lignes fournies (atol 1e-7 / rtol 1e-6). Il n'ajuste jamais, ne modifie pas le modèle, ne revient pas dans la sélection et ne convertit pas vers les unités brutes. Le rapport consigne aussi `input_features`/`dropped_features` (colonnes entièrement manquantes avec raison, index d'origine, stratégie), `encoding.per_source` (catégories par colonne et `drop_idx_`) et la source des dtypes d'entraînement (métadonnées ou explicitement inconnue). Avec des lignes fournies, un échec (tolérance/forme/non fini) renvoie `status=error` et refuse de publier un artefact de succès ; sans lignes, le rapport reste explicitement non vérifié, et CLI/GUI distinguent les deux états. Le runner écrit CSV/JSON/notes sous `coefficients/` ; la commande CLI est `psyml coefficients` (trust/hash/version et `model_input` réutilisés, écriture seulement dans un dossier nouveau/vide, JSON en dernier). Le chemin modèle chargé vérifie la provenance PsyML (`psyml_version`/`fit_scope`) et le type d'estimateur ; un modèle inconnu donne une raison précise et la prédiction ordinaire n'est pas affectée. Tests : `tests/test_coefficients.py`, `tests/test_coefficients_cli.py` et `gui/tests/test_coefficients.gd` ; `--coefficients-smoke` vérifie l'extraction en classification/régression dans le paquet.

## Construction et publication

[build_native.py](../tools/build_native.py) utilise PyInstaller pour le noyau et Godot pour l’interface, sur le système cible avec les modèles d’export correspondants. Cibles : macOS avec puce Apple et Windows x64. Une construction Mac ne valide pas Windows.

```bash
uv sync --locked --group dev --group build
uv run --group build python tools/build_native.py
```

Le script reconstruit le dossier de sortie de même nom dans `dist/`, vérifie classification et régression avec l’environnement intégré, puis crée un ZIP et son SHA-256. `--reuse-core` sert uniquement au débogage local du GUI quand noyau et dépendances sont inchangés ; reconstruisez intégralement avant livraison. Vérifiez versions, verrouillage, architecture, licences, démarrage après extraction et dialogues natifs. Sans signature commerciale/notarisation, le système peut afficher une alerte.

**L’export natif passe uniquement par `tools/build_native.py`.** Les champs de version macOS/Windows de `gui/export_presets.cfg` (`application/short_version`, `application/version`, `application/file_version`, `application/product_version`) contiennent les jetons `@PSYML_MACOS_VERSION@` / `@PSYML_WINDOWS_VERSION@`, pas des numéros publiables ; un export direct depuis l’éditeur Godot échoue ou écrit de mauvaises versions. `build_native.py` dérive les versions numériques de la constante unique de `src/psyml/__init__.py` le temps d’un export (la version officielle `0.3.0` comme la version de développement `0.3.0.dev0` donnent macOS `0.3.0`, Windows `0.3.0.0`) puis restaure le modèle dans un bloc `finally` : ni un succès ni un échec ne laisse de preset modifié. Déclenchez donc toujours l’export natif via ce script plutôt que d’utiliser directement le preset Godot.

[Core CI](../.github/workflows/ci.yml) couvre trois systèmes. Le [workflow autonome](../.github/workflows/native-test-build.yml) construit Windows sur déclenchement manuel ou push vers `desktop-test`. Un push consomme des ressources de construction ; utilisez cette branche lorsqu’un paquet de test est nécessaire. Il conserve les artefacts sans créer de release.

### Pièces jointes de publication et dossier de partage local

La Release 0.3.0 ne reçoit que les ZIP Windows-x64 et macOS-arm64, avec des notes chinoises, anglaises et françaises (voir [RELEASE_NOTES_0.3.0.md](RELEASE_NOTES_0.3.0.md)). Les scripts produisent toujours des SHA-256 pour vérification locale ; ne publiez ni ces fichiers ni un ZIP de sources supplémentaire, et vérifiez le candidat localement avec `tools/verify_release_artifacts.py`. GitHub fournit ses téléchargements Source code. `tools/package_release.py` est un outil facultatif d’archivage local exigeant des sources propres et des PDF actuels ; sa sortie ne fait pas partie des applications publiées. Référence historique : la Release v0.2.0 suivait les mêmes règles.

Vérifiez d’abord README et guide de référence pour 0.3.0, puis produisez les PDF. Remplacez le chemin ci-dessous par une police TrueType chinoise autorisant l’intégration. `output/pdf/sources.json` conserve les empreintes des sources ; régénérez et inspectez visuellement toutes les pages après modification. L’étiquette PDF par défaut vient de la version du noyau (`v0.3.0`) ; pour régénérer un document historique, passez explicitement `--label v0.2.0 --base-ref v0.2.0`, et le fichier est alors marqué comme historique plutôt que comme version courante.

```bash
uv run --with reportlab python tools/build_release_pdfs.py --font /path/to/chinese-font.ttf \
    --output-dir dist/v0.3.0/docs
uv run python tools/verify_release_artifacts.py --directory dist/v0.3.0 --platform all
uv run python tools/package_researcher_share.py --windows-zip dist/PsyML-Toolkit-0.2.0-Windows-x64.zip
```

`tools/verify_release_artifacts.py` lit le contenu réel des ZIP (version/commit/sources propres dans BUILD.json, ressources du noyau et de l’application, licences requises, chemins sûrs), les SHA-256 correspondants et, en mode `all`, les deux PDF chinois non vides et le manifeste `SHA256SUMS` ; il ne se fie jamais à une chaîne de succès dans un journal. Le mode `all` exige les deux ZIP de plateforme, `docs/README_ZH.pdf`, `docs/RESEARCHER_GUIDE_ZH.pdf`, `docs/sources.json` et un `SHA256SUMS` listant les quatre artefacts dans `dist/v0.3.0/` ; le mode mono-plateforme ne demande que le ZIP et le `.sha256` de cette plateforme, ce qui permet de valider le paquet Mac avant l’arrivée du téléchargement Windows.

Le script de partage n’appelle aucune API de publication. Il crée `PsyML-Toolkit-Researcher-Share-v0.2.0.zip` à la racine pour partage direct uniquement ; **ne jamais le joindre à une Release** ; ce n’est pas un fichier de release, sa génération doit être confirmée séparément. Dans le dossier v0.2.0 (le dernier généré), Windows/ contient l’application, TestData/ les données et configurations, Documents/ les deux PDF chinois ; 从这里开始.txt décrit dossiers et étapes et renvoie les utilisateurs Mac vers GitHub. Déplacez ou sauvegardez un ancien dossier avant de reconstruire ; ne réutilisez pas de PDF périmés.

Pour changer la version, ne modifiez que `__version__` dans `src/psyml/__init__.py` (`pyproject.toml` est dynamique et suit automatiquement ; `gui/export_presets.cfg` garde ses jetons et `tools/build_native.py` dérive les valeurs numériques à l’export). Vérifiez aussi uv.lock, `tools/build_native.py`, `tools/NATIVE_START_HERE.txt`, versions/liens du générateur PDF et notes trilingues (`docs/RELEASE_NOTES_<version>.md`). Inspectez commit et états des sources dans BUILD.json, puis archives et empreintes locales avec `tools/verify_release_artifacts.py`. Les tests intégrés couvrent l’entraînement classification/régression, l’enregistrement/chargement, dix nouvelles prédictions par tâche (écrites dans `predictions.csv` du dossier de cette exécution) et le fait que l’action d’ouverture cible exactement ce dossier ; ils ne remplacent pas l’examen d’une vraie fenêtre. Le CLI `export-table` et la lecture/écriture multi-format restent pris en charge et ne font pas partie de ce contrôle intégré. Faites un commit par fonctionnalité indépendante terminée et poussez immédiatement, sans accumulation.
