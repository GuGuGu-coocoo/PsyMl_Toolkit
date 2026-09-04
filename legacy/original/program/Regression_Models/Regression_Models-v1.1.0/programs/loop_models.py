# -*- coding: utf-8 -*-
'''
@File    :   loop_models.py
@Author  :   GuGuGu?coocoo! 
@Time    :   2023/04/30 01:21:58 UTC+08:00
'''
import pandas as pd
from MLP_Regressor_sklearn import mlp
from SVM_Regressor_sklearn import svm
from RandomForest_Regressor_sklearn import rf
from KNN_Regressor_sklearn import knn
from Lasso_Regressor_sklearn import lasso
mlp_results = []
svm_results = []
rf_results = []
knn_results = []
lasso_results = []
def loop_mlp(file,test_sizes,hidden_layer_sizeses,activations,solvers,m_alphas,max_iters):
    """
    loop the mlp and save the reuslts in 'mlp'sheet of 'models_result.xlsx'
    
    ## file:
    path of the file

    ## test_sizes:
    list of floats in the range [0.0, inf)
    
    ## hidden_layer_sizes:
    list of tulps like (10),(20),(10,20),(20,10,10)....
    
    ## activations:
    list of strs among {'tanh', 'relu', 'logistic', 'identity'}
    
    ## solvers: 
    list of strs among {'lbfgs', 'adam', 'sgd'}
    
    ## m_alphas:
    list of floats in the range [0.0, inf)
    
    ## max_iters:
    list of ints in the range [1, inf)
    """
    file = file
    test_sizes=test_sizes
    hidden_layer_sizeses = hidden_layer_sizeses 
    activations = activations          
    solvers = solvers            
    m_alphas = m_alphas                    
    max_iters = max_iters
    for test_size in test_sizes: 
        for hidden_layer_sizes in hidden_layer_sizeses:
            for activation in activations:
                for solver in solvers:
                    for alpha in m_alphas:
                        for max_iter in max_iters:
                            mlp_result = mlp(file,test_size,hidden_layer_sizes,activation,solver,alpha,max_iter)
                            mlp_results.append(mlp_result)

    mlp_writer = pd.ExcelWriter('mlp_result.xlsx',engine='xlsxwriter')                        
    mlp_sheet_name = 'mlp'
    mlp_sheet_exists = True
    for i, mlp_result in enumerate(mlp_results):
        if i==0:
            mlp_result.to_excel(mlp_writer,sheet_name=mlp_sheet_name,index=False,startrow=i,header=mlp_sheet_exists)
            mlp_sheet_exists = False
        else:
            mlp_result.to_excel(mlp_writer,sheet_name=mlp_sheet_name,index=False,startrow=i+1,header=mlp_sheet_exists)
    mlp_writer._save()



def loop_svm(file,test_sizes,kernels,Cs,gammas,shrinkings):
    """
    loop the svm and save the reuslts in 'svm'sheet of 'models_result.xlsx'
    ## file:
    path of the file

    ## test_sizes:
    list of floats in the range [0.0, inf)

    ## kernels
    list of strs among {'rbf', 'sigmoid', 'poly', 'precomputed', 'linear'}.

    ## Cs:
    list of floats in the range [0.0, inf)

    ## gammas:
    list of strs among {'auto', 'scale'} or a float in the range [0.0, inf).
      
    ## shrinkings:
    list of instances of 'bool'
    
    """
    file = file
    test_sizes=test_sizes
    kernels = kernels
    Cs = Cs
    gammas = gammas
    shrinkings = shrinkings
    for test_size in test_sizes:
        for kernel in kernels:
            for C in Cs:
                for gamma in gammas:
                    for shrinking in shrinkings:
                        svm_result = svm(file,test_size,kernel,C,gamma,shrinking,)
                        svm_results.append(svm_result)
    svm_writer = pd.ExcelWriter('svm_result.xlsx',engine='xlsxwriter')
    svm_sheet_name = 'svm'
    svm_sheet_exists = True
    for i, svm_result in enumerate(svm_results):
        if i==0:
            svm_result.to_excel(svm_writer,sheet_name=svm_sheet_name,index=False,startrow=i,header=svm_sheet_exists)
            svm_sheet_exists = False
        else:
            svm_result.to_excel(svm_writer,sheet_name=svm_sheet_name,index=False,startrow=i+1,header=svm_sheet_exists)
    svm_writer._save()

def loop_rf(file,test_sizes,n_estimatorses, criterions,bootstraps, oob_scores):
    """
    loop the svm and save the reuslts in 'rf'sheet of 'models_result.xlsx'
    ## file:
    path of the file
    
    ## test_sizes:
    list of floats in the range [0.0, inf)

    ## n_estimatorses
    list of ints in the range [1, inf)
    
    ## criterions
    list of strs among {'entropy', 'gini', 'log_loss'}

    ## bootstraps
    list of instances of 'bool'
    
    ## oob_scores
    list of instances of 'bool'
    
    """
    file=file
    test_sizes=test_sizes
    n_estimatorses=n_estimatorses
    criterions=criterions
    bootstraps=bootstraps
    oob_scores=oob_scores
    for test_size in test_sizes:
        for n_estimators in n_estimatorses:
            for criterion in criterions:
                for bootstrap in bootstraps:
                    for oob_score in oob_scores:
                        rf_result = rf(file,test_size,n_estimators, criterion,bootstrap, oob_score)
                        rf_results.append(rf_result)
    rf_writer = pd.ExcelWriter('rf_result.xlsx',engine='xlsxwriter')
    rf_sheet_name = 'rf'
    rf_sheet_exists = True
    for i, rf_result in enumerate(rf_results):
        if i==0:
            rf_result.to_excel(rf_writer,sheet_name=rf_sheet_name,index=False,startrow=i,header=rf_sheet_exists)
            rf_sheet_exists = False
        else:
            rf_result.to_excel(rf_writer,sheet_name=rf_sheet_name,index=False,startrow=i+1,header=rf_sheet_exists)
    rf_writer._save()


def loop_knn(file,test_sizes,n_neighborses,weightses,algorithms):
    """
    ## file:
    path of the file
    
    ## test_size:
    list of floats in the range [0.0, inf)

    ## n_neighbors:
    list of ints in the range [1, inf)

    ## weights:
    list of strs among {'uniform', 'distance'}

    ## algorithm:
    list of strs among {'auto', 'ball_tree', 'kd_tree', 'brute'}
    """
    file=file
    test_sizes=test_sizes
    n_neighborses=n_neighborses
    weightses=weightses
    algorithms=algorithms
    for test_size in test_sizes:
        for n_neighbors in n_neighborses:
            for weights in weightses:
                for algorithm in algorithms:
                    knn_result = knn(file,test_size,n_neighbors,weights,algorithm)
                    knn_results.append(knn_result)

    knn_writer = pd.ExcelWriter('knn_result.xlsx',engine='xlsxwriter')
    knn_sheet_name = 'knn'
    knn_sheet_exists = True
    for i, knn_result in enumerate(knn_results):
        if i==0:
            knn_result.to_excel(knn_writer,sheet_name=knn_sheet_name,index=False,startrow=i,header=knn_sheet_exists)
            knn_sheet_exists = False
        else:
            knn_result.to_excel(knn_writer,sheet_name=knn_sheet_name,index=False,startrow=i+1,header=knn_sheet_exists)
    knn_writer._save()

def loop_lasso(file,test_sizes,l_alphas, fit_intercepts, precomputes, max_iters, positives, selections, random_state):
    file = file
    test_sizes=test_sizes
    l_alphas = l_alphas
    fit_intercepts = fit_intercepts
    precomputes = precomputes
    max_iters = max_iters
    positives = positives
    selections = selections
    random_state = random_state

    for test_size in test_sizes:
        for alpha in l_alphas:
            for fit_intercept in fit_intercepts:
                for precompute in precomputes:
                    for max_iter in max_iters:
                        for positive in positives:
                            for selection in selections:
                                lasso_result = lasso(file, test_size,alpha, fit_intercept, precompute, max_iter, positive, selection, random_state)
                                lasso_results.append(lasso_result)

    lasso_writer = pd.ExcelWriter('lasso_result.xlsx',engine='xlsxwriter')                        
    lasso_sheet_name = 'lasso'
    lasso_sheet_exists = True
    for i, lasso_result in enumerate(lasso_results):
        if i==0:
            lasso_result.to_excel(lasso_writer,sheet_name=lasso_sheet_name,index=False,startrow=i,header=lasso_sheet_exists)
            lasso_sheet_exists = False
        else:
            lasso_result.to_excel(lasso_writer,sheet_name=lasso_sheet_name,index=False,startrow=i+1,header=lasso_sheet_exists)
    lasso_writer._save()
