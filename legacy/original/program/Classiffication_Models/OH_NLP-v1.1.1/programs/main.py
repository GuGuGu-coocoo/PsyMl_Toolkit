# -*- coding: utf-8 -*-
'''
@File    :   main.py
@Author  :   GuGuGu?coocoo! 
@Time    :   2023/08/13 09:47:01 UTC+08:00
@E-mail  :   maintainer@example.invalid
'''
import threading
import time

from loop_model import *
from RNN_pytorch import *
from predict import *


start_time = time.time()
running = True

path = r'E:\pythonProject\Classiffication_Models\OH_NLP-v1.1.1\data\primary_school.xlsx'
predict_path = r'E:\pythonProject\Classiffication_Models\OH_NLP-v1.1.1\data\testp.xlsx'
model_path = r'E:\pythonProject\Classiffication_Models\OH_NLP-v1.1.1\saved_models\primary_school.pth' 
vocab_path = r'E:\pythonProject\Classiffication_Models\OH_NLP-v1.1.1\results\primary_school_vocab.xlsx'

batch_sizes =[16,32,64]
test_sizes = [0.2,0.3]
hidden_sizes = [100,50,25]
L1s=[20,30,40] 
L2s=[40,50,60]
num_epochses = [20,30]
lrs=[0.001,0.01]
plt_statuses = [False]

def main():
    #loop_rnn(path, vocab_path,batch_sizes[:1], test_sizes[:1], hidden_sizes[:1], L1s[:1], L2s[:1], num_epochses[:1], lrs[:1], plt_statuses)     # test
    #loop_rnn(path, vocab_path,batch_sizes, test_sizes, hidden_sizes, L1s, L2s, num_epochses, lrs, plt_statuses)
    #save_rnn(path, vocab_path,batch_sizes[0], test_sizes[0], hidden_sizes[0], L1s[0], L2s[0], num_epochses[0], lrs[0], plt_statuses[0])
    #save_vocabulary(path)
    rnn_predict(vocab_path,predict_path,model_path)
    
    global running
    running = False

def print_time():
    global running
    while running:
        current_time = time.time()
        elapsed_time = current_time - start_time
        print(f"Program has been running for {elapsed_time:.2f}s")
        time.sleep(1)
    if not running:
        print(f"Program running time is {elapsed_time:.2f}s")


t1 = threading.Thread(target=main)
t2 = threading.Thread(target=print_time)

t1.start()
t2.start()

t1.join()
t2.join()
