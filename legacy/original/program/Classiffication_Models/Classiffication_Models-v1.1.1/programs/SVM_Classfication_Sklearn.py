# -*- coding: utf-8 -*-
'''
@File    :   SVM_Classfication_Sklearn.py
@Author  :   GuGuGu?coocoo! 
@Time    :   2023/04/29 15:23:59 UTC+08:00
'''
import pandas as pd
import numpy as np
import joblib

from sklearn.svm import SVC
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix, classification_report,accuracy_score,precision_recall_fscore_support
from sklearn.inspection import permutation_importance

def svm(file,test_size=0.3,kernel='rbf',C = 0.1,gamma='auto',decision_function_shape='ovo',shrinking=True,probability=True):
    """
    ## file:
    path of the file

    ## featrue_num:
    number of featrues
    
    ## test_size:
    a float in the range [0.0, inf)
    
    ## kernel
    a str among {'rbf', 'sigmoid', 'poly', 'precomputed', 'linear'}.

    ## C:
    a float in the range [0.0, inf)

    ## gamma:
    a str among {'auto', 'scale'} or a float in the range [0.0, inf).
    
    ## decision_function_shape:
    a str among {'ovo', 'ovr'}
    
    ## shrinking:
    an instance of 'bool'

    ## probability:
    an instance of 'bool'
    
    """
    file = file
    test_size=test_size
    kernel = kernel
    C = C
    gamma = gamma
    decision_function_shape = decision_function_shape
    shrinking = shrinking
    probability = probability

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

    # ---------------------------The above are data preprocessing operations---------------------------------
    # print parameters
    print('SVM_Classiffication_Sklearn','\nFileName:',file,'\nRunning the svm model with parameters:','\nFeatrue:',features_num,'\nTest_size',test_size,'\nkernel:',kernel, 
        '\nC:',C,'\nGamma:',gamma,'\nDecision_function_shape:',decision_function_shape, '\nShrinking:',shrinking,
        '\nProbability:',probability)
    
    # Create an instance of the SVM classifier and Train the classifier on the training data
    svm = SVC(kernel=kernel, C=C,gamma=gamma,decision_function_shape=decision_function_shape, shrinking=shrinking,probability=probability)
    svm.fit(train_X, train_y)
    # Compute feature importance using Permutation Improtance method
    result = permutation_importance(svm, X, y, n_repeats=10, random_state=1624)
    
    # Print accuracy
    print('Training accuracy =',svm.score(train_X,train_y))
    print('Testing accuracy =',svm.score(test_X,test_y))

    # Calculate and output the confusion matrix and classification report for the training and testing sets separately
    print('Training confusion matrix:\n',confusion_matrix(train_y,svm.predict(train_X)))
    print('Testing confusion matrix:\n',confusion_matrix(test_y,svm.predict(test_X)))
    print('Training classification report:\n',classification_report(train_y,svm.predict(train_X),))
    print('Testing classification report:\n',classification_report(test_y,svm.predict(test_X)))
  
    # Sort features by importance score
    importance_scores = result.importances_mean
    features = range(X.shape[1])
    sorted_features = [x for _,x in sorted(zip(importance_scores, features), reverse=True)]

    # Print sorted features by importance score
    ranks=[]
    for i, feature in enumerate(sorted_features):
        print(f"Rank {i+1}: Feature {feature + 1} with importance score {importance_scores[feature]}")
        ranks.append(f"f{feature + 1},{importance_scores[feature]}")
    # Calculate and save the scores of train and test in svm_result as a DataFrame
    train_pred_y = svm.predict(train_X)
    train_accuracy = accuracy_score(train_y,train_pred_y)
    train_precision, train_recall, train_f1_score, train_support = precision_recall_fscore_support(train_y,train_pred_y,average='weighted')
    train_support = len(train_y)
    test_pred_y = svm.predict(test_X)
    test_accuracy = accuracy_score(test_y,test_pred_y)
    test_precision, test_recall, test_f1_score, test_support = precision_recall_fscore_support(test_y,test_pred_y,average='weighted')
    test_support = len(test_y)
    mlp_result_dict = {'Test_size': [test_size],
                       'Kernel':[kernel],
                       'C':[C],
                       'Gamma':[gamma],
                       'Decision_function_shape':[decision_function_shape],
                       'Shrinking':[shrinking],
                       'Probability':[probability],
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
        mlp_result_dict[rank_name] = [ranks[i]]
        
    svm_result = pd.DataFrame(mlp_result_dict)
    return svm_result

def save_svm(file,kernel='rbf',C = 0.1,gamma='auto',decision_function_shape='ovo',shrinking=True,probability=True):
    file = file
    kernel = kernel
    C = C
    gamma = gamma
    decision_function_shape = decision_function_shape
    shrinking = shrinking
    probability = probability
    # extract the data in each column of the dataframe, and stores it as separate lists
    df = pd.read_excel(file)
    features_num = int(pd.read_excel(file).shape[1] - 1)
    X = np.c_[df.iloc[:,:features_num].values.tolist()] 
    labels = df.iloc[:, features_num].tolist()
    # Convert the labels column into a numpy array
    y = np.c_[labels]
    # Create and train the model
    svm = SVC(kernel=kernel, C=C,gamma=gamma,decision_function_shape=decision_function_shape, shrinking=shrinking,probability=probability)
    svm.fit(X,y.ravel())
    joblib.dump(svm,'svm_model.joblib')