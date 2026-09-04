# -*- coding: utf-8 -*-
'''
@File    :   main.py
@Author  :   GuGuGu?coocoo! 
@Time    :   2023/05/03 18:04:15 UTC+08:00
'''
import threading
import time

from loop_models import *

from MLP_Regressor_sklearn import save_mlp
from SVM_Regressor_sklearn import save_svm
from RandomForest_Regressor_sklearn import save_rf
from KNN_Regressor_sklearn import save_knn
from Lasso_Regressor_sklearn import save_lasso

start_time = time.time()
running = True
file = r'E:\Regression_Models\Regression_Models-v1.0.0\data\interference_4.xlsx'                 # path of the file


test_sizes = [0.2,0.3]                                                                      # list of floats in the range [0.0, inf)
# MLP parameters:
hidden_layer_sizeses = [(70,35),(60,30),(50,25),(40,20),(30,15),(20,10)]                    # list of tulps like (10),(20),(10,20),(20,10,10)....
activations = ['tanh', 'relu', 'logistic', 'identity']                                      # list of strs among {'tanh', 'relu', 'logistic', 'identity'}
solvers = ['lbfgs', 'adam', 'sgd']                                                          # list of strs among {'lbfgs', 'adam', 'sgd'}
m_alphas = [0.01,0.1,1]                                                                     # list of floats in the range [0.0, inf)
max_iters=[500,1000,1500,2000,3000]                                                         # list of ints in the range [1, inf)

# SVM parameters:
kernels = ['rbf', 'sigmoid', 'poly', 'linear']                                              # list of strs among {'rbf', 'sigmoid', 'poly', 'precomputed', 'linear'}.better not use 'precomputed'
Cs = [0.001,0.1,1]                                                                          # list of floats in the range [0.0, inf)
gammas = ['auto','scale',0.001,0.1,1]                                                       # list of strs among {'auto', 'scale'} or a float in the range [0.0, inf).                                                       # list of strs among {'ovo', 'ovr'}
shrinkings =[True,False]                                                                    # list of instances of 'bool'

# RandomForest parameters
n_estimatorses = [25,50,100,150,200]                                                        # list of ints in the range [1, inf)
criterions = ['friedman_mse', 'absolute_error', 'squared_error', 'poisson']                 # list of strs among {'entropy', 'gini', 'log_loss'}
bootstraps = [True]                                                                         # list of instances of 'bool'.But there is someting wrong when using 'False'
oob_scores = [True,False]                                                                   # list of instances of 'bool'

# KNN parameters
n_neighborses=[30,35,40,45,50]                                                              #list of ints in the range [1, inf)
weightses=['uniform', 'distance']                                                           #list of strs among {'uniform', 'distance'}
algorithms=['auto', 'ball_tree', 'kd_tree', 'brute']                                        #list of strs among {'auto', 'ball_tree', 'kd_tree', 'brute'}

# Lasso parameters
l_alphas=[0.01,0.1,1]                                                                       # list of floats in the range [0.0, inf)
fit_intercepts=[True,False]                                                                 # list of instances of 'bool'
precomputes=[True,False]                                                                    # list of instances of 'bool'
max_iters=[500,1000,1500,2000,3000]                                                         # list of ints in the range [1, inf)
positives=[True,False]                                                                      # list of instances of 'bool'
selections=['cyclic', 'random']                                                             # list of strs among{'cyclic', 'random'}
random_state=42                                                                             # a number




def main():
    """
    Loop,save the models
    
    ## MLP:
    #loop_mlp(file,test_sizes,hidden_layer_sizeses,activations,solvers,m_alphas,max_iters)
    #save_mlp(file,hidden_layer_sizeses[0],activations[0],solvers[0],alphas[0],max_iters[0])

    ## SVM:
    #loop_svm(file,test_sizes,kernels,Cs,gammas,shrinkings)
    #save_svm(file,kernels[0],Cs[0],gammas[0],shrinkings[0])
    
    ## RandomForest:
    #loop_rf(file,test_sizes,n_estimatorses, criterions,bootstraps, oob_scores)
    #save_rf(file,n_estimatorses[0], criterions[0],bootstraps[0], oob_scores[0])

    ## KNN:
    #loop_knn(file,test_sizes,n_neighborses,weightses,algorithms)
    #save_knn(file,n_neighborses[0],weightses[0],algorithms[0])
    
    ## Lasso:
    #loop_lasso(file,test_sizes,l_alphas,fit_intercepts, precomputes, max_iters, positives, selections, random_state)
    #save_lasso(file,l_alphas[0], fit_intercepts[0], precomputes[0], max_iters[0], positives[0], selections[0], random_state)


    """
    # train the models:
    loop_mlp(file,test_sizes,hidden_layer_sizeses,activations,solvers,m_alphas,max_iters)
    loop_svm(file,test_sizes,kernels,Cs,gammas,shrinkings)
    loop_rf(file,test_sizes,n_estimatorses, criterions,bootstraps, oob_scores)
    loop_knn(file,test_sizes,n_neighborses,weightses,algorithms)
    loop_lasso(file,test_sizes,l_alphas,fit_intercepts, precomputes, max_iters, positives, selections, random_state)


    # save the models:
    #save_mlp(file,hidden_layer_sizeses[0],activations[0],solvers[0],m_alphas[0],max_iters[0])
    #save_svm(file,kernels[0],Cs[0],gammas[0],shrinkings[0])
    #save_rf(file,n_estimatorses[0], criterions[0],bootstraps[0], oob_scores[0])
    #save_knn(file,n_neighborses[0],weightses[0],algorithms[0])
    #save_lasso(file,l_alphas[0], fit_intercepts[0], precomputes[0], max_iters[0], positives[0], selections[0], random_state)

    
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