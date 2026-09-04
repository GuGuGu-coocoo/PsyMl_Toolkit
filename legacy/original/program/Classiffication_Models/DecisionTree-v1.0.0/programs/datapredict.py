# -*- coding: utf-8 -*-
'''
@File    :   datapredict.py
@Author  :   GuGuGu?coocoo! 
@Time    :   2023/05/31 22:52:52 UTC+08:00
for any problem,please contact maintainer@example.invalid
'''
from predict import *

predict_file = 'E:\\Classiffication_Models\\DecisionTree-v1.0.0\\data\\test_p.xlsx'

dt_model = 'E:\\Classiffication_Models\\DecisionTree-v1.0.0\\saved_models\\小学生.joblib'

# predict
dt_predict(predict_file,dt_model)
