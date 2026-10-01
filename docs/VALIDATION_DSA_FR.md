# Validation PsyML sur données publiques d’activités : cas DSA groupé par participant

[中文](VALIDATION_DSA_ZH.md) · [English](VALIDATION_DSA_EN.md)

Ce document décrit un cas reproductible de validation logicielle : les données
publiques UCI *Daily and Sports Activities* (DSA, UCI 256) sont modélisées avec
un protocole figé de validation croisée imbriquée groupée par participant, puis
le résultat est vérifié point par point contre une implémentation scikit-learn
indépendante qui n’importe jamais PsyML. L’exemple exécutable se trouve dans
[`examples/public/dsa_group_nested_v1/`](../examples/public/dsa_group_nested_v1/README.md)
et les valeurs attendues figées dans le
[`expected/`](../examples/public/dsa_group_nested_v1/expected/README.md) de ce
dossier.

## 1. Objectif et portée

Le cas sert la maintenance du projet et l’acceptation du flux : conversion des
données, appartenance des plis, prétraitement ajusté uniquement sur les plis
d’entraînement, sélection imbriquée, prédiction hors pli, calcul des métriques,
export de la matrice de confusion et rechargement du modèle enregistré, avec
accord numérique entre les deux implémentations. Ce n’est **pas** un nouvel
algorithme, pas une reproduction du benchmark de l’article original, pas une
comparaison d’outils, et cela ne soutient aucune affirmation sur les construits
psychologiques, l’usage clinique, la causalité ou la réduction de l’erreur des
utilisateurs.

> Un protocole prédéfini de validation croisée imbriquée, groupée par
> participant, a été appliqué à un jeu public d’activités quotidiennes, puis un
> flux scikit-learn indépendant a recalculé la séparation, le prétraitement des
> plis d’entraînement, la sélection interne, la prédiction hors pli, l’évaluation
> et la persistance du modèle. Dans l’environnement figé, les deux
> implémentations concordent ligne à ligne pour les prédictions et les
> statistiques de prétraitement et réussissent les tests de perturbation ciblés.
> Ce cas fournit des preuves de conformité numérique et de reproductibilité pour
> le flux testé ; il n’affirme rien sur la nouveauté algorithmique, la validité
> externe dans d’autres populations, ni la réduction de l’erreur des
> utilisateurs.

En tant que maintenance d’un logiciel de recherche, la contribution
descriptible est l’exécution et la traçabilité unifiées de la conception de
l’étude, du prétraitement limité aux plis d’entraînement, de la sélection
imbriquée, de la sémantique d’évaluation et des artefacts reproductibles ; ce
n’est ni un nouveau modèle, ni une revendication de performance, ni un résultat
sur l’erreur humaine.

## 2. Version, date et environnement

- Commit source figé : `de33abfe52ccfee67f461a850edd00a14d2fbfaa` (PsyML `0.3.0`).
- Protocole figé le 2026-10-01 à 11:48:43 UTC ; première exécution réelle sur
  données à 11:49:02.979300 UTC. Figé avant la modélisation ; aucun changement
  après consultation des scores.
- SHA-256 du modèle de configuration figé d’origine :
  `a156dee0bde4e65f4e89ceef28320faa6931ded8dc9eccab62b514b2dba69941`
  (contient les chemins de l’époque ; conservé pour la vérification
  forensique. L’exemple du dépôt garde les champs scientifiques et utilise des
  chemins relatifs).
- Environnement de parité du cas (Linux x86_64) : Python 3.12.14, NumPy 2.3.5,
  pandas 2.2.3, scikit-learn 1.8.0, SciPy 1.17.0, joblib 1.5.3,
  matplotlib 3.10.8, pyreadstat 1.3.6 ; `OPENBLAS_NUM_THREADS`,
  `OMP_NUM_THREADS` et `MKL_NUM_THREADS` à 1. pyarrow et SHAP non installés.
- Il s’agit d’un **environnement de parité du cas** : un venv isolé a installé
  ces dépendances et construit la source figée avec `--no-deps`.
  L’environnement officiel du `uv.lock` du dépôt **n’a pas** été reconstruit
  (le lock actuel fixe scikit-learn 1.9.0 sur Python ≥ 3.11) et n’a pas servi de
  base aux valeurs enregistrées.
- `uv run psyml ...` utilise l’environnement actif du dépôt. Une autre version
  ou plateforme produit un **nouveau résultat de vérification** : elle ne doit
  jamais écraser `expected/` ni relâcher les tolérances.

## 3. Données, attribution et conversion

- Données : Barshan, B. & Altun, K. (2010). *Daily and Sports Activities*
  [Dataset]. UCI Machine Learning Repository. DOI
  <https://doi.org/10.24432/C5C59F> ; page
  <https://archive.ics.uci.edu/dataset/256/daily+and+sports+activities> ;
  licence CC BY 4.0 (selon la page officielle ; aucun membre restrictif
  supplémentaire trouvé dans le ZIP). Les auteurs ne cautionnent ni PsyML ni ce
  cas.
- Structure : 8 adultes (20–30 ans), 19 activités, 60 segments de cinq secondes
  par participant et activité, 9 120 segments ; chaque segment fait 125×45. Les
  dossiers `p1..p8` sont les identifiants officiels. **Les 8 participants sont
  les unités indépendantes ; les 9 120 segments ne sont pas 9 120 personnes**,
  et des segments voisins peuvent être corrélés. L’archive ne définit aucune
  séparation entraînement/test.
- ZIP brut : 170 800 010 octets, SHA-256
  `f42ad7744ecf14151c9fa3a86dfb5b24de9d7cb7ffe956ef5de242983459c77e` ;
  téléchargé uniquement depuis l’URL officielle et entièrement vérifié avant
  lecture.
- Conversion : seuls les 9 120 membres
  `data/a01..a19/p1..p8/s01..s60.txt` sont lus (énumération stricte : membre
  manquant, dupliqué, supplémentaire hors dossier, forme autre que 125×45 ou
  valeur NaN/infinie interrompent l’exécution). Seules les six premières
  colonnes sont utilisées (accélération du torse x/y/z et vitesse angulaire du
  torse x/y/z) ; chaque segment fournit, par canal, la moyenne puis l’écart-type
  de population (`ddof=0`) dans cet ordre, soit 12 variables. Ni filtrage, ni
  ACP, ni sélection de variables, ni normalisation inter-segments.
- CSV dérivé : 2 343 871 octets, SHA-256
  `75a5fe87a58f4cfde777d914d674362b5148854a3c7064d8c686c0e25c3a047e` ;
  colonnes fixées à `segment_id,subject_id,activity` plus les 12 variables ;
  UTF-8, LF, sans index, `float_format %.17g` ; exactement 60 lignes par
  participant × activité, 480 par classe, 1 140 par participant. Une
  recompilation indépendante des 12 statistiques (`csv.reader` + `math.fsum`) a
  donné un écart absolu maximal de 1.2434497875801753e-14 (atol=rtol=1e-12).
- Les colonnes de rôle `segment_id`, `subject_id`, `activity` ne servent qu’à la
  jointure, au regroupement et à la cible ; elles n’entrent **jamais** dans
  `feature_columns`.
- Le dépôt ne redistribue pas les données : `examples/public/data/` est ignoré
  par Git et le CSV dérivé reste local. `tools/cases/prepare_dsa.py` ne
  télécharge pas, n’extrait pas toute l’arborescence et n’exécute aucun code de
  l’archive ; il publie la procédure, l’attribution et les empreintes.

## 4. Protocole figé et règles de sélection

- Extérieur : `GroupKFold(n_splits=4, shuffle=False)` sur l’ordre d’origine.
  Participants test par pli : `[4,8]`, `[3,7]`, `[2,6]`, `[1,5]` (2 280 segments
  test et 6 840 entraînement par pli).
- Intérieur : `StratifiedGroupKFold(n_splits=3, shuffle=True,
  random_state=20261001 + numéro de pli externe)` (plis numérotés à partir de 1,
  soit 20261002…20261005) ; chaque pli valide 2 participants et entraîne sur 4,
  et chaque partition contient les 19 classes.
- Choix final sur toutes les données : même `StratifiedGroupKFold(n_splits=3,
  shuffle=True, random_state=20261001)` ; il ne fournit **aucun nouveau score
  de test non biaisé**.
- Chaque ajustement construit un pipeline neuf `ColumnTransformer(numeric) →
  SimpleImputer(strategy='median') → StandardScaler → estimateur`, ajusté
  uniquement sur les lignes d’entraînement correspondantes.
- Candidats : ordre des familles `['dummy','logistic_regression']` ;
  `DummyClassifier(strategy='prior', random_state=20261001)` ;
  `LogisticRegression(C∈[0.1, 1.0], solver='lbfgs', max_iter=2000, tol=1e-8,
  class_weight=None, fit_intercept=True, random_state=20261001)` ;
  `max_candidates=2` s’applique par famille et ne déclenche jamais
  d’échantillonnage aléatoire.
- Sélection : moyenne non pondérée des balanced accuracies internes ;
  remplacement uniquement sur une valeur **strictement supérieure**, égalité
  exacte conservant le premier candidat/famille ; les scores externes ne
  départagent jamais. Un pli interne en échec invalide le candidat (pas de
  moyenne sur les plis réussis) ; si le gagnant interne échoue à l’extérieur,
  toute la procédure échoue et aucune autre famille n’est substituée.
- Volume : 45 ajustements internes + 8 ajustements externes par famille + 1
  ajustement final = 54 par flux complet ; CPU uniquement, un seul thread de
  bibliothèque numérique, sans SHAP.

## 5. Rôles et frontières de code

| Exécution | Emplacement | Rôle | Frontière |
| --- | --- | --- | --- |
| CLI native (principale) | `uv run psyml run --config ...` | Seul résultat principal | Entrée de production ; source non modifiée |
| Référence indépendante | [`tools/cases/reference_dsa.py`](../tools/cases/reference_dsa.py) | Reconstruit le protocole avec les API publiques scikit-learn | **N’importe jamais psyml** et ne copie pas sa chaîne d’appel ; vérification statique des imports en test et revue du flux de données |
| Complément d’observation | [`tools/cases/observe_psyml_dsa.py`](../tools/cases/observe_psyml_dsa.py) | Complète l’appartenance des plis et l’audit des 54 ajustements | Ne fait qu’envelopper et enregistrer les appels de production ; ne change ni entrées, ni plis, ni modèles, ni seuils ; **pas une implémentation indépendante** |
| Acceptation comparative | [`tools/cases/compare_dsa.py`](../tools/cases/compare_dsa.py) | 26 contrôles numériques + 4 structurels + 2 d’export | Peut importer PsyML pour inspecter la persistance ; conserve les écarts et sort en code non nul en cas d’échec |
| Contrôles d’ingénierie | [`tools/cases/check_dsa_controls.py`](../tools/cases/check_dsa_controls.py) | Audit du row-split, perturbations du pli 1, canari de labels mélangés | Diagnostique seulement ; les scores perturbés ne servent jamais à réviser le protocole ni à choisir un modèle |

La référence indépendante partage les estimateurs, séparateurs et métriques
scikit-learn avec PsyML : elle valide le flux, pas les solveurs. Le comparateur
recalcule en outre la balanced accuracy et le macro-F1 à partir des comptes
TP/FN/FP par classe (contrôle au niveau des métriques, pas un deuxième
ajustement indépendant).

Le comparateur ne compare jamais « seulement certaines colonnes » : chaque
colonne de production doit exister dans la référence et est contrôlée ; un écart
du nombre de lignes, une colonne de production manquante ou une colonne
supplémentaire non enregistrée dans la référence échoue. Les champs numériques
suivent des règles explicites : tout ±Inf, un NaN d’un seul côté, ou un NaN dans
une **statistique qui doit être finie** échoue même si les deux côtés
concordent ; seules deux catégories de valeurs vides sont admises — les
diagnostics enregistrés comme pouvant être vides (par exemple une colonne
`error` vide) et les scores NaN d’un candidat explicitement `status=failed` ; une
discordance de dtype (numérique vs texte) échoue aussi. La colonne de diagnostic
`inner_scores` propre à la référence n’est pas ignorée : elle doit contenir une
liste finie de scores de la longueur des plis internes pour chaque candidat
terminé, dont la moyenne non pondérée égale le score déclaré. Cette politique
vient d’un premier correctif : l’auxiliaire initial exigeait des ensembles de
colonnes identiques, prenait le diagnostic de la référence pour une divergence
et sérialisait un `inf` dans le JSON, interrompant l’exécution ; le
comportement retenu est couvert par trois groupes de tests de régression dans
`tests/test_public_dsa_case_contract.py` : aucun masquage (colonnes manquantes/
non enregistrées, dérive numérique, nombre de lignes), rejet des valeurs non
finies (NaN unilatéral, NaN de statistique, Inf, dtype) et validation du
diagnostic de la référence.

## 6. Conventions de métriques

- Principal : moyenne non pondérée, sur les plis externes, de la balanced
  accuracy de la procédure sélectionnée en interne. L’écart-type entre plis
  utilise `ddof=0` et reste descriptif, sans erreur type ni intervalle de
  confiance.
- Secondaire : même agrégation pour l’accuracy et le macro-F1
  (`zero_division=0`) ; matrice de confusion hors pli mise en commun
  (explicitement « pooled ») ; différences appariées procédure−Dummy ; balanced
  accuracy par participant (descriptive).
- **La moyenne des plis et le « pooled » ne se mélangent pas** : des plis
  équilibrés et de taille égale font coïncider accuracy/BA pooled avec la
  moyenne des plis, mais le macro-F1 diffère (pooled 0.5702035749465654 contre
  0.5513874769696934).
- Le modèle final est ajusté sur toutes les lignes analysées ; sa relecture
  vérifie la persistance et le schéma, **pas** la validité externe, et ne peut
  pas être présenté comme un score de généralisation.

## 7. Valeurs enregistrées et trace de sélection (cas figé)

| Grandeur | Valeur |
| --- | --- |
| Pli externe 1 (participants test 4, 8), balanced accuracy | 0.5394736842105263 |
| Pli externe 2 (participants test 3, 7), balanced accuracy | 0.4986842105263158 |
| Pli externe 3 (participants test 2, 6), balanced accuracy | 0.6644736842105264 |
| Pli externe 4 (participants test 1, 5), balanced accuracy | 0.5934210526315788 |
| **Balanced accuracy principale (moyenne des plis)** | **0.5740131578947368** |
| Macro-F1 moyen des plis | 0.5513874769696934 |
| Écart-type entre plis (ddof=0, BA / macro-F1) | ≈ 0.062103 / ≈ 0.068311 |
| Dummy du même pli | 1/19 = 0.05263157894736842 |
| Différence moyenne procédure − Dummy | 0.5213815789473684 |
| Macro-F1 pooled hors pli | 0.5702035749465654 |
| Étendue par participant | ≈ 0.4553–0.6658 (8 participants, descriptif) |

Les quatre plis externes et le choix final ont tous retenu
`logistic_regression, C=1.0`, avec des moyennes internes de
0.5381578947368421, 0.577485380116959, 0.5399122807017545 et
0.508187134502924, et un score final de 0.5450779727095517. Le classement des
familles à l’extérieur est exploratoire : ce n’est pas un nouveau score «
meilleur modèle » non biaisé et cela ne prouve pas l’inutilité de comparer des
familles.

## 8. Résultats d’acceptation et contrôles

| Catégorie | Nombre | Résultat | Preuve |
| --- | --- | --- | --- |
| Acceptation numérique | 26 | Réussi | `checks.json` du comparateur |
| Contrôles structurels | 4 | Réussi | Partitions disjointes couvrant les lignes source ; 19 classes par partition ; portées internes strictement incluses dans l’entraînement externe ; colonnes de rôle exclues |
| Contrôles d’export | 2 | Réussi | Colonnes de probabilité dans l’ordre de `classes_` ; métadonnées du modèle enregistré identiques au modèle final indépendant |
| Contrôles sur données réelles | 7 | Réussi | L’auditeur de groupes supplémentaire rejette le row-split ordinaire ; la rotation des labels du pli externe 1 ne change ni scores/choix internes ni statistiques d’entraînement ni prédictions/probabilités de test ; l’ajout de +1000 aux variables du pli 1 ne change ni statistiques ni sélection interne |
| Canari de labels mélangés | 6 + 1 | Réussi | Le flux imbriqué complet avec labels mélangés par participant concorde avec la référence ; BA = 0.0532894736842105, sous le seuil d’alerte prédéfini 0,10 ; le mélange ne touche que la colonne cible (1 contrôle octet) |

Autres faits clés : les 9 120 prédictions hors pli concordent ligne à ligne ;
les lignes d’entraînement, familles, paramètres et statistiques de prétraitement
des 54 ajustements s’alignent (statistiques à 1e-12, coefficients/intercepts à
0) ; l’écart maximal de probabilité PsyML-référence est 0 ; la CLI native et la
relecture d’observation produisent des fichiers identiques ; le modèle
enregistré rechargé de façon fiable reproduit les classes et probabilités du
modèle final indépendant, résiste à la réorganisation des colonnes et refuse une
variable manquante ; l’empreinte du CSV d’entrée correspond à la valeur figée.
Les tests existants du dépôt sur la perturbation du classement externe et le
repli en cas d’échec (`tests/test_nested_family_selection.py`) ont été
**réellement exécutés** pendant cette intégration, pas seulement cités.

Fuites de groupes : PsyML avertit lorsqu’une colonne de groupe accompagne un
k-fold ordinaire, mais ne le **bloque pas** en dur. Ici, l’auditeur
supplémentaire détecte l’injection de faute ; ce comportement ne doit pas être
présenté comme une protection intégrée de PsyML.

Journal d’exécution de maintenance (2026-10-01, trois environnements
enregistrés séparément) :

- **`.venv` local du dépôt** (Python 3.12.13 ; numpy 2.5.2, pandas 3.0.5,
  scikit-learn 1.9.0, scipy 1.18.1, joblib 1.6.0, matplotlib 3.11.1,
  pyarrow 23.0.1, plus l’extra explain `shap 0.52.0`) : `ruff check src tests
  tools` a réussi ; la suite par défaut `pytest -q` a rapporté **1212 réussites**
  (jeu de tests actuel ; la reprise antérieure, avant l’ajout des 3 tests de
  régression du comparateur, en rapportait 1209) ; `tools/audit_repository.py` a
  réussi l’audit. Comme l’extra explain est installé, les tests d’explication
  SHAP s’exécutent réellement ici.
- **Environnement officiel `uv.lock`** (chemin séparé,
  `UV_PROJECT_ENVIRONMENT=… uv sync --locked --group dev` ; `uv.lock` non
  modifié) : Python 3.12.13 avec les mêmes versions verrouillées
  (scikit-learn 1.9.0, joblib 1.6.0, matplotlib 3.11.1, pyarrow 23.0.1, …) ;
  `pytest -q` a rapporté **1152 réussites, 2 ignorés**, code 0. Les deux
  ignorés sont les `pytest.importorskip("shap")` au niveau module de
  `tests/test_explanation.py` et `tests/test_explanation_cli.py`, car cette
  commande n’installe volontairement pas l’extra explain — ces deux tests **ne
  sont pas comptés comme réussis**. Cet environnement n’a **pas** rejoué le cas
  DSA lui-même.
- **Environnement de parité du cas** (Python 3.12.14, scikit-learn 1.8.0,
  scipy 1.17.0, …) ne sert qu’au recalcul du cas DSA et diffère des deux
  environnements de test ; ses chiffres ne doivent pas être présentés comme ceux
  de l’environnement officiel verrouillé ou du développement local.

## 9. Reprise macOS enregistrée pendant cette intégration (preuve additive)

L’intégration a rejoué toutes les étapes avec la source figée et les mêmes
versions de parité (macOS aarch64, Python 3.12.14, scikit-learn 1.8.0, etc. ;
voir
[`expected/reverification_macos.json`](../examples/public/dsa_group_nested_v1/expected/reverification_macos.json)) :

- Codes de sortie : CLI native 0, référence 0, observation 0, comparaison 1,
  contrôles 0 ; le 1 de la comparaison vient uniquement de l’écart de métrique
  inter-plateformes ci-dessous.
- Les 26 contrôles numériques, 4 structurels et 2 d’export réussissent ; les
  9 120 prédictions hors pli sont **identiques octet pour octet** au résultat
  figé (SHA-256 de `predictions.csv` :
  `36c39a34c9317d568c79f37de17c2b566d10f24db9de0625886f3bda83022b53`) ;
  les BA par pli, la trace de sélection, le macro-F1 et les différences Dummy
  correspondent à la base figée.
- Le seul écart par rapport à la base figée concerne `roc_auc_ovr_weighted`,
  dérivé des probabilités (colonnes touchées : `fold_metrics.csv`,
  `metrics.csv`, moyenne/écart-type/min de `metrics_summary.csv`) : environ
  2,03e-7 pour les plis externes 1 et 2 et 0 pour les plis 3 et 4. Les 9 120
  probabilités hors pli diffèrent d’au plus 1.9762588500393807e-05 (maxima par
  pli : 1,98e-5, 8,70e-6, 6,56e-6, 5,23e-6 ; 97 415 des 173 280 cellules de
  probabilité dépassent 1e-10). Prédictions dures, appartenances, sélection et
  toutes les métriques fondées sur les labels sont identiques ; **cette reprise
  ne revendique pas l’équivalence numérique entre plateformes**.
- Les détails ont été alignés et vérifiés : ordre des classes
  (`probability_1..19` des deux côtés, `classes_` des deux modèles finaux =
  1..19), alignement des échantillons (séquences `row_index` et colonnes
  `fold/observed/predicted/model` identiques, 9 120 prédictions dures
  identiques octet pour octet), dépendances et configuration des bibliothèques
  numériques (configuration numpy/scipy côté macOS et enregistrements des deux
  environnements) conservés dans l’archive de preuves locale ignorée par Git ;
  les différences par ligne et par pli et les principales lignes divergentes
  figurent dans `probability_difference_details.json` et
  `probability_differences_by_row.csv`.
- Expérience d’isolation (mêmes versions de parité) : recalculer le ROC-AUC
  sous macOS à partir des **matrices de probabilité figées** reproduit les
  valeurs figées à 1,11e-16 près, donc le calcul de la métrique est cohérent
  entre plateformes ; l’écart suit les probabilités — les deux modèles finaux
  diffèrent d’au plus environ 3,07e-5 pour les coefficients, 7,08e-5 pour les
  intercepts et 3,03e-6 pour les probabilités sur toutes les données.
  Conclusion : l’écart provient du niveau des paramètres/probabilités ajustés ;
  **la cause n’est pas confirmée et pourrait être liée aux implémentations
  numériques des plateformes** — aucune expérience de cause racine au niveau
  implémentation n’a été menée, et il n’est pas écrit « causé par le chemin
  d’algèbre linéaire ». L’écart est conservé et signalé, jamais utilisé pour
  relâcher les tolérances ni remplacer la base ; le cas n’est donc pas présenté
  comme un « succès complet ».
- La BA du canari et l’empreinte du CSV mélangé correspondent aux valeurs figées
  (`e02699c680cfaa6ec91477c79fff68d7229013d7cc9f7c2acb2ddc4b0d961d86`) ; le
  décalage +1000 des variables a modifié 2 122 prédictions, même nombre que
  sous Linux.
- Après l’exécution, les 423 fichiers du manifeste figé ont été contrôlés :
  aucun fichier Python/GUI/test/lock ne diffère ; seuls les 3 documents publics
  intentionnellement modifiés par cette intégration (`README.md`,
  `docs/TESTING.md`, `examples/public/README.md`) diffèrent.
- Toutes les étapes ont produit un stderr vide ; le `warnings.json` de la CLI
  conserve la mise en garde scientifique (les métriques principales évaluent la
  procédure de sélection imbriquée ; le classement des familles est
  exploratoire), tandis que les listes de la référence, de l’observation et des
  contrôles sont vides, sans ConvergenceWarning.

Cette reprise est une preuve supplémentaire inter-plateformes ; elle ne
remplace pas la base Linux figée. Windows et l’environnement officiel verrouillé
restent non exécutés.

## 10. Avertissements, écarts et échecs conservés

- La première reprise portable du paquet de cas s’est arrêtée au seuil strict de
  stderr car une analyse de polices neuve ne trouvait pas de dossier de cache
  inscriptible ; la comparaison numérique avait réussi, les journaux ont été
  conservés, seuls les chemins de cache des sous-processus ont été redirigés
  vers un dossier inscriptible avant une reprise complète réussie. Il s’agit de
  portabilité du lanceur, pas d’une erreur de logique d’entraînement.
- La première comparaison a produit un avertissement de diagnostic All-NaN dû à
  une colonne `error` vide lue comme entièrement NaN ; seul le diagnostic de
  rapport a été corrigé, sans changement de modèle, données, sélection,
  tolérances ni résultats. Les outils du dépôt ignorent les diagnostics non
  finis/vides et ne traitent pas une colonne d’erreur vide comme un échec
  scientifique.
- Aucun défaut n’a nécessité de modification du cœur numérique de PsyML.

## 11. Limite de lisibilité de la figure native

L’export natif de la matrice de confusion à 19 classes est dense à sa taille
compacte par défaut : annotations à trois chiffres voisines et étiquettes d’axe
serrées, certains chiffres se touchant visuellement. Le CSV sous-jacent, les
totaux et les métriques sont corrects. C’est une limite réelle de lisibilité de
l’export, **pas un échec numérique et pas une preuve que l’interface a été
testée**. La figure d’origine est conservée ; une redessin indépendante
clairement étiquetée (même CSV, 361 cellules vérifiées par programme) en est
distincte et n’est pas une sortie de production. Ce dépôt ne contient aucune
correction graphique de production ; toute modification de figsize/étiquetage
adaptatif exige d’abord un plan minimal et une vérification trilingue
multi-classes.

## 12. Ce qui n’a pas été exécuté

- La suite Python complète pour ce cas est couverte par le journal de
  maintenance : cette intégration a réellement exécuté `ruff check src tests
  tools` (réussi), la suite par défaut dans le `.venv` local (`pytest -q` :
  1212 réussites, dont les 19 nouveaux tests contractuels et les tests existants
  de perturbation du classement externe/repli) et `tools/audit_repository.py`
  (réussi) ; l’environnement officiel `uv.lock` a été créé séparément et a
  exécuté la suite selon la convention du dépôt (1152 réussites + 2 ignorés
  explain-extra, voir section 8), mais n’a **pas** rejoué le cas DSA lui-même.
- Godot/interface, fenêtres réelles, paquets autonomes Windows et macOS (la
  reprise macOS utilisait un environnement source, pas une application
  empaquetée).
- SHAP/explication, formats autres que CSV, étude dédiée des tolérances
  inter-plateformes, études utilisateurs, validation externe et audit de
  sécurité complet.
- Le retéléchargement et la conversion du ZIP brut complet (le CSV dérivé fourni
  a été utilisé ; `prepare_dsa.py` est couvert par des tests contractuels sur
  des ZIP synthétiques : énumération stricte, empreinte, forme, valeurs finies,
  refus de comptage).

## 13. Commandes de reprise et conditions d’échec

```bash
# 1) Facultatif : reconstruire le CSV dérivé depuis le ZIP officiel (contrôles stricts, aucun code de l’archive exécuté)
uv run python tools/cases/prepare_dsa.py --archive <official.zip> --output-dir examples/public/data
# 2-5) CLI principale, référence indépendante, observation, comparaison, contrôles :
#      la séquence complète se trouve dans examples/public/dsa_group_nested_v1/README.md
```

Conditions d’échec : toute empreinte incorrecte, ensemble de membres inattendu,
valeur non finie, forme/comptage erroné, chevauchement de groupes, égalité
départagée par approximation, métriques/probabilités hors tolérance, relecture
du modèle incohérente, BA du canari > 0,10 ou stderr non examiné. Ne jamais «
corriger » un échec en changeant les tolérances, en supprimant des plis, en
augmentant les itérations, en changeant C, en échangeant les données ou en
choisissant une autre validation. La CLI et chaque outil exigent un **nouveau
dossier de sortie vide** ; les résultats existants ne sont jamais écrasés.
`input_path`/`output_dir` se résolvent par rapport au répertoire courant du
processus.

## 14. Limites des affirmations

- Les enregistrements publics de huit participants ne soutiennent aucune
  conclusion clinique, de population générale ou naturaliste ; ce cas n’est pas
  une validation externe.
- La référence indépendante partage les solveurs scikit-learn ; le canari est
  une perturbation d’ingénierie unique, pas un test de permutation, pas une
  estimation du taux de faux positifs, ni une preuve d’absence de fuite.
- Les résultats établissent la conformité numérique et la reproductibilité du
  flux testé dans l’environnement enregistré uniquement ; ils ne revendiquent
  ni nouvel algorithme, ni performance de pointe, ni réduction de l’erreur des
  utilisateurs.
