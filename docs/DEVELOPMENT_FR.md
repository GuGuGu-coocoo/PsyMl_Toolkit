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

[Core CI](../.github/workflows/ci.yml) couvre trois systèmes. Le [workflow autonome](../.github/workflows/native-test-build.yml) construit Windows sur déclenchement manuel ou push vers `desktop-test`. **Ne poussez pas sur cette branche lorsque l’empaquetage est suspendu.** Il conserve les artefacts sans créer de release.

`tools/package_release.py` prépare l’ancienne distribution source, pas les applications autonomes. `tools/build_release_pdfs.py` génère les deux PDF chinois à vérifier page par page ; ils appartiennent à une archive de partage distincte, pas aux pièces jointes de la nouvelle release. Construction, acceptation utilisateur et publication sont séparées ; aucune publication de release n’est automatique.
