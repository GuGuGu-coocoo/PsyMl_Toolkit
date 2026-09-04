# -*- coding: utf-8 -*-
'''
@File    :   RNN.py
@Author  :   GuGuGu?coocoo! 
@Time    :   2023/07/08 14:40:19 UTC+08:00
for any problem,please contact maintainer@example.invalid
'''
import torch
import torch.nn as nn
import torch.optim as optim
import pandas as pd
import jieba
import json
from collections import Counter
from torch.utils.data import Dataset, DataLoader
from torch.nn.utils.rnn import pad_sequence
import matplotlib.pyplot as plt
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

# 读取数据
path = r'E:\Classiffication_Models\OH_NLP\data\中学.xlsx'
data = pd.read_excel(path)
texts = data.iloc[:, :4].astype(str).values.tolist()
labels = data.iloc[:, 4].values.tolist()

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

# 将字典保存为txt文件
output_file = '中学词汇表.txt'  
with open(output_file, 'w') as f:
    for word, idx in word_to_idx.items():
        f.write(f"{word}: {idx}\n")

print(f"词汇表已保存到文件: {output_file}")

# 编码特征值和标签
encoded_texts = [torch.tensor([word_to_idx[word] for word in text]) for text in jieba_texts]
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

# 创建数据加载器
batch_size = 32

def collate_fn(batch):
    texts, labels = zip(*batch)
    padded_texts = pad_sequence(texts, batch_first=True, padding_value=0)
    return padded_texts, torch.tensor(labels)

# 数据集分割，按照设定的测试集比例分割数据
test_size = 0.2  # 测试集占总数据的比例
train_texts, test_texts, train_labels, test_labels = train_test_split(encoded_texts, encoded_labels, test_size=test_size, random_state=42)

# 构建训练集和测试集的数据加载器
train_dataset = TextDataset(train_texts, train_labels)
test_dataset = TextDataset(test_texts, test_labels)
train_dataloader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, collate_fn=collate_fn)
test_dataloader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, collate_fn=collate_fn)

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
# 创建模型实例
input_size = len(word_to_idx) + 1
hidden_size = 100
L1=89
L2=64
output_size = len(set(labels))
model = RNNClassifier(input_size, hidden_size, L1, L2, output_size)

# 定义损失函数和优化器
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

# 训练模型
num_epochs = 20
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model.to(device)

# 定义空列表用于记录损失和正确率
train_losses = []
train_accs = []

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
print("Train Classification Report:")
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
print("Test Classification Report:")
print(test_report)

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


