# Guide de développement

[README](../README.md#french) · [中文](DEVELOPMENT_ZH.md) · [English](DEVELOPMENT_EN.md)

Ce guide concerne la modification, la maintenance et la construction de PsyML. Les chercheurs utilisent l’interface sans outils de développement ni ces commandes. La version du code figure dans [pyproject.toml](../pyproject.toml) ; Releases indique les versions publiées.

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

## Construction et publication

[build_native.py](../tools/build_native.py) utilise PyInstaller pour le noyau et Godot pour l’interface, sur le système cible avec les modèles d’export correspondants. Cibles : macOS avec puce Apple et Windows x64. Une construction Mac ne valide pas Windows.

```bash
uv sync --locked --group dev --group build
uv run --group build python tools/build_native.py
```

Le script reconstruit le dossier de sortie de même nom dans `dist/`, vérifie classification et régression avec l’environnement intégré, puis crée un ZIP et son SHA-256. `--reuse-core` sert uniquement au débogage local du GUI quand noyau et dépendances sont inchangés ; reconstruisez intégralement avant livraison. Vérifiez versions, verrouillage, architecture, licences, démarrage après extraction et dialogues natifs. Sans signature commerciale/notarisation, le système peut afficher une alerte.

[Core CI](../.github/workflows/ci.yml) couvre trois systèmes. Le [workflow autonome](../.github/workflows/native-test-build.yml) construit Windows sur déclenchement manuel ou push vers `desktop-test`. Un push consomme des ressources de construction ; utilisez cette branche lorsqu’un paquet de test est nécessaire. Il conserve les artefacts sans créer de release.

### Pièces jointes de publication et dossier de partage local

La Release 0.2.0 ne reçoit que les ZIP Windows-x64 et macOS-arm64, avec des notes chinoises, anglaises et françaises. Les scripts produisent toujours des SHA-256 pour vérification locale ; ne publiez ni ces fichiers ni un ZIP de sources supplémentaire. GitHub fournit ses téléchargements Source code. `tools/package_release.py` est un outil facultatif d’archivage local exigeant des sources propres et des PDF actuels ; sa sortie ne fait pas partie des applications publiées.

Vérifiez d’abord README et guide de référence pour 0.2.0, puis produisez les PDF. Remplacez le chemin ci-dessous par une police TrueType chinoise autorisant l’intégration. `output/pdf/sources.json` conserve les empreintes des sources ; régénérez et inspectez visuellement toutes les pages après modification.

```bash
uv run --with reportlab python tools/build_release_pdfs.py --font /path/to/chinese-font.ttf
uv run python tools/package_researcher_share.py --windows-zip dist/PsyML-Toolkit-0.2.0-Windows-x64.zip
```

Le script de partage n’appelle aucune API de publication. Il crée `PsyML-Toolkit-Researcher-Share-v0.2.0.zip` à la racine pour partage direct uniquement ; **ne jamais le joindre à une Release**. Windows/ contient l’application, TestData/ les données et configurations, Documents/ les deux PDF chinois ; 从这里开始.txt décrit dossiers et étapes et renvoie les utilisateurs Mac vers GitHub. Déplacez ou sauvegardez un ancien dossier avant de reconstruire ; ne réutilisez pas de PDF périmés.

Pour changer la version, vérifiez pyproject.toml, src/psyml/__init__.py, uv.lock, gui/export_presets.cfg, tools/build_native.py, tools/NATIVE_START_HERE.txt, versions/liens du générateur PDF et notes trilingues. Inspectez commit et états des sources dans BUILD.json, puis archives et empreintes locales. Les tests intégrés couvrent entraînement classification/régression, enregistrement/chargement, dix nouvelles prédictions par tâche et export XLSX ; ils ne remplacent pas l’examen d’une vraie fenêtre. Faites un commit par fonctionnalité indépendante terminée et poussez immédiatement, sans accumulation.
