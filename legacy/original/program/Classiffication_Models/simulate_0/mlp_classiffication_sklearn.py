# -*- coding: utf-8 -*-
'''
@File    :   mlp_classiffication_sklearn.py
@Author  :   GuGuGu?coocoo! 
@Time    :   2023/04/12 22:40:53 UTC+08:00
'''
import threading
import time

import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import LabelEncoder

start_time = time.time()
running = True
def mlp():
    # extract the data in each column of the dataframe, and stores it as separate lists
    file = 'E:\\Classiffication_Models\\simulated_data.csv'
    df = pd.read_csv(file)
    f1 = df.iloc[:, 0].tolist()
    f2 = df.iloc[:, 1].tolist()
    f3 = df.iloc[:, 2].tolist()
    f4 = df.iloc[:, 3].tolist()
    f5 = df.iloc[:, 4].tolist()
    f6 = df.iloc[:, 5].tolist()
    f7 = df.iloc[:, 6].tolist()
    f8 = df.iloc[:, 7].tolist()
    f9 = df.iloc[:, 8].tolist()
    f10 = df.iloc[:, 9].tolist()
    f11 = df.iloc[:, 10].tolist()
    f12 = df.iloc[:, 11].tolist()
    f13 = df.iloc[:, 12].tolist()
    f14 = df.iloc[:, 13].tolist()
    f15 = df.iloc[:, 14].tolist()
    f16 = df.iloc[:, 15].tolist()
    f17 = df.iloc[:, 16].tolist()
    f18 = df.iloc[:, 17].tolist()
    f19 = df.iloc[:, 18].tolist()
    f20 = df.iloc[:, 19].tolist()
    f21 = df.iloc[:, 20].tolist()
    f22 = df.iloc[:, 21].tolist()
    f23 = df.iloc[:, 22].tolist()
    f24 = df.iloc[:, 23].tolist()
    f25 = df.iloc[:, 24].tolist()
    f26 = df.iloc[:, 25].tolist()
    labels = df.iloc[:, 26].tolist()

    # Concatenate feature columns into a numpy array
    X = np.c_[f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13,f14,f15,f16,f17,f18,f19,f20,f21,f22,f23,f24,f25,f26]
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

        """
        X = X - np.mean(X, axis=0)
        X = X/np.std(X, axis=0, ddof=1)
        X = np.c_[np.ones(len(X)) - 1,X]
        #le = LabelEncoder()
        #y = le.fit_transform(labels)
        y = np.c_[y]
        print(X)
        """
        return X, y

    X,y = preprocess(X, y)
    # print(y)
    

    # Split the data into training and test sets
    """
    m = len(X)
    d = int(m * 0.7)
    train_X,test_X = np.split(X,[d])
    train_y,test_y = np.split(y,[d])
    """
    # Split the dataset into training and testing data
    train_X, test_X, train_y, test_y = train_test_split(X, y, test_size=0.2, random_state=1010)

    # print("PREPROCESS COMPLETED !!!")

    # ---------------------------The above are data preprocessing operations---------------------------------
    mlp = MLPClassifier(hidden_layer_sizes=(20,10), activation='relu', solver='sgd', alpha=0.1, max_iter=1000)
    mlp.fit(train_X,train_y.ravel())
  
    # Compute feature importance using Permutation Improtance method
    result = permutation_importance(mlp, X, y, n_repeats=10, random_state=1624)
    
    # Accuracy
    print('Training accuracy =',mlp.score(train_X,train_y))
    print('Testing accuracy =',mlp.score(test_X,test_y))

    # Calculate and output the confusion matrix and classification report for the training and testing sets separately
    print('Training confusion matrix:\n',confusion_matrix(train_y,mlp.predict(train_X)))
    print('Testing confusion matrix:\n',confusion_matrix(test_y,mlp.predict(test_X)))
    print('Training classification report:\n',classification_report(train_y,mlp.predict(train_X),))
    print('Testing classification report:\n',classification_report(test_y,mlp.predict(test_X)))
    
    # Sort features by importance score
    importance_scores = result.importances_mean
    features = range(X.shape[1])
    sorted_features = [x for _,x in sorted(zip(importance_scores, features), reverse=True)]

    # Print sorted features by importance score
    for i, feature in enumerate(sorted_features):
        print(f"Rank {i+1}: Feature {feature + 1} with importance score {importance_scores[feature]}")
 
    global running
    running = False


def print_time():
    global running
    while running:
        current_time = time.time()
        elapsed_time = current_time - start_time
        print(f"Program has been running for {elapsed_time:.2f}s")
        time.sleep(1)
    if not running:
        print(f"Program running time is {elapsed_time:.2f}s")


t1 = threading.Thread(target=mlp)
t2 = threading.Thread(target=print_time)

t1.start()
t2.start()

t1.join()
t2.join()