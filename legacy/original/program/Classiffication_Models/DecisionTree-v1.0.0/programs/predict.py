# -*- coding: utf-8 -*-
'''
@File    :   predict.py
@Author  :   GuGuGu?coocoo! 
@Time    :   2023/05/31 22:53:22 UTC+08:00
for any problem,please contact maintainer@example.invalid
'''
import joblib
import pandas as pd
import numpy as np

def dt_predict(predict_file,dt_model):
    predict_file = predict_file
    dt_model = dt_model

    df = pd.read_excel(predict_file,sheet_name='Sheet1')
    features_num = int(pd.read_excel(predict_file).shape[1])
    X = np.c_[df.iloc[:,:features_num].values.tolist()]
    dt_model = joblib.load(dt_model)
    dt_pred = dt_model.predict(X)
    dt_pred=pd.Series(dt_pred,name='lable')
    print(dt_pred)
    df = pd.concat([df,dt_pred],axis=1)
    with pd.ExcelWriter(predict_file,mode='a',engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='dt_pred',index=False)

