<center>
目录
</center>
[TOC]
# 1.使用准备
## 1.1 python下载与安装
有关python下载与安装请见[Python的下载安装教程](https://blog.csdn.net/weixin_43654123/article/details/121367803)
## 1.2 编辑器下载
>编辑器可用于修改与运行代码，这里提供了PyCharm与VScode的下载与安装两种方法
### 1.2.1 PyChram下载
有关PyCharm下载与安装请见[PyCharm安装教程](https://blog.csdn.net/m0_75067840/article/details/127898332?ops_request_misc=&request_id=&biz_id=102&utm_term=pycharm%E5%AE%89%E8%A3%85%E6%95%99%E7%A8%8B&utm_medium=distribute.pc_search_result.none-task-blog-2~all~sobaiduweb~default-0-127898332.nonecase&spm=1018.2226.3001.4187)
### 1.2.2 VScode下载、安装与配置
有关VScode下载与安装请见[用VScode配置Python开发环境](https://blog.csdn.net/eastyell/article/details/104696619?ops_request_misc=%257B%2522request%255Fid%2522%253A%2522168301767016800211536258%2522%252C%2522scm%2522%253A%252220140713.130102334..%2522%257D&request_id=168301767016800211536258&biz_id=0&utm_medium=distribute.pc_search_result.none-task-blog-2~all~top_positive~default-2-104696619-null-null.142^v86^koosearch_v1,239^v2^insert_chatgpt&utm_term=vscode%E9%85%8D%E7%BD%AEpython&spm=1018.2226.3001.4187)
## 1.3第三方库的下载与安装
>在本程序中使用了numpy、pandas、sklearn库，在运行程序前请确保您已经下载并安装了所有需要的第三方库，这里提供了从终端中安装与从PyCharm中安装两种方法
### 1.3.1使用终端/terminal安装第三方库
1. 使用`win+R`打开'运行'对话框。
2. 在对话框中输入·cmd·，点击确定
3. 分行输入以下代码
>注：一次仅输入一行，运行完成后再按顺序输入下一行。
```python
pip install numpy 
pip install pandas
pip install scipy 
pip install matplotlib
pip install scikit_learn
pip install openpyxl
pip install xlsxwriter
pip install joblib
pip install torch
pip install jieba
pip install collections
```
如果发生网络错误，试试以下换源代码
```python
pip install [第三方库名] --trusted-host pypi.mirrors.ustc.edu.cn/simple  # 中科大源
pip install [第三方库名] --trusted-host pypi.tuna.tsinghua.edu.cn/simple # 清华源
```
### 1.3.2使用PyCharm安装第三方库
有关使用PyCharm下载安装第三方库请见[安装第三方库的四种方法](https://zhuanlan.zhihu.com/p/394087378)


## 1.4打开程序
打开编辑器，点击左上角的File，再点击Open，选择文件夹所在的位置，点击确定。

# 2.开始使用
>关于文件：
请将训练文件命名为英文，否则可能会出现乱码的结果文件名。
训练文件的xlsx文件格式为：第一列为OH卡图片对应的编号，第二、三、四列为OH卡的三个问题，第五列为标签列。
用于预测的xlsx文件格式请与训练文件相同。
## 2.1 修改文件路径
打开`main.py`,找到：
```python
path = r'E:\Classiffication_Models\OH_NLP\data\primary_school.xlsx'
predict_path = r'E:\Classiffication_Models\OH_NLP\data\testp.xlsx'
model_path = r'E:\Classiffication_Models\OH_NLP\saved_models\primary_school.pth' 
```
其中`path`是用于训练的文件的路径,`predict_path`是用于预测的文件路径,`model_path`是训练好的模型路径。
```python
def main():
    #loop_rnn(path, batch_sizes, test_sizes, hidden_sizes, L1s, L2s, num_epochses, lrs, plt_statuses)
    #save_rnn(path, batch_sizes[0], test_sizes[0], hidden_sizes[0], L1s[0], L2s[0], num_epochses[0], lrs[0], plt_statuses[0])
    #save_vovabulary(path)
    #rnn_predict(predict_path,model_path)
```
## 2.2 寻找合适的参数组合
将
```python
batch_sizes =[32,64]
test_sizes = [0.2,0.3]
hidden_sizes = [100,50]
L1s=[20,30]
L2s=[40,50]
num_epochses = [20,30]
lrs=[0.001,0.01]
plt_statuses = [False] # 用于绘制损失率与准确率的图像，在运行多组参数组合时最好调成False
```
中改为合适的数字。然后将
`#loop_rnn(path, batch_sizes, test_sizes, hidden_sizes, L1s, L2s, num_epochses, lrs, plt_statuses)`
前的`#`删除，点击运行，得到`{文件名}_result.xlsx`。

## 2.3 保存模型
在2.2中得到的文件中选择效果最好的参数组合，将
`#save_rnn(path, batch_sizes[0], test_sizes[0], hidden_sizes[0], L1s[0], L2s[0], num_epochses[0], lrs[0], plt_statuses[0])`
中的索引修改到最好的参数组合，删除`#`，点击运行，得到`{文件名}.pth`。
>以上面的参数列表中数为例，如果最好的组合是`batch_sizes`中的第2个，`test_sizes`中的第1个，
`hidden_sizes`中的第2个，`L1s`中的第1个，`L2s`中的第2个，`num_epochses`中的第1个，`lrs`中的第2个，`plt_statuses`中的第1个，
则就应该将`save_rnn`修改为`save_rnn(path, batch_sizes[1], test_sizes[0], hidden_sizes[1], L1s[0], L2s[1], num_epochses[0], lrs[1], plt_statuses[0])`。

>即：列表中的第`n`个参数对应的是`save_rnn`中的`[n-1]`(列表索引编号从0开始)

## 2.4 保存词汇表
将`#save_vovabulary(path)`前的`#`删除，点击运行，得到得到`{文件名}.txt`。

## 2.5 预测数据
准备号用于预测的数据文件与模型，将对应的文件路径修改。然后将
`#rnn_predict(predict_path,model_path)`
前的`#`删除，点击运行，得到的预测结果在预测文件的`rnn_pred`工作表中。
