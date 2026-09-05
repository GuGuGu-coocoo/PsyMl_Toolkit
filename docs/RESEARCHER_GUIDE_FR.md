# Guide de référence : modèles, métriques, résultats et terminologie

Version du code documentée : **v0.1.1-rc1**. Les versions de l’environnement et des dépendances figurent dans `analysis_manifest.json` pour chaque analyse.

[Retour au README français](../README.md#french) · [中文](RESEARCHER_GUIDE_ZH.md) · [English](RESEARCHER_GUIDE_EN.md) · **Français**

Ce guide explique les concepts utilisés dans l’implémentation actuelle de PsyML Toolkit. Consultez-le pour configurer une analyse ou interpréter ses résultats. Les noms de code correspondent aux clés de configuration et aux colonnes CSV. Le texte se lit hors ligne ; les références externes nécessitent une connexion. Les formules courtes servent à comprendre, sans exiger de calcul manuel. Si votre lecteur Markdown ne les affiche pas, utilisez les explications qui les accompagnent.

La pertinence d’un modèle dépend de la question de recherche, de la structure des données et du plan de validation. Il n’existe ni modèle universellement optimal ni seuil de performance universellement acceptable. Le projet réalise des prédictions ; il n’établit pas automatiquement de causalité, de significativité statistique ou de règle de décision clinique. Les résumés et rapports automatiques ne sont pas garantis exacts et doivent être vérifiés par les chercheurs.

## Navigation

- [1. Données et prétraitement](#data)
- [2. Modèles disponibles](#models)
- [3. Métriques de classification et de régression](#metrics)
- [4. Validation, réglage et modèle final](#validation)
- [5. Lire les fichiers de résultats et les figures](#results)
- [6. Paramètres et terminologie](#glossary)
- [7. Interprétations erronées et ordre de vérification](#checklist)
- [8. Implémentation et lectures complémentaires](#references)

<a id="data"></a>

## 1. Données et prétraitement

| Terme | Sens dans ce projet |
| --- | --- |
| Classification | Prédire des catégories distinctes, par exemple une condition A/B ; au moins deux classes cibles sont nécessaires. Des étiquettes numériques ne transforment pas automatiquement le problème en régression |
| Régression | Prédire une valeur numérique, par exemple un score d’échelle ; les erreurs s’expriment dans l’unité de la cible |
| Cible / variable à prédire, `target_column` | Colonne dont on prédit la valeur. Elle fournit les réponses d’apprentissage et est exclue des prédicteurs |
| Prédicteur / caractéristique, `feature_columns` | Colonne d’entrée utilisée pour prédire. Un identifiant ou une information disponible seulement après le résultat peut introduire une fuite |
| Identifiant de groupe, `group_column` | Relie les lignes d’un même participant, foyer ou centre. Il est exclu des prédicteurs et se distingue des classes de la cible |
| Ligne / observation indépendante | Dix mesures d’un participant ne sont pas dix participants indépendants. La validation doit respecter cette dépendance |
| Pipeline | Enchaîne imputation, mise à l’échelle, encodage et estimateur, réajustés dans chaque partition d’apprentissage |

**Valeurs manquantes :** les lignes dont la cible manque sont d’abord supprimées. Avec `drop`, les lignes présentant encore une valeur manquante dans les prédicteurs sélectionnés, la cible ou le groupe sont supprimées ; une colonne administrative non sélectionnée ne déclenche pas cette suppression. Sinon, les prédicteurs numériques sont imputés par moyenne, médiane ou mode, tandis que les prédicteurs catégoriels utilisent toujours le mode. Un identifiant de groupe encore manquant provoque une erreur ; le groupe n’est pas deviné. L’imputation ne prouve pas l’absence de biais lié au mécanisme de données manquantes.

**Mise à l’échelle :** `standard` utilise les statistiques d’apprentissage, `z = (x − moyenne_train) / écart_type_train`. `minmax` utilise le minimum et le maximum d’apprentissage. Une nouvelle valeur hors de cet intervalle peut être transformée en une valeur hors de [0, 1]. `none` désactive la mise à l’échelle. Les distances, la régularisation et l’optimisation par gradient sont souvent sensibles aux unités ; les arbres ne dépendent généralement pas de cette transformation.

**Encodage one-hot :** les prédicteurs catégoriels deviennent des colonnes indicatrices. Le code distingue les entrées numériques et catégorielles par leur type de données. Des catégories nominales enregistrées comme nombres 1/2/3 seront donc traitées comme numériques si rien n’est corrigé lors de la préparation. L’encodeur ignore les catégories nouvelles ; cela ne signifie pas que leur sens a été appris.

Ces détails suivent le [pipeline de prétraitement](../src/psyml/preprocessing/pipeline.py) et la [préparation des données dans le moteur](../src/psyml/runner.py).

<a id="models"></a>

## 2. Modèles disponibles

Le projet propose 12 options de classification et 11 de régression, soit 17 noms de code distincts. Un nom commun aux deux tâches peut désigner des estimateurs différents. L’interface filtre les modèles selon la tâche. Les limites ci-dessous expliquent leur comportement et ne constituent pas une règle de sélection automatique. Voir la [fabrique de modèles](../src/psyml/models/factory.py) et le [catalogue](../src/psyml/models/catalog.py).

### Disponibles pour les deux tâches

| Modèle et code | Principe | Interprétation et limites |
| --- | --- | --- |
| Modèle de référence Dummy, `dummy` | Ignore les relations avec les prédicteurs. En classification, utilise les fréquences de classes ou une règle majoritaire ; en régression, la moyenne ou la médiane, selon `strategy` | C’est un comparateur utile. Un modèle complexe doit être comparé à cette référence sous le même plan de validation |
| K plus proches voisins, `knn` | Utilise K observations d’apprentissage similaires : vote en classification, moyenne en régression, éventuellement pondérés par la distance | Sensible à l’échelle et à la distance. En grande dimension, les voisinages peuvent être peu informatifs ; K ne doit pas dépasser l’effectif du pli d’apprentissage concerné |
| Arbre de décision, `decision_tree` | Partitionne les observations par conditions successives, puis prédit dans les feuilles | Représente des seuils et interactions. Un arbre profond peut surajuster ; de petites modifications des données peuvent changer sa structure |
| Forêt aléatoire, `random_forest` | Combine des arbres comportant de l’aléa, en moyennant probabilités de classe ou prédictions numériques | Souvent plus stable qu’un arbre unique. Ajouter des arbres ne corrige pas un mauvais plan ; l’extrapolation en régression reste généralement limitée |
| Gradient boosting, `gradient_boosting` | Ajoute des arbres successifs afin d’améliorer la fonction de perte | Taux d’apprentissage, nombre d’arbres et profondeur interagissent. Une recherche élargie peut augmenter le coût et le risque de surajustement |
| Perceptron multicouche, MLP, `mlp` | Apprend une relation par couches de transformations pondérées et d’activations non linéaires | Vérifier l’échelle, l’effectif et les avertissements de convergence. Un réseau neuronal n’est pas nécessairement meilleur sur un petit échantillon |

### Classification uniquement

| Modèle et code | Principe | Interprétation et limites |
| --- | --- | --- |
| Régression logistique, `logistic_regression` | Modélise les probabilités de classe, généralement avec régularisation ; malgré son nom, cette option est un classificateur | La frontière de base est linéaire dans les caractéristiques transformées. Les coefficients n’établissent pas automatiquement causalité ou significativité |
| Classification par machine à vecteurs de support, `svm` | Recherche une frontière à grande marge ; un noyau peut représenter une frontière non linéaire | Sensible à l’échelle et à `C`. Un score de décision n’est pas une probabilité calibrée |
| Bayes naïf gaussien, `gaussian_nb` | Suppose l’indépendance conditionnelle des caractéristiques dans chaque classe et des distributions gaussiennes | De fortes corrélations ou des distributions très éloignées de l’hypothèse gaussienne peuvent fragiliser le modèle. Une probabilité fournie n’est pas nécessairement calibrée |
| Analyse discriminante linéaire, LDA, `lda` | Modélise des classes gaussiennes partageant une matrice de covariance, avec une frontière linéaire | Les hypothèses de distribution et de covariance comptent ; attention à la grande dimension, aux petits effectifs et à la colinéarité |
| Analyse discriminante quadratique, QDA, `qda` | Autorise une covariance différente pour chaque classe, avec une frontière quadratique | Estime davantage de quantités que LDA. De petites classes ou des variables redondantes peuvent rendre la covariance instable |
| Empilement de modèles, stacking, `stacking` | Entraîne un méta-modèle sur des prédictions obtenues par ajustement croisé des modèles de base | Ici, les bases sont KNN, forêt aléatoire et SVM ; le méta-modèle est une régression logistique. Les pipelines complets sont ajustés par croisement, en respectant les groupes lorsqu’ils sont renseignés. Le coût augmente |

Pour comprendre la régression logistique binaire :

$$
p(y=1\mid x)=\frac{1}{1+\exp[-(b+\beta^\top x)]}.
$$

Ici, 1 représente la classe positive mathématique, `b` l’ordonnée à l’origine, `β` les coefficients et `x` les caractéristiques prétraitées. Cette écriture ne signifie pas que l’interface permet de choisir librement une classe positive clinique. L’objectif d’apprentissage peut aussi différer de la métrique de sélection, comme F1.

### Régression uniquement

| Modèle et code | Principe | Interprétation et limites |
| --- | --- | --- |
| Régression linéaire, `linear_regression` | Prédit une somme pondérée de caractéristiques en minimisant les résidus au carré | Sa forme de base ne représente pas automatiquement toute non-linéarité ; la colinéarité peut déstabiliser les coefficients |
| Régression Ridge, `ridge` | Ajoute une pénalité L2 qui réduit les coefficients linéaires | Conserve généralement plusieurs coefficients non nuls ; augmenter `alpha` renforce la pénalité |
| Régression Lasso, `lasso` | Ajoute une pénalité L1 pouvant annuler certains coefficients | Un coefficient nul dépend de cet ajustement et de cette pénalité ; ce n’est pas une preuve d’absence de rôle scientifique |
| Elastic Net, `elastic_net` | Combine les pénalités L1 et L2 ; `l1_ratio` règle leur mélange | Interpréter prudemment la sélection avec des prédicteurs corrélés ; considérer conjointement intensité et proportion |
| Régression par vecteurs de support, `svr` | Ajuste avec une zone de tolérance ε, éventuellement à l’aide d’un noyau | `epsilon` est un paramètre de tolérance dans l’échelle de la cible, pas un intervalle de confiance ; échelle, `C` et noyau influencent le résultat |

La prédiction linéaire s’écrit `ŷ = b + Σ βⱼxⱼ`. Une représentation conceptuelle de la régularisation est :

$$
\text{objectif}=\text{perte d’ajustement}+\lambda\times\text{pénalité},\qquad
L_1=\sum_j|\beta_j|,\quad L_2=\sum_j\beta_j^2.
$$

Ce n’est pas une fonction exacte commune à tous les estimateurs : normalisation de la perte et sens des paramètres varient. Des valeurs identiques d’`alpha` ne garantissent pas une régularisation équivalente entre modèles. Un `C` plus petit renforce généralement la régularisation en SVM et en régression logistique. Voir les références scikit-learn sur les [modèles linéaires](https://scikit-learn.org/stable/modules/linear_model.html) et les [ensembles](https://scikit-learn.org/stable/modules/ensemble.html).

<a id="metrics"></a>

## 3. Métriques de classification et de régression

Les formules décrivent une partition de test. L’agrégation entre plis est expliquée à la fin de cette section. Les clés suivent l’[implémentation des métriques](../src/psyml/evaluation/metrics.py).

### Métriques de classification

Pour une classe opposée à toutes les autres, TP désigne les vrais positifs, FP les faux positifs, FN les faux négatifs et TN les vrais négatifs.

$$
\mathrm{Precision}=\frac{TP}{TP+FP},\qquad
\mathrm{Recall}=\frac{TP}{TP+FN},\qquad
F_1=\frac{2TP}{2TP+FP+FN}.
$$

La précision indique la proportion correcte parmi les prédictions d’une classe. Le rappel, ou sensibilité pour une classe positive donnée, indique la proportion de ses membres retrouvés. La précision se distingue de l’exactitude globale, appelée accuracy.

| Clé de sortie | Sens et direction | Interprétation |
| --- | --- | --- |
| `accuracy`, exactitude globale | Prédictions correctes / total ; plus élevé est meilleur | Peut masquer les erreurs sur une classe minoritaire |
| `balanced_accuracy`, exactitude équilibrée | Moyenne non pondérée du rappel des classes réelles ; plus élevé est meilleur | Métrique de sélection par défaut en classification. En binaire avec les deux classes présentes, moyenne de la sensibilité et de la spécificité |
| `precision_macro` / `recall_macro` / `f1_macro` | Calcul par classe, puis moyenne donnant le même poids aux classes ; plus élevé est meilleur | Petite et grande classe ont le même poids. Le F1 macro n’est pas la moyenne harmonique de la précision macro et du rappel macro |
| `precision_weighted` / `recall_weighted` / `f1_weighted` | Moyenne des métriques par classe, pondérée par les effectifs réels du test ; plus élevé est meilleur | Les grandes classes pèsent davantage. En classification actuelle à étiquette unique, le rappel pondéré égale accuracy |
| `roc_auc`, aire sous la courbe ROC | Capacité des scores à ordonner les deux classes ; plus élevé est meilleur | Ce n’est ni accuracy ni la calibration. La valeur 0,5 est une référence sans discrimination pour l’AUC, pas un niveau de hasard universel |
| `roc_auc_ovr_weighted` | AUC multiclasse « un contre le reste », pondérée par les effectifs des classes | Produite uniquement si des probabilités sont disponibles et si les ensembles de classes du test et de l’apprentissage coïncident |

On peut écrire `macro = Σ m_c / C` et `weighted = Σ (n_c / n) m_c`, où `m_c` est la métrique d’une classe, `n_c` son effectif réel dans le test et `C` le nombre de classes incluses dans la moyenne. Ces poids concernent les classes, pas les plis de validation.

**Conventions du projet :** précision, rappel et F1 utilisent `zero_division=0`. L’AUC binaire traite `classes_[1]` de l’estimateur comme classe positive, avec les probabilités si disponibles, sinon un score de décision disponible. L’interface ne propose actuellement aucun sélecteur séparé de classe positive ou de seuil de décision. Si les classes du test et de l’apprentissage diffèrent, l’AUC est omise. Une AUC absente signifie que ses conditions ne sont pas réunies ; ne la remplacez pas par zéro. Les définitions générales figurent dans le [guide des métriques de scikit-learn](https://scikit-learn.org/stable/modules/model_evaluation.html).

**Petit exemple :** un test contient 90 observations négatives et 10 positives. Tout prédire comme négatif donne accuracy = 0,90, rappel positif = 0 et balanced accuracy = 0,50. Une exactitude élevée peut donc coexister avec l’omission de tous les positifs. Ce sont des valeurs illustratives, pas des seuils conseillés pour une étude.

### Métriques de régression

Soient `yᵢ` la valeur observée, `ŷᵢ` la prédiction, `n` l’effectif du test courant et `ȳ` la moyenne observée dans cette partition de test.

$$
\mathrm{MAE}=\frac{1}{n}\sum_{i=1}^{n}|y_i-\hat y_i|,\qquad
\mathrm{RMSE}=\sqrt{\frac{1}{n}\sum_{i=1}^{n}(y_i-\hat y_i)^2}.
$$

$$
R^2=1-\frac{\sum_i(y_i-\hat y_i)^2}{\sum_i(y_i-\bar y)^2}.
$$

| Clé de sortie | Direction et unité | Interprétation |
| --- | --- | --- |
| `mae`, erreur absolue moyenne | Plus petit est meilleur, minimum 0 ; unité de la cible | Écart absolu moyen par rapport à l’observation |
| `rmse`, racine de l’erreur quadratique moyenne | Plus petit est meilleur, minimum 0 ; unité de la cible | Accentue les grandes erreurs. Métrique de sélection par défaut en régression ; ce n’est pas l’écart-type entre plis |
| `r2`, coefficient de détermination | Plus élevé est meilleur, maximum 1 ; sans unité, peut être négatif | Zéro correspond à l’erreur quadratique de la moyenne observée du test. Une valeur négative n’est ni un bogue ni une preuve de corrélation négative |

La formule ordinaire de R² ne s’applique pas si le dénominateur est nul. L’appel actuel utilise le traitement fini par défaut de `r2_score` dans scikit-learn : avec une cible constante, une prédiction parfaite donne 1, sinon 0. R² n’est pas défini avec moins de deux observations de test. Les métriques secondaires non définies sont exclues et cela se reflète dans le nombre de plis valides ; une métrique de sélection non définie peut faire échouer l’analyse. R² n’est pas en général interchangeable avec le carré de la corrélation de Pearson.

**Petit exemple :** observations `[1, 2, 3]`, prédictions `[1, 2, 2]` : MAE = 1/3, RMSE = √(1/3), R² = 0,5. Cet exemple explique les formules ; ce n’est pas un effectif suffisant pour une étude.

### Sélection et agrégation

- La sélection interne propose en classification `balanced_accuracy` (défaut), `f1_macro`, `accuracy` ; en régression `rmse` (défaut), `mae`, `r2`. Toutes les métriques produites ne sont pas des objectifs de réglage disponibles.
- `metrics.csv` contient la **moyenne non pondérée des métriques des plis externes de la validation principale (ou du sous-dossier indépendant consulté)**, plutôt que des métriques recalculées sur toutes les prédictions réunies. Des effectifs de plis différents peuvent modifier la comparaison ; une métrique non linéaire comme RMSE peut différer même avec des plis de même taille.
- Dans `metrics_summary.csv`, `std` utilise `ddof=0` : pour K plis valides, `std = √[Σ(m_k − moyenne)² / K]`. `n_folds` indique le nombre de plis valides pour cette métrique. Les plis partagent des informations d’apprentissage ; cet écart-type n’est ni une erreur standard ni un intervalle de confiance (IC).
- Une validation holdout ne contient qu’une partition externe de test ; un std nul n’implique donc pas l’absence d’incertitude.

<a id="validation"></a>

## 4. Validation, réglage et modèle final

### Six stratégies de validation

| Valeur de configuration | Usage | Limites de l’implémentation actuelle |
| --- | --- | --- |
| `holdout` | Une partition apprentissage/test | Avec un groupe renseigné, découpage par groupe : `test_size` est une proportion de groupes, pas nécessairement de lignes. La classification sans groupes est stratifiée si possible ; les très petits échantillons peuvent échouer |
| `k_fold` | Chacun des K plis sert à son tour de test | Mélange les lignes ; renseigner un groupe ne rend pas la partition externe disjointe par groupe |
| `stratified_k_fold` | Cherche à maintenir les proportions de classes | Classification uniquement ; n’isole pas les groupes externes |
| `group_k_fold` | Garde les lignes d’un groupe ensemble | Nécessite assez de groupes indépendants ; les proportions de classes peuvent varier |
| `stratified_group_k_fold` | Cherche à équilibrer les classes tout en séparant les groupes | Classification uniquement ; ne garantit pas chaque classe dans chaque pli |
| `leave_one_group_out` | Teste sur un groupe entier à chaque itération | Au moins deux groupes ; leur nombre détermine les plis, pas `n_splits`. La recherche interne nécessite aussi assez de groupes d’apprentissage |

**Renseigner une colonne de groupe ne rend pas automatiquement toutes les validations externes sensibles aux groupes.** Les mesures répétées exigent une stratégie adaptée à la question. Il n’existe actuellement aucun découpage dédié aux séries temporelles. Voir le [guide général de validation croisée](https://scikit-learn.org/stable/modules/cross_validation.html).

### Ordre de la sélection imbriquée

1. Mettre de côté le pli externe de test courant.
2. Utiliser une validation interne uniquement dans l’apprentissage externe pour choisir famille et paramètres ; les groupes renseignés sont isolés dans les plis internes.
3. Ajuster ce choix sur l’apprentissage externe, puis prédire son test. Les scores externes ne permettent pas de remplacer la famille sélectionnée en interne.
4. Agréger les résultats externes pour évaluer la procédure complète. Les familles retenues peuvent différer entre plis.
5. Refaire la sélection interne sur toutes les données analysées, puis ajuster le modèle final. Cela choisit les paramètres du dernier ajustement sans produire un nouveau score de test indépendant.

Une famille fixée à l’avance avec un seul candidat de paramètres ne nécessite pas de recherche interne. Plusieurs familles sont toujours comparées en interne lorsque `tuning_mode="none"`. Un candidat échouant dans un pli interne devient inéligible ; les égalités suivent l’ordre des familles/candidats dans la configuration. Le projet utilise `selection_protocol="nested_family_v1"` ; voir le [moteur](../src/psyml/runner.py) et l’[exemple de validation imbriquée et non imbriquée](https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html).

La **validation principale** est choisie dans le menu de l’interface et enregistrée en premier dans `validation_strategies`. Elle détermine les métriques principales, les prédictions et les figures. Les autres stratégies sont des **analyses de sensibilité** permettant d’examiner la dépendance au plan de validation, pas de choisir après coup le résultat le plus favorable. Vous pouvez aussi choisir **sans validation principale**, avec `primary_validation: null`. La même procédure imbriquée s’exécute séparément pour chaque validation, avec des sorties complètes dans `validations/<stratégie>/`. La page de résultats demande un choix sans privilégier automatiquement une validation. Aucun score principal ni modèle gagnant global n’est produit. `completed_with_errors` indique des échecs partiels ; les succès restent accessibles. Un échec total ne crée pas de marqueur de succès. L’omission du champ conserve la première validation comme principale ; un nom la désigne explicitement.

<a id="results"></a>

## 5. Lire les fichiers de résultats et les figures

Les fichiers ci-dessous correspondent à une analyse avec validation principale ou à chaque sous-dossier réussi du mode indépendant. En mode indépendant, le résumé racine utilise `role=independent`. En Python, les résultats complets sont dans `validation_results[stratégie]` ; le modèle global est None et ses métriques sont vides.

### Trouver un fichier selon sa question

| Question | Fichiers | Interprétation |
| --- | --- | --- |
| Y a-t-il des risques ou des échecs ? | `warnings.json`, `result.json` | Lire les avertissements d’abord. Seule une sortie completed correspond à une exécution entièrement réussie ; des avertissements peuvent subsister |
| Quelle performance hors apprentissage et quelle variabilité ? | `metrics.csv`, `metrics_summary.csv`, `fold_metrics.csv` | Métriques principales, effectifs valides et variabilité, puis détail par pli |
| Une autre validation prédéfinie est-elle cohérente ? | `validation_summary.csv` | Séparer primary et sensitivity ; ne pas retenir le meilleur score entre plans |
| Quel modèle a finalement été retenu ? | `best_model`, `best_parameters` dans `result.json` | Sélection finale sur toutes les données, pas nécessairement le modèle utilisé dans chaque pli externe |
| Quelles familles méritent un examen ultérieur ? | `model_comparison.csv` | Rangs exploratoires recommençant dans chaque validation ; le rang 1 peut différer du modèle final |
| Quel choix dans chaque pli ? | `selection_trace.csv` | Distingue `outer_training_fold` et `final_full_data` ; `outer_fold=0` désigne la sélection sur toutes les données, pas un pli de test numéro zéro |
| Pourquoi un candidat a-t-il été choisi ou rejeté ? | `parameter_search.csv` | Examiner score interne, paramètres, status et error. Le score garde l’échelle d’origine : RMSE/MAE plus petites restent meilleures |
| Peut-on réutiliser les paramètres finaux ? | `best_parameters.json`, `best_parameters_configure.json` | Le premier conserve les valeurs remplaçant les défauts ; `{}` signifie utiliser les défauts. Le second fixe modèle et paramètres et désactive la recherche |
| Comment répéter le plan original ? | `config.json`, `analysis_config.json`, `study_config.json` | Conservent le plan de recherche original ; les noms assurent la compatibilité d’interfaces. Vérifier input_path et choisir un nouveau output_dir vide |
| Que signifient les champs de configuration ? | `configuration_guide.md` | Définitions courtes en chinois et anglais, séparées du JSON standard |
| Quelles prédictions sont erronées ? | `predictions.csv`, `confusion_matrix.csv` en classification | `observed` est la vérité, `predicted` la prédiction. Pour les fichiers d’entrée, `row_index` commence à 0 et désigne une ligne de données, pas le numéro de ligne du tableur avec en-tête |
| Environnement et effectifs correspondent-ils ? | `analysis_manifest.json` | Lignes initiales/analysées, nombre de caractéristiques, empreinte et versions. Ce nombre de caractéristiques n’est pas le nombre de colonnes après encodage one-hot |
| Comment commencer la rédaction ? | `methods_summary.md` / `methods_summary_zh.md`, `reproducibility_report.md` / `reproducibility_report_zh.md` | Brouillons hors ligne en anglais/chinois à vérifier, pas des textes déjà validés pour publication |

Les **meilleurs paramètres** sont ceux sélectionnés pour cette plage de candidats, cette métrique, ces données et ce découpage, pas un optimum global ou un choix universel. `best_parameters_configure.json` réutilise les données ayant servi à sélectionner les paramètres ; son nouveau score n’est pas une validation indépendante et ne reproduit pas l’estimation de la recherche imbriquée originale. L’interface n’exporte actuellement pas de fichier de modèle ajusté directement rechargeable : la configuration est une recette de réentraînement.

### Figures

| Fichier | Axes ou contenu | Questions à examiner |
| --- | --- | --- |
| `confusion_matrix.png` | Classes réelles en lignes, prédites en colonnes ; effectifs dans les cellules | Quelles classes sont confondues ? Une diagonale sombre peut masquer un déséquilibre |
| `class_distribution.png` | Effectifs réels et prédits des classes hors apprentissage | Le modèle prédit-il surtout la classe majoritaire ? Des totaux identiques peuvent cacher des erreurs individuelles |
| `observed_vs_predicted.png` | Observation en x, prédiction en y ; ligne pointillée d’égalité | Surestimation ou sous-estimation systématique ? Interpréter la dispersion selon l’unité de la cible et les métriques |
| `residuals.png` | Prédiction en x ; résidu = observation − prédiction en y | Résidu positif : sous-estimation ; négatif : surestimation. Courbure ou forme d’entonnoir peuvent suggérer une structure manquée ou une variabilité inégale |
| `residual_distribution.png` | Histogramme des résidus | Décalage, queues lourdes ou erreurs extrêmes ? Un histogramme seul ne prouve ni normalité ni indépendance |

Les figures utilisent les prédictions hors apprentissage de la validation principale ou du sous-dossier indépendant consulté. Holdout n’inclut que le test ; la validation croisée inclut généralement une prédiction externe par observation conservée. Class 1, Class 2, etc. suivent l’ordre de `confusion_matrix.csv` et ne désignent pas une classe positive clinique choisie dans l’interface. Plusieurs figures, ou aucune, peuvent être sélectionnées ; elles sont enregistrées dans `figures/`. Les graphiques SHAP, d’importance des variables, ROC et d’intervalles de confiance ne sont pas actuellement exportés.

<a id="glossary"></a>

## 6. Paramètres et terminologie

| Terme / clé | Explication |
| --- | --- |
| Famille de modèles | Une méthode comme forêt aléatoire ou Ridge ; plusieurs candidats de paramètres peuvent appartenir à la même famille |
| Paramètre / hyperparamètre | Les coefficients sont généralement appris ; profondeur ou pénalité sont spécifiées ou recherchées. `model_params` fournit surtout des hyperparamètres d’initialisation de l’estimateur |
| Candidat / grille de paramètres | Un candidat est un ensemble concret de réglages ; la grille liste les valeurs possibles. Le nombre de combinaisons peut croître rapidement |
| `tuning_mode` | `none` : paramètres fixes ; `quick` : grille interne limitée ; `custom` : grille utilisateur. La recherche rapide ne garantit pas une recommandation optimale |
| `max_candidates` | Limite des combinaisons par famille ; une grille plus grande est échantillonnée, pas nécessairement parcourue exhaustivement |
| `n_splits` / `inner_splits` | Nombres de plis externes / internes ; lignes, classes et groupes doivent permettre le découpage. Le nombre interne effectif peut être réduit |
| `random_seed` | Contrôle les partitions aléatoires et les estimateurs munis d’une graine ; un `random_state` explicite de l’estimateur la remplace. Une graine identique ne garantit pas l’identité bit à bit entre versions |
| `n_neighbors` | Nombre entier de voisins de KNN |
| `n_estimators` / `max_depth` / `min_samples_leaf` | Nombre d’arbres, profondeur maximale, effectif minimal d’une feuille. `null` peut supprimer la limite de profondeur. L’interface traite les candidats entiers comme des effectifs ; les fractions doivent respecter les règles du paramètre |
| `C` / `alpha` / `l1_ratio` | Contrôlent la pénalité : C plus petit la renforce généralement, alpha plus grand aussi, l1_ratio mélange L1/L2 ; le sens exact dépend du modèle |
| `learning_rate` / `learning_rate_init` | Taux d’apprentissage du boosting / taux initial du MLP ; clés non interchangeables |
| `epsilon` | Tolérance de SVR, pas un intervalle de confiance de l’erreur d’estimation |
| `class_weight` / déséquilibre des classes | class_weight modifie l’influence des classes pendant l’apprentissage ; ce n’est pas la moyenne pondérée des métriques à l’évaluation |
| Surajustement / sous-ajustement | Apprendre le bruit d’entraînement / manquer une structure importante. Un score de test isolé ne diagnostique pas la cause exacte |
| Fuite de données | Des informations du test entrent indûment dans l’ajustement ou la sélection, rendant l’évaluation optimiste |
| Prédiction hors apprentissage | L’observation est exclue de l’ajustement correspondant ; la sélection imbriquée l’exclut aussi du choix de ce modèle et de ses paramètres |
| Généralisation / validation externe | Performance sur des données nouvelles / évaluation sur des données externes indépendantes. La validation interne ne valide pas à elle seule un nouveau centre, une nouvelle période ou population |
| Calibration | Concordance entre probabilités prédites et fréquences observées. Une bonne AUC de classement ne garantit pas une bonne calibration |
| Empreinte SHA-256 | Permet de détecter un changement du contenu d’entrée. Ce n’est ni chiffrement, ni anonymisation, ni preuve de qualité |
| Avertissement de convergence | L’optimisation n’a pas satisfait son critère d’arrêt dans les conditions choisies. Des résultats peuvent exister sans que l’ajustement soit suffisamment stable |

<a id="checklist"></a>

## 7. Interprétations erronées et ordre de vérification

Vérifier d’abord cible, prédicteurs, groupes et traitement des valeurs manquantes ; puis avertissements et effectif analysé ; ensuite métriques principales, variabilité entre plis et erreurs systématiques ; enfin références et analyses de sensibilité prédéfinies. Documenter les modifications du plan plutôt que changer sans cesse de validation ou de métrique après consultation des résultats.

- **« Le rang 1 est forcément le modèle final. »** Non : classement externe exploratoire et sélection interne finale ont des rôles différents.
- **« R² = 0,6 signifie que chaque individu est prédit correctement à 60 %. »** Non : R² compare des erreurs au carré, pas une exactitude individuelle.
- **« Un F1 ou une AUC plus élevés garantissent l’utilité clinique. »** Non : coûts d’erreur, population, seuils, calibration et preuves externes restent nécessaires.
- **« Un écart-type nul signifie aucune incertitude. »** Non, notamment avec une seule partition holdout.
- **« Les variables retenues par Lasso sont causales. »** La sélection prédictive n’établit pas la causalité.
- **« Une sortie completed peut être publiée telle quelle. »** L’achèvement est un état logiciel, pas une validation scientifique ou de qualité des données.

<a id="references"></a>

## 8. Implémentation et lectures complémentaires

Le comportement du projet suit le [catalogue](../src/psyml/models/catalog.py), la [fabrique](../src/psyml/models/factory.py), les [métriques](../src/psyml/evaluation/metrics.py), les [partitions](../src/psyml/validation/split.py), le [moteur](../src/psyml/runner.py) et les [rapports](../src/psyml/reporting/research.py). Les défauts et comportements peuvent évoluer ; vérifier les versions dans `analysis_manifest.json` pour reproduire une analyse.

Pour les principes généraux, consulter les références scikit-learn sur les [métriques](https://scikit-learn.org/stable/modules/model_evaluation.html), les [modèles linéaires](https://scikit-learn.org/stable/modules/linear_model.html), les [ensembles](https://scikit-learn.org/stable/modules/ensemble.html), la [validation croisée](https://scikit-learn.org/stable/modules/cross_validation.html) et l’[exemple de validation imbriquée](https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html). Ces liens ne signifient pas que PsyML implémente toutes les fonctionnalités décrites.

## Reproduire à partir d’une configuration

À la page 1, **Importer une configuration…** ouvre un exemple fourni, le `config.json` d’un résultat ou `best_parameters_configure.json`, sans terminal. Réassociez les données correspondantes si leur chemin est introuvable ; les colonnes requises sont vérifiées. Vérifiez variables, validation et paramètres, puis choisissez un dossier local et lancez à la page 2. Chaque exécution crée un nouveau sous-dossier sans réutiliser le chemin de sortie importé. **Enregistrer la configuration…** conserve les réglages. Relancer les meilleurs paramètres fixes ne reproduit pas la recherche originale et ne constitue pas une validation indépendante.
