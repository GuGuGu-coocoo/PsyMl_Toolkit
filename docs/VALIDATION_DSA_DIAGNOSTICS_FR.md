# Diagnostics de l’écart numérique DSA : contraste de noyaux Linux et vérifications Mac locales

[中文](VALIDATION_DSA_DIAGNOSTICS_ZH.md) · [English](VALIDATION_DSA_DIAGNOSTICS_EN.md)

Cas `psyml_dsa_group_nested_v1`, commit figé `de33abfe52ccfee67f461a850edd00a14d2fbfaa`, enregistré le 2026-10-02.

## 1. Objectif et conclusion

Cet appendice documente un diagnostic borné de l’écart inter-plateformes publié (`roc_auc_ovr_weighted` environ 2,03e-7 ; probabilités hors pli jusqu’à environ 2e-5) : une expérience contrôlée de distribution de noyaux CPU menée dans l’environnement Linux de parité (25 ajustements au total : 5 ajustements de sonde sur un pli + 20 ajustements de contraste sur quatre plis), complétée par des vérifications minimales en lecture seule sur cette machine macOS.

**Conclusion.** Dans le contraste Linux, changer uniquement la distribution des noyaux CPU OpenBLAS, ou décaler les entrées standardisées d’une unité de dernier rang, suffit à produire un écart d’AUC de même magnitude, de même direction sur le pli 2 et de même inversion d’une paire de classement, avec des prédictions dures inchangées. Cela soutient le mécanisme « le chemin numérique d’ajustement est sensible à des différences numériques extrêmement petites ». Sur ce Mac, les deux plis qui diffèrent se décomposent aussi exactement en une inversion stricte de paire par pli (pli 1 classe 6, pli 2 classe 13), et le backend numérique de cette machine est Apple Accelerate et non OpenBLAS. **La cause racine concrète de l’écart Mac d’origine (quelle bibliothèque, quel chemin d’instructions ou quelle étape de prétraitement) reste non confirmée**, et le changement du pli 1 n’a pas été reproduit par le contraste de noyaux Linux.

Cet appendice ne modifie ni le cœur d’entraînement, ni les tolérances figées, ni la base, ni le protocole scientifique ; aucun réglage diagnostique `tol`/`ftol`/noyau ne devient un défaut produit ; il ne prétend pas que le Mac a été entièrement simulé, ni l’équivalence numérique entre plateformes.

## 2. Matériel et provenance

- **Paquet de diagnostic Linux** (cloud dot, 2026-10-01) : `REPORT_ZH.md`, `DEEP_PLAN.md`, la sonde du pli 1 (`probe.py`, `results.json`, `rank_pair_checks.json`, `perturbation.json`), le contraste de noyaux sur quatre plis (`deep_probe.py`, `default_*`, `Haswell*`, `Sandybridge*`, `deep_comparison.json`, `common_prediction_kernel.json`, `input_checks.json`) et `remote_reverification_macos.json`. Vérifié sur cette machine contre le `MANIFEST.json` du paquet : 26/26 empreintes correspondent.
- **Environnement de vérification local** (parité du cas, distinct de la reprise officielle `uv.lock`) : Python 3.12.14, NumPy 2.3.5, SciPy 1.17.0, scikit-learn 1.8.0, pandas 2.2.3, joblib 1.5.3, matplotlib 3.10.8 ; `OPENBLAS_NUM_THREADS`, `OMP_NUM_THREADS` et `MKL_NUM_THREADS` à 1.
- **Données et artefacts** : le CSV dérivé figé (SHA-256 `75a5fe87a58f4cfde777d914d674362b5148854a3c7064d8c686c0e25c3a047e`), les artefacts de référence Linux figés et les artefacts de la reprise macOS locale (voir aussi `expected/reverification_macos.json`).
- **Outil** : `tools/cases/diagnose_auc_pairs.py` (nouveau dans ce dépôt ; analyse seule, n’ajuste jamais de modèle et ne participe pas à l’entraînement) ; tests unitaires dans `tests/test_auc_rank_contribution.py`.

## 3. Résumé des expériences Linux

### 3.1 Sonde du pli 1 à C=1 fixé (5 ajustements)

| Exécution | Itérations | Condition d’arrêt | Norme ∞ du gradient | Écart d’AUC vs base | Écart max de probabilité | Prédictions dures modifiées |
| --- | --- | --- | --- | --- | --- | --- |
| baseline | 443 | gradient projeté ≤ gtol | 9,72e-9 | 0 | 1,11e-16 | 0 |
| repeat | 443 | gradient projeté ≤ gtol | 9,72e-9 | 0 | 1,11e-16 | 0 |
| entrées +1 ulp | 422 | gradient projeté ≤ gtol | 8,43e-9 | −2.0305393111375025e-7 | 7,116e-5 | 0 |
| tol=1e-11 | 454 | réduction relative de la fonction | 6,20e-9 | 0 | 6,913e-6 | 0 |
| tol=1e-11 et ftol=1e-16 | 531 | réduction relative de la fonction | 1,18e-9 | 0 | 1,457e-5 | 0 |

- La perturbation a décalé les 82 080 valeurs standardisées d’une unité de dernier rang vers +∞ (modification maximale 3,55e-15) ; exactement une inversion stricte de classement est apparue dans la classe 5. L’unité de paire unique de l’AUC OVR pondérée est `1/(19×120×2160) = 2.0305393112410655e-7`, ce qui correspond à cet écart d’AUC.
- Les deux exécutions à tolérances resserrées se sont arrêtées sur le critère de réduction relative de la fonction sans atteindre la condition de gradient plus stricte ; leur AUC égale la base mais leurs probabilités ne sont pas identiques bit à bit. Ce sont des observations diagnostiques, **pas une recommandation de correction**.
- Les `n_iter` figés des quatre plis sont 443/449/451/439, loin du plafond de 2000 itérations.

### 3.2 Contraste des noyaux OpenBLAS sur quatre plis (20 ajustements)

- Entrées : les quatre matrices standardisées d’entraînement/test matérialisées depuis le pipeline d’origine ; les statistiques d’imputer et la moyenne/variance/scale du scaler égalent exactement le `fit_audit` figé, pli par pli. Les noyaux réellement utilisés ont été vérifiés avec threadpoolctl (SkylakeX par défaut, Haswell, Sandybridge), un seul thread.
- Les deux exécutions avec le noyau par défaut ont produit des coefficients, intercepts et tableaux de probabilités identiques.
- Changer uniquement le noyau change les paramètres ajustés et les probabilités, sans modifier les prédictions dures :
  - Écarts maximaux de probabilité avec Haswell (plis 1–4) : 1,01e-5, 7,49e-6, 2,28e-6, 4,87e-6 ; avec Sandybridge : 4,52e-5, 7,64e-6, 2,57e-6, 2,15e-6.
  - L’AUC du pli 2 augmente de 2.030539311e-7 avec Haswell comme avec Sandybridge ; les autres plis ne changent pas.
  - Le compte exact par paire au pli 2 est la classe 13, une inversion stricte, aucune égalité, sous les deux noyaux ; l’écart d’AUC reconstruit par le classement correspond à la valeur rapportée à l’arrondi flottant près.
- En remettant tous les paramètres ajustés sur le noyau par défaut et en recalculant avec un noyau de prédiction commun, toutes les AUC restent inchangées (écart de recalcul des probabilités ≤3,44e-15) : l’écart d’AUC de ce contraste provient des **paramètres ajustés**, pas seulement de la multiplication matricielle en prédiction.
- Une formule indépendante de la log-vraisemblance négative moyenne et du gradient du logistique multinomial avec pénalité L2 correspond à la sortie capturée du solveur (valeurs par pli dans l’archive).
- Ce contraste de noyaux n’a pas reproduit de changement d’AUC au pli 1 (les probabilités du pli 1 changent, mais aucun classement ne change).

## 4. Vérifications Mac locales (2026-10-02)

### 4.1 Entrées et identité

L’empreinte du CSV dérivé correspond à la valeur figée ; l’appartenance des quatre plis est identique au `fold_membership.json` figé ; la trace de sélection est identique et chaque candidat retenu est `logistic_regression, C=1.0` ; les deux tables `predictions_with_probabilities.csv` comptent 9 120 lignes alignées sur `row_index`/`fold`/`observed`, avec le même ordre de colonnes de probabilité.

### 4.2 Analyse du classement par paires aux plis 1 et 2

`tools/cases/diagnose_auc_pairs.py` a comparé les probabilités Linux figées aux probabilités Mac locales :

| Pli | Classe | Paires modifiées | Inversions strictes | Nouvelles égalités | Égalités résolues | Paires concordantes nettes | Contribution | Écart d’AUC mesuré |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 6 | 1 | 1 | 0 | 0 | +1 | 2.0305393112410655e-7 | 2.0305393111375025e-7 |
| 2 | 13 | 1 | 1 | 0 | 0 | +1 | 2.0305393112410655e-7 | 2.0305393111375025e-7 |

La contribution nette égale la contribution absolue dans les deux plis (aucune annulation entre classes) ; la contribution reconstruite diffère de l’écart d’AUC mesuré d’environ 1,04e-17 (arrondi flottant). Le relevé antérieur du dépôt indique 2.030539310e-7 pour le pli 2 (ordre d’accumulation des métriques), également dans l’arrondi.

Paires concrètes (les probabilités sont celles de la classe en OVR ; les identifiants de segment permettent la jointure) :

- **Pli 1, classe 6** : positif `a06_p4_s34` (ligne 2613) contre négatif `a18_p8_s25` (ligne 8604). Marge figée −3,709e-7 (le négatif est mieux classé) → marge Mac +2,490e-7 ; les probabilités de classe des deux échantillons changent de +2,77e-7 et −3,43e-7.
- **Pli 2, classe 13** : positif `a13_p7_s36` (ligne 6155) contre négatif `a17_p3_s25` (ligne 7824). Marge figée −2,122e-9 → Mac +4,936e-9 ; changements de probabilité +8,33e-9 et +1,27e-9 (niveau de probabilité environ 0,00207).

### 4.3 Prétraitement, backend et informations de sortie de l’optimiseur

- États imputer/scaler reconstruits par pli contre le `fit_audit` figé : plis 1 et 2 exactement égaux ; pli 3 variance différente de 8,88e-16 et pli 4 moyenne différente de 3,33e-16 (niveau d’ordre de sommation).
- Écarts maximaux absolus de coefficients/intercepts contre la référence figée : pli 1 3,14e-5/6,73e-5, pli 2 2,23e-5/5,97e-5, pli 3 2,31e-5/8,78e-5, pli 4 1,99e-5/6,00e-5.
- Le NumPy de cette machine utilise **Apple Accelerate** pour BLAS/LAPACK (et non OpenBLAS) ; threadpoolctl ne rapporte que le pool OpenMP avec 1 thread (ce backend n’expose pas de pool BLAS à threadpoolctl).
- Re-ajustements diagnostiques indépendants à C=1 fixé (aucun code de production modifié) : les quatre plis s’arrêtent sur « NORM OF PROJECTED GRADIENT <= PGTOL », `n_iter` 436/436/435/442 (Linux : 443/449/451/439), norme ∞ du gradient 9,08–9,84e-9 ; les probabilités correspondent à la table hors pli Mac à 1,11e-16 près et les prédictions dures ne changent pas.

## 5. Confirmé et non confirmé

**Confirmé (dans la portée enregistrée de ce cas)**

- Des modifications d’entrée extrêmement petites (un ulp) ou le seul changement de distribution des noyaux CPU OpenBLAS suffisent à modifier le chemin d’optimisation et le point d’arrêt, produisant des changements de probabilité et de métrique de classement de la magnitude enregistrée, tandis que les prédictions dures et les principales métriques de labels restent inchangées.
- Les deux plis Mac qui diffèrent se décomposent exactement en une inversion stricte de classement par pli (pli 1 classe 6, pli 2 classe 13), sans égalité ni annulation ; le pli 2 correspond à la classe 13 du contraste Linux.
- Mac et Linux diffèrent par le backend numérique (Accelerate contre OpenBLAS) alors que l’optimiseur s’arrête sur le même critère (gradient projeté) : l’écart ne vient donc pas d’une condition d’arrêt différente.

**Non confirmé**

- Quelle bibliothèque, quel chemin d’instructions ou quelle étape de prétraitement a causé l’écart Mac d’origine ; cet appendice propose un mécanisme candidat, pas une cause unique.
- Le changement du pli 1 n’a pas été reproduit par le contraste de noyaux Linux et ne peut pas être déclaré expliqué.
- Pas de « le Mac a été entièrement simulé », pas d’« équivalence numérique complète » ; unifier les graines ou resserrer `tol` ne garantit pas non plus l’accord bit à bit — les diagnostics `tol`/`ftol` ci-dessus en sont le contre-exemple.

## 6. Évidence minimale pour clore la cause racine

- Les quatre matrices standardisées d’entraînement/test sauvegardées côté Linux (ou des états imputer/scaler rejouables sur les mêmes numéros de ligne) pour que les deux plateformes ajustent sur des entrées **identiques bit à bit** ; le paquet n’a conservé que leurs empreintes (`input_checks.json`).
- Ou bien une exécution Mac équivalente au contraste de noyaux Linux (mêmes matrices, mêmes paramètres, informations de sortie par pli) pour une comparaison bidirectionnelle.
- En attendant cette évidence, il n’est pas recommandé d’élargir les expériences ; les résultats actuels suffisent à consigner une sensibilité reproductible au chemin numérique.

## 7. Points d’entrée des preuves et de l’outil

- Archive locale (ignorée par Git ; contient le paquet Linux d’origine, tous les artefacts de diagnostic locaux et les empreintes par fichier) : `docs/internal/completed/reports/2026-10-02-dsa-mac-numerical-diagnostics/`.
- Outil et tests : `tools/cases/diagnose_auc_pairs.py`, `tests/test_auc_rank_contribution.py` (aucun changement, une inversion stricte, création/résolution d’égalités, annulation mutuelle, poids de classe explicites, rejet des désalignements lignes/colonnes ; tous petits, aucun n’ajuste de modèle complet).
- Commande de reproduction (racine du dépôt) :

```bash
uv run python -m tools.cases.diagnose_auc_pairs \
  --baseline <predictions_with_probabilities.csv figé> \
  --alternative <predictions_with_probabilities.csv de reprise> \
  --fold 2 --segments <CSV avec row_index et segment_id> \
  --output pair_diagnostics_fold2.json
```

## 8. Références

1. scikit-learn 1.8.0 `sklearn/linear_model/_logistic.py` (conditions d’arrêt et paramètres L-BFGS) : <https://github.com/scikit-learn/scikit-learn/blob/1.8.0/sklearn/linear_model/_logistic.py>
2. Documentation SciPy `minimize(method='L-BFGS-B')` (sémantique gtol/ftol) : <https://docs.scipy.org/doc/scipy/reference/optimize.minimize-lbfgsb.html>
3. Relevés du dépôt : `examples/public/dsa_group_nested_v1/expected/reverification_macos.json` (inter-plateformes) et `examples/public/dsa_group_nested_v1/expected/reverification_uv_lock.json` (environnement officiel verrouillé)
