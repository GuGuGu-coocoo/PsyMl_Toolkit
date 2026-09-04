<center>
目录
</center>
\[TOC\] \# 1.使用准备 \#\# 1.1 python下载与安装
有关python下载与安装请见[Python的下载安装教程](https://blog.csdn.net/weixin_43654123/article/details/121367803)
\#\# 1.2 编辑器下载
&gt;编辑器可用于修改与运行代码，这里提供了PyCharm与VScode的下载与安装两种方法
\#\#\# 1.2.1 PyChram下载
有关PyCharm下载与安装请见[PyCharm安装教程](https://blog.csdn.net/m0_75067840/article/details/127898332?ops_request_misc=&request_id=&biz_id=102&utm_term=pycharm%E5%AE%89%E8%A3%85%E6%95%99%E7%A8%8B&utm_medium=distribute.pc_search_result.none-task-blog-2~all~sobaiduweb~default-0-127898332.nonecase&spm=1018.2226.3001.4187)
\#\#\# 1.2.2 VScode下载、安装与配置
有关VScode下载与安装请见[用VScode配置Python开发环境](https://blog.csdn.net/eastyell/article/details/104696619?ops_request_misc=%257B%2522request%255Fid%2522%253A%2522168301767016800211536258%2522%252C%2522scm%2522%253A%252220140713.130102334..%2522%257D&request_id=168301767016800211536258&biz_id=0&utm_medium=distribute.pc_search_result.none-task-blog-2~all~top_positive~default-2-104696619-null-null.142%5Ev86%5Ekoosearch_v1,239%5Ev2%5Einsert_chatgpt&utm_term=vscode%E9%85%8D%E7%BD%AEpython&spm=1018.2226.3001.4187)
\#\# 1.3第三方库的下载与安装
&gt;在本程序中使用了numpy、pandas、sklearn库，在运行程序前请确保您已经下载并安装了所有需要的第三方库，这里提供了从终端中安装与从PyCharm中安装两种方法
\#\#\# 1.3.1使用终端/terminal安装第三方库 1.
使用`win+R`打开'运行'对话框。 2. 在对话框中输入·cmd·，点击确定 3.
分行输入以下代码 &gt;注：一次仅输入一行，运行完成后再按顺序输入下一行。

``` {.python}
pip install numpy 
pip install pandas
pip install scipy 
pip install matplotlib
pip install scikit_learn
```

如果发生网络错误，试试以下换源代码

``` {.python}
pip install [第三方库名] --trusted-host pypi.mirrors.ustc.edu.cn/simple  # 中科大源
pip install [第三方库名] --trusted-host pypi.tuna.tsinghua.edu.cn/simple # 清华源
```

### 1.3.2使用PyCharm安装第三方库

有关使用PyCharm下载安装第三方库请见[安装第三方库的四种方法](https://zhuanlan.zhihu.com/p/394087378)

1.4打开程序
-----------

打开编辑器，点击左上角的File，再点击Open，选择文件夹所在的位置，点击确定。

2.快速使用
==========

2.1数据格式
-----------

请将数据以.xlsx格式保存，包含n个特征列与1个标签列。
&gt;以下操作均使用`data`文件夹下的`subdimension-data.xlsx`文件为例，该文件共包含39列，其中第1-38列为特征，第39列为标签。

2.2更改代码
-----------

> 以下涉及到不同的算法部分操作均以`programs`文件夹下的`MLP_Classiffication_Sklearn.py`为例，各算法需要修改的部分相同，请在运行`main.py`程序前确保各个算法的程序均修改完成
> \#\#\# 2.2.1检查是否有缺失值 在`programs`文件夹下的`if_miss.py`中进行
> 1. 修改文件路径
> 将`file = 'E:\\Classiffication_Models\\real\\subdimension-data.xlsx`修改为当前`subdimension-data.xlsx`文件所在的绝对路径
> 2. 运行程序`if_miss.py` 3.
> 如果每一行最后数值均为0，则无缺失值，进入下一节。若不为零，则存在缺失值，请检查文件。

### 2.2.2修改使用的特征个数

> 在`programs`文件夹下的`f1-fn.py`与`MLP_Classiffication_Sklearn.py`中进行
> 1. 修改`feature`
> 将`feature = 40 # number of featrues`中feature的数值修改为特征的数量。这里我们将其修改为38
> 2. 运行`f1-fn.py` 得到结果：
>
> ``` {.python}
> f1 = df.iloc[:, 0].tolist()
> f2 = df.iloc[:, 1].tolist()
> f3 = df.iloc[:, 2].tolist()
> f4 = df.iloc[:, 3].tolist()
> ......
> f38 = df.iloc[:, 37].tolist()
> 'Rank1ImportanceScore':[ranks[0]],
> 'Rank2ImportanceScore':[ranks[1]],
> 'Rank3ImportanceScore':[ranks[2]],
> ......
> 'Rank38ImportanceScore':[ranks[37]],
> ```
>
> 3.  将`f1-fn.py`输出结果粘贴在`MLP_Classiffication_Sklearn.py`对应的位置
> 4.  修改`lable`
>     将`labels = df.iloc[:, 40].tolist()`中括号的数字修改为标签列数-1,这里我们将其修改为38
>     由于python中数字是从0开始计算的，因此需要减一
> 5.  修改`X` 将
>
>     ``` {.python}
>     X = np.c_[f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13,f14,f15,f16,f17,f18,f19,f20,f21,f22,f23,f24,f25,f26,f27,f28,f29,f30,f31,f32,f33,f34,f35,f36,f37,f38,f39,f40]
>     ```
>
>     删除或增加为特征的数量，这里我们将`X`中删除到只剩下`f1-38` \#\#\#
>     2.2.3修改参数 在`programs`文件夹下的`main.py`中进行
> 6.  打开`main.py`，找到：
>
``` {.python}
test_sizes = [0.2,0.3]
# MLP parameters:
hidden_layer_sizeses = [(70,35),(60,30),(50,25),(40,20),(30,15),(20,10)]# list of tulps like (10),(20),(10,20),(20,10,10)....
activations = ['tanh', 'relu', 'logistic', 'identity']# list of strs among {'tanh', 'relu', 'logistic', 'identity'}
solvers = ['lbfgs', 'adam', 'sgd']# list of strs among {'lbfgs', 'adam', 'sgd'}
alphas = [0.01,0.1,1]# list of floats in the range [0.0, inf)
max_iters = [500,700,1000,1500]# list of ints in the range [1, inf)
```

通过修改列表/list（中括号）中的字符串、元组/tuple（小括号）、整数或小数来得到不同的参数组合以得到不同的结果。

2.  修改`main()` 找到

    ``` {.python}
    def main():
    """
    loop  the models
    ## MLP:
    loop_mlp(file,hidden_layer_sizeses,activations,solvers,alphas,max_iters)
    ## SVM:
    loop_svm(file,test_sizes,kernels,Cs,gammas,decision_function_shapes,shrinkings,probabilitys)
    ## RandomForest:
    loop_rf(file,test_sizes,n_estimatorses, criterions,bootstraps, oob_scores)
    ## KNN:
    loop_knn(file,test_sizes,n_neighborses,weightses,algorithms)

    ## Stack:
    loop_stack(file,test_sizes,estimatorses,final_estimators)

    """
    #loop_mlp(file,test_sizes,hidden_layer_sizeses,activations,solvers,alphas,max_iters)
    loop_svm(file,test_sizes,kernels,Cs,gammas,decision_function_shapes,shrinkings,probabilitys)
    #loop_rf(file,test_sizes,n_estimatorses, criterions,bootstraps, oob_scores)
    #loop_knn(file,test_sizes,n_neighborses,weightses,algorithms)
    #loop_stack(file,test_sizes,estimatorses,final_estimators)
    ```

    这里可以控制运行那些算法，我们将loop\_mlp()前的`#`删除，并在loop\_svm()前加上`#`，此时运行`main.py`,则只会运行MLP算法。
    \#\#\# 2.2.4 结果查看
    由于此处我们仅运行了MLP,因此只会出现一个`mlp_result.xlsx`的文件。包含各个参数组合及运行结果。
    \#\# 2.3 堆叠法
    将四种算法全部运行完成之后，可以尝试使用堆叠法来得到更好的精度与泛化能力，选择四种算法中最好的几种参数组合，在`main.py`中修改`estimatorses`与`final_estimators`内的参数，其中`estimatorses`为基学习器的参数，`final_estimators`为元学习器的参数。 &gt;注意：对于`estimatorses`一个列表/list为一个参数，注意修改时的格式

3.代码结构
==========

> 以MLP方法为例 \#\# 3.1 `main.py`
> `main()`方法，调用`loop_models,py`中的`loop_mlp()`方法，给`loop_mlp()`传入参数`file，test_sizes,hidden_layer_sizeses,activations,solvers,alphas,max_iters`
> \#\# 3.2 `loop_models.py`
> `loop_mlp()`方法得到参数`file,test_sizes,hidden_layer_sizeses,activations,solvers,alphas,max_iters`,其中`file`不参与循环，将其余参数嵌套循环，形成多种参数组合，每一个组合调用一次`MLP_Classiffication_Sklearn.py`中的`mlp()`方法，给`mlp()`方法传入参数`file,test_size,hidden_layer_sizes,activation,solver,alpha,max_iter`，得到`mlp()`返回值`mlp_result`，将`mlp_result`存入到列表`mlp_results`中。创建了一个Excel写入器`mlp_writer`,将结果保存在`mlp_result.xlsx`中的`mlp`sheet中,遍历`mlp_results`,`mlp_writer`将`mlp_results`中的`mlp_result`保存入`mlp_result.xlsx`中。
> \#\# 3.3 `MLP_Classiffication_Sklearn.py`
> `mlp()`方法得到`file,test_size,hidden_layer_sizes,activation,solver,alpha,max_iter`参数，通过`file`读取文件，预处理数据，通过`test_size`切分训练集与测试集，通过`hidden_layer_sizes,activation,solver,alpha,max_iter`建立模型与训练模型，返回包含参数组合、测试结果、哥特征的贡献程度的`mlp_result`
