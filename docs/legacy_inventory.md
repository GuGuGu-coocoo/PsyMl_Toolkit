# Legacy Asset Inventory

Inventory date: 2026-09-04

## Source groups

| Location | Classification | Contents | Status |
| --- | --- | --- | --- |
| `legacy/original/program/Classiffication_Models/Classiffication_Models-v1.0.0` | Historical classification release | KNN, MLP, Random Forest, SVM, and stacking scripts | Superseded candidate |
| `legacy/original/program/Classiffication_Models/Classiffication_Models-v1.1.0` | Historical classification release | Same core classifiers, prediction entry point, saved-model directory | Superseded candidate |
| `legacy/original/program/Classiffication_Models/Classiffication_Models-v1.1.1` | Historical classification release | Same core classifiers plus `datapredict.py` | Superseded candidate |
| `legacy/original/program/Classiffication_Models/Classiffication_Models-v1.1.2` | Historical classification release | KNN, MLP, Random Forest, SVM, stacking, prediction utilities | Latest candidate |
| `legacy/original/program/Classiffication_Models/DecisionTree-v1.0.0` and `legacy/original/program/DecisionTree-v1.0.0` | Decision-tree experiment | Training, looping, prediction, and data-preparation scripts | Unique component; duplicate copies detected |
| `legacy/original/program/Classiffication_Models/OH_NLP-v1.1.0` and `legacy/original/program/Classiffication_Models/OH_NLP-v1.1.1` | RNN NLP experiment | PyTorch RNN, training loop, prediction and data preparation | Experimental branch |
| `legacy/original/program/Classiffication_Models/NLP_test` | NLP prototype | Standalone `RNN.py` | Experimental branch |
| `legacy/original/program/Classiffication_Models/simulate_0` | Simulation experiment | MLP/SVM classification and sample datasets | Experimental branch |
| `legacy/original/program/Regression_Models/Regression_Models-v1.1.0` | Historical regression release | KNN, Lasso, MLP, Random Forest, and SVR scripts | Latest candidate |
| `test` | Miscellaneous tests | AutoGluon placeholder and pooling test | Unknown |

## Confirmed model implementations

- Regression: KNN, Lasso, MLP, Random Forest, SVR.
- Classification: KNN, MLP, Random Forest, SVM, stacking, decision tree.
- Specialized: PyTorch RNN text classification.

## Supporting functions observed

- Train/test splitting and fixed random seeds.
- Standard scaling in regression scripts.
- Classification reports, confusion matrices, accuracy, precision, recall, and F1 metrics.
- Regression R², MSE, and MAE metrics.
- Permutation importance in several model implementations.
- Excel result export and Joblib/PyTorch model saving.

## Not yet validated

This inventory records presence only. Statistical validity, data-leakage handling, dependency compatibility, and runtime behavior are deliberately deferred to later phases.
