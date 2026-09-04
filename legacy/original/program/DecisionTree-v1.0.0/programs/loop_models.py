# -*- coding: utf-8 -*-
'''
@File    :   loop_models.py
@Author  :   GuGuGu?coocoo! 
@Time    :   2023/05/31 22:53:02 UTC+08:00
for any problem,please contact maintainer@example.invalid
'''
import pandas as pd
from DecisionTree_sklearn import dt

dt_results = []
def loop_dt(file,file_name,test_sizes,criterions, max_depths,min_samples_splits):

    file = file
    file_name = file_name
    test_sizes=test_sizes
    criterions=criterions
    max_depths=max_depths
    min_samples_splits=min_samples_splits
    for test_size in test_sizes: 
        for criterion in criterions:
            for max_depth in max_depths:
                for min_samples_split in min_samples_splits:
                    dt_result = dt(file,test_size,criterion, max_depth,min_samples_split)
                    dt_results.append(dt_result)

    dt_writer = pd.ExcelWriter('{}.xlsx'.format(file_name),engine='xlsxwriter')                        
    dt_sheet_name = '{}'.format(file_name)
    dt_sheet_exists = True
    for i, dt_result in enumerate(dt_results):
        if i==0:
            dt_result.to_excel(dt_writer,sheet_name=dt_sheet_name,index=False,startrow=i,header=dt_sheet_exists)
            dt_sheet_exists = False
        else:
            dt_result.to_excel(dt_writer,sheet_name=dt_sheet_name,index=False,startrow=i+1,header=dt_sheet_exists)
    dt_writer._save()

