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
训练文件的xlsx文件格式为：最后一列为目标变量，其余为输入特征。

>以下操作以mlp模型为例
## 2.1 修改文件路径
打开`main.py`,找到：
```python
file = r'E:\Regression_Models\Regression_Models-v1.0.0\data\intensity.xlsx'  (Ln20)
```
将`''`中的内容改为目标文件保存位置

## 2.2 寻找合适的参数组合
将
```python
# MLP parameters:(Ln24)
hidden_layer_sizeses = [(70,35),(60,30),(50,25),(40,20),(30,15),(20,10)]                    # list of tulps like (10),(20),(10,20),(20,10,10)....
activations = ['tanh', 'relu', 'logistic', 'identity']                                      # list of strs among {'tanh', 'relu', 'logistic', 'identity'}
solvers = ['lbfgs', 'adam', 'sgd']                                                          # list of strs among {'lbfgs', 'adam', 'sgd'}
m_alphas = [0.01,0.1,1]                                                                       # list of floats in the range [0.0, inf)
max_iters = [500,700,1000,1500] 
```
中按照格式添加或删去，然后把
```python
#loop_mlp(file,test_sizes,hidden_layer_sizeses,activations,solvers,m_alphas,max_iters)(Ln87)
```
前的`#`删去，要运行哪些文件，就删去对应的`#`即可。

## 2.3 查看运行结果
在`mlp_result.xlsx`中记录了各个参数组合及其结果，其中'R,MSE,MAE'为所有样本运行的结果，'Train_'与'Test_'前缀分别是按照'test_size'将数据切分为训练集与测试集所运行产的数据。
