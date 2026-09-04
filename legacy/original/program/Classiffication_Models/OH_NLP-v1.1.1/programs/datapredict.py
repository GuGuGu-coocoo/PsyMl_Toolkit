# -*- coding: utf-8 -*-
'''
@File    :   datapredict.py
@Author  :   GuGuGu?coocoo! 
@Time    :   2023/08/13 09:50:09 UTC+08:00
@E-mail  :   maintainer@example.invalid
'''
from predict import *

predict_path = r'E:\pythonProject\Classiffication_Models\OH_NLP-v1.1.1\data\testp.xlsx'
model_path = r'E:\pythonProject\Classiffication_Models\OH_NLP-v1.1.1\saved_models\primary_school.pth' 
vocab_path = r'E:\pythonProject\Classiffication_Models\OH_NLP-v1.1.1\results\primary_school_vocab.xlsx'

# 预测
rnn_predict(vocab_path,predict_path,model_path)
