# -*- coding: utf-8 -*-
'''
@File    :   datapredict.py
@Author  :   GuGuGu?coocoo! 
@Time    :   2023/05/06 08:49:48 UTC+08:00
'''
from predict import *

predict_file = 'E:\\Classiffication_Models\\Classiffication_Models-v1.1.1\\data\\test.xlsx'

mlp_model = 'E:\\Classiffication_Models\\Classiffication_Models-v1.1.1\\saved_models\\mlp_model.joblib'
svm_model = 'E:\\Classiffication_Models\\Classiffication_Models-v1.1.1\\saved_models\\svm_model.joblib' 
rf_model = 'E:\\Classiffication_Models\\Classiffication_Models-v1.1.1\\saved_models\\rf_model.joblib' 
knn_model = 'E:\\Classiffication_Models\\Classiffication_Models-v1.1.1\\saved_models\\knn_model.joblib'
stack_model = 'E:\\Classiffication_Models\\Classiffication_Models-v1.1.1\\saved_models\\stack_model.joblib'

# predict
mlp_predict(predict_file,mlp_model)
svm_predict(predict_file,svm_model)
rf_predict(predict_file,rf_model)
knn_predict(predict_file,knn_model)
stack_predict(predict_file,stack_model)