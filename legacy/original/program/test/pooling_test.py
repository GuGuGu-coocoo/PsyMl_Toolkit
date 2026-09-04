import torch
import torch.nn as nn

# 假设有一批文本序列，每个序列的长度不等
sequences = [
    [1, 2, 3, 4, 5],
    [1, 2, 3],
    [1, 2, 3, 4, 5, 6, 7],
    [2,2,2,2,2,2],
]

# 使用嵌入层将每个单词表示为固定长度的向量
embedding = nn.Embedding(8, 16)  # 假设有8个单词，每个单词嵌入为16维
embedded_sequences = [embedding(torch.tensor(seq)) for seq in sequences]

# 使用LSTM处理不等长序列
lstm = nn.LSTM(input_size=16, hidden_size=8, num_layers=1, batch_first=True, bidirectional=True)

# 将嵌入的序列通过LSTM
packed_sequences = nn.utils.rnn.pack_sequence(embedded_sequences, enforce_sorted=False)  # 包装为可变长度序列
packed_output, _ = lstm(packed_sequences)

# 解包输出
output, _ = nn.utils.rnn.pad_packed_sequence(packed_output, batch_first=True)

# output 中的每个序列已经通过LSTM生成固定长度的表示
print(output)
