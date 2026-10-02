# Régression California Housing : télécharger, exécuter et comparer

[中文](CALIFORNIA_VALIDATION_ZH.md) · [English](CALIFORNIA_VALIDATION_EN.md) · [README](../README.md)

Ce cas prédit la valeur médiane des logements de 20 640 zones de recensement californiennes en 1990 à partir de huit variables, dont le revenu et l’âge des logements. Il vérifie l’accord entre PsyML et un programme scikit-learn écrit séparément. Ces données historiques ne permettent pas d’établir les prix actuels.

## Télécharger et exécuter dans l’application

- [CSV pour l’analyse : california_housing.csv, 2,54 Mo](https://raw.githubusercontent.com/GuGuGu-coocoo/PsyMl_Toolkit/main/examples/public/downloads/california_housing.csv). Il est déjà converti selon la transformation de référence et prêt à importer.
- [Configuration : california_config.json](https://raw.githubusercontent.com/GuGuGu-coocoo/PsyMl_Toolkit/a1450dfc374b8a39109c41f2548fdc0dbcad23c1/examples/public/california_random_nested_v1/california_config.json). C’est la configuration originale v1 avec `verbose=0`, utilisée pour vérifier les sources corrigées.
- [Données officielles originales, scripts, licence et empreintes](../examples/public/downloads/README.md). Le script de conversion est public et consultable ; son exécution n’est pas nécessaire pour utiliser ce cas.

Enregistrez le CSV et le JSON dans un même dossier local. Si le navigateur affiche leur contenu, utilisez « Enregistrer sous » en conservant les extensions.

L’application disponible reste v0.3.0 ; aucun installateur contenant les correctifs source ultérieurs n’est encore disponible. La référence historique utilise l’environnement source indiqué sur cette page et ne certifie pas les paquets existants. Vérifier l’application corrigée nécessite son installateur. Les plateformes proposées figurent dans [Releases](https://github.com/GuGuGu-coocoo/PsyMl_Toolkit/releases).

1. Ouvrez PsyML et cliquez sur « Importer une configuration… » à la page 1. Choisissez `california_config.json`. Si le logiciel demande les données, sélectionnez `california_housing.csv` ; vérifiez le chemin et utilisez « Parcourir… » pour le choisir à nouveau si nécessaire.
2. Vérifiez : 20 640 lignes ; régression ; cible `MedHouseVal` ; huit prédicteurs ; aucun groupe ; 5 plis K-fold externes et 3 internes ; graine `20261002` ; sélection selon le RMSE ; candidats Dummy, Ridge et Random Forest. Tous les noms de variables figurent plus bas.
3. À la page 2, choisissez un dossier local et cliquez sur « Exécuter l’analyse ». Conservez les candidats, paramètres et graine du fichier pour comparer avec la référence.
4. À la page 3, consultez le RMSE et ouvrez le dossier complet. Conservez `config.json`, `metrics.csv`, `metrics_summary.csv`, `fold_metrics.csv`, les prédictions et les versions de l’environnement.

Chacun des cinq tests externes met à l’écart 4 128 lignes. Les données restantes sont divisées en trois pour comparer modèles et paramètres avant de tester le réglage retenu. C’est la validation imbriquée. La prédiction de test de chaque ligne provient d’un modèle entraîné sans cette ligne ; leur ensemble constitue les prédictions hors pli (OOF).

## Chiffres, configuration et fichiers de résultats

Ces valeurs proviennent de la référence indépendante originale v1 ; les exports réels de l’interface corrigée lui ont été comparés le 2026-10-02. Toutes les lignes utilisent le même [california_config.json](https://raw.githubusercontent.com/GuGuGu-coocoo/PsyMl_Toolkit/a1450dfc374b8a39109c41f2548fdc0dbcad23c1/examples/public/california_random_nested_v1/california_config.json) et `california_housing.csv` ; il n’y a pas de configuration distincte à télécharger pour chaque métrique.

| Valeur de référence | Sens | Où comparer |
| --- | --- | --- |
| 0.5339815958325378 | Résultat principal : moyenne des RMSE des cinq tests externes. La racine de l’erreur quadratique moyenne diminue lorsque les prédictions se rapprochent des valeurs observées, en unités de 100 000 USD | `rmse` dans `metrics.csv` ; [table de référence](../examples/public/california_random_nested_v1/expected/historical_metrics_summary.csv), `rmse/mean` |
| 0.01850680156369903 | Écart-type des cinq RMSE, décrivant leur dispersion ; ce n’est pas un intervalle de confiance | `metrics_summary.csv` ; [même référence](../examples/public/california_random_nested_v1/expected/historical_metrics_summary.csv), `rmse/std` |
| 0.3610547401259507 | Moyenne des cinq erreurs absolues moyennes (MAE), dans les mêmes unités | `mae` dans `metrics.csv` ; [même référence](../examples/public/california_random_nested_v1/expected/historical_metrics_summary.csv), `mae/mean` |
| 0.7856663784093894 | Moyenne des R² de test, qui mesure l’ajustement relativement à la variation de la cible ; ce n’est pas « 78,6 % d’exactitude » | `r2` dans `metrics.csv` ; [même référence](../examples/public/california_random_nested_v1/expected/historical_metrics_summary.csv), `r2/mean` |
| 0.5343022051161513 | RMSE recalculé par la référence indépendante sur les 20 640 prédictions réunies. Il n’est pas directement exporté dans `metrics.csv` et diffère de la moyenne par pli | [Table des prédictions réunies](../examples/public/california_random_nested_v1/expected/historical_pooled_metrics.csv), `procedure/rmse` |
| 1.153954483920011 / 0.7273658464149191 | Moyennes des RMSE externes de Dummy / Ridge dans la même configuration. Dummy prédit la moyenne d’entraînement ; Ridge est une régression linéaire régularisée | `model_comparison.csv` ; [référence par modèle et pli](../examples/public/california_random_nested_v1/expected/historical_family_fold_metrics.csv) |

Les cinq tests externes et le choix final ont retenu Random Forest. Les RMSE par pli et les autres métriques plus bas utilisent aussi cette configuration. Le modèle final apprend sur toutes les lignes ; ses prédictions sur ces mêmes lignes ne donnent pas un nouveau score de test indépendant.

## Vérification enregistrée de la configuration originale v1

[Relevé de vérification : empreintes de configuration et données, environnement, synthèse des 270 contrôles et périmètre](CALIFORNIA_REPAIRED_V1_RECORD.json).

Le 2026-10-02, l’interface Linux issue des sources corrigées a utilisé la configuration originale v1, avec l’entier `verbose=0`, pour importer, enregistrer, réimporter, entraîner, puis prédire dix lignes après chargement du modèle sauvegardé. Les 270 contrôles observables ont réussi sans la modification de compatibilité v1.1. Le RMSE externe moyen était de 0.5339815958325378. L’interface prévoyait 106 ajustements ; aucune trace séparée de chaque appel d’ajustement en production n’a été recueillie.

Le code applicatif testé est identique au commit public [948c451](https://github.com/GuGuGu-coocoo/PsyMl_Toolkit/commit/948c451bb0e401c7ffe1c9ab65439ebc3521031b). Le commit suivant, `a1450df`, protège seulement les fins de ligne des fichiers historiques. Cette exécution utilisait Linux x86_64, Python 3.12.14, scikit-learn 1.8.0, NumPy 2.3.5, pandas 2.2.3, SciPy 1.17.0 et Godot 4.6.3, avec un seul thread des bibliothèques numériques. Le verrouillage officiel actuel utilise scikit-learn 1.9.0 : c’est un environnement distinct. La [CI sur trois plateformes de a1450df](https://github.com/GuGuGu-coocoo/PsyMl_Toolkit/actions/runs/36978714686) est un test automatique, pas une validation en fenêtre réelle de macOS, Windows ou des paquets applicatifs.

Les CSV archivés liés dans le tableau conservent les valeurs de cette même référence indépendante originale v1. Avant le correctif, l’interface avait échoué avec v1 ; une exécution historique distincte avait réussi avec v1.1, qui omettait `verbose`. Ces résultats restent ci-dessous, distincts de la nouvelle vérification de v1.

La comparaison formelle utilise les tolérances absolue et relative `atol=rtol=1e-10`, avec contrôle des lignes, partitions, candidats et paramètres effectifs. Elle ne garantit pas l’identité bit à bit entre plateformes. Les chiffres arrondis servent à un premier contrôle ; le [comparateur et la référence indépendante](../examples/public/california_random_nested_v1/README.md) vérifient les exports complets. Les 270/270 contrôles couvrent ce qui était observable dans cette exécution. Les exports ordinaires ne montrent pas tous les membres des plis internes, l’état du prétraitement à chaque ajustement interne ou les prédictions des familles non retenues.

Les partitions aléatoires peuvent placer des zones voisines dans l’entraînement et le test. Elles n’établissent ni le transfert vers de nouvelles régions ou de futurs marchés, ni la causalité, ni une aptitude aux décisions de logement ou de crédit. Les valeurs plafonnées sont conservées. Gardez configuration, versions du logiciel et des bibliothèques et dossier de résultats distinct pour chaque nouvelle exécution.

## Historique : échec de v1 avant correction et compatibilité v1.1

Les sections suivantes décrivent les sources antérieures `a145e07`, séparément de la vérification de v1 corrigée ci-dessus. Leur tableau historique correspond à [california_config_v1_1.json](../examples/public/california_random_nested_v1/california_config_v1_1.json) ; cette révision de configuration n’est pas une version du logiciel.

## 1. Résultat et périmètre

Le cas historique du 2 octobre 2026 porte sur l’interface graphique **Linux,
exécutée depuis les sources**, de PsyML 0.3.0, commit
`a145e07c4b6a4135781725c1390f68192ab8e92c`. Il couvre l’import des données et de
la configuration, les réglages scientifiques, l’exécution dans une vraie fenêtre,
la consultation des résultats, l’export complet des prédictions, le chargement
du modèle enregistré et une prédiction sur dix lignes.

La configuration originale v1 a **échoué**. La variante de compatibilité v1.1,
identifiée séparément, a passé **270/270 contrôles dans le périmètre observable**
face à une référence indépendante, avec la tolérance fixée avant les scores.
Ce résultat ne valide ni tous les paramètres, ni tout le logiciel, ni un autre
système, ni les applications distribuées. Aucun code de production n’a été
modifié lors de ce test historique. Les outils publics permettent de comparer d’autres exécutions ; leur présence ne constitue pas une nouvelle validation dans l’interface.
Toute correction ultérieure doit être vérifiée et consignée séparément.

## 2. Données, licence et transformation

Source : [Liu, Nelson (2016), Figshare, version 2](https://doi.org/10.6084/m9.figshare.3829992.v2),
fichier 5976036. Les métadonnées publiques conservées indiquent **CC BY 4.0**;
voir [attribution](../examples/public/california_random_nested_v1/ATTRIBUTION.md)
et [métadonnées originales](../examples/public/california_random_nested_v1/expected/figshare_metadata.json).
Étude originale : [Pace et Barry (1997), *Sparse Spatial Autoregressions*](https://doi.org/10.1016/S0167-7152(96)00140-X).
Les auteurs et dépositaires ne cautionnent pas PsyML ou cette validation.

Archive : 441 963 octets, SHA-256
`aaa5c9a6afe2225cc2aed2723682ae403280c4a3695a2ddda4ffb5d8215ea681`.
CSV dérivé : 2 539 419 octets, SHA-256
`157b6c0d3acd6d93a50c411d0cd4130d8c719ce5eb17b61f1c45300f2af6fc85`.
La préparation est hors ligne, vérifie d’abord l’empreinte complète, puis lit
uniquement les deux membres réguliers déclarés; elle n’extrait ni n’exécute
le contenu de l’archive.

Le jeu comprend 20 640 groupes d’îlots du recensement, huit prédicteurs et la
cible `MedHouseVal`. Ordre : `MedInc`, `HouseAge`, `AveRooms`, `AveBedrms`,
`Population`, `AveOccup`, `Latitude`, `Longitude`. Avec des indices source
commençant à zéro, les transformations sont `raw7`, `raw2`, `raw3/raw6`,
`raw4/raw6`, `raw5`, `raw5/raw6`, `raw1`, `raw0`; cible `raw8/100000`.
Le nombre de ménages sert donc de dénominateur pour les moyennes pertinentes,
et la cible est exprimée en unités de 100 000 USD du recensement de 1990.

Aucune ligne n’est supprimée ou réordonnée; aucune winsorisation, sélection de
variables ou transformation de cible autre que l’unité n’est appliquée. Aucune
valeur n’est manquante ou non finie. L’audit descriptif historique relève 965
valeurs au plafond conservé de 5,00001, soit 4,6754 %. Une ligne ne représente
ni un ménage individuel ni une transaction immobilière actuelle.

## 3. Protocole gelé avant le premier ajustement

Le [protocole original](../examples/public/california_random_nested_v1/expected/PROTOCOL_FROZEN.json)
et les configurations historiques sont conservés octet pour octet. Les copies
portables changent uniquement les chemins d’entrée/sortie; l’identité des
champs scientifiques reste contrôlée, y compris les types numériques JSON.

- Boucle externe : `KFold(5, shuffle=True, random_state=20261002)`, ordre source,
  4 128 lignes de test par pli.
- Boucle interne : `KFold(3, shuffle=True)`, graines 20261003 à 20261007 pour les
  plis externes 1 à 5; 20261002 pour la sélection finale sur toutes les données.
- Chaque ajustement recrée un `ColumnTransformer` numérique, une imputation
  médiane, un `StandardScaler` et l’estimateur, ajustés sur ses seules lignes
  d’apprentissage.
- Familles ordonnées : Dummy(moyenne); Ridge(alpha 0,1, 1, 10, solveur SVD);
  Random Forest(100 arbres, profondeur maximale 10, feuille minimale 3,
  `n_jobs=1`). Les dictionnaires complets sont fixés dans la configuration.
- Minimisation de la moyenne non pondérée des trois RMSE internes; remplacement
  uniquement si strictement inférieur, égalités exactes départagées par l’ordre
  de configuration. Aucun retour des scores externes dans la sélection.
- Charge prévue et enregistrée par la référence : 90 ajustements internes,
  15 ajustements externes par famille, un ajustement final, soit 106. L’interface
  affichait 106 tâches prévues; il n’existait pas de trace séparée de chaque appel
  de production.
- Critère principal : moyenne non pondérée des cinq RMSE externes de la procédure
  sélectionnée. Aussi : MAE/R² moyens, écart-type descriptif entre plis (`ddof=0`),
  métriques OOF regroupées séparément et différences appariées au Dummy sur les
  mêmes plis. CPU monothread; sans SHAP ni importance par permutation.

La tolérance de toutes les comparaisons numériques finies est
**atol = rtol = 1e-10**, fixée avant les résultats. Valeurs non finies et valeurs
manquantes unilatérales échouent; seul le texte vide du champ diagnostique
`error` est autorisé. Identifiants, couverture, appartenance aux plis, ordre des
candidats, choix et configuration scientifique ont des contrats exacts. Le
parseur CSV pandas par défaut reste la règle; le parseur « round trip » n’est
qu’un diagnostic ultérieur.

## 4. Échec original et amendement v1.1

La configuration demandait explicitement RF `verbose=0`. Godot l’a sérialisé
comme `0.0`; la restauration entière de PsyML omettait alors `verbose`.
Scikit-learn a rejeté RF dans les six sélections : cinq plis externes et la
sélection finale. Les autres familles seules ne réalisent donc pas la procédure
prévue. Un problème distinct d’installation des métadonnées du paquet Python
a aussi empêché l’export du modèle final de ce premier essai. Son résultat
**195/227 contrôles réussis, 32 échecs** reste conservé, ainsi que l’absence de
résultat terminal et de modèle.

L’[amendement v1.1](../examples/public/california_random_nested_v1/expected/PROTOCOL_AMENDMENT_v1_1.json)
omettait uniquement `verbose`, utilisant la même valeur entière zéro par défaut.
L’équivalence typée des paramètres effectifs a été vérifiée avant le nouvel
ajustement. Données, comportement des candidats, graines, plis, prédicteurs,
critère et tolérances n’ont pas changé. Cette révision suit l’échec; elle n’est
pas présentée rétroactivement comme la configuration initialement gelée.

Le comparateur public conserve l’identité brute des types de sauvegarde GUI pour
v1. Pour la seule variante historique v1.1, il signale la dérive JSON brute et
applique la restauration bornée et documentée des champs de comptage. Les types
de la configuration exécutée restent exacts. Il ne convertit pas `verbose=0.0`
invalide en zéro entier et ne change pas la sémantique fractionnaire de
`min_samples_*` en nombre entier.

## 5. Résultats numériques historiques

| Mesure | Valeur v1.1 historique |
|---|---:|
| RMSE externe moyenne, principale | 0.5339815958325378 |
| Écart-type de RMSE, ddof=0 | 0.01850680156369903 |
| MAE externe moyenne | 0.3610547401259507 |
| R² externe moyen | 0.7856663784093894 |
| RMSE OOF regroupée | 0.5343022051161513 |
| R² OOF regroupé | 0.7856041590209227 |
| RMSE externe moyenne Dummy | 1.153954483920011 |
| RMSE externe moyenne Ridge | 0.7273658464149191 |

| Pli externe | Famille sélectionnée | RMSE |
|---|---|---:|
| 1 | Random Forest | 0.5622963920650870 |
| 2 | Random Forest | 0.5191199276807156 |
| 3 | Random Forest | 0.5316590028567558 |
| 4 | Random Forest | 0.5460596387779938 |
| 5 | Random Forest | 0.5107730177821366 |

Les cinq plis et la sélection finale ont retenu Random Forest. Les comparaisons
de familles sont descriptives; elles ne justifient pas de choisir la validation
après observation. L’écart-type entre plis n’est ni erreur-type ni intervalle de
confiance. L’unité de RMSE est 100 000 USD historiques, pas l’erreur actuelle de
prix du marché.

Les exports réels comprennent les 20 640 lignes OOF uniques, avec appartenance
aux plis conforme. Le parseur par défaut donne des différences maximales de
8,88e-16 pour OOF et 4,44e-16 pour les dix prédictions GUI. Un diagnostic
ultérieur avec lecture « round trip » retrouve l’égalité exacte des OOF,
30 scores moyens de candidats et métriques par pli, sans changer l’acceptation.
Le rejeu du modèle sur toutes les données et sur le petit fichier, ainsi que
les statistiques finales de prétraitement, étaient exacts. L’export conservait
`sample_id`, valeurs et ordre des colonnes, puis ajoutait `predicted_value`.
Les 30 recherches de candidats v1.1 étaient terminées. Ces chiffres ne sont pas
régénérés par les tests rapides du dépôt.

## 6. Environnement, outils et limites de preuve

Environnement historique : Linux x86_64; Python 3.12.14; NumPy 2.3.5;
SciPy 1.17.0; pandas 2.2.3; scikit-learn 1.8.0; joblib 1.5.3;
Matplotlib 3.10.8; Godot 4.6.3. Le lancement depuis les sources a nécessité
l’import du cache de ressources/classes Godot et une installation Python correcte.
Un dossier Documents par défaut invalide sur ce bureau empêchait la sauvegarde
jusqu’au choix d’une sortie explicite valide; l’erreur apparaissait en page 2.
Ce sont des observations historiques, pas des propriétés de chaque installation.

La [notice exécutable](../examples/public/california_random_nested_v1/README.md)
donne toutes les commandes. La référence n’importe aucun module ou helper
PsyML. Elle consigne les 106 états ajustés, 90 scores internes individuels et
24 périmètres d’apprentissage distincts. Elle partage les estimateurs, métriques
et séparateurs sklearn avec PsyML : elle vérifie l’organisation du flux, pas
les solveurs indépendamment.

La préparation intégrée reproduit les octets historiques. Les contrats et
contrôles synthétiques n’effectuent ni téléchargement ni ajustement complet,
ni observation des appels de production. Ce ne sont pas les perturbations de
fuite du cas DSA, ni un test de permutation. Le comparateur ajoute des contrôles
d’identité scientifique des chemins relocalisés, d’environnement, de chemin de
modèle et de conservation des colonnes prédictives; son nombre de contrôles
peut différer des 270 historiques, qui restent inchangés. Une nouvelle
comparaison des anciens fichiers n’est pas une nouvelle exécution GUI.

Les exports ordinaires ne révèlent pas tous les plis internes, états de
prétraitement par ajustement, scores internes individuels ou OOF des familles
non sélectionnées. L’audit complet de la référence ne doit pas être attribué
aux internes de production non observés. Le dépôt contient les résumés compacts, métadonnées, empreintes et le [CSV préparé](../examples/public/downloads/README.md). Les binaires de modèles, captures et arbres de résultats complets restent exclus. Un modèle joblib peut exécuter du
code : n’utiliser que les résultats locaux de confiance. Le comparateur exige
la même version sklearn que sa référence et vérifie celle du modèle produit.

L’environnement verrouillé actuel utilise sklearn 1.9.0 sur Python ≥3.11;
le cas historique ne l’a pas validé. La référence refuse une autre version par
défaut. L’option explicite `--allow-environment-change` permet un nouveau résultat
séparé, sans modifier les paramètres scientifiques, tolérances ou identités
historiques. Aucun échec ou nouveau score n’autorise à affaiblir la tolérance.

Les plis aléatoires peuvent répartir des voisins géographiques entre
apprentissage et test. Aucune validation spatiale, temporelle ou externe, aucune
conclusion causale ni aptitude aux décisions sensibles de logement ou de crédit
n’est démontrée. Le plafond de cible et l’origine en 1990 demeurent des limites.
Le cas historique ne valide ni macOS, ni Windows, ni les applications distribuées;
les nouveaux environnements et corrections nécessitent une preuve distincte.
