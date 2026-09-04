# -*- coding: utf-8 -*-
'''
@File    :   f1-fn.py
@Author  :   GuGuGu?coocoo! 
@Time    :   2023/04/30 17:59:38 UTC+08:00
'''
feature = 40
for i in range(1, feature + 1):
    f = 'f{}'.format(i)
    code_str = '{} = df.iloc[:, {}].tolist()'.format(f, i-1)
    print(code_str)
feature = 40
for j in range(1, feature + 1):
    ranks = "'Rank{}ImportanceScore':[ranks[{}]],".format(j,j-1)
    print(ranks)