# Legacy Version Relationships

Assessment date: 2026-09-04

## Classification sequence

| Version | Relationship | Evidence | Classification |
| --- | --- | --- | --- |
| `Classiffication_Models-v1.0.0` | Earlier candidate | Core KNN, MLP, Random Forest, SVM, and stacking scripts are present. | Superseded candidate |
| `Classiffication_Models-v1.1.0` | Later candidate | Adds a prediction entry point and saved-model directory. | Superseded candidate |
| `Classiffication_Models-v1.1.1` | Later candidate | Adds `datapredict.py` while retaining the core classifier set. | Superseded candidate |
| `Classiffication_Models-v1.1.2` | Latest candidate | Retains the core classifier set and prediction utilities; includes additional dataset variant. | Latest candidate |

The version labels suggest a sequence, but this is only a working relationship. File-level and behavioral comparison has not yet established that any release fully contains its predecessor.

## Other branches

| Directory | Relationship | Classification |
| --- | --- | --- |
| `legacy/original/program/DecisionTree-v1.0.0` | Same contents and role as the nested decision-tree directory need checksum comparison. | Unknown duplicate / unique component |
| `legacy/original/program/Classiffication_Models/DecisionTree-v1.0.0` | Standalone decision-tree workflow. | Unique component |
| `OH_NLP-v1.1.0` → `OH_NLP-v1.1.1` | Two releases of the RNN NLP experiment. | Experimental branch |
| `NLP_test` | Minimal RNN prototype. | Experimental branch |
| `simulate_0` | Synthetic-data classifier experiment. | Experimental branch |
| `Regression_Models-v1.1.0` | Only extracted regression release available outside archives. | Latest candidate |

## Preservation rule

Original directory names, including the historical `Classiffication` spelling, are retained as historical metadata. No semantic version ordering will be treated as proof of functional supersession without later diff and runtime review.
