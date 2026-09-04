# -*- coding: utf-8 -*-
'''
@File    :   RNN_pytorch.py
@Author  :   GuGuGu?coocoo! 
@Time    :   2023/07/08 14:40:19 UTC+08:00
@E-mail  :   maintainer@example.invalid
'''
import torch
import os
import torch.nn as nn
import torch.optim as optim
import pandas as pd
import jieba

from collections import Counter
from torch.utils.data import Dataset, DataLoader
from torch.nn.utils.rnn import pad_sequence
import matplotlib.pyplot as plt
from sklearn.metrics import accuracy_score,classification_report,precision_recall_fscore_support
from sklearn.model_selection import train_test_split

# 定义RNN模型
class RNNClassifier(nn.Module):
    def __init__(self, input_size, L1, L2, hidden_size, output_size):
        super(RNNClassifier, self).__init__()
        self.hidden_size = hidden_size
        self.L1=L1
        self.L2=L2
        self.embedding = nn.Embedding(input_size, hidden_size)
        self.rnn1 = nn.RNN(hidden_size, L1, batch_first=True) 
        self.rnn2 = nn.RNN(L1, L2, batch_first=True)  
        self.fc = nn.Linear(L2, output_size)  

    
    def forward(self, x):
        embedded = self.embedding(x)
        output1, _ = self.rnn1(embedded)
        output2, _ = self.rnn2(output1)
        output = self.fc(output2[:, -1, :])
        return output
import os
import pandas as pd
from collections import Counter
import jieba

def save_vocabulary(path):
    '''
    保存词汇表为Excel文件
    '''
    path = path
    file_name = os.path.splitext(os.path.basename(path))[0]
    current_directory = os.getcwd()
    target_directory = os.path.join(current_directory, 'results')
    
    if not os.path.exists(target_directory):
        os.makedirs(target_directory)
    
    file_path = os.path.join(target_directory, '{}_vocab.xlsx'.format(file_name))
    
    # 读取数据
    data = pd.read_excel(path)
    features_num = int(data.shape[1] - 1)
    texts = data.iloc[:, :features_num].astype(str).values.tolist()

    # 使用jieba进行分词
    jieba_texts = []
    for texts_row in texts:
        words = []
        for text in texts_row:
            words.extend(jieba.lcut(text))
        jieba_texts.append(words)

    # 构建词汇表
    word_counts = Counter()
    for text in jieba_texts:
        word_counts.update(text)
    vocab = sorted(word_counts, key=word_counts.get, reverse=True)
    word_to_idx = {word: idx + 1 for idx, word in enumerate(vocab)}

    # 创建DataFrame并保存为Excel文件
    vocab_df = pd.DataFrame({'词语': list(word_to_idx.keys()), '索引': list(word_to_idx.values())})
    vocab_df.to_excel(file_path, index=False)

    print(f"词汇表已保存到文件: {file_path}")

def build_vocab_from_xlsx(vocab_path):
    vocab_df = pd.read_excel(vocab_path, engine='openpyxl')
    word_to_idx = {row['词语']: row['索引'] for _, row in vocab_df.iterrows()}
    return word_to_idx

def rnn(path,vocab_path, batch_size = 32, test_size = 0.2, hidden_size = 100, L1=40, L2=30, num_epochs = 20, lr=0.001, plt_status = False):
    path = path
    vocab_path = vocab_path
    batch_size = batch_size
    test_size = test_size
    hidden_size = hidden_size
    L1=L1
    L2=L2
    num_epochs = num_epochs
    lr=lr
    plt_status = plt_status
    # 读取词汇表
    word_to_idx = build_vocab_from_xlsx(vocab_path)

    # 读取数据
    data = pd.read_excel(path)
    features_num = int(data.shape[1] - 1)
    texts = data.iloc[:, :features_num].astype(str).values.tolist()
    labels = data.iloc[:, features_num].values.tolist()
    file_name = os.path.splitext(os.path.basename(path))[0]
    current_directory = os.getcwd()
    target_directory = os.path.join(current_directory, 'saved_models')

    if not os.path.exists(target_directory):
        os.makedirs(target_directory)

    file_path = os.path.join(target_directory, '{}.pth'.format(file_name))

    # 使用jieba进行分词和编码特征值
    encoded_texts = []
    for texts_row in texts:
        words = []
        for text in texts_row:
            words.extend(jieba.lcut(text))
        encoded_text = [word_to_idx.get(word, 0) for word in words]
        encoded_texts.append(encoded_text)

    # 编码标签
    encoded_labels = torch.tensor(labels)

    # 自定义数据集类
    class TextDataset(Dataset):
        def __init__(self, texts, labels):
            self.texts = texts
            self.labels = labels
        
        def __len__(self):
            return len(self.texts)
        
        def __getitem__(self, idx):
            text = self.texts[idx]
            label = self.labels[idx]
            return text, label


    def collate_fn(batch):
        texts, labels = zip(*batch)
        texts = [torch.tensor(text) for text in texts]
        padded_texts = pad_sequence(texts, batch_first=True, padding_value=0)
        return padded_texts, torch.tensor(labels)


    # 数据集分割，按照设定的测试集比例分割数据

    train_texts, test_texts, train_labels, test_labels = train_test_split(encoded_texts, encoded_labels, test_size=test_size, random_state=42)

    # 构建训练集和测试集的数据加载器
    train_dataset = TextDataset(train_texts, train_labels)
    test_dataset = TextDataset(test_texts, test_labels)
    train_dataloader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, collate_fn=collate_fn)
    test_dataloader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, collate_fn=collate_fn)

    # 创建模型实例
    input_size = len(word_to_idx) + 1

    output_size = len(set(labels))
    model = RNNClassifier(input_size, hidden_size, L1, L2, output_size)

    # 定义损失函数和优化器
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)

    # 训练模型

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model.to(device)

    # 定义空列表用于记录损失和正确率
    train_losses = []
    train_accs = []
    print('RNN_pytorch','\nFileName:',file_name,'\nRunning the model with parameters:',
    '\nbatch_size:',batch_size,
    '\ntest_size:',test_size,
    '\nhidden_size:',hidden_size,
    '\nL1:',L1,
    '\nL2:',L2,
    '\nnum_epochs:', num_epochs,
    '\nlr:',lr,
    '\nplt_status:' ,plt_status,)
    for epoch in range(num_epochs):
        total_loss = 0.0
        total_correct = 0
        total_samples = 0
        for texts, labels in train_dataloader:
            texts = texts.to(device)
            labels = labels.to(device)
            
            optimizer.zero_grad()
            outputs = model(texts)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            _, predicted = torch.max(outputs, 1)
            total_loss += loss.item() * labels.size(0)
            total_correct += (predicted == labels).sum().item()
            total_samples += labels.size(0)
        
        epoch_loss = total_loss / total_samples
        epoch_acc = total_correct / total_samples
        train_losses.append(epoch_loss)
        train_accs.append(epoch_acc)
        
        print(f'Epoch [{epoch+1}/{num_epochs}], Loss: {epoch_loss:.4f}, Accuracy: {epoch_acc:.4f}')

    # 在训练集上进行评估
    model.eval()
    train_predictions = []
    with torch.no_grad():
        for texts, labels in train_dataloader:
            texts = texts.to(device)
            labels = labels.to(device)
            
            outputs = model(texts)
            _, predicted = torch.max(outputs, 1)
            
            train_predictions.extend(predicted.cpu().numpy())
            
    # 输出训练集的分类报告
    report = classification_report(train_labels.numpy(), train_predictions)
    print("{}-Train Classification Report:".format(file_name))
    print(report)

    # 在测试集上进行评估
    model.eval()
    test_predictions = []
    with torch.no_grad():
        for texts, labels in test_dataloader:
            texts = texts.to(device)
            labels = labels.to(device)
            
            outputs = model(texts)
            _, predicted = torch.max(outputs, 1)
            
            test_predictions.extend(predicted.cpu().numpy())

    # 输出测试集的分类报告
    test_report = classification_report(test_labels.numpy(), test_predictions)
    print("{}-Test Classification Report:".format(file_name))
    print(test_report)


    train_accuracy = accuracy_score(train_labels.numpy(), train_predictions)
    train_precision, train_recall, train_f1_score, train_support = precision_recall_fscore_support(train_labels.numpy(), train_predictions,average='weighted')
    train_support = len(train_labels.numpy())
    
    test_accuracy = accuracy_score(test_labels.numpy(), test_predictions)
    test_precision, test_recall, test_f1_score, test_support = precision_recall_fscore_support(test_labels.numpy(), test_predictions,average='weighted')
    test_support = len(test_labels.numpy())
    rnn_result_dict = {'batch_size':[batch_size],
                       'test_size':[test_size],
                       'hidden_size':[hidden_size],
                       'L1':[L1],
                       'L2':[L2],
                       'num_epochs':[num_epochs],
                       'lr':[lr],
                       'plt_status':[plt_status],
                       'TrainAccuracy': [train_accuracy],
                       'TrainPrecision': [train_precision],
                       'TrainRecall': [train_recall],
                       'TrainF1Score': [train_f1_score],
                       'TrainSupport': [train_support],
                       'TestAccuracy': [test_accuracy],
                       'TestPrecision': [test_precision],
                       'TestRecall': [test_recall],
                       'TestF1Score': [test_f1_score],
                       'TestSupport': [test_support],
                       }
    rnn_result = pd.DataFrame(rnn_result_dict)
    if plt_status :

        # 绘制损失和正确率曲线
        plt.figure(figsize=(10, 5))
        plt.subplot(1, 2, 1)
        plt.plot(range(1, num_epochs + 1), train_losses, label='Training Loss')
        plt.xlabel('Epoch')
        plt.ylabel('Loss')
        plt.title('Training Loss')

        plt.subplot(1, 2, 2)
        plt.plot(range(1, num_epochs + 1), train_accs, label='Training Accuracy')
        plt.xlabel('Epoch')
        plt.ylabel('Accuracy')
        plt.title('Training Accuracy')

        plt.tight_layout()
        plt.show()
    # 保存模型
    file_name = os.path.splitext(os.path.basename(path))[0]
    current_directory = os.getcwd()
    target_directory = os.path.join(current_directory, 'saved_models')
    if not os.path.exists(target_directory):
        os.makedirs(target_directory)
    file_path = os.path.join(target_directory, '{}-{}-{}-{}-{}-{}-{}-{}.pth'.format(file_name,batch_size,test_size,hidden_size,L1,L2,num_epochs,lr))
    torch.save(model, file_path)
    print(f"模型已保存到文件: {'{}-{}-{}-{}-{}-{}-{}-{}.pth'.format(file_name,batch_size,test_size,hidden_size,L1,L2,num_epochs,lr)}")
    
    return rnn_result


def save_rnn(path, vocab_path, batch_size=32, test_size=0.2, hidden_size=100, L1=40, L2=30, num_epochs=20, lr=0.001, plt_status=False):
    path = path
    vocab_path = vocab_path
    batch_size = batch_size
    test_size = test_size
    hidden_size = hidden_size
    L1=L1
    L2=L2
    num_epochs = num_epochs
    lr=lr
    plt_status = plt_status
    # 读取词汇表
    word_to_idx = build_vocab_from_xlsx(vocab_path)

    # 读取数据
    data = pd.read_excel(path)
    features_num = int(data.shape[1] - 1)
    texts = data.iloc[:, :features_num].astype(str).values.tolist()
    labels = data.iloc[:, features_num].values.tolist()
    file_name = os.path.splitext(os.path.basename(path))[0]
    current_directory = os.getcwd()
    target_directory = os.path.join(current_directory, 'saved_models')

    if not os.path.exists(target_directory):
        os.makedirs(target_directory)

    file_path = os.path.join(target_directory, '{}.pth'.format(file_name))

    # 使用jieba进行分词和编码特征值
    encoded_texts = []
    for texts_row in texts:
        words = []
        for text in texts_row:
            words.extend(jieba.lcut(text))
        encoded_text = [word_to_idx.get(word, 0) for word in words]
        encoded_texts.append(encoded_text)

    # 编码标签
    encoded_labels = torch.tensor(labels)

    # 自定义数据集类
    class TextDataset(Dataset):
        def __init__(self, texts, labels):
            self.texts = texts
            self.labels = labels
        
        def __len__(self):
            return len(self.texts)
        
        def __getitem__(self, idx):
            text = self.texts[idx]
            label = self.labels[idx]
            return text, label


    def collate_fn(batch):
        texts, labels = zip(*batch)
        texts = [torch.tensor(text) for text in texts]
        padded_texts = pad_sequence(texts, batch_first=True, padding_value=0)
        return padded_texts, torch.tensor(labels)

    # 数据集分割，按照设定的测试集比例分割数据

    train_texts, test_texts, train_labels, test_labels = train_test_split(encoded_texts, encoded_labels, test_size=test_size, random_state=42)

    # 构建训练集和测试集的数据加载器
    train_dataset = TextDataset(train_texts, train_labels)
    test_dataset = TextDataset(test_texts, test_labels)
    train_dataloader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, collate_fn=collate_fn)
    test_dataloader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, collate_fn=collate_fn)

    # 创建模型实例
    input_size = len(word_to_idx) + 1

    output_size = len(set(labels))
    model = RNNClassifier(input_size, hidden_size, L1, L2, output_size)

    # 定义损失函数和优化器
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)

    # 训练模型

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model.to(device)


    # 定义空列表用于记录损失和正确率
    train_losses = []
    train_accs = []
    print('RNN_pytorch','\nFileName:',file_name,'\nRunning the model with parameters:',
    '\nbatch_size:',batch_size,
    '\ntest_size:',test_size,
    '\nhidden_size:',hidden_size,
    '\nL1:',L1,
    '\nL2:',L2,
    '\nnum_epochs:', num_epochs,
    '\nlr:',lr,
    '\nplt_status:' ,plt_status,)
    for epoch in range(num_epochs):
        total_loss = 0.0
        total_correct = 0
        total_samples = 0
        for texts, labels in train_dataloader:
            texts = texts.to(device)
            labels = labels.to(device)
            
            optimizer.zero_grad()
            outputs = model(texts)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            _, predicted = torch.max(outputs, 1)
            total_loss += loss.item() * labels.size(0)
            total_correct += (predicted == labels).sum().item()
            total_samples += labels.size(0)
        
        epoch_loss = total_loss / total_samples
        epoch_acc = total_correct / total_samples
        train_losses.append(epoch_loss)
        train_accs.append(epoch_acc)
        
        print(f'Epoch [{epoch+1}/{num_epochs}], Loss: {epoch_loss:.4f}, Accuracy: {epoch_acc:.4f}')

    # 在训练集上进行评估
    model.eval()
    train_predictions = []
    with torch.no_grad():
        for texts, labels in train_dataloader:
            texts = texts.to(device)
            labels = labels.to(device)
            
            outputs = model(texts)
            _, predicted = torch.max(outputs, 1)
            
            train_predictions.extend(predicted.cpu().numpy())
            
    # 输出训练集的分类报告
    report = classification_report(train_labels.numpy(), train_predictions)
    print("{}-Train Classification Report:".format(file_name))
    print(report)

    # 在测试集上进行评估
    model.eval()
    test_predictions = []
    with torch.no_grad():
        for texts, labels in test_dataloader:
            texts = texts.to(device)
            labels = labels.to(device)
            
            outputs = model(texts)
            _, predicted = torch.max(outputs, 1)
            
            test_predictions.extend(predicted.cpu().numpy())

    # 输出测试集的分类报告
    test_report = classification_report(test_labels.numpy(), test_predictions)
    print("{}-Test Classification Report:".format(file_name))
    print(test_report)

    if plt_status :

        # 绘制损失和正确率曲线
        plt.figure(figsize=(10, 5))
        plt.subplot(1, 2, 1)
        plt.plot(range(1, num_epochs + 1), train_losses, label='Training Loss')
        plt.xlabel('Epoch')
        plt.ylabel('Loss')
        plt.title('Training Loss')

        plt.subplot(1, 2, 2)
        plt.plot(range(1, num_epochs + 1), train_accs, label='Training Accuracy')
        plt.xlabel('Epoch')
        plt.ylabel('Accuracy')
        plt.title('Training Accuracy')

        plt.tight_layout()
        plt.show()

    # 保存模型
    torch.save(model, file_path)
    print(f"模型已保存到文件: {'{}.pth'.format(file_name)}")



#print(rnn(path))
