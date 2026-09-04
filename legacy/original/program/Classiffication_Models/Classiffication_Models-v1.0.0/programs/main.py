# -*- coding: utf-8 -*-
'''
@File    :   main.py
@Author  :   GuGuGu?coocoo! 
@Time    :   2023/04/30 11:18:59 UTC+08:00
'''
import threading
import time

from loop_models import *
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC

start_time = time.time()
running = True
file = 'E:\\Classiffication_Models\\real\\data\\subdimension-data.xlsx'                     # path of the file
test_sizes = [0.2,0.3]                                                                      # list of floats in the range [0.0, inf)
# MLP parameters:
hidden_layer_sizeses = [(70,35),(60,30),(50,25),(40,20),(30,15),(20,10)]                    # list of tulps like (10),(20),(10,20),(20,10,10)....
activations = ['tanh', 'relu', 'logistic', 'identity']                                      # list of strs among {'tanh', 'relu', 'logistic', 'identity'}
solvers = ['lbfgs', 'adam', 'sgd']                                                          # list of strs among {'lbfgs', 'adam', 'sgd'}
alphas = [0.01,0.1,1]                                                                       # list of floats in the range [0.0, inf)
max_iters = [500,700,1000,1500]                                                             # list of ints in the range [1, inf)

# SVM parameters:
kernels = ['rbf', 'sigmoid', 'poly', 'linear']                                              # list of strs among {'rbf', 'sigmoid', 'poly', 'precomputed', 'linear'}.better not use 'precomputed'
Cs = [0.001,0.1,1]                                                                          # list of floats in the range [0.0, inf)
gammas = ['auto','scale',0.001,0.1,1]                                                       # list of strs among {'auto', 'scale'} or a float in the range [0.0, inf).    
decision_function_shapes = ['ovo','ovr']                                                    # list of strs among {'ovo', 'ovr'}
shrinkings =[True,False]                                                                    # list of instances of 'bool'
probabilitys = [True,False]                                                                 # list of instances of 'bool'

# RandomForest parameters
n_estimatorses = [25,50,100,150,200]                                                        # list of ints in the range [1, inf)
criterions = ['entropy', 'gini', 'log_loss']                                                # list of strs among {'entropy', 'gini', 'log_loss'}
bootstraps = [True]                                                                         # list of instances of 'bool'.But there is someting wrong when using 'False'
oob_scores = [True,False]                                                                   # list of instances of 'bool'

# KNN parameters
n_neighborses=[30,35,40,45,50]                                                              #list of ints in the range [1, inf)
weightses=['uniform', 'distance']                                                           #list of strs among {'uniform', 'distance'}
algorithms=['auto', 'ball_tree', 'kd_tree', 'brute']                                        #list of strs among {'auto', 'ball_tree', 'kd_tree', 'brute'}

# Stack parameters.Finding the best parameters of every estimator.
estimatorses=[[
    ('mlp',MLPClassifier(hidden_layer_sizes=(20,10),activation='identity',solver='adam',alpha=0.1,max_iter=500)),
    ('svm',SVC(kernel='poly',C = 1,gamma='scale',decision_function_shape='ovo',shrinking=True,probability=True)),
    ('rf',RandomForestClassifier(n_estimators=150, criterion='entropy',bootstrap=True, oob_score=True)),
    ('knn',KNeighborsClassifier(n_neighbors=35,weights='distance',algorithm='auto')),],
    ]
final_estimators=[MLPClassifier(hidden_layer_sizes=(20,10),activation='identity',solver='adam'
                                ,alpha=0.1 ,max_iter=1000),
    ]

def main():
    """
    loop  the models
    ## MLP:
    loop_mlp(file,test_sizes,hidden_layer_sizeses,activations,solvers,alphas,max_iters)
    ## SVM:
    loop_svm(file,test_sizes,kernels,Cs,gammas,decision_function_shapes,shrinkings,probabilitys)
    ## RandomForest:
    loop_rf(file,test_sizes,n_estimatorses, criterions,bootstraps, oob_scores)
    ## KNN:
    loop_knn(file,test_sizes,n_neighborses,weightses,algorithms)

    ## Stack:
    loop_stack(file,test_sizes,estimatorses,final_estimators)

    """
    loop_mlp(file,test_sizes,hidden_layer_sizeses,activations,solvers,alphas,max_iters)
    #loop_svm(file,test_sizes,kernels,Cs,gammas,decision_function_shapes,shrinkings,probabilitys)
    #loop_rf(file,test_sizes,n_estimatorses, criterions,bootstraps, oob_scores)
    #loop_knn(file,test_sizes,n_neighborses,weightses,algorithms)
    #loop_stack(file,test_sizes,estimatorses,final_estimators)
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


t1 = threading.Thread(target=main)
t2 = threading.Thread(target=print_time)

t1.start()
t2.start()

t1.join()
t2.join()