# -*- coding: utf-8 -*-
'''
@File    :   RandomForest_Regressor_sklearn.py
@Author  :   GuGuGu?coocoo! 
@Time    :   2023/08/20 14:54:35 UTC+08:00
@E-mail  :   maintainer@example.invalid
'''
import numpy as np
import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from scipy.stats import pearsonr
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
    y = np.c_[df.iloc[:, features_num].tolist()]
    y = y.ravel()
    # Split the dataset into training and testing data
    train_X, test_X, train_y, test_y = train_test_split(X, y, test_size=test_size, random_state=1846)

    # ---------------------------The above are data preprocessing operations-------------------------------------------
    # print parameters
    print('RandomForest_Regressor_Sklearn',
          '\nFileName:',file,
          '\nRunning the randomforest model with parameters:',
          '\nFeatrue:',features_num,
          '\nTest_size',test_size,
          '\nN_estimators:',n_estimators, 
          '\nCriterion:',criterion,
          '\nBootstrap:',bootstrap, 
          '\nOob_score:',oob_score,
          )
    
    # Create an instance of the randomforest regressor and Train the regressor on the training data
    rf =RandomForestRegressor(n_estimators=n_estimators, criterion=criterion,bootstrap=bootstrap, oob_score=oob_score,n_jobs=-1)
    rf.fit(train_X, train_y)

    # Calculate and save the scores of train and test in rf_result as a DataFrame
    train_pred_y = rf.predict(train_X)
    train_r2 = r2_score(train_y, train_pred_y)
    train_mse = mean_squared_error(train_y, train_pred_y)
    train_mae = mean_absolute_error(train_y, train_pred_y)
    

    test_pred_y = rf.predict(test_X)
    test_r2 = r2_score(test_y, test_pred_y)
    test_mse = mean_squared_error(test_y, test_pred_y)
    test_mae = mean_absolute_error(test_y, test_pred_y)
    # Calculate correlation coefficient and its p-value
    train_corr_coefficient, train_p_value = pearsonr(train_y, train_pred_y)
    test_corr_coefficient, test_p_value = pearsonr(test_y, test_pred_y)


    rf.fit(X,y)
    # Compute feature importance using Permutation Improtance method
    result = permutation_importance(rf, X, y, n_repeats=10, random_state=1624)
    # Sort features by importance score
    importance_scores = result.importances_mean
    features = range(X.shape[1])
    sorted_features = [x for _, x in sorted(zip(importance_scores, features), reverse=True)]
    ranks = []

    for i, feature in enumerate(sorted_features):
        feature_name = df.columns[feature]  # Get the column name using the feature index
        print(f"Rank {i+1}: Feature {feature_name} with importance score {importance_scores[feature]}")
        ranks.append(f"{feature_name},{importance_scores[feature]}")
    pred_y = rf.predict(X)
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
                      'N_estimators':[n_estimators],
                      'Criterion':[criterion],
                      'Bootstrap':[bootstrap],
                      'Oob_score':[oob_score],
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

    rf_result = pd.DataFrame(result_dict)

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
    y = np.c_[df.iloc[:, features_num].tolist()]
    y = y.ravel()
    # Create and train the model
    rf =RandomForestRegressor(n_estimators=n_estimators, criterion=criterion,bootstrap=bootstrap, oob_score=oob_score)
    rf.fit(X,y)
    joblib.dump(rf,'rf_model.joblib')
