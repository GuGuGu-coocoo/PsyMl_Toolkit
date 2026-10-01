# Validation croisée imbriquée groupée par participant de PsyML sur des données publiques d’activité humaine : reproduction numérique et vérification inter-plateformes

[中文](VALIDATION_DSA_ZH.md) · [English](VALIDATION_DSA_EN.md)

Cas `psyml_dsa_group_nested_v1` · PsyML `0.3.0` (commit `de33abfe52ccfee67f461a850edd00a14d2fbfaa`) · 2026-10-01

## Résumé

**Objectif.** Éprouver le comportement numérique du flux de validation imbriquée groupée par participant de PsyML sur des données réelles : les partitions, le prétraitement limité aux plis d’entraînement, la sélection interne, la prédiction hors pli, le calcul des métriques et la persistance du modèle suivent-ils un protocole figé à l’avance, et une implémentation indépendante les reproduit-elle ?

**Méthodes.** Les données sont le jeu UCI *Daily and Sports Activities* (DSA) : 8 participants, 19 activités, 60 enregistrements de cinq secondes par participant et activité, soit 9 120 enregistrements. Chaque segment ne fournit que l’accélération et la vitesse angulaire du torse (trois axes chacune), réduites en moyenne et écart-type de population par canal, soit 12 variables. Le plan externe est une validation croisée à 4 plis groupée par participant ; le plan interne une validation croisée stratifiée à 3 plis groupée par participant ; les candidats sont Dummy et la régression logistique ; la sélection utilise la moyenne non pondérée des balanced accuracies internes. Une implémentation de référence indépendante n’importe jamais PsyML et reconstruit le même protocole avec les API publiques de scikit-learn. Des contrôles d’ingénierie couvrent un audit d’isolement des groupes, des perturbations ciblées du pli externe 1 et un canari de labels mélangés.

**Principaux résultats.** La métrique principale, la moyenne des balanced accuracies des plis externes, vaut 0.5740131578947368. Les 9 120 prédictions hors pli concordent ligne à ligne entre les deux implémentations ; les lignes d’entraînement, familles, paramètres et statistiques de prétraitement des 54 ajustements s’alignent ; la relecture du modèle enregistré correspond au modèle final indépendant. Ces valeurs proviennent de l’exécution Linux figée du paquet de cas d’origine. Lors d’une reprise macOS locale, les prédictions dures sont identiques octet pour octet ; seule la ROC-AUC dérivée des probabilités diffère d’environ 2.03e-7, les probabilités hors pli différant d’au plus environ 1.98e-5. Cet écart est conservé et publié tel quel.

**Portée.** Les résultats ne soutiennent la conformité numérique et la reproductibilité du flux testé que pour ce cas ; ils ne constituent ni un nouvel algorithme, ni une revendication de performance, ni un résultat clinique ou populationnel, et ils ne montrent pas que toutes les fonctions de l’outil sont vérifiées sur toutes les plateformes.

## 1. Introduction

La justesse d’un outil d’apprentissage automatique ne se lit pas dans le score final. Pour les chercheurs, il importe tout autant que les partitions isolent réellement les participants, que le prétraitement soit ajusté à l’intérieur des plis d’entraînement, que les modèles et paramètres soient choisis sur des preuves d’entraînement, que les prédictions et métriques hors pli puissent être recalculées indépendamment, et qu’un modèle enregistré se rejoue fidèlement. Vérifier ces étapes sur des données comportementales réelles avec un protocole figé expose des problèmes de conversion et de groupement que des données synthétiques peuvent masquer. Séparer par participant plutôt que par ligne évite de placer des segments voisins d’une même personne de part et d’autre de la frontière entraînement/test : c’est l’exigence de base contre les fuites pour ce type de données.

Ce rapport documente un tel cas : PsyML est exécuté sur les données publiques UCI *Daily and Sports Activities* (DSA) selon un protocole figé à l’avance, puis comparé point par point à une implémentation scikit-learn indépendante qui n’importe pas PsyML. Il s’agit d’un travail de maintenance logicielle et d’acceptation de flux, **non** d’un article de nouvelle méthode, d’une reproduction du benchmark de l’article original ou d’une comparaison d’outils ; il ne soutient aucune affirmation sur les construits psychologiques, l’usage clinique, la causalité ou les effets humains.

## 2. Données et méthodes

### 2.1 Source, licence et attribution

- Données : Barshan, B. & Altun, K. (2010). *Daily and Sports Activities* [Dataset]. UCI Machine Learning Repository. DOI [10.24432/C5C59F](https://doi.org/10.24432/C5C59F) ; page <https://archive.ics.uci.edu/dataset/256/daily+and+sports+activities>.
- Licence : la page officielle indique CC BY 4.0 ; aucun membre du ZIP téléchargé n’ajoute de restriction supplémentaire. Les auteurs des données ne cautionnent ni PsyML ni ce cas.
- Article original : Altun, K., Barshan, B., & Tunçel, O. (2010). Comparative study on classifying human activities with miniature inertial and magnetic sensors. *Pattern Recognition*, 43(10), 3605–3620. <https://doi.org/10.1016/j.patcog.2010.04.019>.
- ZIP brut : 170 800 010 octets, SHA-256 `f42ad7744ecf14151c9fa3a86dfb5b24de9d7cb7ffe956ef5de242983459c77e` ; téléchargé uniquement depuis l’emplacement officiel et entièrement vérifié avant lecture.

### 2.2 Participants, activités et enregistrements

Le jeu contient 19 activités quotidiennes et sportives réalisées par 8 adultes de 20 à 30 ans, avec 60 segments de cinq secondes par participant et activité — 9 120 segments, chacun de forme initiale 125 lignes × 45 colonnes. Les dossiers `p1..p8` sont les identifiants officiels. **Les 8 participants sont les unités indépendantes ; les 9 120 segments ne doivent pas être traités comme 9 120 individus indépendants**, et des segments voisins peuvent être corrélés. L’archive ne définit aucune séparation entraînement/test.

### 2.3 Construction des variables

Seuls les 9 120 membres `data/a01..a19/p1..p8/s01..s60.txt` sont lus, dans un ordre fixe : membre manquant, dupliqué, supplémentaire hors dossier, forme autre que 125×45 ou valeur NaN/infinie interrompent la conversion, sans suppression silencieuse. Chaque segment ne fournit que ses six premières colonnes (accélération du torse x/y/z et vitesse angulaire du torse x/y/z) ; par canal, la moyenne puis l’écart-type de population (`std(ddof=0)`) sont calculés dans cet ordre, soit 12 variables. Les autres capteurs et magnétomètres ne sont pas utilisés ; aucun filtrage, ACP, sélection de variables ni normalisation inter-segments. Le CSV dérivé est en UTF-8, LF, sans index, `float_format %.17g` ; `segment_id`, `subject_id` et `activity` ne servent qu’à la jointure, au regroupement et à la cible et n’entrent jamais dans les variables.

### 2.4 Prétraitement limité au pli d’entraînement

Chaque ajustement construit un pipeline neuf `ColumnTransformer(numeric) → SimpleImputer(strategy='median') → StandardScaler → estimateur`, ajusté uniquement sur les lignes d’entraînement correspondantes. Le cas ne contient pas de valeurs manquantes, mais le pipeline visible est conservé pour pouvoir auditer sa portée d’ajustement.

### 2.5 Partitions externe et interne

- Externe : `GroupKFold(n_splits=4, shuffle=False)` dans l’ordre d’origine ; les participants test des quatre plis sont `[4,8]`, `[3,7]`, `[2,6]`, `[1,5]` ; chaque pli met de côté 2 280 segments et entraîne sur 6 840.
- Interne : `StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=20261001 + numéro de pli externe)` (plis numérotés à partir de 1), pour sélectionner à l’intérieur de l’ensemble d’entraînement externe ; chaque pli interne valide 2 participants et entraîne sur 4, et chaque partition contient les 19 classes.
- Sélection finale sur toutes les données : la même validation croisée stratifiée à 3 plis groupée avec `random_state=20261001` ; elle ne sert qu’à déterminer le modèle final et ne fournit **aucun nouveau score de test non biaisé**.

### 2.6 Candidats et règle de sélection

L’ordre des familles est `['dummy', 'logistic_regression']` : `DummyClassifier(strategy='prior')` et `LogisticRegression(C∈[0.1, 1.0], solver='lbfgs', max_iter=2000, tol=1e-8, class_weight=None, fit_intercept=True)`, tous deux avec `random_state=20261001`. Chaque paramètre fixe est écrit explicitement dans la configuration ; `max_candidates=2` s’applique par famille et ne déclenche jamais d’échantillonnage aléatoire.

Sélection : pour chaque candidat, la moyenne non pondérée des trois balanced accuracies internes ; le remplacement exige une valeur **strictement supérieure**, et une égalité exacte conserve le premier candidat/famille dans l’ordre de configuration ; les scores externes ne départagent jamais. Un pli interne en échec invalide le candidat, sans moyenner les plis réussis à la place ; si le gagnant interne échoue dans le pli externe, toute la procédure échoue et aucune autre famille n’est substituée. Un flux complet réalise 54 ajustements : 45 internes + 8 externes par famille + 1 final. CPU uniquement, un seul thread de bibliothèque numérique, sans SHAP.

### 2.7 Métriques et conventions de rapport

- Principal : la **moyenne non pondérée des plis** de la balanced accuracy externe de la procédure sélectionnée en interne. L’écart-type entre plis (`ddof=0`) est une variation descriptive et **ne doit pas être lu comme une erreur type ni un intervalle de confiance de population**.
- Secondaire : même agrégation pour l’accuracy et le macro-F1 (`zero_division=0`) ; matrice de confusion et macro-F1 hors pli mises en commun (pooled) ; différences appariées procédure−Dummy ; balanced accuracy par participant (descriptive).
- **La moyenne des plis et le pooled sont rapportés séparément** : des plis de taille égale et à classes équilibrées font coïncider accuracy/BA pooled avec la moyenne des plis, mais le macro-F1 diffère (voir 3.1).
- Le modèle final est ajusté sur toutes les lignes analysées ; sa relecture vérifie la persistance et le schéma, **pas** la validité externe, et ne peut pas être lue comme un score de généralisation.

### 2.8 Référence indépendante et complément d’observation

- La référence indépendante ([`tools/cases/reference_dsa.py`](../tools/cases/reference_dsa.py)) **n’importe jamais PsyML** et reconstruit partitions, prétraitement, sélection interne, prédiction hors pli et ajustement final à partir des API publiques de scikit-learn ; la suite de tests vérifie statiquement ses imports et son flux de données a été relu. Elle **partage les estimateurs, séparateurs et métriques de scikit-learn** avec PsyML : elle valide donc le flux, pas les solveurs scikit-learn eux-mêmes.
- Le complément d’observation ([`tools/cases/observe_psyml_dsa.py`](../tools/cases/observe_psyml_dsa.py)) ne fait qu’envelopper et enregistrer les appels de production de PsyML pour compléter l’appartenance des plis et l’audit des 54 ajustements ; il ne se présente pas comme une implémentation indépendante.
- Le comparateur ([`tools/cases/compare_dsa.py`](../tools/cases/compare_dsa.py)) vérifie l’appartenance, les ensembles de classes, l’isolement des groupes, la portée d’ajustement, les statistiques de prétraitement, les paramètres et scores des candidats, la trace de sélection, les prédictions et probabilités hors pli, les métriques et la relecture du modèle enregistré, sous des tolérances déclarées à l’avance ; il peut importer PsyML pour inspecter la persistance et **ne se présente pas comme une implémentation indépendante** ; il recalcule en outre la balanced accuracy et le macro-F1 à partir des comptes TP/FN/FP par classe. Tout échec conserve ses écarts et sort en code non nul ; voir annexe D.

### 2.9 Contrôles d’ingénierie et acceptation

Quatre contrôles sont exécutés sur les données réelles : audit de fuite de groupes sur une séparation aléatoire par lignes (l’auditeur supplémentaire doit le détecter ; PsyML lui-même avertit sans bloquer, et cela ne doit pas être décrit comme une protection intégrée) ; rotation des labels du pli externe 1 fixé (scores internes, sélection, statistiques d’entraînement et prédictions/probabilités de test inchangés) ; ajout de 1000 aux variables de test du pli externe 1 fixé (statistiques d’entraînement et sélection interne inchangées, prédictions libres) ; et un canari de labels mélangés intra-participant (ordre croissant de `subject_id`, un seul `default_rng(20261002)`, variables et ordre des lignes intacts ; seuil d’alerte prédéfini : BA moyenne des plis > 0,10). Le canari est une perturbation d’ingénierie, **pas un test de permutation**, et n’estime pas de taux de faux positifs.

## 3. Résultats

### 3.1 Valeurs principales

Les valeurs ci-dessous proviennent de l’exécution Linux figée du paquet de cas d’origine et ont été revérifiées par la reprise macOS locale (3.5).

| Grandeur | Valeur |
| --- | --- |
| Pli externe 1 (participants test 4, 8), balanced accuracy | 0.5394736842105263 |
| Pli externe 2 (participants test 3, 7), balanced accuracy | 0.4986842105263158 |
| Pli externe 3 (participants test 2, 6), balanced accuracy | 0.6644736842105264 |
| Pli externe 4 (participants test 1, 5), balanced accuracy | 0.5934210526315788 |
| **Principal : balanced accuracy moyenne des plis** | **0.5740131578947368** |
| Macro-F1 moyen des plis | 0.5513874769696934 |
| Écart-type entre plis (ddof=0, BA / macro-F1) | ≈ 0,062103 / ≈ 0,068311 |
| Dummy du même pli | 1/19 = 0.05263157894736842 |
| Différence moyenne procédure − Dummy | 0.5213815789473684 |
| Macro-F1 pooled hors pli | 0.5702035749465654 |
| Étendue par participant hors pli | ≈ 0,4553–0,6658 (8 participants, descriptif) |

La valeur principale proche de 0,574 est le résultat de ce cas sous le protocole convenu ; elle sert à vérifier que le flux a été correctement exécuté, n’est pas un apport algorithmique nouveau et ne doit pas être comparée directement à des valeurs d’articles obtenues avec d’autres capteurs, variables ou partitions.

### 3.2 Résultats par pli et trace de sélection

Les quatre plis externes et le choix final ont tous retenu `logistic_regression, C=1.0`, avec des moyennes internes de 0.5381578947368421, 0.577485380116959, 0.5399122807017545 et 0.508187134502924, et un choix final de 0.5450779727095517. Le classement des familles à l’extérieur est exploratoire et ne constitue pas un nouveau score « meilleur modèle » non biaisé.

### 3.3 Conformité logiciel–référence

- Les 9 120 prédictions hors pli concordent ligne à ligne entre les deux implémentations (exactement, selon le paquet de cas ; le fichier de prédictions dures de la reprise macOS est identique octet pour octet au résultat figé, voir 3.5).
- Les lignes d’entraînement, familles, paramètres et statistiques de prétraitement des 54 ajustements s’alignent ; le comparateur recalcule aussi directement médiane/moyenne/variance à partir des lignes d’entraînement et la balanced accuracy/macro-F1 à partir des comptes TP/FN/FP par classe.
- L’écart maximal de probabilité entre PsyML et la référence indépendante est 0 ; la CLI native et la reprise d’observation exportent des fichiers identiques de prédictions, métriques de pli, recherche et sélection.
- Après un chargement de confiance, les classes et probabilités du modèle enregistré correspondent au modèle final indépendant ; la réorganisation des colonnes est sans effet et une variable manquante est refusée. La relecture utilise les lignes d’analyse d’origine et **n’est pas** une validation externe.

### 3.4 Résultats des contrôles

| Catégorie | Nombre | Résultat | Résumé |
| --- | --- | --- | --- |
| Acceptation numérique | 26 | Réussi | Appartenance, ajustements, prétraitement, sélection, prédictions/probabilités hors pli, relecture du modèle enregistré |
| Contrôles structurels | 4 | Réussi | Partitions disjointes couvrant les lignes source ; 19 classes par partition ; portées internes strictement incluses dans l’entraînement externe ; colonnes de rôle exclues |
| Contrôles d’export | 2 | Réussi | Colonnes de probabilité dans l’ordre de `classes_` ; métadonnées du modèle enregistré identiques au modèle final indépendant |
| Contrôles sur données réelles | 7 | Réussi | Fuite de la séparation par lignes détectée par l’auditeur supplémentaire ; la rotation des labels du pli 1 ne change ni scores/choix internes ni statistiques d’entraînement ni prédictions/probabilités de test ; +1000 sur les variables du pli 1 ne change ni statistiques ni sélection interne |
| Canari de labels mélangés | 6 + 1 | Réussi | Le flux imbriqué complet correspond à la référence indépendante ; BA moyenne des plis = 0.0532894736842105, sous le seuil 0,10 ; le mélange ne touche que la colonne cible |

Sur les fuites de groupes, deux faits doivent rester distincts : PsyML avertit lorsqu’une colonne de groupe accompagne un k-fold ordinaire mais ne le **bloque pas** en dur ; l’injection de faute de ce cas est détectée par l’auditeur supplémentaire. En outre, les tests existants de perturbation du classement externe et de repli en cas d’échec (`tests/test_nested_family_selection.py`) ont été réellement exécutés et réussis pendant cette intégration.

### 3.5 Vérification inter-plateformes

Pendant l’intégration du dépôt, toutes les étapes ont été rejouées sous macOS (aarch64) avec les mêmes versions de parité que le cas figé (Python 3.12.14, scikit-learn 1.8.0, SciPy 1.17.0, …) ; le relevé est dans [`expected/reverification_macos.json`](../examples/public/dsa_group_nested_v1/expected/reverification_macos.json).

- Codes de sortie : CLI native 0, référence 0, observation 0, comparaison 1, contrôles 0 ; le 1 de la comparaison provient uniquement de l’écart métrique inter-plateformes ci-dessous et est conservé volontairement.
- Les 9 120 prédictions dures hors pli sont **identiques octet pour octet** au résultat figé (SHA-256 de `predictions.csv` : `36c39a34c9317d568c79f37de17c2b566d10f24db9de0625886f3bda83022b53`) ; accuracies par pli, trace de sélection, macro-F1 et différences Dummy correspondent à la base figée.
- Le seul écart concerne `roc_auc_ovr_weighted`, dérivé des probabilités (colonnes touchées : `fold_metrics.csv`, `metrics.csv`, moyenne/écart-type/min de `metrics_summary.csv`) : environ 2,03e-7 pour les plis externes 1 et 2, et 0 pour les plis 3 et 4. L’écart maximal des probabilités hors pli est 1.9762588500393807e-05 (maxima par pli 1,98e-5, 8,70e-6, 6,56e-6, 5,23e-6 ; 97 415 des 173 280 cellules de probabilité dépassent 1e-10).
- Alignement et localisation : les deux côtés ordonnent les colonnes de probabilité en `probability_1..19`, les `classes_` des deux modèles finaux valent 1..19, et les séquences `row_index` ainsi que `fold/observed/predicted/model` sont identiques. Recalculer la ROC-AUC sous macOS à partir des **matrices de probabilité figées** reproduit les valeurs figées à 1,11e-16 près : le calcul de la métrique est donc cohérent entre plateformes, et l’écart suit les probabilités ajustées — les deux modèles finaux diffèrent d’au plus environ 3,07e-5 pour les coefficients, 7,08e-5 pour les intercepts et 3,03e-6 pour les probabilités sur toutes les données.
- L’environnement officiel `uv.lock` (scikit-learn 1.9.0, pandas 3.0.5, …, voir 3.6 et annexe C) a réalisé le 2026-10-02 une reprise complète du même cas : ses 26 contrôles numériques, 4 structurels et 2 d’export passent dans cet environnement, et ses prédictions principales, probabilités, coefficients et toutes les tables de métriques sont **exactement identiques** à la reprise macOS de parité (écart de probabilité 0, écart de coefficients 0, tables de métriques identiques octet pour octet). L’écart par rapport à la base Linux figée reste donc le même écart plateforme déjà enregistré ; aucun nouvel écart imputable au changement de version des dépendances n’a été observé sur ce cas.
- **La cause de cet écart n’est pas confirmée et pourrait être liée aux implémentations numériques des plateformes** ; aucune expérience de cause racine au niveau implémentation n’a été menée, et il n’est pas écrit « causé par telle bibliothèque d’algèbre linéaire ». Ce cas ne revendique pas l’équivalence numérique entre plateformes, et aucune tolérance ni base n’a été modifiée pour cela.
- La BA du canari et l’empreinte du CSV mélangé correspondent aux valeurs figées ; le décalage +1000 des variables a modifié 2 122 prédictions, même nombre que sous Linux. Après l’exécution, les 423 fichiers du manifeste figé ont été contrôlés : aucun fichier Python/GUI/test/lock ne diffère ; seuls les 3 documents publics intentionnellement modifiés par cette intégration diffèrent.

### 3.6 Environnements de test, avertissements et CI

Trois environnements sont enregistrés séparément pour éviter toute confusion :

- **Environnement de parité du cas** : Python 3.12.14, scikit-learn 1.8.0, etc. sous Linux x86_64 et macOS aarch64, utilisé pour les valeurs de 3.1–3.5 ; ce n’est pas l’environnement officiel verrouillé.
- **`.venv` local du dépôt** (Python 3.12.13, scikit-learn 1.9.0, plus l’extra explain `shap 0.52.0`) : `ruff` réussit, la suite par défaut `pytest -q` rapporte **1222 réussites** (dont les 24 tests contractuels/d’intégration de ce cas et 5 nouveaux tests de mise en page/invariance de la matrice de confusion) et l’audit de confidentialité réussit ; les tests d’explication SHAP s’exécutent réellement ici.
- **Environnement officiel `uv.lock`** (chemin séparé, `UV_PROJECT_ENVIRONMENT=… uv sync --locked --group dev` ; `uv.lock` non modifié, SHA-256 `9951e0701e2a0c7bd85614d3a0fd642b9407da6d98fa955bac97397626ebce56`) : `pytest -q` rapporte **1152 réussites, 2 ignorés**, code 0. Les deux ignorés sont les `pytest.importorskip("shap")` au niveau module de `tests/test_explanation*.py`, car cette commande omet volontairement l’extra explain — ces deux tests ne sont pas comptés comme réussis. Le 2026-10-02, cet environnement a aussi réalisé le cas DSA complet (CLI native, référence indépendante, audit d’observation, comparaison et contrôles avec les codes 0/0/0/1/0 ; le 1 de la comparaison provenait encore uniquement de l’écart métrique retenu) ; le relevé succinct est `expected/reverification_uv_lock.json`. Les explications SHAP n’ont pas été exécutées dans cet environnement.

Avertissements Python pendant le cas : le `warnings.json` de la CLI native conserve une mise en garde scientifique (les métriques principales évaluent la procédure de sélection imbriquée ; le classement des familles est exploratoire) ; les listes de la référence, de l’observation et des contrôles sont vides ; aucun ConvergenceWarning ; toutes les étapes ont produit un stderr vide.

Après la poussée, la CI principale du dépôt ([run 36880091260](https://github.com/GuGuGu-coocoo/PsyMl_Toolkit/actions/runs/36880091260)) a réussi sous Windows, macOS et Linux (lint, tests, suite GUI Godot, construction de la wheel et smoke). Une CI verte signifie que les contrôles automatisés existants du dépôt ont réussi pour ce commit ; **cela ne signifie pas que Windows a rejoué ce cas DSA**, et cela ne remplace pas la revue humaine des fenêtres réelles et des applications empaquetées.

## 4. Discussion

### 4.1 Ce que les preuves soutiennent

Le cas soutient ceci : pour la version de code, le protocole et l’environnement enregistrés, le flux imbriqué groupé par participant de PsyML et une implémentation scikit-learn reconstruite indépendamment produisent les mêmes partitions, choix et prédictions ; le prétraitement des plis d’entraînement et la persistance peuvent être vérifiés point par point ; et les contrôles d’ingénierie n’ont montré aucun signe de fuite de groupes ni de contamination de sélection dans ce flux. Il confirme aussi que le dépôt génère les données dérivées localement et ne redistribue pas le jeu de données.

### 4.2 Relation avec les travaux antérieurs

L’article original compare plusieurs classifieurs, utilise cinq unités de capteurs (poitrine, deux bras, deux jambes, magnétomètres inclus), des variables traitées par ACP, et évalue sous-échantillonnage aléatoire, 10 plis aléatoires et validation par participant laissé de côté. Ses entrées, variables, modèles et partitions diffèrent de ce cas. Ce cas n’utilise qu’une unité de torse avec 12 statistiques fixes, un plan externe fixe à 4 plis groupés et un plan interne à 3 plis stratifiés groupés, avec seulement Dummy et la régression logistique comme candidats ; il ne cherche pas à comparer des scores avec l’article original ni avec une autre étude. L’article original a déjà évalué la généralisation à de nouveaux participants : ce cas n’introduit donc pas la validation groupée, et sa valeur ne porte aucune interprétation de performance de domaine.

### 4.3 Limites et périmètre non vérifié

- Les enregistrements publics de huit participants ne peuvent soutenir aucune conclusion clinique, de population générale ou naturaliste ; ce cas n’est pas une validation externe et ne couvre pas d’autres protocoles d’acquisition, appareils ou populations.
- La référence indépendante partage les solveurs scikit-learn avec PsyML ; le canari de labels mélangés est une perturbation d’ingénierie unique, pas un test de permutation, et n’estime ni taux de faux positifs ni absence de fuite.
- La cause de l’écart inter-plateformes n’est pas confirmée ; le rapport conserve l’écart brut et ne l’interprète ni comme défaut ni comme amélioration logicielle.
- Non exécuté : inspection en fenêtre réelle au-delà des contrôles Godot/GUI automatisés, applications empaquetées Windows et macOS, explications SHAP dans l’environnement officiellement verrouillé, formats d’entrée autres que CSV, études utilisateurs et validation sur données externes, audit de sécurité complet, et nouveau téléchargement/conversion du ZIP brut complet (l’énumération stricte, les empreintes, formes, valeurs finies et refus de comptage de `prepare_dsa.py` sont couverts par des tests contractuels sur ZIP synthétiques). Le cas DSA dans l’environnement officiel `uv.lock` a été réalisé le 2026-10-02 (3.5, 3.6).

### 4.4 Lisibilité des figures

L’export natif de la matrice de confusion à 19 classes était dense sous sa disposition par défaut d’origine : annotations à trois chiffres voisines et étiquettes d’axe serrées, certains chiffres se touchant visuellement. Le CSV sous-jacent, les totaux et les métriques étaient corrects. Cette observation est conservée comme historique. Le 2026-10-02, le chemin de tracé natif (`src/psyml/reporting/research.py`) a reçu un correctif minimal adaptatif selon le nombre de classes : la toile et les polices évoluent avec le nombre de classes, les étiquettes de graduation pivotent davantage pour les grandes matrices (les libellés restent les espaces réservés `Class 1..N` dans l’ordre de `confusion_matrix.csv`), et au-delà de quatorze classes les cellules nulles ne sont plus annotées, tandis que toutes les classes et tous les comptes non nuls restent visibles ; le sens des axes, l’ordre des classes, le mode de comptage et la barre de couleur sont inchangés. Cinq tests de régression couvrent la politique de mise en page et les scénarios binaire / peu de classes / 19 classes / libellés longs / libellés CJK / matrice entièrement nulle, et vérifient que le tracé laisse les prédictions, métriques et le fichier de matrice identiques octet pour octet dans le même environnement. L’export natif corrigé à 19 classes et les figures de scénario ont été inspectés visuellement : le texte est lisible, les libellés ne sont pas tronqués et les axes ne se chevauchent pas. Le correctif ne touche aucun code d’interface et **ne prouve pas que l’interface ou les applications empaquetées ont été testées**.

## 5. Disponibilité des données et du code, et reproduction

- Les données sont obtenues sous CC BY 4.0 depuis l’emplacement officiel d’UCI ; le dépôt **ne les redistribue pas**, et le CSV dérivé n’est généré que dans le dossier local ignoré par Git `examples/public/data/`. L’attribution et la note de modification se trouvent dans `examples/public/dsa_group_nested_v1/expected/` et `tools/cases/prepare_dsa.py`.
- Le code est publié sous Apache License 2.0. Les outils du cas sont dans `tools/cases/`, la configuration dans `examples/public/configs/dsa_group_nested_v1.json`, les attentes figées dans `examples/public/dsa_group_nested_v1/expected/`, et les tests contractuels/d’intégration dans `tests/test_public_dsa_case_contract.py`.
- Reproduction (depuis la racine du dépôt) :

```bash
# 1) Facultatif : reconstruire le CSV dérivé depuis le ZIP officiel (contrôles stricts, aucun code de l’archive exécuté)
uv run python tools/cases/prepare_dsa.py --archive <official.zip> --output-dir examples/public/data
# 2-5) CLI native, référence indépendante, audit d’observation, comparaison, contrôles :
#      la séquence complète est dans examples/public/dsa_group_nested_v1/README.md
```

La CLI et chaque outil exigent un nouveau dossier de sortie vide ; les résultats existants ne sont jamais écrasés, et `input_path`/`output_dir` se résolvent par rapport au répertoire courant du processus. Les conditions d’échec incluent toute empreinte incorrecte, ensemble de membres inattendu, valeur non finie ou forme/comptage erroné, chevauchement de groupes, égalité départagée par approximation, métriques ou probabilités hors tolérance, relecture du modèle incohérente, BA du canari > 0,10, ou avertissements stderr non examinés. Un échec ne doit pas être rendu vert en changeant les tolérances, en supprimant des plis, en augmentant les itérations, en changeant C, en échangeant les données ou en choisissant une autre validation.

## 6. Références

1. Barshan, B., & Altun, K. (2010). *Daily and Sports Activities* [Dataset]. UCI Machine Learning Repository. <https://doi.org/10.24432/C5C59F> (page : <https://archive.ics.uci.edu/dataset/256/daily+and+sports+activities> ; licence : <https://creativecommons.org/licenses/by/4.0/>)
2. Altun, K., Barshan, B., & Tunçel, O. (2010). Comparative study on classifying human activities with miniature inertial and magnetic sensors. *Pattern Recognition*, 43(10), 3605–3620. <https://doi.org/10.1016/j.patcog.2010.04.019>
3. scikit-learn developers. Common pitfalls and recommended practices (fuites de données). <https://scikit-learn.org/stable/common_pitfalls.html>
4. scikit-learn developers. Nested versus non-nested cross-validation. <https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html>
5. scikit-learn developers. Tuning the hyper-parameters of an estimator. <https://scikit-learn.org/stable/modules/grid_search.html>
6. scikit-learn developers. Cross-validation: evaluating estimator performance (validation par groupes). <https://scikit-learn.org/stable/modules/cross_validation.html>
7. Collins, G. S., et al. TRIPOD+AI statement: updated guidance for reporting clinical prediction models that use regression or machine learning methods. *BMJ*, 385, e078378. <https://www.bmj.com/content/385/bmj-2023-078378>

## Annexe

### A. Points clés du protocole figé

- Version de protocole `psyml_dsa_group_nested_v1` ; figé le 2026-10-01 à 11:48:43 UTC ; première exécution réelle à 11:49:02.979300 UTC. La configuration a été figée avant la modélisation et n’a pas changé après consultation des scores.
- Externe `GroupKFold(4, shuffle=False)` ; sélection interne et finale `StratifiedGroupKFold(3, shuffle=True)` avec les graines 20261001+pli et 20261001 ; candidats et règle de sélection en 2.6 ; 54 ajustements attendus.
- SHA-256 du modèle de configuration figé : `a156dee0bde4e65f4e89ceef28320faa6931ded8dc9eccab62b514b2dba69941` (contient les chemins de l’époque, conservé pour la vérification forensique) ; l’exemple du dépôt conserve tous les champs scientifiques avec des chemins relatifs.

### B. Empreintes et attentes figées

| Objet | SHA-256 |
| --- | --- |
| ZIP brut | `f42ad7744ecf14151c9fa3a86dfb5b24de9d7cb7ffe956ef5de242983459c77e` |
| CSV dérivé | `75a5fe87a58f4cfde777d914d674362b5148854a3c7064d8c686c0e25c3a047e` |
| CSV de labels mélangés (canari) | `e02699c680cfaa6ec91477c79fff68d7229013d7cc9f7c2acb2ddc4b0d961d86` |
| Prédictions principales de la reprise macOS | `36c39a34c9317d568c79f37de17c2b566d10f24db9de0625886f3bda83022b53` (identiques octet pour octet au résultat figé) |

La configuration figée lisible par machine, les attentes de métriques, l’appartenance des plis et les tolérances sont dans `examples/public/dsa_group_nested_v1/expected/` (`case_summary.json` pour les métriques principales et les compteurs d’acceptation, `fold_membership_expected.json` pour les participants et la trace de sélection, `golden_hashes.json` pour les empreintes des artefacts figés).

### C. Environnements

Environnement de parité du cas : Python 3.12.14 ; NumPy 2.3.5 ; pandas 2.2.3 ; scikit-learn 1.8.0 ; SciPy 1.17.0 ; joblib 1.5.3 ; matplotlib 3.10.8 ; pyreadstat 1.3.6 ; `OPENBLAS_NUM_THREADS`, `OMP_NUM_THREADS` et `MKL_NUM_THREADS` à 1 ; pyarrow et SHAP non installés. C’est un venv isolé avec la source figée installée en `--no-deps` ; le `uv.lock` officiel n’a pas été reconstruit. La reprise macOS utilise les mêmes versions de parité ; sa configuration numpy/scipy et les relevés des deux environnements sont conservés dans l’archive de preuves locale ignorée par Git. Les résultats des tests du `.venv` local et de l’environnement officiel `uv.lock` sont en 3.6. La reprise complète du cas dans l’environnement officiel `uv.lock` (2026-10-02) a utilisé Python 3.12.13, NumPy 2.5.2, pandas 3.0.5, scikit-learn 1.9.0, SciPy 1.18.1, joblib 1.6.0, matplotlib 3.11.1 et pyarrow 23.0.1 ; le `uv.lock` n’a pas été modifié (SHA-256 `9951e0701e2a0c7bd85614d3a0fd642b9407da6d98fa955bac97397626ebce56`), et ses sorties sont exactement identiques à la reprise macOS de parité, avec le même écart plateforme vis-à-vis de la base figée.

### D. Comportement de l’outil d’acceptation et points d’échec

- Le comparateur définit un **contrat de colonnes obligatoires fixe** par table d’acceptation et vérifie séparément les côtés production et référence : colonne manquante d’un côté, même colonne critique absente des deux côtés, écart du nombre de lignes ou colonne supplémentaire non enregistrée dans la référence échouent et signalent le nom de table et les colonnes manquantes ; chaque colonne de production doit aussi exister dans la référence et est comparée.
- Règles numériques : tout ±Inf, NaN unilatéral, ou NaN dans une statistique qui doit être finie échoue ; seules une colonne de diagnostic vide autorisée (comme `error`) et les scores NaN d’un candidat `status=failed` sont admis ; une discordance de dtype échoue aussi. La colonne de diagnostic `inner_scores` propre à la référence n’est pas ignorée : sa longueur de plis, sa finitude et la moyenne égale au score du candidat sont vérifiées.
- La validation du diagnostic et le recalcul direct des métriques vérifient d’abord leurs colonnes de dépendance réelles (`status/score/inner_scores`, `fold/accuracy/balanced_accuracy/f1_macro`) ; en cas d’incomplétude, le nom de table, les colonnes manquantes et la raison sont signalés sans interrompre le rapport, et les contrôles indépendants encore exécutables continuent.
- Tolérances : métriques ≤1e-12 en absolu dans le même environnement ; prétraitement atol=rtol=1e-12 ; probabilités atol=1e-10, rtol=1e-8. Ces tolérances n’ont pas été ajustées pour l’écart inter-plateformes.
- Les tests de régression sont dans `tests/test_public_dsa_case_contract.py` ; les sorties détaillées et les enregistrements d’échec sont archivés localement dans `docs/internal/completed/reports/2026-10-01-dsa-case-macos-reverification/` (ignoré par Git ; `checks/`, `diff/`, `logs/`, `environment/`, `handoff/`).

### E. Écarts, avertissements et échecs conservés

- L’écart inter-plateformes (`roc_auc_ovr_weighted` environ 2,03e-7 et probabilités hors pli jusqu’à environ 1,98e-5) est conservé et publié ; la cause n’est pas confirmée (3.5) et aucune tolérance ni base n’a été ajustée pour lui.
- Correctif de la figure de confusion (2026-10-02) : l’export natif est devenu adaptatif selon le nombre de classes ; les tests de mise en page/scénarios et d’invariance numérique passent, et l’export corrigé à 19 classes ainsi que les figures de scénario ont été inspectés visuellement ; l’observation historique de densité reste en 4.4. Le correctif n’affecte que l’image et laisse le CSV de matrice, les prédictions, les métriques et la sélection inchangés.
- Correctifs du comparateur : le premier auxiliaire prenait la colonne de diagnostic de la référence pour une divergence et sérialisait `inf` dans le JSON, interrompant l’exécution ; des revues ultérieures ont trouvé « les colonnes obligatoires dépendent de la table de production » et « les exceptions de colonne manquante du diagnostic/du recalcul empêchent l’écriture du rapport », tous deux corrigés avec des tests de régression et des tests d’intégration de flux complet.
- La première reprise portable du paquet de cas s’est terminée avec le code 1 au seuil strict de stderr, faute de dossier de cache de polices inscriptible ; seuls les chemins de cache des sous-processus ont été ajustés avant une reprise complète réussie. Ce relevé concerne la configuration de l’environnement du lanceur, pas la logique d’entraînement.
- Aucun défaut n’a nécessité de modification du cœur numérique de PsyML.
