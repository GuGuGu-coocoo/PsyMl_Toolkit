# -*- coding: utf-8 -*-
'''
@File    :   predict.py
@Author  :   GuGuGu?coocoo! 
@Time    :   2023/05/03 23:25:43 UTC+08:00
'''
import joblib
import pandas as pd
import numpy as np

# Load the model
predict_file = 'E:\\Classiffication_Models\\Classiffication_Models-v1.2.1\\data\\test.xlsx'

mlp_model = 'E:\\Classiffication_Models\\Classiffication_Models-v1.2.1\\saved_models\\mlp_model.joblib'
svm_model = 'E:\\Classiffication_Models\\Classiffication_Models-v1.2.1\\saved_models\\svm_model.joblib' 
rf_model = 'E:\\Classiffication_Models\\Classiffication_Models-v1.2.1\\saved_models\\rf_model.joblib' 
knn_model = 'E:\\Classiffication_Models\\Classiffication_Models-v1.2.1\\saved_models\\knn_model.joblib'
stack_model = 'E:\\Classiffication_Models\\Classiffication_Models-v1.2.1\\saved_models\\stack_model.joblib'


def mlp_predict(predict_file,mlp_model):
    predict_file = predict_file
    mlp_model = mlp_model

    df = pd.read_excel(predict_file,sheet_name='Sheet1')
    features_num = int(pd.read_excel(predict_file).shape[1])
    X = np.c_[df.iloc[:,:features_num].values.tolist()]
    mlp_model = joblib.load(mlp_model)
    mlp_pred = mlp_model.predict(X)
    mlp_pred=pd.Series(mlp_pred,name='lable')
    print(mlp_pred)
    df = pd.concat([df,mlp_pred],axis=1)
    with pd.ExcelWriter(predict_file,mode='a',engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='mlp_pred',index=False)

def svm_predict(predict_file,svm_model):
    predict_file = predict_file
    svm_model = svm_model

    df = pd.read_excel(predict_file,sheet_name='Sheet1')
    features_num = int(pd.read_excel(predict_file).shape[1])
    X = np.c_[df.iloc[:,:features_num].values.tolist()]
    svm_model = joblib.load(svm_model)
    svm_pred = svm_model.predict(X)
    svm_pred=pd.Series(svm_pred,name='lable')
    print(svm_pred)
    df = pd.concat([df,svm_pred],axis=1)
    with pd.ExcelWriter(predict_file,mode='a',engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='svm_pred',index=False)

def rf_predict(predict_file,rf_model):
    predict_file = predict_file
    rf_model = rf_model

    df = pd.read_excel(predict_file,sheet_name='Sheet1')
    features_num = int(pd.read_excel(predict_file).shape[1])
    X = np.c_[df.iloc[:,:features_num].values.tolist()]
    rf_model = joblib.load(rf_model)
    rf_pred = rf_model.predict(X)
    rf_pred=pd.Series(rf_pred,name='lable')
    print(rf_pred)
    df = pd.concat([df,rf_pred],axis=1)
    with pd.ExcelWriter(predict_file,mode='a',engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='rf_pred',index=False)

def knn_predict(predict_file,knn_model):
    predict_file = predict_file
    knn_model = knn_model

    df = pd.read_excel(predict_file,sheet_name='Sheet1')
    features_num = int(pd.read_excel(predict_file).shape[1])
    X = np.c_[df.iloc[:,:features_num].values.tolist()]
    knn_model = joblib.load(knn_model)
    knn_pred = knn_model.predict(X)
    knn_pred=pd.Series(knn_pred,name='lable')
    print(knn_pred)
    df = pd.concat([df,knn_pred],axis=1)
    with pd.ExcelWriter(predict_file,mode='a',engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='knn_pred',index=False)

def stack_predict(predict_file,stack_model):
    predict_file = predict_file
    stack_model = stack_model

    df = pd.read_excel(predict_file,sheet_name='Sheet1')
    features_num = int(pd.read_excel(predict_file).shape[1])
    X = np.c_[df.iloc[:,:features_num].values.tolist()]
    stack_model = joblib.load(stack_model)
    stack_pred = stack_model.predict(X)
    stack_pred=pd.Series(stack_pred,name='lable')
    print(stack_pred)
    df = pd.concat([df,stack_pred],axis=1)
    with pd.ExcelWriter(predict_file,mode='a',engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='stack_pred',index=False)

