# -*- coding: utf-8 -*-
'''
@File    :   predict.py
@Author  :   GuGuGu?coocoo! 
@Time    :   2023/08/13 09:50:36 UTC+08:00
@E-mail  :   maintainer@example.invalid
'''
import torch
import pandas as pd
import jieba

from collections import Counter
from torch.utils.data import Dataset, DataLoader
from torch.nn.utils.rnn import pad_sequence



def build_vocab_from_xlsx(vocab_path):
    vocab_df = pd.read_excel(vocab_path, engine='openpyxl')
    word_to_idx = {row['词语']: row['索引'] for _, row in vocab_df.iterrows()}
    return word_to_idx

def rnn_predict(vocab_path, predict_path, model_path):
    # 加载整个模型与权重
    loaded_model = torch.load(model_path)
    loaded_model.eval()  # 设置模型为评估模式

    # 读取数据
    data = pd.read_excel(predict_path)
    features_num = int(data.shape[1] - 1)
    texts = data.iloc[:, :features_num].astype(str).values.tolist()
    
    # 读取词汇表
    word_to_idx = build_vocab_from_xlsx(vocab_path)
    
    # 使用jieba进行分词和编码特征值
    encoded_texts = []
    for texts_row in texts:
        words = []
        for text in texts_row:
            words.extend(jieba.lcut(text))
        encoded_text = [word_to_idx.get(word, 0) for word in words]
        encoded_texts.append(encoded_text)

    # 自定义数据集类
    class TextDataset(Dataset):
        def __init__(self, texts):
            self.texts = texts
        
        def __len__(self):
            return len(self.texts)
        
        def __getitem__(self, idx):
            text = self.texts[idx]
            return text

    # 创建数据加载器
    dataset = TextDataset(encoded_texts)
    batch_size = 32

    def collate_fn(batch):
        texts = batch
        texts = [torch.tensor(text) for text in texts]
        padded_texts = pad_sequence(texts, batch_first=True, padding_value=0)
        return padded_texts

    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True, collate_fn=collate_fn)
    predictions = []

    with torch.no_grad():
        for batch_texts in dataloader:
            # 使用模型进行预测
            batch_texts = batch_texts
            outputs = loaded_model(batch_texts)
            predicted_labels = torch.argmax(outputs, dim=1)
            
            predictions.extend(predicted_labels.tolist())

    print(predictions)
    # 打印预测结果
    for i, prediction in enumerate(predictions):
        print(f"Sample {i+1}: Predicted Label: {prediction}")

    # 保存到Excel    
    df = pd.read_excel(predict_path)
    predictions = pd.Series(predictions, name='label')    
    df = pd.concat([df, predictions], axis=1)
    with pd.ExcelWriter(predict_path, mode='a', engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='rnn_pred', index=False)
