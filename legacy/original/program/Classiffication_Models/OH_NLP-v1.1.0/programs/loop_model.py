# -*- coding: utf-8 -*-
'''
@File    :   loop_model.py
@Author  :   GuGuGu?coocoo! 
@Time    :   2023/08/13 09:50:23 UTC+08:00
@E-mail  :   maintainer@example.invalid
'''
import pandas as pd
import os
from RNN_pytorch import rnn
rnn_results = []
def loop_rnn(path,vocab_path, batch_sizes, test_sizes, hidden_sizes, L1s, L2s, num_epochses, lrs, plt_statuses):
    path = path
    vocab_path =vocab_path
    batch_sizes = batch_sizes
    test_sizes = test_sizes
    hidden_sizes = hidden_sizes
    L1s=L1s
    L2s=L2s
    num_epochses = num_epochses
    lrs=lrs
    plt_statuses = plt_statuses
    file_name = os.path.splitext(os.path.basename(path))[0]
    for batch_size in batch_sizes:
        for test_size in test_sizes:
            for hidden_size in hidden_sizes:
                for L1 in L1s:
                    for L2 in L2s:
                        for num_epochs in num_epochses:
                            for lr in lrs:
                                for plt_status in plt_statuses:
                                    rnn_result = rnn(path, vocab_path,batch_size, test_size, hidden_size, L1, L2, num_epochs, lr, plt_status)
                                    rnn_results.append(rnn_result)
    file_name = os.path.splitext(os.path.basename(path))[0]
    current_directory = os.getcwd()
    target_directory = os.path.join(current_directory, 'results')
    if not os.path.exists(target_directory):
        os.makedirs(target_directory)
    file_path = os.path.join(target_directory, '{}_result.xlsx'.format(file_name))
    rnn_writer = pd.ExcelWriter(file_path.format(file_name),engine='xlsxwriter')                        
    rnn_sheet_name = 'rnn'
    rnn_sheet_exists = True
    for i, rnn_result in enumerate(rnn_results):
        if i==0:
            rnn_result.to_excel(rnn_writer,sheet_name=rnn_sheet_name,index=False,startrow=i,header=rnn_sheet_exists)
            rnn_sheet_exists = False
        else:
            rnn_result.to_excel(rnn_writer,sheet_name=rnn_sheet_name,index=False,startrow=i+1,header=rnn_sheet_exists)
    rnn_writer._save()


                     
