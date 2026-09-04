# -*- coding: utf-8 -*-
'''
@File    :   MLP_Regressor_sklearn.py
@Author  :   GuGuGu?coocoo! 
@Time    :   2023/08/18 15:22:03 UTC+08:00
@E-mail  :   maintainer@example.invalid
'''
import numpy as np
import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from scipy.stats import pearsonr
from sklearn.inspection import permutation_importance


def mlp(file,test_size=0.3,hidden_layer_sizes=(60,30),activation='tanh',solver='lbfgs',alpha=1 ,max_iter=500):
    """
    ## file:
    path of the file
    
    ## test_size:
    a float in the range [0.0, inf)
   
    ## hidden_layer_sizes: 
    Setting layers and numbers of neurons.
    (60,30)means 2 layers,the first layers consisting of 60 neurons 
    and the second layer consisting of 30 neurons 
    
    ## activation: 
    a str among {'tanh', 'relu', 'logistic', 'identity'}

    ## solver: 
    a str among {'lbfgs', 'adam', 'sgd'}
    
    ## alpha: 
    a float in the range [0.0, inf).Larger values of alpha lead to stronger regularization, 
    while smaller values of alpha lead to weaker regularization.

    ## max_iter: 
    an int in the range [1, inf)
    """ 
    file = file
    test_size=test_size
    hidden_layer_sizes = hidden_layer_sizes 
    activation = activation          
    solver = solver            
    alpha = alpha                    
    max_iter = max_iter

    # extract the data in each column of the dataframe, and stores it as separate lists               
    df = pd.read_excel(file)
    features_num = int(pd.read_excel(file).shape[1] - 1)
    X = np.c_[df.iloc[:,:features_num].values.tolist()] 
    y = np.c_[df.iloc[:, features_num].tolist()]
    
    
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
        """
        X_min = np.min(X)
        X_max = np.max(X)
        X = (X - X_min)/(X_max - X_min)
        y = y.ravel()
        """
        scaler = StandardScaler()
        X = scaler.fit_transform(X)
        y = scaler.fit_transform(y)
        y = y.ravel()

        return X, y

    X,y = preprocess(X, y)

    # Split the dataset into training and testing data
    train_X, test_X, train_y, test_y = train_test_split(X, y, test_size=test_size, random_state=1846)

    # ---------------------------The above are data preprocessing operations-------------------------------------------
    # print parameters
    print('MLP_Regressor_Sklearn',
          '\nFileName:',file,
          '\nRunning the mlp model with parameters:',
          '\nFeatrue:',features_num,
          '\nTest_size',test_size,
          '\nHidden_layer_sizes:',hidden_layer_sizes,
          '\nActivation:',activation,
          '\nSolver:',solver,
          '\nAlpha:',alpha,
          '\nMax_iter:',max_iter,
          )
    # Create and train the model
    mlp = MLPRegressor(hidden_layer_sizes=hidden_layer_sizes, activation=activation, solver=solver, alpha=alpha, max_iter=max_iter)
    mlp.fit(train_X,train_y)

    # Calculate and save the scores of train and test in mlp_result as a DataFrame
    train_pred_y = mlp.predict(train_X)
    train_r2 = r2_score(train_y, train_pred_y)
    train_mse = mean_squared_error(train_y, train_pred_y)
    train_mae = mean_absolute_error(train_y, train_pred_y)
    

    test_pred_y = mlp.predict(test_X)
    test_r2 = r2_score(test_y, test_pred_y)
    test_mse = mean_squared_error(test_y, test_pred_y)
    test_mae = mean_absolute_error(test_y, test_pred_y)
    # Calculate correlation coefficient and its p-value
    train_corr_coefficient, train_p_value = pearsonr(train_y, train_pred_y)
    test_corr_coefficient, test_p_value = pearsonr(test_y, test_pred_y)

    mlp.fit(X,y)
    # Compute feature importance using Permutation Improtance method
    result = permutation_importance(mlp, X, y, n_repeats=10, random_state=1624)
    # Sort features by importance score
    importance_scores = result.importances_mean
    features = range(X.shape[1])
    sorted_features = [x for _, x in sorted(zip(importance_scores, features), reverse=True)]
    ranks = []

    for i, feature in enumerate(sorted_features):
        feature_name = df.columns[feature]  # Get the column name using the feature index
        print(f"Rank {i+1}: Feature {feature_name} with importance score {importance_scores[feature]}")
        ranks.append(f"{feature_name},{importance_scores[feature]}")
    pred_y = mlp.predict(X)
    r2 = r2_score(y, pred_y)
    mse = mean_squared_error(y, pred_y)
    mae = mean_absolute_error(y, pred_y)
    corr_coefficient, p_value = pearsonr(y, pred_y)
    f_X = np.c_[df.iloc[:,0].values.tolist()]
    f_X = f_X.flatten()
    f_corr_coefficient, f_p_value = pearsonr(f_X, pred_y)
    print('\nr2:',r2,
          '\nmse:',mse,
          '\nmas',mae,
          '\nTrain_r2',train_r2,
          '\nTrain_mse',train_mse,
          '\nTrain_mae',train_mae,
          '\nTest_r2',test_r2,
          '\nTest_mse',test_mse,
          '\nTest_mae',test_mae,
          )
    result_dict = {'Test_size': [test_size],
                       'Hidden_layer_size':[hidden_layer_sizes],
                       'Activation':[activation],
                       'Solver':[solver],
                       'Alpha':[alpha],
                       'max_iter':[max_iter],
                       'F_corr_coefficient':[f_corr_coefficient],
                      'F_p_value':[f_p_value],
                       'R2':[r2],
                       'Corr_Coefficient': [corr_coefficient],
                       'P_Value': [p_value],
                       'MSE':[mse],
                       'MAE':[mae],
                       'Train_r2': [train_r2],
                       'Train_Corr_Coefficient': [train_corr_coefficient],
                       'Train_P_Value': [train_p_value],
                       'Train_mse': [train_mse],
                       'Train_mae': [train_mae],
                       'Test_r2': [test_r2],
                       'Test_Corr_Coefficient': [test_corr_coefficient],
                       'Test_P_Value': [test_p_value],
                       'Test_mse': [test_mse],
                       'Test_mae': [test_mae],
                       }

    for i in range(len(ranks)):
        rank_name = 'Rank{}ImportanceScore'.format(i + 1)
        result_dict[rank_name] = [ranks[i]]   
    mlp_result = pd.DataFrame(result_dict)

    return mlp_result

def save_mlp(file,hidden_layer_sizes=(60,30),activation='tanh',solver='lbfgs',alpha=1 ,max_iter=500):
    file = file
    hidden_layer_sizes = hidden_layer_sizes 
    activation = activation          
    solver = solver            
    alpha = alpha                    
    max_iter = max_iter 
    # extract the data in each column of the dataframe, and stores it as separate lists
    df = pd.read_excel(file)
    features_num = int(pd.read_excel(file).shape[1] - 1)
    X = np.c_[df.iloc[:,:features_num].values.tolist()] 
    y = np.c_[df.iloc[:, features_num].tolist()]
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
        scaler = StandardScaler()
        X = scaler.fit_transform(X)
        y = scaler.fit_transform(y)
        y = y.ravel()

        return X, y

    X,y = preprocess(X, y)

    # Create and train the model
    mlp = MLPRegressor(hidden_layer_sizes=hidden_layer_sizes, activation=activation, solver=solver, alpha=alpha, max_iter=max_iter)
    mlp.fit(X,y)
    joblib.dump(mlp,'mlp_model.joblib')

