# -*- coding: utf-8 -*-
'''
@File    :   main.py
@Author  :   GuGuGu?coocoo! 
@Time    :   2023/05/27 19:46:11 UTC+08:00
for any problem,please contact maintainer@example.invalid
'''
import threading
import time

from loop_models import *
from DecisionTree_sklearn import plot_dt,save_dt,print_dt
from predict import dt_predict

start_time = time.time()
running = True
file = 'E:\\Classiffication_Models\\DecisionTree-v1.0.0\\data\\p.xlsx'               # path of the file
predict_file = 'E:\\Classiffication_Models\\DecisionTree-v1.0.0\\data\\test_p.xlsx'
dt_model = 'E:\\Classiffication_Models\\DecisionTree-v1.0.0\\saved_models\\小学生.joblib'

file_name = '小学生'

test_sizes = [0.2,0.3]                                                               
# parameters:
criterions=['gini', 'entropy', 'log_loss']
max_depths=[2,3,4,5,6,7,8,9,10]
min_samples_splits=[5,10,20,25,30,40,50,60,100,200,300]

def main():
    
    # train the models:
    #loop_dt(file,file_name,test_sizes,criterions, max_depths, min_samples_splits)

    # save the models:
    #save_dt(file,file_name,criterions[0], max_depths[0], min_samples_splits[0])

    # Visualize
    #plot_dt(file,file_name,criterions[0], max_depths[0], min_samples_splits[0])    

    # predict
    #dt_predict(predict_file,dt_model)

    #print
    #print_dt(file,criterions[0], max_depths[0], min_samples_splits[0])    


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
