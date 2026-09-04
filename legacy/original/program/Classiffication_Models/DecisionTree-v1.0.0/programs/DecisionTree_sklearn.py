# -*- coding: utf-8 -*-
'''
@File    :   DecisionTree_sklearn.py
@Author  :   GuGuGu?coocoo! 
@Time    :   2023/05/31 22:53:13 UTC+08:00
for any problem,please contact maintainer@example.invalid
'''
import numpy as np
import pandas as pd
import joblib
from sklearn.inspection import permutation_importance
from sklearn.metrics import accuracy_score,classification_report, confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.tree import export_graphviz
import graphviz

def dt(file,test_size=0.3,criterion='gini', max_depth=6, min_samples_split=60):

    file = file
    test_size=test_size
    criterion=criterion
    max_depth=max_depth
    min_samples_split=min_samples_split
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
        """
        # Normalize the feature
        X_min = np.min(X)
        X_max = np.max(X)
        X = (X - X_min)/(X_max - X_min)
        """

        return X, y

    X,y = preprocess(X, y)

    # Split the dataset into training and testing data
    train_X, test_X, train_y, test_y = train_test_split(X, y, test_size=test_size, random_state=1325)

    # ---------------------------The above are data preprocessing operations-------------------------------------------
    # print parameters
    print('DecisionTree_Sklearn','\nFileName:',file,'\nRunning the dt model with parameters:','\nFeatrue:',features_num,'\nTest_size',test_size,'\ncriterion:',criterion,
          '\nmax_depth:',max_depth,'\nmin_samples_split:',min_samples_split,)
    # Create and train the model
    dt = DecisionTreeClassifier(criterion=criterion, max_depth=max_depth,min_samples_split=min_samples_split)
    dt.fit(train_X,train_y.ravel())
  
    # Compute feature importance using Permutation Improtance method
    result = permutation_importance(dt, X, y, n_repeats=10, random_state=1624)
    # Print accuracy
    print('Training accuracy =',dt.score(train_X,train_y))
    print('Testing accuracy =',dt.score(test_X,test_y))

    # Calculate and output the confusion matrix and classification report for the training and testing sets separately  
    print('Training confusion matrix:\n',confusion_matrix(train_y,dt.predict(train_X)))
    print('Testing confusion matrix:\n',confusion_matrix(test_y,dt.predict(test_X)))
    print('Training classification report:\n',classification_report(train_y,dt.predict(train_X),))
    print('Testing classification report:\n',classification_report(test_y,dt.predict(test_X)))

    # Sort features by importance score
    importance_scores = result.importances_mean
    features = range(X.shape[1])
    sorted_features = [x for _,x in sorted(zip(importance_scores, features), reverse=True)]

    # Print sorted features by importance score
    ranks = []
    for i, feature in enumerate(sorted_features):
        print(f"Rank {i+1}: Feature {feature + 1} with importance score {importance_scores[feature]}")
        ranks.append(f"f{feature + 1},{importance_scores[feature]}")
    # Calculate and save the scores of train and test in dt_result as a DataFrame
    train_pred_y = dt.predict(train_X)
    train_accuracy = accuracy_score(train_y,train_pred_y)
    train_precision, train_recall, train_f1_score, train_support = precision_recall_fscore_support(train_y,train_pred_y,average='weighted')
    train_support = len(train_y)
    test_pred_y = dt.predict(test_X)
    test_accuracy = accuracy_score(test_y,test_pred_y)
    test_precision, test_recall, test_f1_score, test_support = precision_recall_fscore_support(test_y,test_pred_y,average='weighted')
    test_support = len(test_y)
    dt_result_dict = {'Test_size': [test_size],
                       'Criterion':[criterion],
                       'Max_depth':[max_depth],
                       'Min_samples_split':[min_samples_split],
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
        dt_result_dict[rank_name] = [ranks[i]]
        
    dt_result = pd.DataFrame(dt_result_dict)


    
    return dt_result

def save_dt(file,file_name,criterion='gini', max_depth=5, min_samples_split=10):
    file = file
    file_name=file_name
    criterion=criterion
    max_depth=max_depth
    min_samples_split=min_samples_split
    # extract the data in each column of the dataframe, and stores it as separate lists
    df = pd.read_excel(file)
    features_num = int(pd.read_excel(file).shape[1] - 1)
    X = df.iloc[:, : features_num].values.tolist() 
    labels = df.iloc[:, features_num].tolist()

    # Convert the labels column into a numpy array
    y = np.c_[labels]
    # Create and train the model
    dt = DecisionTreeClassifier(criterion=criterion, max_depth=max_depth,min_samples_split=min_samples_split)
    dt.fit(X,y)
    joblib.dump(dt,'{}.joblib'.format(file_name))

def plot_dt(file,file_name,criterion='gini', max_depth=5, min_samples_split=10):
    file = file
    file_name = file_name
    criterion=criterion
    max_depth=max_depth
    min_samples_split=min_samples_split
    # extract the data in each column of the dataframe, and stores it as separate lists               
    df = pd.read_excel(file)
    features_num = int(pd.read_excel(file).shape[1] - 1)
    X = np.c_[df.iloc[:,:features_num].values.tolist()] 
    labels = df.iloc[:, features_num].tolist()
    feature_name = df.columns[:-1].tolist()
    
    # Convert the labels column into a numpy array
    y = np.c_[labels]
    
    # create and train
    dt = DecisionTreeClassifier(criterion=criterion, max_depth=max_depth,min_samples_split=min_samples_split)
    dt.fit(X,y)
    # Generate decision tree in Graphviz format
    dot_data = export_graphviz(dt, out_file=None, feature_names=feature_name, class_names=['0','1','2','3','4'],filled=True, rounded=True)

    # Visualize using the Graphviz library
    graph = graphviz.Source(dot_data)
    graph.render("{}".format(file_name))  # Optional step to save the decision tree as an image file
    graph.view()  # Display the decision tree in a window

def print_dt(file,criterion='gini', max_depth=5, min_samples_split=10):
    file = file
    criterion=criterion
    max_depth=max_depth
    min_samples_split=min_samples_split
    # extract the data in each column of the dataframe, and stores it as separate lists               
    df = pd.read_excel(file)
    features_num = int(pd.read_excel(file).shape[1] - 1)
    X = np.c_[df.iloc[:,:features_num].values.tolist()] 
    labels = df.iloc[:, features_num].tolist()
    feature_name = df.columns[:-1].tolist()
    
    # Convert the labels column into a numpy array
    y = np.c_[labels]
    
    # create and train
    dt = DecisionTreeClassifier(criterion=criterion, max_depth=max_depth,min_samples_split=min_samples_split)
    dt.fit(X,y)

    def print_decision_tree_class_conditions(tree, feature_names, class_names):
        left = tree.tree_.children_left
        right = tree.tree_.children_right
        threshold = tree.tree_.threshold
        feature = tree.tree_.feature

        def recurse(node, depth, condition):
            if threshold[node] != -2:
                feature_name = feature_names[feature[node]]
                threshold_value = threshold[node]
                
                condition.append(f"{feature_name} <= {threshold_value:.4f}")
                recurse(left[node], depth + 1, condition)
                condition[-1] = f"{feature_name} > {threshold_value:.4f}"
                recurse(right[node], depth + 1, condition)
                condition.pop()
            else:
                class_index = tree.tree_.value[node].argmax()
                class_label = class_names[class_index]
                print(f"if {' and '.join(condition)}, class = {class_label}")

        recurse(0, 0, [])
    print_decision_tree_class_conditions(dt,feature_names=feature_name,class_names=['0','1','2','3','4'])
