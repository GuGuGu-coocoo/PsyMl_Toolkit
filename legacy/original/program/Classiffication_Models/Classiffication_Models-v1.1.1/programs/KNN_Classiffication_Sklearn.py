# -*- coding: utf-8 -*-
'''
@File    :   KNN_Classiffication_Sklearn.py
@Author  :   GuGuGu?coocoo! 
@Time    :   2023/05/01 15:39:13 UTC+08:00
'''
import numpy as np
import pandas as pd
import joblib

from sklearn.inspection import permutation_importance
from sklearn.metrics import accuracy_score,classification_report, confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier

def knn(file,test_size=0.3,n_neighbors=5,weights='distance',algorithm='kd_tree'):
    """
    ## file:
    path of the file
    
    ## test_size:
    a float in the range [0.0, inf)

    ## n_neighbors:
    an int in the range [1, inf)

    ## weights:
    a str among {'uniform', 'distance'}

    ## algorithm:
    a str among {'auto', 'ball_tree', 'kd_tree', 'brute'}

    """ 
    file = file
    test_size=test_size
    n_neighbors=n_neighbors
    weights=weights
    algorithm=algorithm            
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
        np.random.seed(1846)
        order = np.random.permutation(m)
        X = X[order]
        y = y[order]

        # Normalize the feature
        X_min = np.min(X)
        X_max = np.max(X)
        X = (X - X_min)/(X_max - X_min)

        return X, y

    X,y = preprocess(X, y)

    # Split the dataset into training and testing data
    train_X, test_X, train_y, test_y = train_test_split(X, y, test_size=test_size, random_state=1846)

    # ---------------------------The above are data preprocessing operations-------------------------------------------
    # print parameters
    print('KNN_Classiffication_Sklearn','\nFileName:',file,'\nRunning the knn model with parameters:','\nFeatrue:',features_num,'\nTest_size',test_size,
          '\nN_neighbors:',n_neighbors,'\nWeights:',weights,'\nAlgorithm:',algorithm)
    
    # Create and train the model
    knn = KNeighborsClassifier(n_neighbors=n_neighbors,weights=weights,algorithm=algorithm,n_jobs=-1)
    knn.fit(train_X,train_y.ravel())
  
    # Compute feature importance using Permutation Improtance method
    result = permutation_importance(knn, X, y, n_repeats=10, random_state=1624)
    
    # Print accuracy
    print('Training accuracy =',knn.score(train_X,train_y))
    print('Testing accuracy =',knn.score(test_X,test_y))

    # Calculate and output the confusion matrix and classification report for the training and testing sets separately
    print('Training confusion matrix:\n',confusion_matrix(train_y,knn.predict(train_X)))
    print('Testing confusion matrix:\n',confusion_matrix(test_y,knn.predict(test_X)))
    print('Training classification report:\n',classification_report(train_y,knn.predict(train_X),))
    print('Testing classification report:\n',classification_report(test_y,knn.predict(test_X)))
    
    # Sort features by importance score
    importance_scores = result.importances_mean
    features = range(X.shape[1])
    sorted_features = [x for _,x in sorted(zip(importance_scores, features), reverse=True)]

    # Print sorted features by importance score
    ranks = []
    for i, feature in enumerate(sorted_features):
        print(f"Rank {i+1}: Feature {feature + 1} with importance score {importance_scores[feature]}")
        ranks.append(f"f{feature + 1},{importance_scores[feature]}")
    # Calculate and save the scores of train and test in mlp_result as a DataFrame
    train_pred_y = knn.predict(train_X)
    train_accuracy = accuracy_score(train_y,train_pred_y)
    train_precision, train_recall, train_f1_score, train_support = precision_recall_fscore_support(train_y,train_pred_y,average='weighted')
    train_support = len(train_y)
    test_pred_y = knn.predict(test_X)
    test_accuracy = accuracy_score(test_y,test_pred_y)
    test_precision, test_recall, test_f1_score, test_support = precision_recall_fscore_support(test_y,test_pred_y,average='weighted')
    test_support = len(test_y)
    knn_result_dict = {'Test_size': [test_size],
                       'N_neighbors':[n_neighbors],
                       'Weights':[weights],
                       'Algorithm':[algorithm],
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
        knn_result_dict[rank_name] = [ranks[i]]
        
    knn_result = pd.DataFrame(knn_result_dict)
    
    return knn_result

def save_knn(file,n_neighbors=5,weights='distance',algorithm='kd_tree'):
    file = file
    n_neighbors=n_neighbors
    weights=weights
    algorithm=algorithm 
    # extract the data in each column of the dataframe, and stores it as separate lists
    df = pd.read_excel(file)
    features_num = int(pd.read_excel(file).shape[1] - 1)
    X = df.iloc[:, : features_num].values.tolist() 
    labels = df.iloc[:, features_num].tolist()

    # Convert the labels column into a numpy array
    y = np.c_[labels]
    # Create and train the model
    knn = KNeighborsClassifier(n_neighbors=n_neighbors,weights=weights,algorithm=algorithm,n_jobs=-1)
    knn.fit(X,y)
    joblib.dump(knn,'knn_model.joblib')