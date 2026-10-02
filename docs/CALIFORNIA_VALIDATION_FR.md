# California Housing : cas de conformité numérique et d’interface réelle

[中文](CALIFORNIA_VALIDATION_ZH.md) · [English](CALIFORNIA_VALIDATION_EN.md) · [Cas exécutable et commandes](../examples/public/california_random_nested_v1/README.md)

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
modifié lors de ce test historique. L’intégration présente ajoute des outils et
des documents publics; elle ne constitue pas une nouvelle validation de fenêtre.
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
aux internes de production non observés. Seuls résumés compacts, métadonnées et
empreintes sont suivis dans Git; données, binaires de modèles, captures et
arbres de résultats volumineux sont exclus. Un modèle joblib peut exécuter du
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
