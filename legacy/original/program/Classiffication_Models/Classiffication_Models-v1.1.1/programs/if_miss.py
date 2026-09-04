# -*- coding: utf-8 -*-
'''
@File    :   if_miss.py
@Author  :   GuGuGu?coocoo! 
@Time    :   2023/04/29 16:01:09 UTC+08:00
'''
import numpy as np
import pandas as pd
file = 'E:\\Classiffication_Models\\real\\standardized-data.xlsx'
df = pd.read_excel(file)
print(df.isnull().sum())