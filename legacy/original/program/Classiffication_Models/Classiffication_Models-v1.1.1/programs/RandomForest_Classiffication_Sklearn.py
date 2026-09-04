# -*- coding: utf-8 -*-
'''
@File    :   RandomForest_Classiffication_Sklearn.py
@Author  :   GuGuGu?coocoo! 
@Time    :   2023/04/29 15:23:33 UTC+08:00
'''
import pandas as pd
import numpy as np
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix, classification_report,accuracy_score,precision_recall_fscore_support
from sklearn.inspection import permutation_importance

def rf(file,test_size=0.3,n_estimators=100, criterion='gni',bootstrap=True, oob_score=False):
    """
    ## file:
    path of the file
    
    ## test_size:
    a float in the range [0.0, inf)

    ## n_estimators
    an int in the range [1, inf)
    
    ## criterion
    a str among {'entropy', 'gini', 'log_loss'}

    ## bootstrap
    an instance of 'bool'
    
    ## oob_score
    an instance of 'bool'
    
    """
    file = file
    test_size = test_size
    n_estimators = n_estimators
    criterion = criterion
    bootstrap = bootstrap
    oob_score = oob_score
    # extract the data in each column of the dataframe, and stores it as separate lists               
    df = pd.read_excel(file)
    features_num = int(pd.read_excel(file).shape[1] - 1)
    X = np.c_[df.iloc[:,:features_num].values.tolist()] 
    labels = df.iloc[:, features_num].tolist()

    # Convert the labels column into a numpy array
    y = np.c_[labels]
    def preprocess(X, y):
        """
        Preprocess the data
        """
        # Randomly shuffles the data
        m = len(X)
        np.random.seed(2240)
        order = np.random.permutation(m)
        X = X[order]
        y = y[order]
        
        # Normalize the feature
        X_min = np.min(X)
        X_max = np.max(X)
        X = (X - X_min)/(X_max - X_min)
        y = np.c_[y].ravel()
        return X, y
    X,y = preprocess(X, y)

    # Split the dataset into training and testing data
    train_X, test_X, train_y, test_y = train_test_split(X, y, test_size=test_size, random_state=1010)

    # print("PREPROCESS COMPLETED !!!")

    # ---------------------------The above are data preprocessing operations-------------------------------
    # print parameters
    print('RandomForest_Classiffication_Sklearn','\nFileName:',file,'\nRunning the randomforest model with parameters:','\nFeatrue:',features_num,'\nTest_size',test_size,'\nN_estimators:',n_estimators, 
          '\nCriterion:',criterion,'\nBootstrap:',bootstrap, '\nOob_score:',oob_score)
    
    # Difine random forest model
    rf =RandomForestClassifier(n_estimators=n_estimators, criterion=criterion,bootstrap=bootstrap, oob_score=oob_score,n_jobs=-1)
    rf.fit(train_X,train_y)

    # Compute feature importance using Permutation Improtance method
    result = permutation_importance(rf, X, y, n_repeats=10, random_state=1624)
    
    # Print accuracy
    
    print('Training accuracy =',rf.score(train_X,train_y))
    print('Testing accuracy =',rf.score(test_X,test_y))

    # Calculate and output the confusion matrix and classification report for the training and testing sets separately
    print('Training confusion matrix:\n',confusion_matrix(train_y,rf.predict(train_X)))
    print('Testing confusion matrix:\n',confusion_matrix(test_y,rf.predict(test_X)))
    print('Training classification report:\n',classification_report(train_y,rf.predict(train_X),))
    print('Testing classification report:\n',classification_report(test_y,rf.predict(test_X)))
    
    # Sort features by importance score
    importance_scores = result.importances_mean
    features = range(X.shape[1])
    sorted_features = [x for _,x in sorted(zip(importance_scores, features), reverse=True)]

    # Print sorted features by importance score
    ranks=[]
    for i, feature in enumerate(sorted_features):
        print(f"Rank {i+1}: Feature {feature + 1} with importance score {importance_scores[feature]}")
        ranks.append(f"f{feature + 1},{importance_scores[feature]}")
    # Calculate and save the scores of train and test in mlp_result as a DataFrame
    train_pred_y = rf.predict(train_X)
    train_accuracy = accuracy_score(train_y,train_pred_y)
    train_precision, train_recall, train_f1_score, train_support = precision_recall_fscore_support(train_y,train_pred_y,average='weighted')
    train_support = len(train_y)
    test_pred_y = rf.predict(test_X)
    test_accuracy = accuracy_score(test_y,test_pred_y)
    test_precision, test_recall, test_f1_score, test_support = precision_recall_fscore_support(test_y,test_pred_y,average='weighted')
    test_support = len(test_y)
    rf_result_dict = {'Test_size': [test_size],
                      'N_estimators':[n_estimators],
                      'Criterion':[criterion],
                      'Bootstrap':[bootstrap],
                      'Oob_score':[oob_score],
                       'TrainAccuracy': [train_accuracy],
                       'TrainPrecision': [train_precision],
                       'TrainRecall': [train_recall],
                       'TrainF1Score': [train_f1_score],
                       'TrainSupport': [train_support],
                       'TestAccuracy': [test_accuracy],
                       'TestPrecision': [test_precision],
                       'TestRecall': [test_recall],
                       'TestF1Score': [test_f1_score],
                       'TestSupport': [test_support],
                       }
    for i in range(len(ranks)):
        rank_name = 'Rank{}ImportanceScore'.format(i+1)
        rf_result_dict[rank_name] = [ranks[i]]
        
    rf_result = pd.DataFrame(rf_result_dict)
    return rf_result

def save_rf(file,n_estimators=100, criterion='gni',bootstrap=True, oob_score=False):
    file = file
    n_estimators = n_estimators
    criterion = criterion
    bootstrap = bootstrap
    oob_score = oob_score
    # extract the data in each column of the dataframe, and stores it as separate lists
    df = pd.read_excel(file)
    features_num = int(pd.read_excel(file).shape[1] - 1)
    X = np.c_[df.iloc[:,:features_num].values.tolist()] 
    labels = df.iloc[:, features_num].tolist()
    
    # Convert the labels column into a numpy array
    y = np.c_[labels]
    # Create and train the model
    rf =RandomForestClassifier(n_estimators=n_estimators, criterion=criterion,bootstrap=bootstrap, oob_score=oob_score)
    rf.fit(X,y)
    joblib.dump(rf,'rf_model.joblib')
